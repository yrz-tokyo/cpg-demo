#!/usr/bin/env python3
"""
Brickshouse Food and Beverage — 合成生データ生成（stdlib のみ）

方針
  - 列の値域は **業界データモデルの列コメント**から取る（`Valid values are ...`）。自作しない。
  - FK は親の採番済みキーから引くので参照整合が構造的に成り立つ。
  - 「売上」の定義差は **業務的に正しい連鎖**で作る:
        受注(order.total_net_amount)
          → 出荷・請求(ar_invoice.gross_amount は受注の一部)
            → 販促控除(trade_discount_amount / deduction_amount)
              → 純売上(ar_invoice.net_amount)
    さらに ap_invoice / purchase_order は **売上ではない**が同名の measure を持つ（true negative）。
  - 出力は ops_landing Volume に置く生 CSV（gzip）。ソースシステム名を接頭辞にする。
"""
import csv, gzip, json, random, re, sys
from datetime import date, datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((BASE / "02_data" / "schema.json").read_text())
OUTDIR = BASE / "02_data" / "raw"
SEED = 20261025
FY_START = date(2026, 1, 1)
FY_TODAY = date(2026, 10, 24)
FY_END = date(2026, 12, 31)

ROWS = {
    "master_core.category": 24, "master_core.sku": 300, "master_core.product_standard_cost": 300,
    "finance_core.gl_account": 60, "finance_core.cost_center": 40, "finance_core.profit_center": 20,
    "finance_core.finance_standard_cost": 300,
    "procure_core.supplier": 80, "procure_core.purchase_order": 8000,
    "finance_core.ap_invoice": 8000,
    "sales_core.territory": 12, "sales_core.rep": 60, "sales_core.account": 150,
    "sales_core.order": 24000, "sales_core.invoice": 22000,
    "sales_core.pos_transaction": 80000, "sales_core.distribution_point": 2400,
    "finance_core.ar_invoice": 22000,
    "trade_core.fund": 30, "trade_core.promotion_event": 400, "trade_core.promotion_line": 4000,
    "trade_core.accrual": 4000, "trade_core.settlement": 1800, "trade_core.deduction": 5000,
    # マーケ（フェーズ2）。brand は BRANDS と1対1、他は campaign にロールアップする粒度
    "marketing_core.brand": 12, "marketing_core.campaign": 240,
    "marketing_core.media_spend": 9000, "marketing_core.consumer_insight": 600,
    "marketing_core.campaign_execution": 6000, "marketing_core.syndicated_market_data": 7200,
}

# ソースシステム（bronze をソース単位に分けるため）
SOURCE = {
    "master_core.sku": "sap_mm", "master_core.category": "sap_mm",
    "master_core.product_standard_cost": "sap_co",
    "finance_core.gl_account": "sap_fi", "finance_core.cost_center": "sap_co",
    "finance_core.profit_center": "sap_co", "finance_core.finance_standard_cost": "sap_co",
    "finance_core.ar_invoice": "sap_fi", "finance_core.ap_invoice": "sap_fi",
    "sales_core.order": "sap_sd", "sales_core.invoice": "sap_sd",
    "sales_core.account": "salesforce", "sales_core.rep": "workday",
    "sales_core.territory": "salesforce", "sales_core.pos_transaction": "pos_edi852",
    "sales_core.distribution_point": "nielsen",
    "trade_core.fund": "tpm", "trade_core.promotion_event": "tpm",
    "trade_core.promotion_line": "tpm", "trade_core.accrual": "tpm",
    "trade_core.settlement": "tpm", "trade_core.deduction": "tpm",
    "procure_core.supplier": "sap_mm", "procure_core.purchase_order": "sap_mm",
    "marketing_core.brand": "salesforce_mc", "marketing_core.campaign": "salesforce_mc",
    "marketing_core.campaign_execution": "salesforce_mc",
    "marketing_core.media_spend": "mediaocean",
    "marketing_core.consumer_insight": "nielsen_bases",
    "marketing_core.syndicated_market_data": "nielsen",
}

