"""Phase 3 (AI-UGC creation) + spend-cap tests."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from frio.config import Config
from frio.connectors.video_gen import VideoGenResult
from frio.modules import creation
from frio.pipeline import run_phase3
from frio.spend import SpendCapError


@dataclass
class FakeGen:
    """A generator that reports a non-zero cost, to exercise spend caps."""

    cost: float = 5.0
    name: str = "fake"

    def generate(self, prompt: str) -> VideoGenResult:
        return VideoGenResult(uri="x://v.mp4", cost_usd=self.cost, provider=self.name,
                              meta={"offline": False})


PRODUCT = {"title": "369 method tee", "metadata": {"blank": "tee", "theme": "369 method tee",
                                                   "mockup_uri": "placeholder://m.png"}}
HOOKS = ["Stop scrolling. This is your sign."]


def test_preview_spends_nothing() -> None:
    cfg = Config()
    out = creation.preview(PRODUCT, HOOKS, cfg)
    assert out["brief"]["video_prompt"]
    # angle is taken from the product "theme" (not a stale "keyword" key)
    assert out["brief"]["angle"] == "369 method tee"
    assert out["estimated_cost_usd"] == 0.50  # informational list price
    assert out["live"] is False


def test_render_blocked_when_creation_disabled() -> None:
    cfg = Config(creation_enabled=False)
    with pytest.raises(PermissionError):
        creation.render_video({"hook": "h", "video_prompt": "p"}, cfg, approve=True)


def test_render_blocked_without_approval() -> None:
    cfg = Config(creation_enabled=True)
    with pytest.raises(PermissionError):
        creation.render_video({"hook": "h", "video_prompt": "p"}, cfg, approve=False)


def test_render_blocked_when_cost_exceeds_cap(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'cap.db'}"
    cfg = Config(creation_enabled=True, per_clip_cost_cap_usd=1.0, daily_spend_cap_usd=100,
                 database_url=url)
    with pytest.raises(SpendCapError):
        creation.render_video({"hook": "h", "video_prompt": "p"}, cfg, approve=True,
                              video_gen=FakeGen(cost=5.0), database_url=url)


def test_render_succeeds_within_caps_and_records_spend(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'ok.db'}"
    cfg = Config(creation_enabled=True, per_clip_cost_cap_usd=10, daily_spend_cap_usd=100,
                 database_url=url)
    out = creation.render_video({"hook": "h", "video_prompt": "p"}, cfg, approve=True,
                                video_gen=FakeGen(cost=5.0), database_url=url)
    assert out["approved"] and out["cost_usd"] == 5.0

    from frio.db.base import make_session_factory
    from frio.db.models import SpendLedger, VideoAsset

    Session = make_session_factory(url)
    with Session() as s:
        assert s.query(VideoAsset).count() == 1
        assert s.query(SpendLedger).count() == 1
        assert s.query(SpendLedger).one().amount_usd == 5.0


def test_daily_cap_accumulates(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'daily.db'}"
    cfg = Config(creation_enabled=True, per_clip_cost_cap_usd=10, daily_spend_cap_usd=8,
                 database_url=url)
    creation.render_video({"hook": "a", "video_prompt": "p"}, cfg, approve=True,
                          video_gen=FakeGen(cost=5.0), database_url=url)
    # second $5 render would push the day to $10 > $8 cap
    with pytest.raises(SpendCapError):
        creation.render_video({"hook": "b", "video_prompt": "p"}, cfg, approve=True,
                              video_gen=FakeGen(cost=5.0), database_url=url)


def test_run_phase3_preview_offline() -> None:
    res = run_phase3(config=Config(database_url="sqlite://"), persist=False)
    assert res.product and res.brief
    assert res.rendered is None  # no approval => preview only


def test_run_phase3_render_gate_blocks_when_disabled() -> None:
    # creation disabled by default => approve attempt is gracefully gated
    res = run_phase3(config=Config(database_url="sqlite://"), approve=True, persist=False)
    assert res.rendered is None
    assert "disabled" in (res.gate_message or "")


def test_run_phase3_render_offline_when_enabled(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'p3.db'}"
    cfg = Config(creation_enabled=True, database_url=url)  # caps 0 ok: placeholder costs $0
    res = run_phase3(config=cfg, approve=True)
    assert res.rendered is not None
    assert res.rendered["cost_usd"] == 0.0 and res.rendered["offline"] is True
