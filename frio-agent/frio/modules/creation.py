"""Phase 3 — AI-UGC video creation (semi-gated).

Turns a demand-validated product + a mined hook into a 30s UGC ad brief, then
renders an MP4. Rendering is GATED: it requires ``creation_enabled``, explicit
human approval, and passes the per-clip + daily spend caps (enforced against the
spend ledger). Preview is ungated and spends nothing.
"""

from __future__ import annotations

from ..capabilities import capability
from ..compliance import review_creative
from ..config import Config, load_config
from ..connectors.image_ugc import HiggsfieldImageGenerator, ImageGenResult
from ..connectors.video_gen import PlaceholderVideoGenerator, VideoGenResult
from ..db.base import init_db, make_session_factory
from ..db.models import Decision, ImageAsset, VideoAsset
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
    """Build the brief + cost + compliance check. Spends nothing (ungated)."""
    brief = build_brief(product, hooks, llm)
    # NOTE: AI-UGC disclosure injection deferred (see NOTES). Claims scan stays on.
    gen = PlaceholderVideoGenerator(config)
    text = f"{brief.get('hook', '')} {brief.get('video_prompt', '')}"
    compliance = review_creative(text, requires_ai_disclosure=config.require_ai_disclosure)
    return {"brief": brief, "estimated_cost_usd": gen.estimate(),
            "provider": gen.name, "live": gen.available(), "compliance": compliance}


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


# --- Carousel (UGC image) ad creation ---------------------------------------

CAROUSEL_SYSTEM = (
    "You are a UGC ad creative director. Design a TikTok/Meta image carousel ad. "
    "Return ONLY JSON: {hook, slides:[{caption, image_prompt}]}. Slide 1 is the "
    "scroll-stopping hero with the hook; middle slides show benefits/lifestyle/"
    "social proof; the last slide is a clear CTA."
)


def build_carousel_brief(product: dict, hooks: list[str], n_slides: int = 4,
                         llm: LLMClient | None = None) -> dict:
    """Assemble an image-carousel brief (one image_prompt per slide)."""
    hook = (hooks[0] if hooks else f"{product['title']} — this is your sign").strip()
    meta = product.get("metadata", {})
    blank = meta.get("blank", "tee")

    if llm is not None and llm.available():
        prompt = (f"Product: {product['title']} ({blank}). Hook: {hook!r}. "
                  f"Slides: {n_slides}. Write the JSON carousel brief.")
        data = llm.complete_json(CAROUSEL_SYSTEM, prompt)
        if data.get("slides"):
            data.setdefault("_engine", "claude")
            return data

    roles = ["hero hook shot", "benefit close-up", "lifestyle in-use", "social proof",
             "clear CTA"]
    slides = []
    for i in range(max(2, n_slides)):
        role = roles[i] if i < len(roles) else "lifestyle in-use"
        caption = hook if i == 0 else f"{product['title']}: {role}"
        slides.append({
            "caption": caption,
            "image_prompt": (f"{role} of {product['title']} ({blank}), spirituality/"
                             f"wellbeing aesthetic, soft natural light, editorial UGC "
                             f"style, on-image caption '{caption}'"),
        })
    return {"hook": hook, "slides": slides, "_engine": "heuristic"}


def preview_carousel(product: dict, hooks: list[str], config: Config, n_slides: int = 4,
                     llm: LLMClient | None = None) -> dict:
    """Build the carousel brief + show the would-be cost (spends nothing)."""
    brief = build_carousel_brief(product, hooks, n_slides, llm)
    # NOTE: AI-UGC disclosure injection deferred (see NOTES). Claims scan stays on.
    gen = HiggsfieldImageGenerator(config)
    text = " ".join([brief.get("hook", "")] + [s["caption"] for s in brief["slides"]])
    compliance = review_creative(text, requires_ai_disclosure=config.require_ai_disclosure)
    return {"brief": brief, "slides": len(brief["slides"]),
            "estimated_cost_usd": round(gen.estimate() * len(brief["slides"]), 4),
            "provider": gen.name, "live": gen.available(), "compliance": compliance}


def render_carousel(brief: dict, config: Config, *, approve: bool,
                    image_gen=None, database_url: str | None = None) -> dict:
    """Render each carousel slide. GATED: creation_enabled + approval + spend caps."""
    if not config.creation_enabled:
        raise PermissionError(
            "creation is disabled — set FRIO_CREATION_ENABLED=1 to allow rendering.")
    if not approve:
        raise PermissionError(
            "render requires explicit human approval (pass approve=True / --approve).")

    gen = image_gen or HiggsfieldImageGenerator(config)
    database_url = database_url or config.database_url
    init_db(database_url)
    Session = make_session_factory(database_url)

    rendered, total = [], 0.0
    with Session() as s:
        for idx, slide in enumerate(brief["slides"]):
            result: ImageGenResult = gen.generate(slide["image_prompt"])
            # Each image is guarded individually against the per-image + daily caps.
            guard_and_record(s, config, category="creation", amount=result.cost_usd,
                             reference=f"carousel:{brief.get('hook')}:{idx}",
                             per_item_cap=config.per_image_cost_cap_usd)
            s.add(ImageAsset(provider=result.provider, uri=result.uri, slide_index=idx,
                             cost_usd=result.cost_usd, approved=True))
            rendered.append({"slide": idx, "uri": result.uri,
                             "caption": slide["caption"], "cost_usd": result.cost_usd})
            total += result.cost_usd
        s.add(Decision(kind="render_carousel", actor="human", target=brief.get("hook"),
                       rationale="approved UGC carousel render",
                       payload={"slides": len(rendered), "total_cost_usd": total,
                                "provider": gen.name}))
        s.commit()
    return {"slides": rendered, "total_cost_usd": total, "approved": True,
            "offline": all(r["cost_usd"] == 0.0 for r in rendered)}


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


@capability(
    "creation.carousel_preview",
    "Build a UGC image-carousel brief + estimated cost (no spend).",
    parameters={"product": {"type": "object", "required": True}},
    category="research",
)
def _cap_carousel_preview(product: dict, hooks: list[str], n_slides: int = 4,
                          config: Config | None = None) -> dict:
    config = config or load_config()
    return preview_carousel(product, hooks, config, n_slides, make_llm(config))


@capability(
    "creation.render_carousel",
    "Render a UGC image carousel (spends money — gated + HITL + spend caps).",
    parameters={"brief": {"type": "object", "required": True},
                "approve": {"type": "boolean", "required": True}},
    enabled=lambda c: c.creation_enabled,
    disabled_reason="AI-UGC rendering disabled (set FRIO_CREATION_ENABLED=1 and "
    "FRIO_PER_IMAGE_COST_CAP_USD / FRIO_DAILY_SPEND_CAP_USD).",
    category="gated",
)
def _cap_render_carousel(brief: dict, approve: bool, config: Config | None = None) -> dict:
    config = config or load_config()
    return render_carousel(brief, config, approve=approve)
