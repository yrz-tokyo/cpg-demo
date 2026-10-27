#!/usr/bin/env python3
"""
統治ON: Genie Agent に instructions と例SQLを入れる。

統治前（create_agents.py）では「売上の正本はどれか」を一切教えていない。
ここで教える。Workspace instructions は Genie Agent には効かない（docs 明記）ので
Agent 側には別途入れる必要がある。

使い方
  python3 06_genie/apply_instructions.py          # 統治ON（instructions を入れる）
  python3 06_genie/apply_instructions.py --off     # 統治OFF（最小に戻す）
"""
import argparse, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude/plugins/cache/fe-vibe/fe-internal-tools/1.4.7/skills/genie-rooms/resources"))
from genie_space_builder import GenieSpaceBuilder   # noqa: E402

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
C = "rongzi_catalog_dev"
BASE = Path(__file__).resolve().parent

MINIMAL = (
    "Brickshouse Food and Beverage（ビール類・清涼飲料・健康食品を製造販売する日本の食品飲料メーカー）のデータです。"
    "会計年度は暦年（1月〜12月）。データは 2026-10-24 まで。"
)

# 統治ONで足す横断マート。create_agents.py の spec["governed"] と同じもの。
# 横断マートは「誰かが部門をまたいで意味を揃えた成果物」なので、
# 統治前の Agent には存在しない。統治の一部として配る。
GOVERNED = {
    "営業": [f"{C}.xdept_mart.mart_revenue_definitions", f"{C}.xdept_mart.mart_customer_360"],
    "財務": [f"{C}.xdept_mart.mart_revenue_definitions", f"{C}.xdept_mart.mart_customer_360"],
    "マーケ": [f"{C}.xdept_mart.mart_spend_definitions", f"{C}.xdept_mart.mart_brand_investment_return"],
    "横断": [f"{C}.xdept_mart.mart_revenue_definitions", f"{C}.xdept_mart.mart_customer_360",
             f"{C}.xdept_mart.mart_spend_definitions", f"{C}.xdept_mart.mart_brand_investment_return"],
}

