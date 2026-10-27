#!/usr/bin/env python3
"""
Brickshouse 評価ハーネス — 統治の効果を数字で測る。

各質問について
  1. truth_sql を SQL warehouse で実行して**正解**を得る
  2. Genie Agent に同じ質問を自然言語で投げ、回答・生成SQL・参照テーブルを得る
  3. 採点
       value_ok  : 返ってきた数値が正解と許容誤差内か
       source_ok : 正本（authoritative）のテーブル/ビューを参照したか
       trap_hit  : 罠（同名だが別物の measure）を参照してしまったか
  4. テキストのレポートを出す（FE Bar のエビデンスはテキストで読めることが要件）

使い方
  python3 run_eval.py --space <genie_space_id> --label before
  python3 run_eval.py --space <genie_space_id> --label after
"""
import argparse, json, re, subprocess, sys, time
from pathlib import Path

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"
BASE = Path(__file__).resolve().parent
TOLERANCE = 0.02           # 2% 以内なら一致とみなす


def api(method, path, payload=None):
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"_error": (r.stderr or r.stdout).strip()[:400]}
    try:
        return json.loads(r.stdout or "{}")
    except Exception:
        return {"_raw": r.stdout[:400]}


# ------------------------------------------------------------------ 正解
def sql_scalar_rows(stmt):
    res = api("post", "/api/2.0/sql/statements", {
        "statement": stmt, "warehouse_id": WAREHOUSE, "catalog": CATALOG,
        "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"})
    sid = res.get("statement_id")
    state = (res.get("status") or {}).get("state")
    while state in ("PENDING", "RUNNING"):
        time.sleep(3)
        res = api("get", f"/api/2.0/sql/statements/{sid}")
        state = (res.get("status") or {}).get("state")
    if state != "SUCCEEDED":
        return None, ((res.get("status") or {}).get("error") or {}).get("message", "")[:200]
    man = res.get("manifest") or {}
    cols = [c["name"] for c in (man.get("schema") or {}).get("columns", [])]
    data = ((res.get("result") or {}).get("data_array")) or []
    return {"columns": cols, "rows": data}, None


def numbers_of(result):
    """結果セットから数値だけを拾う（比較用）。"""
    out = []
    if not result:
        return out
    for row in result["rows"]:
        for v in row:
            if v is None:
                continue
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                pass
    return out


# ------------------------------------------------------------------ Genie
def genie_ask(space_id, question, timeout_s=240):
    r = api("post", f"/api/2.0/genie/spaces/{space_id}/start-conversation",
            {"content": question})
    if "_error" in r:
        return {"error": r["_error"]}
    cid = (r.get("conversation") or {}).get("id") or r.get("conversation_id")
    mid = (r.get("message") or {}).get("id") or r.get("message_id")
    if not (cid and mid):
        return {"error": f"unexpected start-conversation shape: {str(r)[:200]}"}
    deadline = time.time() + timeout_s
    msg = {}
    while time.time() < deadline:
        msg = api("get", f"/api/2.0/genie/spaces/{space_id}/conversations/{cid}/messages/{mid}")
        st = msg.get("status")
        if st in ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"):
            break
        time.sleep(5)
    atts = msg.get("attachments") or []
    text = next((a["text"]["content"] for a in atts if a.get("text")), "")
    gen_sql, statement_id, desc = "", None, ""
    for a in atts:
        q = a.get("query")
        if q:
            gen_sql = q.get("query") or ""
            statement_id = q.get("statement_id")
            desc = q.get("description") or ""
            break
    result = None
    if statement_id:
        rr = api("get", f"/api/2.0/sql/statements/{statement_id}")
        man = rr.get("manifest") or {}
        result = {"columns": [c["name"] for c in (man.get("schema") or {}).get("columns", [])],
                  "rows": ((rr.get("result") or {}).get("data_array")) or []}
    return {"status": msg.get("status"), "text": text, "sql": gen_sql,
            "description": desc, "result": result,
            "conversation_id": cid, "message_id": mid}


# ------------------------------------------------------------------ 採点
TBL = re.compile(r"`?(\w+)`?\.`?(\w+)`?\.`?(\w+)`?")


