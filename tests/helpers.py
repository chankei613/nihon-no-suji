"""テスト用のヘルパ。fixture 読み込みと fetch のモック。"""
from __future__ import annotations

import contextlib
from pathlib import Path
from unittest import mock

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def fixture_text(name: str, encoding: str = "utf-8") -> str:
    return (FIXTURES / name).read_text(encoding=encoding)


@contextlib.contextmanager
def patch_fetch(collector_module: str, url_to_fixture: dict[str, str]):
    """collectors.<mod>.fetch を、URL部分一致で fixture を返す関数に差し替える。"""

    def fake_fetch(url: str, **_kw) -> bytes:
        for needle, fname in url_to_fixture.items():
            if needle in url:
                return fixture_bytes(fname)
        raise AssertionError(f"想定外のURL: {url}")

    with mock.patch(f"{collector_module}.fetch", side_effect=fake_fetch):
        yield
