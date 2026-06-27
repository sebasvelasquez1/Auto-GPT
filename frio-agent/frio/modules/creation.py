"""Phase 3 — AI-UGC video creation (semi-gated).

Turns a demand-validated product + a mined hook into a 30s UGC ad brief, then
renders an MP4. Rendering is GATED: it requires ``creation_enabled``, explicit
human approval, and passes the per-clip + daily spend caps (enforced against the
spend ledger). Preview is ungated and spends nothing.
"""

from __future__ import annotations

from ..capabilities import capability
from ..config import Config, load_config
from ..connectors.video_gen import PlaceholderVideoGenerator, VideoGenResult
from ..db.base import init_db, make_session_factory
from ..db.models import Decision, VideoAsset
from ..llm.client import LLMClient, make_llm
from ..spend import guard_and_record

BRIEF_SYSTEM = (
    "You are a UGC ad creative director. Given a product and a hook, write a 30s "
    "TikTok UGC ad brief. Return ONLY JSON with keys: hook, angle, "
    "funnel_stage (cold|warm|retargeting), video_prompt (a vivid shot-by-shot "
    "prompt for an AI video generator)."
)


def build_brief(product: dict, hooks: list[str], llm: LLMClient | None = None) -> dict:
    """Assemble a creative brief from a product + the strategist's hook bank."""
    hook = (hooks[0] if hooks else f"{product['title']} — this is your sign").strip()
    meta = product.get("metadata", {})
    blank = meta.get("blank", "tee")

    if llm is not None and llm.available():
        prompt = (f"Product: {product['title']} ({blank}). Hook: {hook!r}. "
                  f"Mockup: {meta.get('mockup_uri')}. Write the JSON brief.")
        data = llm.complete_json(BRIEF_SYSTEM, prompt)
        if data.get("video_prompt"):
            data.setdefault("_engine", "claude")
            return data

    video_prompt = (
        f"30s UGC TikTok ad, spirituality/wellbeing aesthetic. "
        f"First 2s hook on screen: '{hook}'. Creator holds the {product['title']} "
        f"({blank}); soft natural light, lifestyle b-roll, on-screen captions, "
        f"calm trending audio, soft CTA 'tap to shop'."
    )
    return {
        "hook": hook, "angle": meta.get("keyword", product["title"]),
        "funnel_stage": "cold", "video_prompt": video_prompt, "_engine": "heuristic",
    }


def preview(product: dict, hooks: list[str], config: Config,
            llm: LLMClient | None = None) -> dict:
    """Build the brief + show the would-be cost. Spends nothing (ungated)."""
    brief = build_brief(product, hooks, llm)
    gen = PlaceholderVideoGenerator(config)
    return {"brief": brief, "estimated_cost_usd": gen.estimate(),
            "provider": gen.name, "live": gen.available()}


def render_video(brief: dict, config: Config, *, approve: bool,
                 video_gen=None, database_url: str | None = None) -> dict:
    """Render the MP4. GATED: creation_enabled + human approval + spend caps."""
    if not config.creation_enabled:
        raise PermissionError(
            "creation is disabled — set FRIO_CREATION_ENABLED=1 to allow rendering.")
    if not approve:
        raise PermissionError(
            "render requires explicit human approval (pass approve=True / --approve).")

    gen = video_gen or PlaceholderVideoGenerator(config)
    result: VideoGenResult = gen.generate(brief["video_prompt"])

    database_url = database_url or config.database_url
    init_db(database_url)
    Session = make_session_factory(database_url)
    with Session() as s:
        # Enforce caps + record spend BEFORE persisting the asset.
        guard_and_record(s, config, category="creation", amount=result.cost_usd,
                         reference=brief.get("hook"))
        asset = VideoAsset(provider=result.provider, uri=result.uri,
                           cost_usd=result.cost_usd, approved=True)
        s.add(asset)
        s.add(Decision(kind="render", actor="human", target=brief.get("hook"),
                       rationale="approved AI-UGC render",
                       payload={"provider": result.provider, "cost_usd": result.cost_usd,
                                "offline": result.meta.get("offline", False)}))
        s.commit()
        return {"uri": result.uri, "provider": result.provider,
                "cost_usd": result.cost_usd, "approved": True,
                "offline": result.meta.get("offline", False)}


@capability(
    "creation.preview",
    "Build a UGC ad brief + estimated render cost (no spend).",
    parameters={"product": {"type": "object", "required": True}},
    category="research",
)
def _cap_preview(product: dict, hooks: list[str], config: Config | None = None) -> dict:
    config = config or load_config()
    return preview(product, hooks, config, make_llm(config))


@capability(
    "creation.render_video",
    "Render a ~30s AI-UGC MP4 (spends money — gated + HITL + spend caps).",
    parameters={"brief": {"type": "object", "required": True},
                "approve": {"type": "boolean", "required": True}},
    enabled=lambda c: c.creation_enabled,
    disabled_reason="AI-UGC rendering disabled (set FRIO_CREATION_ENABLED=1 and "
    "FRIO_PER_CLIP_COST_CAP_USD / FRIO_DAILY_SPEND_CAP_USD).",
    category="gated",
)
def _cap_render(brief: dict, approve: bool, config: Config | None = None) -> dict:
    config = config or load_config()
    return render_video(brief, config, approve=approve)
