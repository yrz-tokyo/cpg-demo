#!/usr/bin/env python3
"""
業務ロジックの上書き — 「売上」の定義差を業務的に正しい連鎖として作る。

    受注      sales_core.order.total_net_amount      = 総額 - 値引
    請求      finance_core.ar_invoice.gross_amount   = 受注純額 × 出荷率（一部出荷あり）
    純売上    finance_core.ar_invoice.net_amount     = 請求総額 - 販促値引 - 控除
    店頭実売  sales_core.pos_transaction.dollar_sales= sell-out（在庫差があるので上記と一致しない）
    販促精算  trade_core.settlement.net_amount       = 得意先への支払い（売上ではない）
    仕入      ap_invoice / purchase_order .net_amount= 仕入（売上ではない）

ECM の metric view はこのうち5つに `total_net_amount` という同名の measure を持つ。
どれを選ぶかで答えが最大2倍変わる。これが FE Bar の課題そのもの。

マーケ（フェーズ2）で衝突が3組増える。いずれも ECM に素で存在する:

    投下額    marketing.campaign.actual_spend_usd          = キャンペーン投下（USD）
    調査費    marketing.consumer_insight.actual_spend_usd  = 消費者調査の費用（USD・投下ではない）
              -> ECM の metric view は両方に total_actual_spend_usd を持つ。約20倍違う。

    通貨      マーケは USD 建て、営業・財務・販促は JPY 建て
              -> 足すと150倍ずれる。ROI の分母に使うと150倍良く見える。

    市場実売  marketing.syndicated_market_data.dollar_sales = 市場全体（競合込み・USD）
    自社実売  sales.pos_transaction.dollar_sales            = 自社の店頭実売（パネル投影・JPY）
              -> 完全同名。混ぜると自社が市場規模に見える。
"""
from datetime import date, timedelta

TAX = 0.10
USD = 150.0       # デモ内の固定レート。マーケが USD 建てであることを意味のある差にするため
SEASON = {"ビール類": {1:.75,2:.72,3:.85,4:.95,5:1.10,6:1.35,7:1.55,8:1.50,9:1.10,10:.95,11:.90,12:1.25},
          "清涼飲料": {1:.70,2:.68,3:.82,4:.95,5:1.15,6:1.40,7:1.60,8:1.55,9:1.10,10:.88,11:.75,12:.78},
          "健康食品": {1:1.45,2:1.15,3:1.00,4:.95,5:.90,6:.95,7:1.00,8:.95,9:1.30,10:1.20,11:1.05,12:1.00}}
_S = {}

# syndicated 市場データの構造。乱数だけで作るとブランド間の ROI 差が意味を持たないので、
# カテゴリごとの市場規模とブランドごとのシェアを固定の構造として置く。
# これで「市場は大きいがシェアが薄い」「市場は小さいが強い」という会話が成立する。
CAT_MARKET_USD = {"ビール類": 2_400_000, "清涼飲料": 1_760_000, "健康食品": 610_000}  # 1行(ブランド×地域×週)あたりの平均
BRAND_SHARE = {                     # 金額シェア(%)。カテゴリ内の自社の立ち位置
    "ブリックス ラガー": 18.0, "ブリックス プレミアム": 11.0, "ブリックス THE生": 8.0, "ブリックス 零": 5.0,
    "ブリックス 緑茶": 9.0, "ブリックス 麦茶": 7.0, "ブリックス 天然水": 5.0,
    "ブリックス レモン": 6.0, "ブリックス 微炭酸": 8.0,
    "ブリックス 乳酸菌ガード": 24.0, "ブリックス コラーゲン": 17.0, "ブリックス 血糖ケア": 13.0,
}


def st(row, key, value):
    """その列が実在するときだけ代入する（ECM の実列名に追従するためのガード）。"""
    if key in row:
        row[key] = value


def remember(g, table, rows):
    if table == "marketing_core.brand":
        _S["brand"] = {r["brand_id"]: (r["brand_name"], r["brand_category"]) for r in rows}
    elif table == "marketing_core.campaign":
        _S["campaign"] = {r["campaign_id"]: (r["brand_id"], r["start_date"], r["end_date"],
                                             r["actual_spend_usd"], r["campaign_type"]) for r in rows}
    elif table == "master_core.sku":
        _S["sku"] = {r["sku_id"]: (r["product_name"], r["product_line"], _S["price"][r["sku_id"]])
                     for r in rows}
    elif table == "sales_core.account":
        _S["account"] = {r["account_id"]: (r["account_name"], r["channel"], r["shipping_state"])
                         for r in rows}
    elif table == "sales_core.order":
        _S["order"] = {r["order_id"]: (r["total_net_amount"], r["placed_timestamp"][:10], r["account_id"])
                       for r in rows}