def referenced_objects(sql):
    """生成SQL から catalog.schema.object を拾う。"""
    out = set()
    for m in TBL.finditer(sql or ""):
        c, s, t = m.groups()
        if c == CATALOG:
            out.add(f"{s}.{t}")
    return out


# boolean の採点に使う3つの語彙。
#
# 当初は「否定表現があれば いいえ と答えた」とだけ見ていたが、実測で両方向に外れた。
#   偽陽性: 「判定する質問には該当しません」「判定不可」= **拒否**なのに
#           「該当しません」が否定語に当たって正解扱いになった
#   偽陰性: 「含まれていません」「当社売上ではなく」= 正しい否定なのに辞書に無かった
# 拒否は「答えていない」であって「いいえ」ではない。先に拒否を判定して切り分ける。
REFUSAL_WORDS = ("判定できません", "判定不可", "判断できません", "該当しません",
                 "どちらとも言えません", "とも言えません", "特定できて", "確認できていません",
                 "わかりません", "分かりません", "回答できません", "直接判定")
NEGATIVE_WORDS = ("含まれていません", "含まれません", "含まれない", "含めません", "含みません",
                  "入っていません", "入っていない", "いいえ",
                  "ではありません", "ではない", "ではなく", "でなく",
                  "違います", "異なります", "別のもの", "別物", "別指標",
                  "足せません", "使えません", "no,", "not ")
AFFIRM_WORDS = ("含まれています", "含まれます", "含んでいます", "含みます", "はい、", "はい。",
                "入っています", "そのとおり", "その通り")


def primary_numbers(result, top=1):
    """結果セットの最初の数値列を上から順に拾う（ランキングの比較用）。"""
    if not result or not result["rows"]:
        return []
    ncols = len(result["rows"][0])
    for ci in range(ncols):
        vals = []
        for row in result["rows"]:
            try:
                vals.append(float(row[ci]))
            except (TypeError, ValueError):
                vals = []
                break
        if vals and not all(float(v).is_integer() and abs(v) < 100000 for v in vals):
            return vals[:top] if top else vals
    # 整数しかない場合は最後の数値列を使う
    for ci in reversed(range(ncols)):
        vals = []
        for row in result["rows"]:
            try:
                vals.append(float(row[ci]))
            except (TypeError, ValueError):
                vals = []
                break
        if vals:
            return vals[:top] if top else vals
    return []


def numeric_columns(result):
    """結果セットの数値列を、列ごとに（値の並びを保って）全部返す。

    どれが「主の数値列」かを当てようとすると外す。TR-F-03 で Genie は正しい
    net_amount を返していたのに、採点器が gross_amount の列を主と判定して
    偽陰性になった。当てずに全部見るほうが堅い。
    """
    if not result or not result.get("rows"):
        return []
    ncols = len(result["rows"][0])
    cols = []
    for ci in range(ncols):
        vals = []
        for row in result["rows"]:
            try:
                vals.append(float(row[ci]))
            except (TypeError, ValueError):
                vals = []
                break
        if vals:
            cols.append(vals)
    return cols


def close(a, b):
    """許容誤差内で一致するか。

    率を聞く質問では Genie が「46.99%」、正解SQLが「0.4652」と、**同じ量を違う単位**で返す。
    実測で FI-M-02（原価率）と SA-M-04（計上率）がこれで偽陰性になった。
    どちらかが [0,1] に収まる率らしい値のときだけ 100倍 / 100分の1 も試す。
    無条件に試すと桁違いの別物を拾うので、率らしい場合に限る。
    """
    if _near(a, b):
        return True
    ratio_like = (0 < abs(a) <= 1.5) or (0 < abs(b) <= 1.5)
    pct_like = (1.5 < abs(a) <= 100.0) or (1.5 < abs(b) <= 100.0)
    if ratio_like and pct_like:
        return _near(a, b / 100.0) or _near(a * 100.0, b)
    return False


def _near(a, b):
    if a == b:
        return True
    denom = max(abs(a), abs(b))
    return denom > 0 and abs(a - b) / denom <= TOLERANCE


