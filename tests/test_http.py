"""API client pagination tests with a fake transport."""

from __future__ import annotations

from cta.config import load_config
from cta.http import CtgovClient


class FakeClient(CtgovClient):
    """CtgovClient whose fetch_page serves scripted pages."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.cfg = load_config().api

    async def fetch_page(self, term, page_size, page_token, fields):
        if not self.pages:
            return [], None
        studies, token = self.pages.pop(0)
        return studies, token


async def test_iter_studies_pages_until_done():
    client = FakeClient([
        (["s1", "s2"], "t1"),
        (["s3"], None),
    ])
    studies = [s async for s in client.iter_studies("q", 100, 10, [])]
    assert studies == ["s1", "s2", "s3"]


async def test_iter_studies_respects_max():
    client = FakeClient([(["s1", "s2", "s3"], "t1"), (["s4"], None)])
    studies = [s async for s in client.iter_studies("q", 2, 10, [])]
    assert studies == ["s1", "s2"]