BRANDS = [
    ("ブリックス ラガー", "ビール類", 1.00), ("ブリックス プレミアム", "ビール類", 1.45),
    ("ブリックス THE生", "ビール類", 1.10), ("ブリックス 零", "ビール類", 0.85),
    ("ブリックス 緑茶", "清涼飲料", 0.42), ("ブリックス 麦茶", "清涼飲料", 0.38),
    ("ブリックス 天然水", "清涼飲料", 0.30), ("ブリックス レモン", "清涼飲料", 0.46),
    ("ブリックス 微炭酸", "清涼飲料", 0.44),
    ("ブリックス 乳酸菌ガード", "健康食品", 1.85), ("ブリックス コラーゲン", "健康食品", 2.10),
    ("ブリックス 血糖ケア", "健康食品", 2.40),
]
PACKS = [("350ml缶", 1.0), ("500ml缶", 1.38), ("500mlPET", 1.25), ("2LPET", 3.1),
         ("6缶パック", 5.8), ("24缶ケース", 22.5), ("30日分", 1.0), ("90日分", 2.7)]
# 得意先。社名に地域名を入れない。
#   当初は「東海フレッシュストア」「関西マルシェ」のような社名にしていたが、
#   150件に増やすため地域を前置した結果「東北東海フレッシュストア」という
#   地名が矛盾した名前が生まれ、shipping_state も食い違った。
#   回答に必ず出る文字列なので、地域中立な社名 × 地域で「〇〇 関東支社」の形にする。
ACCOUNTS = [
    ("フレッシュストア", "SM"), ("マルシェ興産", "SM"), ("さつき屋", "SM"),
    ("みなとスーパー", "SM"), ("緑風マート", "SM"), ("フードセンターいずみ", "SM"),
    ("デイリーワン", "CVS"), ("クイックマート", "CVS"), ("ステップイン", "CVS"),
    ("さくら薬品", "DgS"), ("ヘルスベース", "DgS"), ("くすりのミドリ", "DgS"),
    ("全日本酒類卸", "卸"), ("中央食品卸", "卸"), ("ブリックス公式オンライン", "EC"),
]
# 15社 × 10地域 = 150得意先。ちょうど一意になる数にしてある。
REGIONS = ["北海道", "東北", "関東", "北陸", "中部", "関西", "中国", "四国", "九州", "沖縄"]
SUPPLIERS = ["協和製缶", "日東包材", "中央原料", "山陽糖業", "北陸アルミ", "東和ラベル",
             "共栄飲料受託", "新光香料", "大和麦芽", "泉州精糖"]


def topo_order(schema):
    order, seen = [], set()
    def visit(k, stack=()):
        if k in seen or k not in schema:
            return
        if k in stack:
            return  # 自己参照・循環は無視（キーは先に採番済み）
        for fk in schema[k]["fks"]:
            visit(fk["parent"], stack + (k,))
        if k not in seen:
            seen.add(k); order.append(k)
    for k in schema:
        visit(k)
    return order


