"""Phase 3 carousel (UGC image) tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from frio.config import Config
from frio.connectors.image_ugc import ImageGenResult
from frio.modules import creation
from frio.pipeline import run_phase3_carousel
from frio.spend import SpendCapError


@dataclass
class FakeImageGen:
    cost: float = 0.10
    name: str = "fake_img"

    def generate(self, prompt: str) -> ImageGenResult:
        return ImageGenResult(uri="x://s.png", cost_usd=self.cost, provider=self.name,
                              meta={"offline": False})


PRODUCT = {"title": "369 method tee", "metadata": {"blank": "tee"}}
HOOKS = ["Stop scrolling. This is your sign."]


def test_carousel_brief_has_hook_hero_and_cta() -> None:
    brief = creation.build_carousel_brief(PRODUCT, HOOKS, n_slides=4)
    assert len(brief["slides"]) == 4
    assert brief["slides"][0]["caption"] == HOOKS[0]  # hero = hook
    assert all(s["image_prompt"] for s in brief["slides"])


def test_carousel_preview_costs_n_times_list_price() -> None:
    out = creation.preview_carousel(PRODUCT, HOOKS, Config(), n_slides=5)
    assert out["slides"] == 5
    assert out["estimated_cost_usd"] == round(0.10 * 5, 4)
    assert out["live"] is False


def test_carousel_render_blocked_when_disabled() -> None:
    with pytest.raises(PermissionError):
        creation.render_carousel({"hook": "h", "slides": [{"caption": "c",
                                 "image_prompt": "p"}]}, Config(creation_enabled=False),
                                 approve=True)


def test_carousel_per_image_cap_enforced(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'c.db'}"
    cfg = Config(creation_enabled=True, per_image_cost_cap_usd=0.05,
                 daily_spend_cap_usd=100, database_url=url)
    brief = {"hook": "h", "slides": [{"caption": "c", "image_prompt": "p"}]}
    with pytest.raises(SpendCapError):  # $0.10 image > $0.05 cap
        creation.render_carousel(brief, cfg, approve=True,
                                 image_gen=FakeImageGen(cost=0.10), database_url=url)


def test_carousel_renders_and_persists_slides(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'c2.db'}"
    cfg = Config(creation_enabled=True, per_image_cost_cap_usd=1.0,
                 daily_spend_cap_usd=100, database_url=url)
    brief = creation.build_carousel_brief(PRODUCT, HOOKS, n_slides=3)
    out = creation.render_carousel(brief, cfg, approve=True,
                                   image_gen=FakeImageGen(cost=0.10), database_url=url)
    assert len(out["slides"]) == 3
    assert round(out["total_cost_usd"], 2) == 0.30

    from frio.db.base import make_session_factory
    from frio.db.models import ImageAsset, SpendLedger

    Session = make_session_factory(url)
    with Session() as s:
        assert s.query(ImageAsset).count() == 3
        assert s.query(SpendLedger).count() == 3


def test_run_phase3_carousel_offline_render(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'c3.db'}"
    cfg = Config(creation_enabled=True, database_url=url)  # caps 0 ok: $0 placeholders
    res = run_phase3_carousel(config=cfg, slides=3, approve=True)
    assert res.rendered and res.rendered["offline"] is True
    assert len(res.rendered["slides"]) == 3
