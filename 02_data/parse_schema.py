#!/usr/bin/env python3
"""抽出済み DDL を機械可読なスキーマ JSON にする（列名・型・NULL可否・コメント・値域・PK・FK）。

列コメントの `Valid values are `a|b|c`` をそのまま値域として取り出すのが要点。
業界データモデルの列コメントが、そのまま合成データの制約として使える。
"""
import json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DDL = BASE / "01_model" / "tables.sql"
FKS = BASE / "01_model" / "foreign_keys.sql"
OUT = BASE / "02_data" / "schema.json"

VALID = re.compile(r"Valid values are\s*`([^`]+)`")
COL = re.compile(r"^\s{4}`(\w+)`\s+([A-Z]+(?:\(\d+(?:,\d+)?\))?)\s*(NOT NULL)?\s*(?:COMMENT '(.*)')?,?\s*$")
PK = re.compile(r"CONSTRAINT\s+`?pk_\w+`?\s+PRIMARY KEY\(([^)]*)\)")

def parse_tables():
    txt = DDL.read_text()
    tables = {}
    for m in re.finditer(
        r"CREATE OR REPLACE TABLE `\w+`\.`(\w+)`\.`(\w+)` \((.*?)\n\) COMMENT '(.*?)';",
        txt, re.S):
        schema, name, body, tcomment = m.groups()
        cols, pk = [], []
        for line in body.splitlines():
            cm = COL.match(line)
            if cm:
                cname, ctype, notnull, comment = cm.groups()
                comment = comment or ""
                vm = VALID.search(comment)
                vals = None
                if vm:
                    raw = vm.group(1)
                    # 正規表現っぽいもの（メール等）は値域ではない
                    if not raw.startswith("^"):
                        vals = [v.strip() for v in raw.split("|") if v.strip()]
                cols.append({"name": cname, "type": ctype,
                             "nullable": notnull is None, "comment": comment,
                             "values": vals})
                continue
            pm = PK.search(line)
            if pm:
                pk = [c.strip().strip("`") for c in pm.group(1).split(",")]
        tables[f"{schema}.{name}"] = {
            "schema": schema, "name": name, "comment": tcomment,
            "columns": cols, "pk": pk, "fks": []}
    return tables

def parse_fks(tables):
    alter = re.compile(
        r"ALTER TABLE `\w+`\.`(\w+)`\.`(\w+)` ADD CONSTRAINT `?(\w+)`? "
        r"FOREIGN KEY \(([^)]*)\) REFERENCES `\w+`\.`(\w+)`\.`(\w+)`\(([^)]*)\);")
    for m in alter.finditer(FKS.read_text()):
        cs, ct, nm, cols, ps, pt, pcols = m.groups()
        clean = lambda s: [c.strip().strip("`") for c in s.split(",")]
        key = f"{cs}.{ct}"
        if key in tables:
            tables[key]["fks"].append({
                "name": nm, "columns": clean(cols),
                "parent": f"{ps}.{pt}", "parent_columns": clean(pcols)})
    return tables

if __name__ == "__main__":
    t = parse_fks(parse_tables())
    OUT.write_text(json.dumps(t, indent=2, ensure_ascii=False))
    ncol = sum(len(v["columns"]) for v in t.values())
    nval = sum(1 for v in t.values() for c in v["columns"] if c["values"])
    nfk  = sum(len(v["fks"]) for v in t.values())
    print(f"テーブル {len(t)} / 列 {ncol} / FK {nfk}")
    print(f"列コメントから値域が取れた列: {nval} 列  ← これが合成データの制約になる")
    print()
    for k in ("sales_core.order", "finance_core.ar_invoice", "trade_core.settlement"):
        v = t[k]
        money = [c["name"] for c in v["columns"]
                 if re.search(r"amount|revenue|price|cost|discount", c["name"])]
        dates = [c["name"] for c in v["columns"] if re.search(r"date|timestamp", c["name"])]
        print(f"[{k}]  PK={v['pk']}  FK={len(v['fks'])}本")
        print(f"   金額列: {money}")
        print(f"   日付列: {dates}")
        print(f"   親: {sorted({f['parent'] for f in v['fks']})}")
        print()