class Gen:
    def __init__(self):
        self.rnd = random.Random(SEED)
        self.keys = {}        # table -> [pk値]
        self.extra = {}       # table -> {pk: 付随情報}

    # ---------- 基本ジェネレータ ----------
    def d(self, lo=FY_START, hi=FY_TODAY):
        return lo + timedelta(days=self.rnd.randint(0, (hi - lo).days))

    def ts(self, dt=None):
        dt = dt or self.d()
        return f"{dt} {self.rnd.randint(6,22):02d}:{self.rnd.randint(0,59):02d}:{self.rnd.randint(0,59):02d}"

    def money(self, lo, hi):
        return round(self.rnd.uniform(lo, hi), 2)

    def by_name_type(self, col, table):
        n, t = col["name"], col["type"]
        if col["values"]:
            return self.rnd.choice(col["values"])
        if re.search(r"^is_|^has_|_flag$|_eligible$|_required$", n) or t == "BOOLEAN":
            return self.rnd.random() < 0.25
        if t == "DATE" or re.search(r"_date$", n):
            return self.d()
        if t == "TIMESTAMP" or re.search(r"_timestamp$|_at$", n):
            return self.ts()
        if re.search(r"_pct$|_percent$|_rate$|_ratio$", n):
            return round(self.rnd.uniform(0, 100), 2)
        if re.search(r"amount|revenue|price|cost|fee|spend|budget|value", n):
            return self.money(1000, 900000)
        if re.search(r"_qty$|quantity|_units$|_count$|_cases$|headcount", n):
            return self.rnd.randint(1, 900)
        if re.search(r"_id$", n) and t == "BIGINT":
            return self.rnd.randint(1, 500)     # subset 外の参照（孤児FKは張っていない）
        if t.startswith("DECIMAL") or t == "DOUBLE":
            return round(self.rnd.uniform(0, 1000), 2)
        if t in ("BIGINT", "INT"):
            return self.rnd.randint(1, 10000)
        if re.search(r"_code$", n):
            return f"{n[:3].upper()}-{self.rnd.randint(1000,9999)}"
        if re.search(r"currency", n):
            return "JPY"
        if re.search(r"_name$|_description$|_title$|_text$|comment|note", n):
            return f"{n.replace('_',' ')} {self.rnd.randint(1,999)}"
        return f"{n[:6]}-{self.rnd.randint(100,999)}"

    def fk_value(self, table, col_name):
        for fk in SCHEMA[table]["fks"]:
            if col_name in fk["columns"]:
                pool = self.keys.get(fk["parent"])
                if pool:
                    return self.rnd.choice(pool)
        return None


def main():
    # --no-dirt: 汚れを注入しない版を別ディレクトリに出す。
    # 列コメントの値域を実データに合わせるとき、注入した汚れ（'スーパー' や 'ACTIVE '）を
    # 正規の値として宣言してしまわないために使う。
    no_dirt = "--no-dirt" in sys.argv
    outdir = (BASE / "02_data" / "clean") if no_dirt else OUTDIR
    outdir.mkdir(parents=True, exist_ok=True)
    g = Gen()
    order = [t for t in topo_order(SCHEMA) if t in ROWS]
    import business  # 業務ロジックの上書き（別ファイル）
    summary = []
    for table in order:
        meta = SCHEMA[table]
        n = ROWS[table]
        pk = meta["pk"][0] if len(meta["pk"]) == 1 else None
        rows = []
        override = business.OVERRIDES.get(table)
        g.keys[table] = []
        for i in range(n):
            row = {}
            for col in meta["columns"]:
                cn = col["name"]
                if pk and cn == pk:
                    row[cn] = i + 1
                    continue
                v = g.fk_value(table, cn)
                row[cn] = v if v is not None else g.by_name_type(col, table)
            if pk:
                g.keys[table].append(i + 1)
            if override:
                override(g, row, i)
            rows.append(row)
        dirt = [] if no_dirt else business.inject_dirt(g, table, rows)
        src = SOURCE.get(table, "misc")
        fname = outdir / f"{src}__{meta['schema']}__{meta['name']}.csv.gz"
        cols = [c["name"] for c in meta["columns"]]
        with gzip.open(fname, "wt", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        business.remember(g, table, rows)
        nd = sum(c for _, c in dirt)
        summary.append((table, n, len(cols), fname.stat().st_size, nd))
        print(f"  {table:36s} {n:7,d} 行 x {len(cols):3d} 列  {fname.stat().st_size/1024:8.0f} KB  "
              f"<- {src}" + (f"  汚れ {nd} 行" if nd else ""))
    total = sum(s[1] for s in summary)
    print(f"\n合計 {total:,} 行 / {len(summary)} ファイル / "
          f"{sum(s[3] for s in summary)/1024/1024:.1f} MB / "
          f"注入した汚れ {sum(s[4] for s in summary):,} 行")
    json.dump([{"table": t, "rows": r, "cols": c, "bytes": b, "dirty_rows": d}
               for t, r, c, b, d in summary],
              open(BASE / "02_data" / "generated.json", "w"), indent=2)

if __name__ == "__main__":
    sys.path.insert(0, str(BASE / "02_data"))
    main()
