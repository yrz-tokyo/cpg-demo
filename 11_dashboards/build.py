#!/usr/bin/env python3
"""
部門別 AI/BI ダッシュボード3本を組み立てる（営業 / 財務 / マーケ）。

なぜダッシュボードを作るのか
  当初要件の「ダッシュボードも ontology の snippet になる」。ダッシュボードが存在すると、
  その SQL が inferred ontology に取り込まれる。つまりダッシュボードは
  見るためだけでなく、**Genie に文脈を供給する資産**でもある。

設計の決まり（venture-loop-demo の DESIGN_SPEC に合わせる）
  - KPI は3つまで。単位・期間・基準を必ず添える
  - 状態を色だけで区別しない。文字でも書く
  - 計画/実績/推計を言葉で書き分ける
  - 注入した汚れ（未マップのチャネルコード）を隠さず、品質シグナルとして出す

出力: 11_dashboards/{sales,finance,marketing}.json
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent

# 3本で同じパレット。1つのシステムとして読めるようにする。
# アクセント（選択色）だけ Databricks の lava を使い、系列色とぶつけない。
THEME = {
    "canvasBackgroundColor": {"light": "#F9F7F4", "dark": "#0B2026"},
    "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#112B33"},
    "fontColor": {"light": "#11252C", "dark": "#EEF4F5"},
    "selectionColor": {"light": "#FF3621", "dark": "#FF5F46"},
    "visualizationColors": ["#003F5C", "#3C6997", "#594E90", "#BC4C96",
                            "#FF5F66", "#FFA600", "#12795A"],
    "widgetHeaderAlignment": "LEFT",
    "fontFamily": "DM Sans",
    "widgetCornerRadius": 12,
}


def text(name, lines, x, y, w, h):
    return {"widget": {"name": name, "multilineTextboxSpec": {"lines": lines}},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def counter(name, ds, measure, title, caption, x, y, w=3, h=3, fmt=None, tmpl=None):
    enc = {"value": {"fieldName": f"measure({measure})", "displayName": caption}}
    if fmt:
        enc["value"]["format"] = fmt
    if tmpl:
        enc["value"]["formatTemplate"] = tmpl
    return {"widget": {
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": ds,
            "fields": [{"name": f"measure({measure})", "expression": f"MEASURE(`{measure}`)"}],
            "disaggregated": False}}],
        "spec": {"version": 2, "widgetType": "counter", "encodings": enc,
                 "frame": {"title": title, "showTitle": True}}},
        "position": {"x": x, "y": y, "width": w, "height": h}}


def bar(name, ds, dim, measures, title, x, y, w, h, horizontal=False,
        sort_by_value=True, color_dim=None, mark=None):
    fields = [{"name": dim, "expression": f"`{dim}`"}]
    for m in measures:
        fields.append({"name": f"measure({m['measure']})",
                       "expression": f"MEASURE(`{m['measure']}`)"})
    if color_dim:
        fields.append({"name": color_dim, "expression": f"`{color_dim}`"})
    qdim = {"fieldName": dim, "scale": {"type": "categorical"}}
    if sort_by_value:
        qdim["scale"]["sort"] = {"by": "value"}
    qnum = {"scale": {"type": "quantitative"},
            "fields": [{"fieldName": f"measure({m['measure']})",
                        "displayName": m["label"]} for m in measures]}
    enc = {"x": qnum, "y": qdim} if horizontal else {"x": qdim, "y": qnum}
    if color_dim:
        enc["color"] = {"fieldName": color_dim, "scale": {"type": "categorical"}}
    spec = {"version": 3, "widgetType": "bar", "encodings": enc,
            "frame": {"title": title, "showTitle": True}}
    if mark:
        spec["mark"] = mark
    return {"widget": {"name": name,
                       "queries": [{"name": "main_query", "query": {
                           "datasetName": ds, "fields": fields, "disaggregated": False}}],
                       "spec": spec},
            "position": {"x": x, "y": y, "width": w, "height": h}}


def line(name, ds, tcol, measures, title, x, y, w, h, grain="MONTH"):
    tname = f"monthly({tcol})" if grain == "MONTH" else f"daily({tcol})"
    fields = [{"name": tname, "expression": f'DATE_TRUNC("{grain}", `{tcol}`)'}]
    for m in measures:
        fields.append({"name": f"measure({m['measure']})",
                       "expression": f"MEASURE(`{m['measure']}`)"})
    return {"widget": {
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": ds, "fields": fields, "disaggregated": False,
            "orders": [{"direction": "ASC", "expression": f'DATE_TRUNC("{grain}", `{tcol}`)'}]}}],
        "spec": {"version": 3, "widgetType": "line",
                 "encodings": {
                     "x": {"fieldName": tname, "scale": {"type": "temporal"},
                           "displayName": "月"},
                     "y": {"scale": {"type": "quantitative"},
                           "fields": [{"fieldName": f"measure({m['measure']})",
                                       "displayName": m["label"]} for m in measures]}},
                 "frame": {"title": title, "showTitle": True}}},
        "position": {"x": x, "y": y, "width": w, "height": h}}


def table(name, ds, cols, title, x, y, w, h):
    return {"widget": {
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": ds,
            "fields": [{"name": c["field"], "expression": f"`{c['field']}`"} for c in cols],
            "disaggregated": True}}],
        "spec": {"version": 2, "widgetType": "table",
                 "encodings": {"columns": [
                     {k: v for k, v in
                      (("fieldName", c["field"]), ("displayName", c["label"]),
                       ("format", c.get("format"))) if v is not None}
                     for c in cols]},
                 "frame": {"title": title, "showTitle": True}}},
        "position": {"x": x, "y": y, "width": w, "height": h}}


def flt(name, ds, field, label, x, y, w=3, h=2, multi=True):
    qn = f"{ds}_{field}"
    return {"widget": {
        "name": name,
        "queries": [{"name": qn, "query": {
            "datasetName": ds, "fields": [{"name": field, "expression": f"`{field}`"}],
            "disaggregated": False}}],
        "spec": {"version": 2,
                 "widgetType": "filter-multi-select" if multi else "filter-single-select",
                 "encodings": {"fields": [
                     {"fieldName": field, "displayName": label, "queryName": qn}]},
                 "frame": {"title": label, "showTitle": True}}},
        "position": {"x": x, "y": y, "width": w, "height": h}}


JPY = {"type": "number-currency", "currencyCode": "JPY",
       "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}
USD = {"type": "number-currency", "currencyCode": "USD",
       "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}
PCT = {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 1}}
NUM = {"type": "number", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 0}}


def write(name, dashboard):
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    nds = len(dashboard["datasets"])
    nw = sum(len(pg["layout"]) for pg in dashboard["pages"])
    print(f"  {p.name}: データセット {nds} / ウィジェット {nw}")
    return p
