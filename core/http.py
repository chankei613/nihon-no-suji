"""共通HTTP取得ユーティリティ。

気象庁の非公式JSON/CSVや各官庁のHTMLは落ちる前提。
ブラウザUA固定・タイムアウト・指数バックオフ・リトライを標準で入れる。
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request

# 官庁系サイトは非ブラウザUAを弾くことがある（www1.river.go.jp など）
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36 "
    "(+nihon-no-suji data collector)"
)


class FetchError(RuntimeError):
    pass


def fetch(url: str, *, timeout: float = 20.0, retries: int = 3, backoff: float = 2.0) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise FetchError(f"fetch failed after {retries} tries: {url}: {last}")


def fetch_text(url: str, *, encoding: str = "utf-8", **kwargs) -> str:
    return fetch(url, **kwargs).decode(encoding, errors="replace")
