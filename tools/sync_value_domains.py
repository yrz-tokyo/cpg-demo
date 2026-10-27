#!/usr/bin/env python3
"""
生成したデータの実際の値を読んで、列コメントの値域宣言を実データに合わせる。

ECM の列コメントは `Valid values are \\`a|b|c\\`` という形で値域を宣言している。
business.py で列を業務的に上書きすると、この宣言と実データがずれる。
ずれていると Genie がコメントを信じて WHERE 句を組み、正しい質問に 0 件で答える
（sales_core.order.channel で実際に起きた: 宣言 retail|wholesale… / 実データ SM|CVS|DgS|卸|EC）。

データを上書きするなら辞書も上書きしなければならない。これはその同期器。
出力を gen_pipeline.py が読んで silver の列コメントを書き換える。

ウェアハウスではなくローカルの CSV を読む。データはシードで決まるので結果は同じで、
パイプラインを作る前に実行できる（順番の循環を避けるため）。

読むのは `02_data/clean`（`generate.py --no-dirt` の出力）。bronze に注入した汚れ
（'スーパー'、'ACTIVE ' など）を正規の値域として宣言してしまわないため。
"""
import csv, gzip, json, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "02_data" / "clean"      # 汚れ無しの版（generate.py --no-dirt）
MAX_DISTINCT = 24          # これを超えるものは値域ではなく自由記述として扱う


def main():
    schema = json.loads((BASE / "02_data" / "schema.json").read_text())
    src_of = {}
    for f in sorted(RAW.glob("*.csv.gz")):
        _src, sch, tbl = f.name.replace(".csv.gz", "").split("__")
        src_of[f"{sch}.{tbl}"] = f

    out, checked = {}, 0
    for key, meta in schema.items():
        f = src_of.get(key)
        if not f:
            continue
        enum_cols = {}
        for c in meta["columns"]:
            v = c.get("values")
            if isinstance(v, list) and len(v) >= 2 and not any(str(x).startswith("^") for x in v):
                enum_cols[c["name"]] = [str(x) for x in v]
        if not enum_cols:
            continue
        seen = {k: set() for k in enum_cols}
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                for k in enum_cols:
                    val = (row.get(k) or "").strip()
                    if val and len(seen[k]) <= MAX_DISTINCT:
                        seen[k].add(val)
        for col, declared in enum_cols.items():
            checked += 1
            actual = seen[col]
            if not actual or len(actual) > MAX_DISTINCT:
                continue
            if actual - set(declared):
                out.setdefault(key, {})[col] = sorted(actual)

    dest = BASE / "02_data" / "value_domains_actual.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    n = sum(len(v) for v in out.values())
    print(f"列挙値域を宣言している列 {checked} / 実データとずれていて上書きする列 {n}")
    for key in sorted(out):
        for col, vals in sorted(out[key].items()):
            print(f"  {key}.{col:34s} -> {vals}")
    print(f"\n-> {dest}")


if __name__ == "__main__":
    sys.exit(main())
