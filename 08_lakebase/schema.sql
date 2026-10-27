-- Brickshouse / Lakebase (Postgres) — 統治ループの「人間側の状態」を持つ唯一の場所
--
-- なぜ Delta テーブルではないのか（この問いに答えられることが設計の要点）
--   ① 行単位の更新が頻発する     … 1つの衝突の状態が 検出→調査中→正本決定→公開 と何度も書き換わる
--   ② 同時更新がある             … 営業部長と財務部長が別々の行に自分の主張を書く
--   ③ read-modify-write がある   … 検出バッチが毎回「却下済み」を読んで、次の提案から除外する
--   ④ アプリがサブ秒で読み書きする … レビュー画面の操作がそのまま永続化される
--   バッチ分析用のテーブルでは①〜④が成立しない。
--
-- ループ: App が判断を集める → Lakebase が持つ → ML が学ぶ → 提案が良くなる → また App
--         どれか1つ抜くとループが壊れる。これが Lakebase / App / ML が必要な理由。

CREATE SCHEMA IF NOT EXISTS semantics;
CREATE SCHEMA IF NOT EXISTS app;

-- ---------------------------------------------------------------- 検出された衝突
CREATE TABLE IF NOT EXISTS semantics.conflict (
    conflict_id        BIGSERIAL PRIMARY KEY,
    term               TEXT        NOT NULL,            -- 業務語（例: 売上）
    term_normalized    TEXT        NOT NULL,            -- 突合用に正規化した語
    measure_name       TEXT,                            -- 衝突している measure 名（例: total_net_amount）
    status             TEXT        NOT NULL DEFAULT 'detected'
                       CHECK (status IN ('detected','investigating','resolved','rejected')),
    authoritative_object TEXT,                          -- 人が選んだ正本（catalog.schema.object）
    detector_version   TEXT        NOT NULL,
    ml_score           NUMERIC(6,4),                    -- 本物の衝突である確度（serving endpoint の出力）
    ml_model_version   TEXT,
    evidence           JSONB       NOT NULL DEFAULT '{}'::jsonb,  -- 値の重なり率・カーディナリティ比など
    detected_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (term_normalized, measure_name, detector_version)
);
CREATE INDEX IF NOT EXISTS ix_conflict_status    ON semantics.conflict (status, ml_score DESC);
CREATE INDEX IF NOT EXISTS ix_conflict_term      ON semantics.conflict (term_normalized);

-- 衝突に参加している各オブジェクト（1衝突に N 件）
CREATE TABLE IF NOT EXISTS semantics.conflict_candidate (
    candidate_id    BIGSERIAL PRIMARY KEY,
    conflict_id     BIGINT      NOT NULL REFERENCES semantics.conflict(conflict_id) ON DELETE CASCADE,
    object_name     TEXT        NOT NULL,               -- catalog.schema.object
    object_type     TEXT        NOT NULL,               -- METRIC_VIEW / MATERIALIZED_VIEW / TABLE / DASHBOARD
    department      TEXT,                               -- brickshouse_department の値
    measure_expr    TEXT,                               -- 実際の計算式
    role            TEXT        NOT NULL DEFAULT 'candidate'
                    CHECK (role IN ('candidate','authoritative','not_this_concept','variant')),
    observed_value  NUMERIC(20,2),                      -- その定義で出した実測値（画面で並べて見せる）
    note            TEXT,
    UNIQUE (conflict_id, object_name)
);