# 全部門に共通で入れる4つの衝突の正本。これが統治の中身。
COMMON = f"""Brickshouse Food and Beverage（ビール類・清涼飲料・健康食品）のデータです。
会計年度は暦年（1月〜12月）。データは 2026-10-24 まで。

【衝突1: 「売上」の正本】
「Brickshouse の売上」「純売上」「計上売上」を聞かれたら、必ず
  {C}.finance_mart.finance_ar_invoice の total_net_amount
を使う。計算式は 請求総額 − 販促値引(trade_discount_amount) − 控除(deduction_amount)。

以下は total_net_amount という**同じ名前の measure を持つが売上ではない**。
「売上」を聞かれてこれらを使ってはならない。
  - {C}.sales_mart.sales_order.total_net_amount          = 受注。一部出荷・値引・控除の前。純売上より約22%大きい
  - {C}.procure_mart.procurement_purchase_order.total_net_amount = 発注（仕入）
  - {C}.finance_mart.finance_ap_invoice.total_net_amount  = 買掛請求（仕入）
  - {C}.trade_mart.trade_settlement.total_net_amount      = 販促精算（得意先への支払い）
  - {C}.trade_mart.trade_promotion_event.actual_revenue   = 販促システムの入力値。財務の純売上と一致しない

【衝突2: 「マーケ投下額」の正本】
「マーケ投下額」「広宣費」「マーケに使ったお金」を聞かれたら、必ず
  {C}.marketing_mart.marketing_campaign_performance の total_actual_spend_usd
を使う。2026年は約 $54.2M。以下は**同じ名前の measure を持つが投下額ではない**。
  - {C}.marketing_mart.marketing_consumer_insight.total_actual_spend_usd = 消費者調査の費用。投下額の約5%（約18分の1）
  - {C}.marketing_mart.marketing_media_spend.total_actual_spend_amount   = 媒体費。投下額の約70%で全部ではない
  - {C}.marketing_core.brand.annual_marketing_budget                     = 予算。実績ではない

【衝突3: 通貨（最も事故が多い）】
建値が部門で違う。
  - マーケ（marketing_core / marketing_mart）= **USD**
  - 営業・財務・販促（sales / finance / trade）= **JPY**
マーケの金額と他部門の金額は、**換算してからでないと足せない・割れない**。
換算せずに足すと150倍ずれる。ROI の分母に使うと150倍良く見える。
換算が必要な集計は {C}.xdept_mart.mart_brand_investment_return を使う。
この表は換算レートを marketing_spend_fx_rate 列、根拠を fx_basis 列に明示して持っている。
media_spend には currency_code が空の明細がある。空を JPY と見なしてはならない。

【衝突4: dollar_sales は2つある】
  - {C}.sales_core.pos_transaction.dollar_sales          = **自社**の店頭実売。**JPY**。Nielsenパネルの約15% ACV 投影値
  - {C}.marketing_core.syndicated_market_data.dollar_sales = **市場全体**の売上。**USD**。競合他社を含む
列名が完全に同じだが別物。混ぜると自社が市場規模に見える（約550倍）。
「当社の店頭での売れ行き」は pos_transaction。「市場規模」は syndicated_market_data。
自社の市場売上が必要なら market_dollar_sales_usd × dollar_share_pct ÷ 100 を使う。
pos_transaction は投影値なので、当社の売上と**絶対額で比較してはならない**。伸び率・指数で比較する。

【ROI は3つあり、分母も分子も違う】
  - ブランド単位  = {C}.xdept_mart.mart_brand_investment_return.return_on_investment ← 「マーケのROI」はこれ
  - 販促イベント単位 = {C}.trade_mart.mart_promotion_roi.roi
  - 媒体の指数     = {C}.marketing_mart.marketing_media_spend.avg_roi_index（指数。投資回収率ではない）

【横断して見るとき】
  - 「売上」の5つの数字を並べる → {C}.xdept_mart.mart_revenue_definitions
  - 「マーケに使ったお金」を並べる → {C}.xdept_mart.mart_spend_definitions
  - 得意先を軸に部門を横断     → {C}.xdept_mart.mart_customer_360

【その他の用語】
- 原価率 = 発注(procurement_purchase_order.total_net_amount) ÷ 純売上。2026年は約47%。
  mart_revenue_definitions で計算する場合は purchase_order_net_amount ÷ revenue_net_amount。
  sales_order_net_amount は**受注**であって発注ではない。原価率の分子に使ってはならない
- レベニューリーケージ = ar_invoice の trade_discount_amount + deduction_amount。未回収売掛(open_amount)とは別物
- 配下率 = distribution_point.acv_weighted_distribution_pct（Nielsen 由来）
- チャネル = account.channel の SM / CVS / DgS / 卸 / EC の5区分
- sales_core.order は受注ヘッダ粒度で sku_id を持たない。商品軸は pos_transaction / distribution_point / promotion_line を使う
- ブランド軸は marketing_core.brand の brand_id が hub キー。sku / promotion_line / fund / distribution_point がこれを参照する

【「係争中」「照合不一致」の判定列（取り違えが多い）】
- 係争中の**売掛請求** = {C}.finance_core.ar_invoice の dispute_status = 'open'
  （3値 none / open / resolved。resolved は決着済みなので係争中に含めない）
- 三者照合が**合っていない買掛請求** = {C}.finance_core.ap_invoice の match_status <> 'matched'
  （price_variance と qty_variance の2種）
- 係争中の**控除** = {C}.trade_core.deduction の deduction_status = 'disputed'
  （dispute_flag も同じ行で true。どちらで数えても同じ）
- 得意先名は「<社名> <地域>支社」の形。社名だけでは一意にならないので、
  部分一致で聞かれたら複数支社が該当することを明示する
"""

