"""気象庁「さくらの開花状況」から、開花・満開した地点数。

    sakura/data/sakura_kaika.html  … 本年の開花状況（12月〜6月に1日3回更新）
    sakura/data/sakura_mankai.html … 本年の満開状況（同上）

観測期間外（7月〜11月）はその年最後の更新内容のまま変わらない
（シーズンオフはその年の最終値を出し続け、翌年12月の初回更新でリセットされる）。

※ うめ・いちょう・かえで・あじさいの生物季節観測は2021年で終了しており、
   現在はさくらの開花・満開のみ継続観測されている（他は2020年までのPDFしか残っていない）。
"""
from __future__ import annotations

import html
import re

from core.http import fetch
from core.models import Observation, now_jst

KAIKA_URL = "https://www.data.jma.go.jp/sakura/data/sakura_kaika.html"
MANKAI_URL = "https://www.data.jma.go.jp/sakura/data/sakura_mankai.html"
HEADER_CELLS = {"地点名", "観測日", "平年差(日)", "平年日", "昨年差(日)", "昨年日"}


def _cells(tr: str) -> list[str]:
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]


def _count_observed(page: str) -> int:
    page = re.sub(r"<(script|style).*?</\1>", "", page, flags=re.S)
    n = 0
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S):
        cells = _cells(tr)
        if len(cells) < 2:
            continue
        place, observed = cells[0], cells[1]
        if not place or place in HEADER_CELLS or "月" not in observed:
            continue
        n += 1
    return n


def collect() -> list[Observation]:
    observed_at = now_jst().replace(microsecond=0).isoformat(timespec="seconds")
    out: list[Observation] = []

    try:
        kaika_page = fetch(KAIKA_URL, timeout=20).decode("utf-8", errors="replace")
        n_kaika = _count_observed(kaika_page)
        out.append(Observation("sakura-kaika-points", n_kaika, observed_at, {
            "caption": f"さくらが開花した地点は全国{n_kaika}地点" if n_kaika else "まだ開花の便りはない",
        }))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! jma_sakura(開花): {exc}")

    try:
        mankai_page = fetch(MANKAI_URL, timeout=20).decode("utf-8", errors="replace")
        n_mankai = _count_observed(mankai_page)
        out.append(Observation("sakura-mankai-points", n_mankai, observed_at, {
            "caption": f"さくらが満開した地点は全国{n_mankai}地点" if n_mankai else "まだ満開の便りはない",
        }))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! jma_sakura(満開): {exc}")

    return out