-- ---------------------------------------------------------------- 人間の判断
CREATE TABLE IF NOT EXISTS semantics.decision (
    decision_id      BIGSERIAL PRIMARY KEY,
    conflict_id      BIGINT      NOT NULL REFERENCES semantics.conflict(conflict_id) ON DELETE CASCADE,
    decision         TEXT        NOT NULL CHECK (decision IN ('approve','reject','defer')),
    authoritative_object TEXT,                          -- approve のとき必須
    rationale        TEXT,
    decided_by       TEXT        NOT NULL,
    decided_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_decision_conflict ON semantics.decision (conflict_id, decided_at DESC);

-- 却下された衝突。検出バッチが毎回これを読んで、同じものを再提案しない。
-- ここが read-modify-write で、フィードバックループの折り返し点。
CREATE TABLE IF NOT EXISTS semantics.rejected_pair (
    term_normalized TEXT NOT NULL,
    measure_name    TEXT NOT NULL,
    object_a        TEXT NOT NULL,
    object_b        TEXT NOT NULL,
    rejected_by     TEXT NOT NULL,
    rejected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    reason          TEXT,
    PRIMARY KEY (term_normalized, measure_name, object_a, object_b)
);

-- ---------------------------------------------------------------- Page ドラフト
CREATE TABLE IF NOT EXISTS semantics.page_draft (
    page_draft_id  BIGSERIAL PRIMARY KEY,
    conflict_id    BIGINT      REFERENCES semantics.conflict(conflict_id) ON DELETE SET NULL,
    title          TEXT        NOT NULL,                -- 「売上（Brickshouse 全社定義）」
    domain_tag     TEXT        NOT NULL DEFAULT 'Brickshouse Food and Beverage',
    synonyms       TEXT[]      NOT NULL DEFAULT '{}',
    definition_md  TEXT        NOT NULL,
    business_use_md TEXT,
    related_assets TEXT[]      NOT NULL DEFAULT '{}',
    source_assets  TEXT[]      NOT NULL DEFAULT '{}',
    status         TEXT        NOT NULL DEFAULT 'draft'
                   CHECK (status IN ('draft','approved','published','rejected')),
    generated_by   TEXT,                                -- 生成した LLM
    uc_page_id     TEXT,                                -- 公開後に UC の Page id を書き戻す
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_page_draft_status ON semantics.page_draft (status, updated_at DESC);

-- ---------------------------------------------------------------- 認定台帳
CREATE TABLE IF NOT EXISTS semantics.certification (
    object_name   TEXT        PRIMARY KEY,
    cert_status   TEXT        NOT NULL CHECK (cert_status IN ('certified','deprecated','none')),
    conflict_id   BIGINT      REFERENCES semantics.conflict(conflict_id) ON DELETE SET NULL,
    applied_by    TEXT        NOT NULL,
    applied_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    uc_synced_at  TIMESTAMPTZ                            -- UC へ反映した時刻
);

-- ---------------------------------------------------------------- ML の学習ラベル
-- decision から機械的に導出する。衝突候補ランキングモデルの教師データ。
CREATE OR REPLACE VIEW semantics.ml_training_label AS
SELECT c.conflict_id,
       c.term_normalized,
       c.measure_name,
       c.evidence,
       CASE WHEN d.decision = 'approve' THEN 1 ELSE 0 END AS label_is_real_conflict,
       d.decided_at
FROM semantics.conflict c
JOIN (SELECT DISTINCT ON (conflict_id) conflict_id, decision, decided_at
      FROM semantics.decision ORDER BY conflict_id, decided_at DESC) d
  ON c.conflict_id = d.conflict_id
WHERE d.decision IN ('approve', 'reject');

-- ---------------------------------------------------------------- アプリ側の状態
CREATE TABLE IF NOT EXISTS app.annotation (
    annotation_id BIGSERIAL PRIMARY KEY,
    object_name   TEXT        NOT NULL,
    persona       TEXT        NOT NULL,                 -- 営業部長 / 営業現場 / 財務部長 ...
    body          TEXT        NOT NULL,
    created_by    TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_annotation_object ON app.annotation (object_name, created_at DESC);

CREATE TABLE IF NOT EXISTS app.bookmark (
    persona     TEXT NOT NULL,
    object_name TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (persona, object_name)
);

CREATE TABLE IF NOT EXISTS app.audit_log (
    audit_id   BIGSERIAL PRIMARY KEY,
    actor      TEXT        NOT NULL,
    action     TEXT        NOT NULL,
    target     TEXT,
    payload    JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_created ON app.audit_log (created_at DESC);

-- updated_at の自動更新
CREATE OR REPLACE FUNCTION semantics.touch_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tg_conflict_touch ON semantics.conflict;
CREATE TRIGGER tg_conflict_touch BEFORE UPDATE ON semantics.conflict
  FOR EACH ROW EXECUTE FUNCTION semantics.touch_updated_at();

DROP TRIGGER IF EXISTS tg_page_draft_touch ON semantics.page_draft;
CREATE TRIGGER tg_page_draft_touch BEFORE UPDATE ON semantics.page_draft
  FOR EACH ROW EXECUTE FUNCTION semantics.touch_updated_at();