DEPT_EXTRA = {
    "営業": "この Agent は営業部門向け（販促を含む）。着地見込みには受注(sales_order)を使ってよいが、"
            "それを「会社の売上」と呼んではならない。純売上を聞かれたら財務の正本を参照する。"
            "販促については promotion_event.actual_revenue は入力値であり会社の売上ではない。"
            "settlement と deduction は売上のマイナス要素であり売上そのものではない。二重計上に注意。",
    "財務": "この Agent は財務部門向け。純売上の正本を持つのはこの部門。"
            "段ごとの照合（請求総額→値引・控除→純売上→入金）は "
            "finance_mart.mart_revenue_reconciliation を使う。"
            "ただしこの表の粒度は 月 × 得意先 × 請求ステータス であり、月の全社の数字ではない。"
            "全社の月次推移を聞かれたら得意先と請求ステータスを SUM して GROUP BY month_start だけにする。"
            "得意先別を聞かれていないのに得意先の行をそのまま返してはならない。"
            "入金(payment_amount)・残高(open_receivable_amount)はこの表にしかない。"
            "入金を含まない月次の売上だけなら xdept_mart.mart_revenue_definitions でもよい。",
    "マーケ": "この Agent はマーケティング部門向け。この部門の金額はすべて USD 建て。"
             "営業・財務・販促の JPY 建ての金額と足すときは必ず換算し、レートを答えの中に書く。"
             "「マーケ投下額」は campaign、調査費は consumer_insight、媒体費は media_spend で、3つは別物。"
             "市場規模は syndicated_market_data（競合込み）、自社の店頭実売は pos_transaction（JPY）。",
    "横断": "この Agent は部門横断。「売上」を聞かれたら mart_revenue_definitions で5つの数字を並べ、"
            "どれが正本かを明示して答える。違いの理由（一部出荷・値引・控除）も説明する。"
            "通貨の違う金額を足す依頼が来たら、足さずに理由を説明し、換算した上での数字を示す。",
}

EXAMPLES = [
    ("Brickshouse の2026年の売上はいくらですか？",
     f"SELECT MEASURE(total_net_amount) AS revenue_net\nFROM {C}.finance_mart.finance_ar_invoice",
     "「売上」は純売上。finance_ar_invoice が正本。受注(sales_order)や発注(purchase_order)を使ってはならない。"),
    ("営業が言う売上と財務が言う売上が違うのはなぜですか？",
     f"""SELECT date_format(month_start,'yyyy-MM') AS month,
       sales_order_net_amount, invoiced_gross_amount,
       trade_discount_amount, deduction_amount, revenue_net_amount,
       revenue_to_order_ratio
FROM {C}.xdept_mart.mart_revenue_definitions ORDER BY month_start""",
     "受注 → 一部出荷 → 請求総額 → 販促値引・控除 → 純売上 の連鎖。どちらも間違いではない。"),
    ("2026年のマーケティング投下額はいくらですか？",
     f"SELECT MEASURE(total_actual_spend_usd) AS campaign_spend_usd\nFROM {C}.marketing_mart.marketing_campaign_performance",
     "「マーケ投下額」は campaign。単位は USD。consumer_insight は調査費で投下額ではない（約18分の1）。"),
    ("マーケ投下額と販促費を合わせた総投資額はいくらですか？",
     f"""SELECT SUM(campaign_actual_jpy)   AS marketing_jpy,
       SUM(trade_funding_jpy)    AS trade_jpy,
       SUM(total_investment_jpy) AS total_jpy,
       MAX(marketing_spend_fx_rate) AS fx_rate, MAX(fx_basis) AS fx_basis
FROM {C}.xdept_mart.mart_brand_investment_return""",
     "マーケは USD、販促は JPY。換算してから足す。レートと根拠を答えに必ず書く。"),
]


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


