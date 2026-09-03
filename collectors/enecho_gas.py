"""資源エネルギー庁 石油製品価格調査から、レギュラーガソリンの全国平均価格。

    results.html に最新回の xlsx がリンクされている（ファイル名は YYMMDD.xlsx）。
    xlsx は openpyxl を使わず zipfile + XML で読む（依存ライブラリを増やさない）。
    週次更新（月曜調査・水曜公表）。
"""
from __future__ import annotations

import datetime as dt
import re
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

from core.http import fetch
from core.models import Observation, now_jst

RESULTS = "https://www.enecho.meti.go.jp/statistics/petroleum_and_lpgas/pl007/results.html"
BASE = "https://www.enecho.meti.go.jp"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
EXCEL_EPOCH = dt.date(1899, 12, 30)


def _latest_xlsx_url() -> str:
    html = fetch(RESULTS, timeout=20).decode("utf-8", errors="replace")
    m = re.search(r'href="(/statistics/petroleum_and_lpgas/pl007/xlsx/(\d{6})\.xlsx)"', html)
    if not m:
        raise RuntimeError("xlsx リンクが見つからない")
    return BASE + m.group(1)


def _sheet_rows(xlsx: bytes) -> list[list]:
    z = zipfile.ZipFile(BytesIO(xlsx))
    strings: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        r = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in r.findall(f"{NS}si"):
            strings.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows: list[list] = []
    for row in root.iter(f"{NS}row"):
        cells: dict[str, object] = {}
        for c in row.findall(f"{NS}c"):
            ref = re.sub(r"\d+", "", c.get("r", ""))
            v = c.find(f"{NS}v")
            if v is None or v.text is None:
                continue
            val: object = v.text
            if c.get("t") == "s":
                val = strings[int(v.text)]
            else:
                try:
                    val = float(v.text)
                except ValueError:
                    pass
            cells[ref] = val
        rows.append(cells)
    return rows


def collect() -> list[Observation]:
    try:
        url = _latest_xlsx_url()
        rows = _sheet_rows(fetch(url, timeout=25))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! enecho_gas: {exc}")
        return []

    # 「レギュラー」ラベルの行から数行が週次データ。列D=Excel日付, 列P=全国(小数)
    start = None
    for i, r in enumerate(rows):
        if any(isinstance(v, str) and v.strip() == "レギュラー" for v in r.values()):
            start = i
            break
    if start is None:
        print("  ! enecho_gas: レギュラー行が見つからない")
        return []

    best = None
    for r in rows[start:start + 8]:
        d = r.get("D")
        price = r.get("P") or r.get("O")
        if isinstance(d, float) and isinstance(price, float) and 50 < price < 400:
            if best is None or d > best[0]:
                best = (d, price)
    if best is None:
        print("  ! enecho_gas: 価格セルが読めない")
        return []

    serial, price = best
    survey_date = EXCEL_EPOCH + dt.timedelta(days=int(serial))
    observed_at = now_jst().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")

    return [Observation("gas-regular", round(price, 1), observed_at, {
        "survey_date": survey_date.isoformat(),
        "caption": f"レギュラーガソリン全国平均（{survey_date:%-m月%-d日}調査）",
    })]