def score(q, truth, got):
    """
    質問の形に応じて採点する。
      scalar  … 正解の主要な数値が Genie の数値の中にあるか（厳しめ・意味がある）
      ranking … 正解の1位の数値が Genie の1位（または上位）と一致するか
      boolean … 回答文の否定表現で判定
    任意の数値同士を総当たりで照合すると、一覧系の質問で偽陰性が出るため分けた。
    """
    refs = referenced_objects(got.get("sql", ""))
    auth = q["authoritative"]
    auth_objs = {m.group(0) for m in re.finditer(r"\b(\w+_(?:core|mart))\.(\w+)", auth)}
    source_ok = bool(auth_objs & refs) if auth_objs else None
    trap_objs = set()
    for t in q.get("trap", []):
        trap_objs |= {m.group(0) for m in re.finditer(r"\b(\w+_(?:core|mart))\.(\w+)", t)}
    trap_hit = bool(trap_objs & refs)

    st = q.get("score_type", "scalar")
    tn = numbers_of(truth)
    gn = numbers_of(got.get("result"))
    value_ok, detail = None, ""

    if st == "explanation":
        # 概念ごとに「言い方の候補」を持たせる。単語を1つに決め打ちすると、
        # 内容が合っているのに表現違いで落ちる（XD-02 が実際にそうなっていた）。
        text = (got.get("text") or "") + " " + (got.get("description") or "")
        groups = q.get("expect_concepts") or [[k] for k in q.get("expect_keywords", [])]
        hit = [g for g in groups if any(w in text for w in g)]
        need = q.get("min_keywords", max(1, len(groups) - 1))
        value_ok = len(hit) >= need
        detail = f"概念 {len(hit)}/{len(groups)} 一致（必要 {need}）: {[g[0] for g in hit]}"
    elif st == "boolean":
        text = ((got.get("text") or "") + " " + (got.get("description") or ""))
        low = text.lower()
        refused = any(w in text for w in REFUSAL_WORDS)
        negated = any((w in text) or (w in low) for w in NEGATIVE_WORDS)
        affirmed = any(w in text for w in AFFIRM_WORDS)
        expect = q.get("expect_answer")
        expect = expect if isinstance(expect, bool) else False
        # 拒否が優勢なのは「方向が立たないとき」。質問文の選択肢を両方引用すると
        # 否定も肯定も当たるので、その場合も拒否として扱う。
        if refused and not (negated ^ affirmed):
            # 答えを出さずに断った。統治前には正しい振る舞いでもあるので不正解とは別に数える。
            value_ok = False
            detail = "拒否（はい/いいえを答えていない）"
        elif expect:
            value_ok = affirmed and not negated
            detail = f"肯定={affirmed} 否定={negated} / 期待=はい"
        else:
            value_ok = negated and not affirmed
            detail = f"否定={negated} 肯定={affirmed} / 期待=いいえ"
    elif st == "ranking":
        t1 = primary_numbers(truth, top=1)
        cols = numeric_columns(got.get("result"))
        if t1 and cols:
            target = t1[0]
            # ID 列との偶然の一致を避けるため、桁が近い列だけを見る
            def comparable(vals):
                m = max(abs(v) for v in vals) or 1.0
                return abs(target) == 0 or (abs(target) / m <= 1000 and m / max(abs(target), 1e-9) <= 1000)
            hit_col = None
            for ci, vals in enumerate(cols):
                if not comparable(vals):
                    continue
                if any(close(v, target) for v in vals[:5]):
                    hit_col = ci
                    break
            value_ok = hit_col is not None
            shown = cols[hit_col][:5] if hit_col is not None else (cols[0][:5] if cols else [])
            detail = (f"正解1位={target:,.0f} / 一致した列={hit_col} "
                      f"/ その列の上位={[round(x) for x in shown]} / 数値列数={len(cols)}")
        elif t1:
            value_ok = False
            detail = "Genie が数値を返さなかった"
    else:  # scalar
        if tn and gn:
            # 正解の数値（上位3つ）が、それぞれ Genie の数値のどれかと一致するか
            hits = sum(1 for t in tn[:3] if any(close(g, t) for g in gn[:40]))
            value_ok = hits >= min(len(tn[:3]), 1)
            detail = f"正解={[round(x,4) for x in tn[:3]]} / 一致={hits}件"
        elif tn:
            value_ok = False
            detail = "Genie が数値を返さなかった"

    # 聞き返し: 数値を返さず、質問で終わっている。統治前は「正しい振る舞い」でもあるので
    # 不正解とは別枠で数える（統治後に直答へ変わることが改善の証拠になる）。
    gtext = (got.get("text") or "").strip()
    clarified = bool(gtext) and not gn and (
        gtext.endswith(("？", "?")) or
        any(w in gtext for w in ("特定できて", "どちら", "どの粒度", "instead of",
                                 "Would you like", "指定してください", "教えてください")) or
        any(w in gtext for w in REFUSAL_WORDS))

    return {"refs": sorted(refs), "source_ok": source_ok, "trap_hit": trap_hit,
            "value_ok": value_ok, "clarified": clarified, "score_type": st, "detail": detail,
            "truth_numbers": [round(x, 4) for x in tn[:6]],
            "genie_numbers": [round(x, 4) for x in gn[:6]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", default=None, help="1スペースで全問やる場合")
    ap.add_argument("--route", action="store_true",
                    help="部門ごとに space_ids.json のスペースへ振り分ける")
    # before / after 以外も受ける。同じ状態を2回測ってばらつきを出すため（after2 など）。
    # 「1回測っただけの差」は誤差と区別できないので、再現測定を取れるようにしておく。
    ap.add_argument("--label", required=True,
                    help="before / after / after2 など。evidence と 04_eval に label 付きで出る")
    ap.add_argument("--only", default=None, help="質問ID の接頭辞でフィルタ")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    bank = json.loads((BASE / "question_bank.json").read_text())
    qs = bank["questions"]
    if a.only:
        qs = [q for q in qs if q["id"].startswith(a.only)]
    spaces = {}
    if a.route:
        spaces = json.loads((BASE.parent / "06_genie" / "space_ids.json").read_text())
    elif not a.space:
        sys.exit("--space か --route のどちらかが必要")

    def space_for(q):
        return spaces.get(q["dept"], spaces.get("横断")) if a.route else a.space

    lines, rows = [], []
    lines.append(f"# Brickshouse 評価ハーネス — {a.label}")
    lines.append(f"routing={'部門別' if a.route else a.space} / 質問数={len(qs)} / 許容誤差={TOLERANCE:.0%}")
    if a.route:
        lines.append(f"spaces={json.dumps(spaces, ensure_ascii=False)}")
    lines.append("")
    # 1問でも例外が出たら評価全体を落とす作りだった（実測: 33問目で Genie がエラーを返し、
    # エラー用の戻り値に score_type が無くて KeyError で全滅、40分が無駄になった）。
    # 1問の失敗はその問だけを未測定にして続行する。
    def blank(truth, why):
        return {"refs": [], "source_ok": None, "trap_hit": None, "value_ok": None,
                "clarified": None, "score_type": "unknown", "detail": f"未測定: {why}",
                "truth_numbers": numbers_of(truth)[:6], "genie_numbers": []}

    out_json = BASE / f"eval_{a.label}.json"
    # IP ACL で弾かれ始めたら即座に止める。
    # 実測: 測定中に VPN が切れて生IPになり、26問が
    # 「Source IP address ... is blocked by Databricks IP ACL」で未測定になった。
    # 気づかずに走り切ると 39% という嘘の数字が出て、ばらつきと見分けがつかない。
    # 測定を汚すより、止めて原因を直してから測り直すほうが安い。
    FATAL = ("blocked by Databricks IP ACL", "is not allowed to access",
             "PERMISSION_DENIED", "invalid access token", "Token expired")
    fatal_hits = 0
    for i, q in enumerate(qs, 1):
        truth, terr = sql_scalar_rows(q["truth_sql"])
        sp = space_for(q)
        try:
            got = genie_ask(sp, q["q"])
        except Exception as e:                       # noqa: BLE001
            got = {"error": f"{type(e).__name__}: {e}"}
        if "error" in got:
            msg = str(got["error"])
            if any(w in msg for w in FATAL):
                fatal_hits += 1
                if fatal_hits >= 2:
                    print(f"\n!! 測定を中止します（{i-1}/{len(qs)} 問まで測定済み）")
                    print(f"!! 原因: {msg[:200]}")
                    print("!! VPN / 認証を直してから測り直してください。"
                          "途中までの結果は eval_*.json に残っていますが、"
                          "**この run は集計に使わないこと**。")
                    sys.exit(2)
            sc = blank(truth, msg[:120])
        else:
            try:
                sc = score(q, truth, got)
            except Exception as e:                   # noqa: BLE001
                sc = blank(truth, f"採点で例外 {type(e).__name__}: {e}")
        rows.append({"id": q["id"], "dept": q["dept"], "persona": q["persona"],
                     "conflict": q["conflict"], "space": sp, **sc,
                     # 画面(09_app)が before/after を並べるのに必要。prose を再パースしないため。
                     "question": q["q"], "authoritative": q["authoritative"],
                     "genie_text": got.get("text") or "", "genie_sql": got.get("sql") or "",
                     "genie_status": got.get("status"), "error": got.get("error")})
        lines.append(f"## [{q['id']}] {q['dept']} / {q['persona']} / conflict={q['conflict']} / space={sp}")
        lines.append(f"Q: {q['q']}")
        lines.append(f"正本: {q['authoritative']}")
        if q.get("trap"):
            lines.append(f"罠: {' | '.join(q['trap'])}")
        lines.append(f"truth_sql: {q['truth_sql'][:300]}")
        if terr:
            lines.append(f"!! 正解SQLエラー: {terr}")
        lines.append(f"正解の数値: {sc['truth_numbers']}")
        lines.append(f"Genie status: {got.get('status')}  error={got.get('error')}")
        lines.append(f"Genie 回答: {(got.get('text') or '')[:400]}")
        lines.append(f"Genie 生成SQL: {(got.get('sql') or '')[:500]}")
        lines.append(f"参照オブジェクト: {sc['refs']}")
        lines.append(f"Genie の数値: {sc['genie_numbers']}")
        lines.append(f"採点方式: {sc.get('score_type','unknown')}  {sc.get('detail','')}")
        lines.append(f"判定 -> value_ok={sc['value_ok']}  source_ok={sc['source_ok']}  "
                     f"trap_hit={sc['trap_hit']}  聞き返し={sc.get('clarified')}")
        lines.append("")
        print(f"[{i:2d}/{len(qs)}] {q['id']:8s} value={sc['value_ok']} source={sc['source_ok']} "
              f"trap={sc['trap_hit']}" + ("  (聞き返し)" if sc.get("clarified") else ""))
        # 途中で落ちても測った分は残す
        out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def rate(pred, subset=None):
        s = [r for r in rows if (subset is None or subset(r))]
        n = len(s)
        k = sum(1 for r in s if pred(r))
        return f"{k}/{n}" + (f" ({k/n:.0%})" if n else "")

    summary = [
        "# 集計",
        f"全体 value_ok   : {rate(lambda r: r['value_ok'] is True)}",
        f"全体 source_ok  : {rate(lambda r: r['source_ok'] is True)}",
        f"罠を踏んだ       : {rate(lambda r: r['trap_hit'] is True)}",
        f"聞き返しで終了   : {rate(lambda r: r.get('clarified') is True)}",
        f"直答して不正解   : {rate(lambda r: r['value_ok'] is False and not r.get('clarified'))}",
        "",
        f"衝突あり value_ok : {rate(lambda r: r['value_ok'] is True, lambda r: r['conflict'])}",
        f"衝突あり source_ok: {rate(lambda r: r['source_ok'] is True, lambda r: r['conflict'])}",
        f"衝突あり 罠を踏んだ: {rate(lambda r: r['trap_hit'] is True, lambda r: r['conflict'])}",
        "",
        f"衝突なし value_ok : {rate(lambda r: r['value_ok'] is True, lambda r: not r['conflict'])}",
        "",
    ]
    for d in ("営業", "財務", "マーケ", "横断"):
        summary.append(f"{d:4s} value_ok: {rate(lambda r: r['value_ok'] is True, lambda r, d=d: r['dept'] == d)}")
    summary.append("")
    for t in ("scalar", "ranking", "boolean", "explanation"):
        summary.append(f"{t:8s} value_ok: {rate(lambda r: r['value_ok'] is True, lambda r, t=t: r.get('score_type') == t)}")

    out = a.out or str(BASE.parent / "evidence" / f"eval_{a.label}.txt")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(summary + [""] + lines))
    out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print("\n".join(summary))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