# ------------------------------------------------------------------ マスタ
def sku(g, row, i):
    from generate import BRANDS, PACKS
    brand, cat, pmul = BRANDS[i % len(BRANDS)]
    pack, qmul = PACKS[(i // len(BRANDS)) % len(PACKS)]
    price = round(118 * pmul * qmul, 2)
    _S.setdefault("price", {})[row["sku_id"]] = price
    # brand_id は FK のランダム値ではなく brand テーブルと一致させる。
    # product_name のブランドと brand.brand_name が食い違うと、マーケ×営業の join が嘘になる。
    st(row, "brand_id", (i % len(BRANDS)) + 1)
    st(row, "sku_code", f"BR-{1000+i:04d}")
    st(row, "product_name", f"{brand} {pack}")
    st(row, "product_line", cat)
    st(row, "flavor_variety", brand.replace("ブリックス ", ""))
    st(row, "product_description", f"{brand}（{cat}） {pack}")
    st(row, "pack_size", pack)
    st(row, "packaging_type", "缶" if "缶" in pack else ("PET" if "PET" in pack else "個装"))
    st(row, "unit_of_measure", "CS" if "ケース" in pack or "パック" in pack else "EA")
    st(row, "product_status", g.rnd.choices(["active", "active", "active", "discontinued"])[0])
    st(row, "plm_stage", "commercialized")
    st(row, "abv", round(g.rnd.uniform(4.5, 6.0), 1) if cat == "ビール類" else 0.0)
    st(row, "calories_per_serving", {"ビール類": 140, "清涼飲料": 35, "健康食品": 18}[cat])
    st(row, "shelf_life_days", {"ビール類": 270, "清涼飲料": 365, "健康食品": 730}[cat])
    st(row, "launch_date", date(2019 + (i % 7), 1 + (i % 12), 1 + (i % 27)))
    st(row, "gtin", f"45{g.rnd.randint(10**10, 10**11-1)}")
    st(row, "ean", f"45{g.rnd.randint(10**10, 10**11-1)}")
    st(row, "discontinuation_date", "")


def category(g, row, i):
    cats = ["ビール類", "清涼飲料", "健康食品"]
    sub = ["主力", "プレミアム", "ノンアル", "無糖茶", "水", "炭酸", "果汁", "機能性表示"]
    c = cats[i % 3]
    st(row, "category_name", c if i < 3 else f"{c} / {sub[i % len(sub)]}")
    st(row, "category_code", f"CAT-{i+1:03d}")
    st(row, "category_description", f"{c} カテゴリ（{sub[i % len(sub)]}）")
    st(row, "category_type", "major" if i < 3 else "sub")
    st(row, "hierarchy_level", 1 if i < 3 else 2)
    st(row, "category_status", "active")
    st(row, "parent_category_id", "" if i < 3 else (i % 3) + 1)
    st(row, "is_perishable", c != "健康食品")


def account(g, row, i):
    from generate import ACCOUNTS, REGIONS
    name, ch = ACCOUNTS[i % len(ACCOUNTS)]
    region = REGIONS[(i // len(ACCOUNTS)) % len(REGIONS)]
    st(row, "account_name", f"{name} {region}支社")
    st(row, "channel", ch)
    st(row, "shipping_state", region)
    st(row, "account_number", f"ACC-{10000+i:05d}")
    st(row, "account_status", "active")
    st(row, "account_type", {"SM": "retail", "CVS": "retail", "DgS": "retail",
                             "卸": "distributor", "EC": "ecommerce"}[ch])
    st(row, "market_segment", ch)
    st(row, "key_account_flag", i % len(ACCOUNTS) < 4)
    st(row, "annual_revenue_band", g.rnd.choice(["<1B", "1-5B", "5-20B", ">20B"]))
    st(row, "first_order_date", date(2017 + (i % 8), 1 + (i % 12), 1 + (i % 27)))
    st(row, "last_order_date", g.d())
    st(row, "nps_score", g.rnd.randint(-20, 70))
    st(row, "shipping_country", "JP")
    st(row, "shipping_city", region)
    st(row, "primary_contact_name", "担当 窓口")


def rep(g, row, i):
    from generate import REGIONS
    sei = ["佐藤","鈴木","高橋","田中","伊藤","渡辺","山本","中村","小林","加藤","吉田","山田"]
    mei = ["健","翔","結衣","大輔","彩","涼","拓真","美咲","悠","航"]
    st(row, "full_name", f"{sei[i%len(sei)]} {mei[(i//len(sei))%len(mei)]}")
    st(row, "external_rep_code", f"REP-{100+i:04d}")
    st(row, "sales_region", REGIONS[i % len(REGIONS)])
    st(row, "sales_district", f"{REGIONS[i % len(REGIONS)]}第{(i % 3)+1}")
    st(row, "quota_annual_revenue", round(g.rnd.uniform(3.0e8, 1.4e9), 2))
    st(row, "quota_annual_cases", g.rnd.randint(40000, 260000))
    st(row, "employment_status", "active")
    st(row, "rep_type", g.rnd.choice(["direct", "broker", "key_account"]))
    st(row, "sales_channel", g.rnd.choice(["SM", "CVS", "DgS", "卸", "EC"]))
    st(row, "termination_date", "")


def supplier(g, row, i):
    from generate import SUPPLIERS, REGIONS
    nm = SUPPLIERS[i % len(SUPPLIERS)]
    full = nm if i < len(SUPPLIERS) else f"{nm}{(i//len(SUPPLIERS))+1}"
    st(row, "legal_name", f"{full}株式会社")
    st(row, "trade_name", full)
    st(row, "vendor_code", f"SUP-{2000+i:04d}")
    st(row, "region", REGIONS[i % len(REGIONS)])
    st(row, "country_code", "JP")
    st(row, "lead_time_days", g.rnd.choice([7, 14, 21, 30, 45, 60]))
    st(row, "single_source_flag", g.rnd.random() < 0.22)
    st(row, "strategic_supplier_flag", i % 7 == 0)
    st(row, "risk_rating", g.rnd.choices(["low", "medium", "high"], weights=[60, 30, 10])[0])
    st(row, "payment_currency_code", "JPY")
    st(row, "onboarding_status", "active")
    st(row, "deactivation_date", "")
    st(row, "primary_contact_name", "購買窓口")


def territory(g, row, i):
    from generate import REGIONS
    r = REGIONS[i % len(REGIONS)]
    st(row, "territory_name", f"{r}エリア" + ("" if i < len(REGIONS) else "2"))
    st(row, "territory_code", f"TER-{i+1:03d}")
    st(row, "region", r)
    st(row, "district", f"{r}第{(i % 3)+1}")
    st(row, "country", "JP")
    st(row, "quota_amount", round(g.rnd.uniform(8.0e8, 4.0e9), 2))
    st(row, "sales_target_amount", round(g.rnd.uniform(8.0e8, 4.0e9), 2))
    st(row, "territory_status", "active")
    st(row, "effective_end_date", "")


# ------------------------------------------------- 受注（売上の定義①）
def order(g, row, i):
    sku_tbl = _S.get("sku", {})
    sid = g.rnd.choice(list(sku_tbl)) if sku_tbl else 1
    _, cat, price = sku_tbl.get(sid, ("", "ビール類", 118.0))
    d = g.d(date(2026, 1, 1), date(2026, 10, 24))
    cases = max(1, int(g.rnd.gauss(220, 90) * 50 * SEASON[cat][d.month]))
    gross = round(cases * price * g.rnd.uniform(0.95, 1.05), 2)
    disc = round(gross * g.rnd.uniform(0.02, 0.12), 2)
    net = round(gross - disc, 2)
    acc = _S.get("account", {}).get(row.get("account_id"))
    st(row, "placed_timestamp", g.ts(d))
    st(row, "created_timestamp", row.get("placed_timestamp"))
    st(row, "requested_delivery_date", d + timedelta(days=g.rnd.randint(2, 7)))
    st(row, "promised_delivery_date", row.get("requested_delivery_date"))
    st(row, "actual_delivery_date", row.get("requested_delivery_date"))
    st(row, "total_gross_amount", gross)
    st(row, "total_discount_amount", disc)
    st(row, "total_net_amount", net)
    st(row, "total_tax_amount", round(net * TAX, 2))
    st(row, "total_quantity", cases)
    st(row, "total_weight_kg", round(cases * 9.2, 1))
    st(row, "total_volume_cu_m", round(cases * 0.021, 3))
    st(row, "order_number", f"SO-2026-{100000+i:06d}")
    st(row, "order_status", g.rnd.choices(
        ["delivered", "invoiced", "shipped", "open", "cancelled"], weights=[55, 25, 10, 8, 2])[0])
    st(row, "order_type", g.rnd.choices(["standard", "rush", "promotional", "consignment"],
                                        weights=[70, 10, 17, 3])[0])
    st(row, "order_source", g.rnd.choices(["EDI", "portal", "rep", "phone"], weights=[55, 20, 20, 5])[0])
    st(row, "channel", acc[1] if acc else "SM")
    st(row, "sales_region", acc[2] if acc else "関東")
    st(row, "currency_code", "JPY")
    st(row, "is_backorder", g.rnd.random() < 0.06)
    st(row, "is_split_order", g.rnd.random() < 0.09)
    st(row, "trade_allowance_flag", g.rnd.random() < 0.34)


# ------------------------------- 売掛請求（売上の定義②＝純売上。受注とズレる）
def ar_invoice(g, row, i):
    o = _S.get("order", {}).get(row.get("order_id"))
    onet, base = None, None
    if o:
        onet, odate, oacct = o
        if oacct not in ("", None):
            st(row, "account_id", oacct)
        try:
            base = date.fromisoformat(odate)      # 上流の汚れ（空の日付）で失敗しうる
        except (ValueError, TypeError):
            base = None
    try:
        onet = abs(float(onet))
    except (TypeError, ValueError):
        onet = None
    if onet is None:
        onet = g.money(50000, 2000000)
    if base is None:
        base = g.d()
    ship = g.rnd.choices([1.0, g.rnd.uniform(0.80, 0.98), g.rnd.uniform(0.45, 0.70)],
                         weights=[62, 30, 8])[0]
    gross = round(onet * ship, 2)
    trade_disc = round(gross * g.rnd.uniform(0.01, 0.06), 2)
    deduct = round(gross * g.rnd.uniform(0.00, 0.04), 2)
    net = round(gross - trade_disc - deduct, 2)
    inv_d = base + timedelta(days=g.rnd.randint(1, 20))
    paid = g.rnd.random() < 0.82
    pay = net if paid else round(net * g.rnd.uniform(0, 0.6), 2)
    acc = _S.get("account", {}).get(row.get("account_id"))
    st(row, "invoice_date", inv_d)
    st(row, "due_date", inv_d + timedelta(days=g.rnd.choice([30, 45, 60])))
    st(row, "revenue_recognition_date", inv_d)
    st(row, "payment_date", inv_d + timedelta(days=g.rnd.randint(20, 75)) if paid else "")
    st(row, "gross_amount", gross)
    st(row, "trade_discount_amount", trade_disc)
    st(row, "deduction_amount", deduct)
    st(row, "short_payment_amount", round(gross * g.rnd.uniform(0, 0.01), 2))
    st(row, "early_payment_discount_amount", round(net * 0.01, 2))
    st(row, "net_amount", net)
    st(row, "tax_amount", round(net * TAX, 2))
    st(row, "payment_amount", pay)
    st(row, "open_amount", round(net - pay, 2))
    st(row, "invoice_status", "paid" if paid else g.rnd.choice(["open", "partially_paid", "overdue"]))
    st(row, "invoice_type", g.rnd.choices(["standard", "credit_memo", "debit_memo"],
                                          weights=[92, 6, 2])[0])
    st(row, "billing_document_number", f"AR-2026-{200000+i:06d}")
    st(row, "fiscal_period", f"2026-{inv_d.month:02d}")
    st(row, "channel_type", acc[1] if acc else "SM")
    st(row, "currency_code", "JPY")
    st(row, "dispute_status", g.rnd.choices(["none", "open", "resolved"], weights=[88, 7, 5])[0])


def sales_invoice(g, row, i):
    sub = round(g.rnd.uniform(5.0e4, 2.2e6), 2)
    td = round(sub * g.rnd.uniform(0.01, 0.06), 2)
    tot = round(sub - td, 2)
    d = g.d()
    st(row, "subtotal_amount", sub)
    st(row, "trade_discount_amount", td)
    st(row, "total_amount", tot)
    st(row, "tax_amount", round(tot * TAX, 2))
    st(row, "tax_rate", 10.0)
    st(row, "freight_amount", round(tot * 0.02, 2))
    st(row, "invoice_date", d)
    st(row, "due_date", d + timedelta(days=g.rnd.choice([30, 45, 60])))
    st(row, "invoice_number", f"SI-2026-{300000+i:06d}")
    st(row, "invoice_status", g.rnd.choices(["posted", "open", "paid"], weights=[40, 20, 40])[0])
    st(row, "is_credit_memo", g.rnd.random() < 0.05)
    st(row, "line_count", g.rnd.randint(1, 18))
    st(row, "currency_code", "JPY")
    st(row, "exchange_rate", 1.0)
    st(row, "original_invoice_id", "")


# --------------------- 販促（売上ではないが同名 measure を持つ）
def promotion_event(g, row, i):
    d = g.d(date(2026, 1, 1), date(2026, 11, 30))
    gross = round(g.rnd.uniform(8.0e6, 7.5e7), 2)
    disc = round(gross * g.rnd.uniform(0.05, 0.25), 2)
    tgt = round(gross * g.rnd.uniform(3.5, 9.0), 2)
    st(row, "promotional_spend_gross", gross)
    st(row, "promotional_spend_discount", disc)
    st(row, "promotional_spend_net", round(gross - disc, 2))
    st(row, "target_revenue", tgt)
    st(row, "actual_revenue", round(tgt * g.rnd.uniform(0.55, 1.35), 2))
    st(row, "target_sales_volume", g.rnd.randint(8000, 140000))
    st(row, "actual_sales_volume", g.rnd.randint(5000, 150000))
    st(row, "planned_start_date", d)
    st(row, "planned_end_date", d + timedelta(days=g.rnd.choice([7, 14, 21, 28])))
    st(row, "actual_start_date", d)
    st(row, "actual_end_date", row.get("planned_end_date"))
    st(row, "event_number", f"PE-2026-{4000+i:05d}")
    st(row, "promotion_type", g.rnd.choice(["price_discount", "feature_display", "bonus_pack",
                                            "coupon", "end_aisle"]))
    st(row, "mechanic_type", g.rnd.choice(["TPR", "BOGO", "多数買い", "増量"]))
    st(row, "promotion_objective", g.rnd.choice(["trial", "volume", "share", "distribution"]))
    st(row, "promotion_event_status", g.rnd.choices(["closed", "executing", "planned"],
                                                    weights=[62, 18, 20])[0])
    st(row, "product_category", g.rnd.choice(["ビール類", "清涼飲料", "健康食品"]))
    st(row, "store_count_planned", g.rnd.randint(60, 2400))
    st(row, "store_count_actual", g.rnd.randint(50, 2400))
    st(row, "currency_code", "JPY")
    st(row, "channel", g.rnd.choice(["SM", "CVS", "DgS", "卸", "EC"]))


def settlement(g, row, i):
    claim = round(g.rnd.uniform(8.0e5, 1.15e7), 2)
    adj = round(claim * g.rnd.uniform(-0.12, 0.05), 2)
    net = round(claim + adj, 2)
    d = g.d()
    st(row, "original_claim_amount", claim)
    st(row, "adjustment_amount", adj)
    st(row, "gross_amount", claim)
    st(row, "net_amount", net)
    st(row, "variance_amount", adj)
    st(row, "tax_amount", round(net * TAX, 2))
    st(row, "settlement_timestamp", g.ts(d))
    st(row, "posted_timestamp", g.ts(d))
    st(row, "accounting_date", d)
    st(row, "period", f"2026-{d.month:02d}")
    st(row, "settlement_number", f"ST-2026-{5000+i:05d}")
    st(row, "settlement_status", g.rnd.choices(["posted", "pending", "disputed"],
                                               weights=[72, 20, 8])[0])
    st(row, "settlement_type", g.rnd.choice(["promotion_claim", "rebate", "chargeback"]))
    st(row, "currency_code", "JPY")
    st(row, "source_system", "TPM")


def deduction(g, row, i):
    # dispute_flag は deduction_status と一致させる。独立に振ると
    # 「cleared なのに係争中」という実在しない行ができ、
    # 「係約中の控除はいくら」の答えが列の選び方で変わってしまう。
    gross = round(g.rnd.uniform(2.0e5, 2.8e6), 2)
    adj = round(gross * g.rnd.uniform(-0.1, 0.02), 2)
    d = g.d()
    st(row, "gross_amount", gross)
    st(row, "net_amount", round(gross + adj, 2))
    st(row, "adjustment_amount", adj)
    st(row, "freight_amount", round(gross * 0.01, 2))
    st(row, "handling_fee_amount", round(gross * 0.005, 2))
    st(row, "tax_amount", round(gross * TAX, 2))
    st(row, "quantity", g.rnd.randint(1, 900))
    st(row, "deduction_date", d)
    st(row, "deduction_number", f"DD-2026-{6000+i:05d}")
    st(row, "deduction_type", g.rnd.choice(["promotion", "shortage", "damage", "pricing", "return"]))
    st(row, "deduction_category", g.rnd.choice(["trade", "logistics", "quality"]))
    st(row, "deduction_status", g.rnd.choices(["cleared", "open", "disputed"], weights=[65, 22, 13])[0])
    st(row, "dispute_flag", row.get("deduction_status") == "disputed")
    st(row, "chargeback_rate_percent", round(g.rnd.uniform(0, 12), 2))
    st(row, "currency_code", "JPY")
    st(row, "source_system", "TPM")
    st(row, "expiration_date", "")


def accrual(g, row, i):
    amt = round(g.rnd.uniform(5.0e5, 7.0e6), 2)
    d = g.d()
    st(row, "amount", amt)
    st(row, "net_sales_amount", round(amt * g.rnd.uniform(6, 20), 2))
    st(row, "basis_quantity", g.rnd.randint(500, 60000))
    st(row, "rate", round(g.rnd.uniform(0.5, 9.0), 2))
    st(row, "basis", g.rnd.choice(["volume", "net_sales", "fixed"]))
    st(row, "accrual_number", f"AC-2026-{7000+i:05d}")
    st(row, "accrual_type", g.rnd.choice(["promotion", "rebate", "slotting"]))
    st(row, "accrual_status", g.rnd.choices(["posted", "open", "reversed"], weights=[70, 22, 8])[0])
    st(row, "reversal_flag", g.rnd.random() < 0.08)
    st(row, "effective_date", d)
    st(row, "period_start", date(2026, d.month, 1))
    st(row, "period_end", d)
    st(row, "currency_code", "JPY")
    st(row, "expiration_date", "")


# ------------------------------------- 仕入（売上ではない・true negative）
def purchase_order(g, row, i):
    gross = round(g.rnd.uniform(1.0e6, 1.5e7), 2)
    net = round(gross * g.rnd.uniform(0.90, 0.99), 2)
    d = g.d()
    qty = g.rnd.randint(100, 40000)
    st(row, "po_gross_amount", gross)
    st(row, "net_amount", net)
    st(row, "tax_amount", round(net * TAX, 2))
    st(row, "total_quantity_ordered", qty)
    st(row, "total_quantity_received", int(qty * g.rnd.uniform(0.7, 1.0)))
    st(row, "order_date", d)
    st(row, "requested_delivery_date", d + timedelta(days=g.rnd.randint(7, 60)))
    st(row, "confirmed_delivery_date", d + timedelta(days=g.rnd.randint(7, 70)))
    st(row, "actual_delivery_date", d + timedelta(days=g.rnd.randint(7, 85)))
    st(row, "po_number", f"PO-2026-{800000+i:06d}")
    st(row, "po_status", g.rnd.choices(["received", "open", "partially_received", "closed"],
                                       weights=[50, 20, 15, 15])[0])
    st(row, "po_type", g.rnd.choice(["standard", "blanket", "contract"]))
    st(row, "currency_code", "JPY")
    st(row, "exchange_rate", 1.0)
    st(row, "source_system", "SAP MM")


def ap_invoice(g, row, i):
    gross = round(g.rnd.uniform(9.0e5, 1.3e7), 2)
    net = round(gross * g.rnd.uniform(0.92, 1.0), 2)
    d = g.d()
    st(row, "gross_amount", gross)
    st(row, "net_amount", net)
    st(row, "tax_amount", round(net * TAX, 2))
    st(row, "discount_amount", round(net * 0.01, 2))
    st(row, "local_currency_amount", net)
    st(row, "invoice_date", d)
    st(row, "posting_date", d)
    st(row, "entry_date", d)
    st(row, "due_date", d + timedelta(days=g.rnd.choice([30, 45, 60])))
    st(row, "fiscal_period", f"{d.month:02d}")
    st(row, "fiscal_year", 2026)
    st(row, "invoice_status", g.rnd.choices(["posted", "paid", "blocked"], weights=[40, 52, 8])[0])
    st(row, "invoice_type", g.rnd.choice(["standard", "credit_memo"]))
    st(row, "match_status", g.rnd.choices(["matched", "price_variance", "qty_variance"],
                                          weights=[80, 12, 8])[0])
    st(row, "currency_code", "JPY")
    st(row, "exchange_rate", 1.0)
    st(row, "is_intercompany", g.rnd.random() < 0.05)
    st(row, "procurement_category", g.rnd.choice(["原料", "包材", "受託製造", "物流", "間接材"]))


# ------------------------ 店頭実売（売上の定義③＝sell-out）
def pos_transaction(g, row, i):
    sku_tbl = _S.get("sku", {})
    sid = row.get("sku_id") or (g.rnd.choice(list(sku_tbl)) if sku_tbl else 1)
    _, cat, price = sku_tbl.get(sid, ("", "ビール類", 118.0))
    d = g.d(date(2026, 1, 1), date(2026, 10, 24))
    units = max(1, int(g.rnd.gauss(64, 28) * SEASON[cat][d.month]))
    amt = round(units * price * g.rnd.uniform(0.92, 1.12), 2)
    acc = _S.get("account", {}).get(row.get("account_id"))
    st(row, "transaction_date", d)
    st(row, "transaction_timestamp", g.ts(d))
    st(row, "scan_timestamp", row.get("transaction_timestamp"))
    st(row, "units_sold", units)
    st(row, "dollar_sales", amt)
    st(row, "average_price", price)
    st(row, "year", 2026)
    st(row, "month_of_year", d.month)
    st(row, "week_of_year", d.isocalendar()[1])
    st(row, "transaction_week", d.isocalendar()[1])
    st(row, "transaction_day_of_week", d.isoweekday())
    st(row, "product_category", cat)
    st(row, "product_subcategory", cat)
    st(row, "store_format", acc[1] if acc else "SM")
    st(row, "store_region", acc[2] if acc else "関東")
    st(row, "retailer_banner", acc[0] if acc else "東海フレッシュストア")
    st(row, "sales_channel", acc[1] if acc else "SM")
    st(row, "promotion_flag", g.rnd.random() < 0.28)
    st(row, "feature_flag", g.rnd.random() < 0.18)
    st(row, "display_flag", g.rnd.random() < 0.15)
    st(row, "price_type", "promo" if row.get("promotion_flag") else "regular")
    st(row, "transaction_status", "settled")
    st(row, "transaction_type", "sale")
    st(row, "currency_code", "JPY")
    st(row, "data_source", "Nielsen panel (projected, ~15% ACV)")
    st(row, "line_number", g.rnd.randint(1, 20))


def distribution_point(g, row, i):
    acc = _S.get("account", {}).get(row.get("account_id"))
    acv = round(g.rnd.uniform(5, 97), 2)
    st(row, "acv_weighted_distribution_pct", acv)
    st(row, "numeric_distribution_pct", round(acv * g.rnd.uniform(0.75, 1.1), 2))
    st(row, "tdp_contribution_pct", round(g.rnd.uniform(0.1, 8.0), 2))
    st(row, "acv_change_pct", round(g.rnd.uniform(-9, 9), 2))
    st(row, "numeric_distribution_change_pct", round(g.rnd.uniform(-9, 9), 2))
    st(row, "period_over_period_change_pct", round(g.rnd.uniform(-12, 12), 2))
    st(row, "tdp_change_pct", round(g.rnd.uniform(-5, 5), 2))
    st(row, "velocity_units_per_point", round(g.rnd.uniform(0.5, 40), 2))
    st(row, "in_stock_flag", g.rnd.random() < 0.93)
    st(row, "snapshot_date", g.d())
    st(row, "period_type", g.rnd.choice(["weekly", "monthly", "quarterly"]))
    st(row, "distribution_status", g.rnd.choices(["authorized", "void", "pending"],
                                                 weights=[80, 12, 8])[0])
    st(row, "classification_type", g.rnd.choice(["must_stock", "optional", "seasonal"]))
    st(row, "retailer_banner", acc[0] if acc else "東海フレッシュストア")
    st(row, "market_area", acc[2] if acc else "関東")
    st(row, "location_name", f"{acc[0] if acc else '店'}{g.rnd.randint(1,900)}号店")
    st(row, "data_source", "Nielsen")
    st(row, "distribution_point_code", f"DP-{90000+i:06d}")
    st(row, "void_date", "")
    st(row, "record_status", "active")


def product_std_cost(g, row, i):
    unit = round(g.rnd.uniform(38, 260), 2)
    st(row, "total_standard_cost_per_unit", unit)
    st(row, "units_per_case", 24)
    st(row, "total_standard_cost_per_case", round(unit * 24, 2))
    st(row, "raw_material_cost", round(unit * 0.52, 2))
    st(row, "direct_labor_cost", round(unit * 0.13, 2))
    st(row, "manufacturing_overhead_cost", round(unit * 0.21, 2))
    st(row, "packaging_cost", round(unit * 0.11, 2))
    st(row, "freight_in_cost", round(unit * 0.03, 2))
    st(row, "copacker_toll_fee", round(unit * 0.05, 2))
    prior = round(unit * g.rnd.uniform(0.9, 1.08), 2)
    st(row, "prior_period_cost_per_unit", prior)
    st(row, "cost_variance_per_unit", round(unit - prior, 2))
    st(row, "cost_variance_percentage", round((unit - prior) / prior * 100, 2))
    st(row, "costing_method", g.rnd.choice(["standard", "moving_average"]))
    st(row, "cost_status", g.rnd.choices(["released", "draft"], weights=[85, 15])[0])
    st(row, "cost_version", "2026.1")
    st(row, "effective_date", date(2026, 1, 1))
    st(row, "expiration_date", date(2026, 12, 31))
    st(row, "currency_code", "JPY")


def finance_std_cost(g, row, i):
    unit = round(g.rnd.uniform(38, 260), 2)
    prev = round(unit * g.rnd.uniform(0.9, 1.08), 2)
    st(row, "standard_price_per_unit", unit)
    st(row, "previous_standard_price", prev)
    st(row, "cost_change_amount", round(unit - prev, 2))
    st(row, "cost_change_percentage", round((unit - prev) / prev * 100, 2))
    st(row, "raw_material_cost", round(unit * 0.52, 2))
    st(row, "direct_labor_cost", round(unit * 0.13, 2))
    st(row, "fixed_overhead_cost", round(unit * 0.12, 2))
    st(row, "variable_overhead_cost", round(unit * 0.09, 2))
    st(row, "packaging_material_cost", round(unit * 0.11, 2))
    st(row, "co_packing_cost", round(unit * 0.05, 2))
    st(row, "freight_in_cost", round(unit * 0.03, 2))
    st(row, "other_cost", round(unit * 0.02, 2))
    st(row, "variance_amount", round(unit - prev, 2))
    st(row, "variance_percentage", round((unit - prev) / prev * 100, 2))
    st(row, "price_unit", 1)
    st(row, "costing_version", "2026.1")
    st(row, "fiscal_year", 2026)
    st(row, "fiscal_period", f"{g.rnd.randint(1,10):02d}")
    st(row, "valid_from_date", date(2026, 1, 1))
    st(row, "valid_to_date", date(2026, 12, 31))
    st(row, "currency_code", "JPY")



# ============================================================================
# マーケ（フェーズ2）
#
# 規模の置き方（すべて実在の CPG 比率に合わせる）:
#   純売上 1,270億円 = $847M  ->  マーケ投下額はその 6.5% = $55M（campaign）
#   うち媒体費が 70%  = $38M（media_spend）
#   調査費は投下額の 5% = $2.8M（consumer_insight）… ここが「投下額」と間違われる
#   執行明細は campaign にロールアップする = $48M（campaign_execution）
#   市場全体（syndicated）は自社の約8倍 = $7.0B。自社シェアは 4〜28%
#
# 通貨は ECM どおり USD のまま置く。JPY に直さないことが、この部門を入れた意味。
# ============================================================================
def brand(g, row, i):
    from generate import BRANDS
    name, cat, pmul = BRANDS[i % len(BRANDS)]
    st(row, "brand_name", name)
    st(row, "legal_name", name.replace("ブリックス ", "Brickshouse "))
    st(row, "brand_code", f"BRK-{cat[:2]}-{i+1:02d}")
    st(row, "erp_brand_code", f"BRK{i+1:03d}")
    st(row, "crm_brand_code", f"SFMC-BRK-{i+1:03d}")
    st(row, "brand_category", cat)
    st(row, "architecture_type", "masterbrand" if i % 4 == 0 else "sub_brand")
    st(row, "lifecycle_status", "active" if i < 11 else "discontinued")
    st(row, "distribution_channel", g.rnd.choice(["retail", "retail", "retail", "ecommerce", "club"]))
    st(row, "owner_division", {"ビール類": "酒類事業本部", "清涼飲料": "飲料事業本部",
                               "健康食品": "ヘルスサイエンス事業本部"}[cat])
    # 年間予算は USD 建て。全ブランド合計で約 $55M になるように置く
    st(row, "annual_marketing_budget", round(4_600_000 * pmul / 1.1, 2))
    st(row, "budget_currency_code", "USD")
    st(row, "awareness_pct", round(g.rnd.uniform(28, 88), 2))
    st(row, "equity_score", round(g.rnd.uniform(41, 86), 2))
    st(row, "nps_score", round(g.rnd.uniform(-12, 48), 2))
    st(row, "launch_date", date(2008 + (i % 15), 1 + (i % 12), 1 + (i % 27)))
    st(row, "discontinuation_date", "" if i < 11 else date(2026, 6, 30))
    st(row, "organic_certified", cat == "健康食品" and i % 2 == 0)
    st(row, "clean_label_certified", cat != "ビール類")
    st(row, "gfsi_certification", g.rnd.choice(["sqf", "fssc_22000", "brc"]))
    st(row, "positioning_statement", f"{name} — {cat}の定番として、価格ではなく中身で選ばれる")
    st(row, "digital_presence_url", f"https://brickshouse.example.co.jp/brand/{i+1:02d}")
    st(row, "logo_asset_url", f"https://dam.brickshouse.example.co.jp/logo/{i+1:02d}.svg")
    st(row, "created_timestamp", g.ts(date(2026, 1, 4)))
    st(row, "updated_timestamp", g.ts(date(2026, 10, 1)))


def campaign(g, row, i):
    bid = row.get("brand_id") or ((i % 12) + 1)
    bname, cat = _S.get("brand", {}).get(bid, ("ブリックス ラガー", "ビール類"))
    start = g.d(date(2026, 1, 1), date(2026, 10, 10))
    end = start + timedelta(days=g.rnd.choice([14, 21, 28, 28, 42, 60, 90]))
    planned = round(max(18_000.0, g.rnd.gauss(245_000, 120_000)), 2)
    # 消化率は 72〜112%。季節性の強いカテゴリは出し切る傾向にする
    rate = g.rnd.uniform(0.72, 1.12) * (1.04 if SEASON[cat][start.month] > 1.2 else 1.0)
    actual = round(planned * min(rate, 1.18), 2)
    ctype = g.rnd.choices(["digital", "tv", "shopper", "ooh", "print", "influencer"],
                          weights=[34, 22, 20, 10, 6, 8])[0]
    st(row, "campaign_name", f"{bname} {start.month}月{ctype}施策")
    st(row, "campaign_code", f"CMP-2026-{i+1:04d}")
    st(row, "sfmc_campaign_code", f"SFMC-{i+1:05d}")
    st(row, "campaign_description", f"{bname}（{cat}）の{ctype}中心の投下。{start.month}月〜{end.month}月")
    st(row, "campaign_type", ctype)
    st(row, "channel", {"digital": "digital", "tv": "tv", "shopper": "in_store",
                        "ooh": "ooh", "print": "print", "influencer": "social"}[ctype])
    st(row, "objective", g.rnd.choice(["awareness", "trial", "repeat", "share_gain"]))
    st(row, "start_date", start)
    st(row, "end_date", end)
    st(row, "fiscal_year", "FY2026")
    st(row, "fiscal_period", f"2026-{start.month:02d}")
    st(row, "planned_budget_usd", planned)
    st(row, "actual_spend_usd", actual)
    st(row, "currency_code", "USD")          # ← JPY ではない。ここが衝突③の源
    st(row, "campaign_status", "completed" if end < date(2026, 10, 24) else "in_flight")
    st(row, "approval_status", g.rnd.choices(["approved", "approved", "pending"], weights=[85, 10, 5])[0])
    st(row, "approved_date", start - timedelta(days=g.rnd.randint(7, 40)))
    st(row, "product_category", cat)
    st(row, "target_geography", g.rnd.choice(["全国", "関東", "関西", "中部", "九州"]))
    st(row, "media_impressions_target", int(planned * g.rnd.uniform(380, 620)))
    st(row, "reach_target_households", int(planned * g.rnd.uniform(18, 42)))
    st(row, "acv_target_pct", round(g.rnd.uniform(42, 94), 2))
    st(row, "tdp_target", str(int(g.rnd.uniform(1200, 9800))))
    st(row, "trade_promotion_flag", ctype == "shopper")
    st(row, "shopper_marketing_flag", ctype == "shopper")
    st(row, "influencer_partnership", ctype == "influencer")
    st(row, "private_label_flag", False)
    st(row, "ftc_claims_reviewed", True)
    st(row, "fda_claims_compliant", True)
    st(row, "internal_order_number", f"IO-{600000+i:06d}")
    st(row, "sku_scope", "brand_all" if i % 3 else "sku_specific")
    st(row, "created_timestamp", g.ts(start - timedelta(days=30)))
    st(row, "updated_timestamp", g.ts(min(end, date(2026, 10, 24))))


def media_spend(g, row, i):
    cid = row.get("campaign_id")
    c = _S.get("campaign", {}).get(cid)
    if c:
        bid, cstart, cend, cactual, ctype = c
        st(row, "brand_id", bid)
        try:
            s = date.fromisoformat(str(cstart)); e = date.fromisoformat(str(cend))
        except (ValueError, TypeError):
            s, e = date(2026, 1, 1), date(2026, 10, 24)
    else:
        s, e, ctype = date(2026, 1, 1), date(2026, 10, 24), "digital"
    if e <= s:
        e = s + timedelta(days=14)
    d = g.d(s, min(e, date(2026, 10, 24)))
    planned = round(max(300.0, g.rnd.gauss(4_300, 2_100)), 2)
    actual = round(planned * g.rnd.uniform(0.80, 1.15), 2)
    impr = int(actual * g.rnd.uniform(620, 1_900))
    clicks = int(impr * g.rnd.uniform(0.0007, 0.0094))
    ch = {"digital": "Digital", "tv": "TV", "shopper": "In-Store", "ooh": "OOH",
          "print": "Print", "influencer": "Social"}.get(ctype, "Digital")
    st(row, "media_channel", ch)
    st(row, "media_type", {"TV": "Video", "Digital": "Display", "Social": "Video",
                           "OOH": "Static", "Print": "Static", "In-Store": "Static"}[ch])
    st(row, "media_format", g.rnd.choice(["15s", "30s", "banner_300x250", "native", "poster"]))
    st(row, "buying_type", g.rnd.choices(["programmatic", "direct", "upfront"], weights=[52, 36, 12])[0])
    st(row, "spend_date", d)
    st(row, "flight_start_date", s)
    st(row, "flight_end_date", e)
    st(row, "fiscal_period", f"2026-{d.month:02d}")
    st(row, "planned_spend_amount", planned)
    st(row, "committed_spend_amount", round(planned * g.rnd.uniform(0.95, 1.0), 2))
    st(row, "actual_spend_amount", actual)
    st(row, "agency_fee_amount", round(actual * g.rnd.uniform(0.04, 0.11), 2))
    st(row, "currency_code", "USD")          # ← ここも USD
    st(row, "impressions", impr)
    st(row, "clicks", clicks)
    st(row, "reach", int(impr / g.rnd.uniform(2.2, 5.8)))
    st(row, "frequency", round(g.rnd.uniform(2.2, 5.8), 2))
    st(row, "grp", round(g.rnd.uniform(18, 640), 2))
    st(row, "cpm", round(1000.0 * actual / impr, 2) if impr else 0.0)
    st(row, "cpc", round(actual / clicks, 2) if clicks else 0.0)
    st(row, "roi_index", round(g.rnd.uniform(0.62, 1.84), 2))
    st(row, "spend_status", g.rnd.choices(["invoiced", "accrued", "committed"], weights=[72, 20, 8])[0])
    st(row, "target_audience", g.rnd.choice(["F20-34", "M20-39", "M35-54", "F35-54", "All18+"]))
    st(row, "data_source", "Mediaocean")
    st(row, "geo_market_code", g.rnd.choice(["JP-13", "JP-27", "JP-23", "JP-40", "JP-01"]))
    st(row, "dma_code", "")
    st(row, "working_media_flag", g.rnd.random() < 0.86)
    st(row, "shopper_marketing_flag", ch == "In-Store")
    st(row, "ftc_compliant", True)
    st(row, "invoice_number", f"MO-{700000+i:06d}")
    st(row, "purchase_order_number", f"PO-MED-{500000+i:06d}")
    st(row, "spend_reference_number", f"MS-2026-{i+1:06d}")
    st(row, "wbs_element", f"WBS-MKT-{(i % 40) + 1:03d}")
    st(row, "claim_type", "")
    st(row, "created_timestamp", g.ts(d))
    st(row, "updated_timestamp", g.ts(d))


def consumer_insight(g, row, i):
    """
    調査費。これは「マーケ投下額」ではない。
    ECM の metric view marketing_consumer_insight はこの列に total_actual_spend_usd という
    campaign と完全同名の measure を置いている。投下額の約5%なので、取り違えると20倍外す。
    """
    bid = row.get("brand_id") or ((i % 12) + 1)
    bname, cat = _S.get("brand", {}).get(bid, ("ブリックス ラガー", "ビール類"))
    fs = g.d(date(2026, 1, 5), date(2026, 9, 20))
    fe = fs + timedelta(days=g.rnd.choice([7, 10, 14, 21, 28]))
    budget = round(max(900.0, g.rnd.gauss(5_100, 2_700)), 2)
    actual = round(budget * g.rnd.uniform(0.84, 1.08), 2)
    stype = g.rnd.choices(["brand_health", "concept_test", "sensory", "shopper", "nps_wave"],
                          weights=[26, 22, 18, 16, 18])[0]
    st(row, "study_name", f"{bname} {stype} {fs.month}月ウェーブ")
    st(row, "study_code", f"CI-2026-{i+1:04d}")
    st(row, "study_type", stype)
    st(row, "insight_category", {"brand_health": "Brand Health", "concept_test": "Concept",
                                 "sensory": "Sensory", "shopper": "Shopper", "nps_wave": "NPS"}[stype])
    st(row, "insight_priority", g.rnd.choices(["high", "medium", "low"], weights=[22, 53, 25])[0])
    st(row, "research_methodology", g.rnd.choice(["online_panel", "cell_test", "cvs_intercept", "clt"]))
    st(row, "research_vendor", g.rnd.choice(["Nielsen", "Intage", "Macromill", "Kantar"]))
    st(row, "data_source_system", "Nielsen BASES")
    st(row, "fielding_start_date", fs)
    st(row, "fielding_end_date", fe)
    st(row, "deliverable_date", fe + timedelta(days=g.rnd.randint(5, 25)))
    st(row, "insight_expiry_date", fe + timedelta(days=548))
    st(row, "study_budget_usd", budget)
    st(row, "actual_spend_usd", actual)      # ← 投下額ではない
    st(row, "sample_size", str(g.rnd.choice([300, 400, 600, 800, 1200])))
    st(row, "confidence_level_pct", round(g.rnd.choice([90.0, 95.0, 95.0, 99.0]), 2))
    st(row, "nps_score", round(g.rnd.uniform(-15, 52), 2))
    st(row, "concept_test_score", round(g.rnd.uniform(38, 91), 2))
    st(row, "sensory_score", round(g.rnd.uniform(44, 89), 2))
    st(row, "geography_scope", g.rnd.choice(["全国", "首都圏", "関西圏", "中京圏"]))
    st(row, "category_scope", cat)
    st(row, "sku_scope", "brand_all" if i % 3 else "sku_specific")
    st(row, "target_segment", g.rnd.choice(["F20-34", "M20-39", "M35-54", "F35-54"]))
    st(row, "study_status", "completed" if fe < date(2026, 10, 1) else "fielding")
    st(row, "key_finding_summary", f"{bname}は{cat}内で想起は取れているが、再購入の理由が価格に寄っている")
    st(row, "insight_action", g.rnd.choice(["reformulate", "repack", "media_shift", "price_hold", "none"]))
    st(row, "deliverable_reference", f"VV-CI-{i+1:05d}")
    st(row, "vendor_project_code", f"VND-{i+1:05d}")
    st(row, "source_record_code", f"CI{i+1:06d}")
    st(row, "cost_center_code", f"CC-MKT-{(i % 8) + 1:03d}")
    st(row, "npd_pipeline_flag", stype == "concept_test")
    st(row, "regulatory_claim_flag", cat == "健康食品" and g.rnd.random() < 0.4)
    st(row, "allergen_relevance", g.rnd.random() < 0.18)
    st(row, "clean_label_relevance", cat != "ビール類")
    st(row, "private_label_relevance", False)
    st(row, "sustainability_relevance", g.rnd.random() < 0.3)
    st(row, "record_created_timestamp", g.ts(fs))
    st(row, "record_updated_timestamp", g.ts(fe))


def campaign_execution(g, row, i):
    """キャンペーンの執行明細。計画に対する消化率が現場ペルソナの問いになる。"""
    cid = row.get("campaign_id")
    c = _S.get("campaign", {}).get(cid)
    if c:
        bid, cstart, cend, cactual, ctype = c
        st(row, "brand_id", bid)
        try:
            s = date.fromisoformat(str(cstart)); e = date.fromisoformat(str(cend))
        except (ValueError, TypeError):
            s, e = date(2026, 1, 1), date(2026, 10, 24)
    else:
        s, e, ctype = date(2026, 1, 1), date(2026, 10, 24), "digital"
    if e <= s:
        e = s + timedelta(days=14)
    planned = round(max(400.0, g.rnd.gauss(8_400, 3_900)), 2)
    # 12% は大きく未消化（70%未満）。現場の「消化できていない施策」の問いが成立する
    rate = g.rnd.uniform(0.30, 0.68) if g.rnd.random() < 0.12 else g.rnd.uniform(0.82, 1.09)
    actual = round(planned * rate, 2)
    impr = int(actual * g.rnd.uniform(580, 1_750))
    clicks = int(impr * g.rnd.uniform(0.0006, 0.0088))
    acc = _S.get("account", {}).get(row.get("account_id"))
    st(row, "execution_number", f"EX-2026-{i+1:06d}")
    st(row, "placement_name", f"{ctype}-{g.rnd.choice(['top','feed','mid','pre','post'])}-{i % 97 + 1}")
    st(row, "channel_type", ctype)
    st(row, "channel_platform", g.rnd.choice(["YouTube", "LINE", "Yahoo", "Meta", "TVer", "店頭POP"]))
    st(row, "ad_format", g.rnd.choice(["15s", "30s", "banner", "native", "shelf_talker"]))
    st(row, "creative_version", f"v{g.rnd.randint(1, 4)}")
    st(row, "buying_type", g.rnd.choices(["programmatic", "direct"], weights=[62, 38])[0])
    st(row, "flight_start_date", s)
    st(row, "flight_end_date", e)
    st(row, "planned_spend_amount", planned)
    st(row, "actual_spend_amount", actual)
    st(row, "spend_currency_code", "USD")    # ← ここも USD
    st(row, "impressions_delivered", impr)
    st(row, "clicks_delivered", clicks)
    st(row, "reach", int(impr / g.rnd.uniform(2.1, 5.4)))
    st(row, "frequency", round(g.rnd.uniform(2.1, 5.4), 2))
    st(row, "cost_per_thousand_impressions", round(1000.0 * actual / impr, 2) if impr else 0.0)
    st(row, "video_views", int(impr * g.rnd.uniform(0.12, 0.74)))
    st(row, "video_completion_rate", round(g.rnd.uniform(18, 82), 2))
    st(row, "execution_status", "completed" if e < date(2026, 10, 24) else "live")
    st(row, "agency_name", g.rnd.choice(["博報堂", "電通", "ADK", "サイバーエージェント"]))
    st(row, "target_audience_segment", g.rnd.choice(["F20-34", "M20-39", "M35-54", "F35-54"]))
    st(row, "target_region", acc[2] if acc else g.rnd.choice(["関東", "関西", "中部", "九州"]))
    st(row, "target_geography_code", g.rnd.choice(["JP-13", "JP-27", "JP-23", "JP-40"]))
    st(row, "target_retailer_name", acc[0] if acc else "")
    st(row, "nielsen_market_code", g.rnd.choice(["JPN-TOT", "JPN-KANTO", "JPN-KANSAI"]))
    st(row, "claim_compliance_status", g.rnd.choices(["cleared", "cleared", "in_review"],
                                                    weights=[80, 12, 8])[0])
    st(row, "marketing_claim_flag", g.rnd.random() < 0.22)
    st(row, "influencer_partnership_flag", ctype == "influencer")
    st(row, "utm_source", g.rnd.choice(["youtube", "line", "yahoo", "meta", "direct"]))
    st(row, "utm_medium", g.rnd.choice(["cpc", "cpm", "social", "display"]))
    st(row, "utm_campaign", f"cmp2026{i % 240 + 1:04d}")
    st(row, "vendor_order_number", f"VO-{800000+i:06d}")
    st(row, "salesforce_activity_code", f"SFA-{i+1:06d}")
    st(row, "created_timestamp", g.ts(s))
    st(row, "updated_timestamp", g.ts(min(e, date(2026, 10, 24))))


def syndicated_market_data(g, row, i):
    """
    Nielsen の syndicated データ。dollar_sales は「市場全体（競合込み）」で単位は USD。
    sales_core.pos_transaction.dollar_sales は「自社の店頭実売（パネル投影）」で JPY。
    列名が完全に同じなので、混ぜると自社が市場規模に見える。これが衝突④。
    """
    bid = row.get("brand_id") or ((i % 12) + 1)
    bname, cat = _S.get("brand", {}).get(bid, ("ブリックス ラガー", "ビール類"))
    wk = i % 75
    pstart = date(2026, 1, 5) + timedelta(days=7 * (wk % 42))
    pend = pstart + timedelta(days=6)
    # 地域だけを置く。「全国」を地域と並列に入れると、合計したときに二重計上になる。
    # 8地域の合計が全国の universe になる形にしておく。
    mkt = ["北海道", "東北", "関東", "中部", "北陸", "関西", "中国・四国", "九州"][i % 8]
    seas = SEASON[cat][pstart.month]
    # 市場全体の規模はカテゴリで決まる（ビール > 清涼飲料 >> 健康食品）
    base = CAT_MARKET_USD[cat]
    dollars = round(max(20_000.0, g.rnd.gauss(base, base * 0.42)) * seas, 2)
    units = round(dollars / g.rnd.uniform(1.6, 4.2), 2)
    # シェアはブランドで決まる。週次のばらつきだけ乱数で乗せる
    share = round(max(0.8, BRAND_SHARE.get(bname, 8.0) * g.rnd.uniform(0.82, 1.18)), 2)
    st(row, "brand_name" if "brand_name" in row else "sku_description", f"{bname} 代表SKU")
    st(row, "manufacturer_name", "Brickshouse Food and Beverage")
    st(row, "category_name", cat)
    st(row, "subcategory_name", {"ビール類": "ビール", "清涼飲料": "無糖茶・水",
                                 "健康食品": "機能性表示食品"}[cat])
    st(row, "segment_name", g.rnd.choice(["主力", "プレミアム", "ノンアル", "機能性"]))
    st(row, "market_name", mkt)
    st(row, "market_type", "category_total")          # ← 自社ではない。市場全体
    st(row, "retail_channel", g.rnd.choice(["Grocery", "CVS", "Drug", "Club", "EC"]))
    st(row, "data_aggregation_level", "brand_market_week")
    st(row, "reporting_period_type", "weekly")
    st(row, "period_start_date", pstart)
    st(row, "period_end_date", pend)
    st(row, "data_vintage_date", pend + timedelta(days=11))
    st(row, "data_load_timestamp", g.ts(pend + timedelta(days=12)))
    st(row, "dollar_sales", dollars)                  # ← USD・市場全体
    st(row, "unit_sales", units)
    st(row, "equivalent_unit_sales", round(units * g.rnd.uniform(0.82, 1.24), 2))
    st(row, "dollar_share_pct", share)
    st(row, "unit_share_pct", round(share * g.rnd.uniform(0.86, 1.18), 2))
    st(row, "dollar_sales_change_pct", round(g.rnd.gauss(2.4, 9.1), 2))
    st(row, "unit_sales_change_pct", round(g.rnd.gauss(0.8, 8.6), 2))
    st(row, "avg_selling_price", round(g.rnd.uniform(1.1, 4.6), 2))
    st(row, "avg_base_price", round(g.rnd.uniform(1.2, 4.9), 2))
    st(row, "price_reduction_pct", round(g.rnd.uniform(0, 24), 2))
    st(row, "promoted_dollar_sales", round(dollars * g.rnd.uniform(0.08, 0.46), 2))
    st(row, "promoted_unit_sales", round(units * g.rnd.uniform(0.10, 0.52), 2))
    st(row, "acv_distribution_pct", round(g.rnd.uniform(22, 98), 2))
    st(row, "numeric_distribution_pct", round(g.rnd.uniform(14, 92), 2))
    st(row, "tdp", round(g.rnd.uniform(900, 11_000), 2))
    st(row, "feature_pct", round(g.rnd.uniform(0, 38), 2))
    st(row, "display_pct", round(g.rnd.uniform(0, 31), 2))
    st(row, "velocity_per_store_per_week", round(g.rnd.uniform(3.2, 48.6), 2))
    st(row, "stores_selling", str(g.rnd.randint(1_200, 46_000)))
    st(row, "total_stores_in_market", str(g.rnd.randint(48_000, 62_000)))
    st(row, "is_own_brand", True)
    st(row, "is_private_label", False)
    st(row, "source_system", "Nielsen Scantrack")
    st(row, "source_record_code", f"NSC{i+1:07d}")
    st(row, "gtin", f"45{g.rnd.randint(10**10, 10**11-1)}")
    st(row, "upc_code", f"0{g.rnd.randint(10**10, 10**11-1)}")
    st(row, "pack_size", g.rnd.choice(["350ml", "500ml", "2L", "6pk", "24pk"]))


OVERRIDES = {
    "master_core.sku": sku,
    "master_core.category": category,
    "master_core.product_standard_cost": product_std_cost,
    "finance_core.finance_standard_cost": finance_std_cost,
    "sales_core.account": account,
    "sales_core.rep": rep,
    "sales_core.territory": territory,
    "sales_core.order": order,
    "sales_core.invoice": sales_invoice,
    "sales_core.pos_transaction": pos_transaction,
    "sales_core.distribution_point": distribution_point,
    "finance_core.ar_invoice": ar_invoice,
    "finance_core.ap_invoice": ap_invoice,
    "procure_core.supplier": supplier,
    "procure_core.purchase_order": purchase_order,
    "trade_core.promotion_event": promotion_event,
    "trade_core.settlement": settlement,
    "trade_core.deduction": deduction,
    "trade_core.accrual": accrual,
    "marketing_core.brand": brand,
    "marketing_core.campaign": campaign,
    "marketing_core.media_spend": media_spend,
    "marketing_core.consumer_insight": consumer_insight,
    "marketing_core.campaign_execution": campaign_execution,
    "marketing_core.syndicated_market_data": syndicated_market_data,
}


# ============================================================================
# bronze への汚れ注入
#
# gold 相当のきれいなデータを作ってから、bronze にわざと現実の汚れを入れる。
# これで silver の expectations に実際の仕事が生まれ、品質メトリクスに差が出る。
# 汚れが無いと expectations は「0件違反」で、機能が飾りに見える。
#
# 注入するのは、業務的に実際に起こる壊れ方だけ:
#   - 上流で値引を二重計上して net > gross になる
#   - 連携の取りこぼしで FK が空になる
#   - 日付が空文字で来る（レガシーの日付欠損）
#   - コード値が想定外（マスタ未整備・新チャネルの手入力）
#   - 数量 0 / マイナス（取消の表現が揃っていない）
# PK は NULL にしない（silver の PK NOT NULL で write が落ちるため）
# ============================================================================
DIRT = {
    "sales_core.order": [
        (0.008, lambda g, r: r.update(total_net_amount=round(r["total_gross_amount"] * 1.04, 2))),
        (0.005, lambda g, r: r.update(account_id="")),
        (0.003, lambda g, r: r.update(placed_timestamp="")),
        (0.010, lambda g, r: r.update(total_quantity=0)),
        (0.004, lambda g, r: r.update(total_net_amount=round(-abs(r["total_net_amount"]), 2))),
    ],
    "finance_core.ar_invoice": [
        (0.007, lambda g, r: r.update(net_amount=round(r["gross_amount"] * 1.03, 2))),
        (0.012, lambda g, r: r.update(net_amount=round(r["net_amount"] * 0.80, 2))),   # 照合が崩れる
        (0.020, lambda g, r: r.update(order_id="")),
        (0.004, lambda g, r: r.update(open_amount=round(-abs(r["gross_amount"]) * 0.5, 2))),
    ],
    "finance_core.ap_invoice": [
        (0.006, lambda g, r: r.update(net_amount=round(r["gross_amount"] * 1.05, 2))),
        (0.008, lambda g, r: r.update(supplier_id="")),
    ],
    "procure_core.purchase_order": [
        (0.006, lambda g, r: r.update(net_amount=round(r["po_gross_amount"] * 1.02, 2))),
        (0.015, lambda g, r: r.update(total_quantity_received=r["total_quantity_ordered"] + 50)),
    ],
    "trade_core.settlement": [
        (0.010, lambda g, r: r.update(net_amount=round(r["net_amount"] * 1.15, 2))),
    ],
    "trade_core.deduction": [
        (0.007, lambda g, r: r.update(net_amount=round(-abs(r["net_amount"]), 2))),
    ],
    "sales_core.pos_transaction": [
        (0.005, lambda g, r: r.update(units_sold=0)),
        (0.003, lambda g, r: r.update(dollar_sales=round(-abs(r["dollar_sales"]), 2))),
        (0.004, lambda g, r: r.update(data_source="")),
    ],
    "master_core.sku": [
        (0.007, lambda g, r: r.update(sku_code="")),
        (0.010, lambda g, r: r.update(product_status="ACTIVE ")),     # 大文字＋末尾空白
    ],
    "sales_core.account": [
        (0.010, lambda g, r: r.update(channel="スーパー")),           # 想定外のコード値
        (0.005, lambda g, r: r.update(account_name="")),
    ],
    "master_core.product_standard_cost": [
        (0.008, lambda g, r: r.update(total_standard_cost_per_unit=0)),
    ],
    "finance_core.finance_standard_cost": [
        (0.008, lambda g, r: r.update(standard_price_per_unit=0)),
    ],
    # マーケの汚れ。いずれもマーケ運用で実際に起こるもの
    "marketing_core.campaign": [
        # 代理店の請求が二重で載り、計画の2倍を超える
        (0.008, lambda g, r: r.update(actual_spend_usd=round(r["planned_budget_usd"] * 2.3, 2))),
        (0.006, lambda g, r: r.update(end_date="")),
        (0.005, lambda g, r: r.update(currency_code="")),
    ],
    "marketing_core.media_spend": [
        # 媒体社の明細で通貨が落ちる。これが一番怖い汚れ（受け手が JPY だと思い込む）
        (0.014, lambda g, r: r.update(currency_code="")),
        (0.006, lambda g, r: r.update(impressions=0)),
        (0.004, lambda g, r: r.update(actual_spend_amount=round(-abs(r["actual_spend_amount"]), 2))),
    ],
    "marketing_core.consumer_insight": [
        # ベンダーのクレジットノートがマイナスで入る
        (0.009, lambda g, r: r.update(actual_spend_usd=round(-abs(r["actual_spend_usd"]), 2))),
        (0.005, lambda g, r: r.update(deliverable_date="")),
    ],
    "marketing_core.campaign_execution": [
        # 配信ログの取りこぼし: 費用は立つのに配信実績が 0
        (0.010, lambda g, r: r.update(impressions_delivered=0)),
        (0.006, lambda g, r: r.update(campaign_id="")),
    ],
    "marketing_core.syndicated_market_data": [
        (0.007, lambda g, r: r.update(dollar_share_pct=round(100 + g.rnd.uniform(1, 40), 2))),
        (0.005, lambda g, r: r.update(period_end_date="")),
    ],
}


def inject_dirt(g, table, rows):
    """bronze に汚れを注入し、何件どう壊したかを返す（証跡に使う）。"""
    rules = DIRT.get(table)
    if not rules:
        return []
    log = []
    for rate, mutate in rules:
        n = max(1, int(len(rows) * rate))
        picks = g.rnd.sample(range(len(rows)), min(n, len(rows)))
        for i in picks:
            try:
                mutate(g, rows[i])
            except Exception:
                pass
        log.append((rate, len(picks)))
    return log