def sort_id_lists(space: dict) -> None:
    """id を持つリストを全部 id 順に並べる。

    GenieSpaceBuilder.to_dict() は data_sources.tables だけソートするが、API は
    instructions.example_question_sqls など**すべての id 付きリスト**が id 順であることを要求する
    （Invalid export proto: ... must be sorted by id）。ビルダー側の漏れをここで埋める。
    """
    paths = [("config", "sample_questions"),
             ("instructions", "text_instructions"),
             ("instructions", "example_question_sqls"),
             ("instructions", "sql_functions"),
             ("instructions", "join_specs"),
             ("instructions", "sql_snippets", "filters"),
             ("instructions", "sql_snippets", "expressions"),
             ("instructions", "sql_snippets", "measures"),
             ("benchmarks", "questions")]
    for path in paths:
        node = space
        for key in path[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
            if node is None:
                break
        if not isinstance(node, dict):
            continue
        lst = node.get(path[-1])
        if isinstance(lst, list):
            lst.sort(key=lambda x: x.get("id", "") if isinstance(x, dict) else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", action="store_true", help="最小 instructions に戻す（統治OFF）")
    a = ap.parse_args()
    ids = json.loads((BASE / "space_ids.json").read_text())

    for dept, sid in ids.items():
        # serialized_space は ?include_serialized_space=true を付けないと返らない。
        # 付けると etag も返るので、更新の衝突検知にそのまま使える。
        cur = api("get", f"/api/2.0/genie/spaces/{sid}?include_serialized_space=true")
        raw = cur.get("serialized_space")
        if not raw:
            print(f"  ERR {dept}: serialized_space が取れない {str(cur)[:150]}")
            continue
        space = json.loads(raw) if isinstance(raw, str) else raw
        b = GenieSpaceBuilder(title=cur.get("title", dept),
                              description=cur.get("description", ""),
                              warehouse_id=WAREHOUSE, space=space)
        gov = GOVERNED.get(dept, [])
        tables = b._space.setdefault("data_sources", {}).setdefault("tables", [])
        have = {x.get("identifier") for x in tables if isinstance(x, dict)}
        if a.off:
            b.set_instructions(MINIMAL)
            # 例SQLも外す
            b._space.setdefault("instructions", {})["example_question_sqls"] = []
            # 横断マートを外す（統治前の状態には存在しないものとして扱う）
            kept = [x for x in tables if x.get("identifier") not in set(gov)]
            b._space["data_sources"]["tables"] = kept
            mode = f"統治OFF（最小 / 横断マート {len(tables)-len(kept)} 本を外した）"
        else:
            b.set_instructions(COMMON + "\n" + DEPT_EXTRA[dept])
            b._space.setdefault("instructions", {})["example_question_sqls"] = []
            for title, sql, desc in EXAMPLES:
                b.add_example_sql(title, sql, desc)
            added = 0
            for ident in gov:
                if ident not in have:
                    b.add_table(ident)
                    added += 1
            mode = f"統治ON（4つの衝突の正本＋例SQL{len(EXAMPLES)}件 / 横断マート {added} 本を追加）"
        sort_id_lists(b._space)
        payload = {"title": cur.get("title", dept),
                   "description": cur.get("description", ""),
                   "warehouse_id": WAREHOUSE,
                   "serialized_space": b.to_json()}
        # etag は付けない。GET で取った etag でも
        # 「Space configuration has been modified since this export was taken」で弾かれる
        # （ビルダーが serialized_space を正規化するため）。
        # 単独で更新するツールなので衝突検知は不要。API のメッセージ自身が omit を案内している。
        r = api("patch", f"/api/2.0/genie/spaces/{sid}", payload)
        if "_error" in r:
            print(f"  ERR {dept:6s} {r['_error'][:220]}")
        else:
            print(f"  OK  {dept:6s} {mode}")


if __name__ == "__main__":
    main()
