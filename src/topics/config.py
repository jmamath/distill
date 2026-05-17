"""Topic configuration schema and loaders for the research briefing system.

A TopicConfig answers every pipeline question that is topic-specific:
what signal classes to accept, which sources to prioritise, how to organise
knowledge into a taxonomy, which dimensions to score on, and which action
labels the brief may recommend.

Swapping topic.md (plus the matching audience profile) is all that should be
needed to retarget the pipeline to a new research area — no orchestration code
changes required.

Public API:
    SignalClass          — recognised signal types a topic can enable
    ActionLabel          — allowed action recommendations in a brief
    FeedConfig           — one RSS feed entry (id, name, url)
    ScoringDimension     — one evaluation axis for a signal
    TaxonomyEntry        — one subtopic area in the topic taxonomy
    AudienceProfile      — loaded from data/audiences/{audience_ref}.md
    TopicConfig          — full validated topic configuration
    load_topic_config(path)      — parse topic.md frontmatter → TopicConfig
    load_audience_profile(path)  — parse audience .md frontmatter → AudienceProfile
"""

import logging
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

import yaml

from topics.frontmatter import load_frontmatter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SignalClass(str, Enum):
    """Recognised signal types that a topic config can enable or disable."""

    paper = "paper"
    lab_post = "lab_post"
    dataset_release = "dataset_release"
    benchmark_release = "benchmark_release"
    engineering_writeup = "engineering_writeup"
    startup_launch = "startup_launch"


class ActionLabel(str, Enum):
    """Allowed action recommendations a brief can emit for a signal."""

    ignore = "ignore"
    monitor = "monitor"
    prototype = "prototype"
    invest = "invest"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class FeedConfig(BaseModel):
    """One RSS feed entry in a topic's source list."""

    id: str    # stable kebab-case id (e.g. "cs-ai", "openai-blog")
    name: str  # human-readable label
    url: str   # RSS feed URL


class ScoringDimension(BaseModel):
    """One axis used to evaluate how important a signal is."""

    id: str
    name: str
    description: str


class TaxonomyEntry(BaseModel):
    """One subtopic area within the topic taxonomy."""

    id: str
    name: str
    theme_ref: str | None = None  # e.g. "themes/synthetic-data-generation.md"


# ---------------------------------------------------------------------------
# Audience profile
# ---------------------------------------------------------------------------


class AudienceProfile(BaseModel):
    """Loaded from data/audiences/{audience_ref}.md frontmatter.

    Informs scoring (how to weigh importance to this audience), explanation
    style, recommended action framing, and briefing tone.
    """

    audience_id: str
    name: str
    description: str
    persona: str
    scope: str
    tone: str


# ---------------------------------------------------------------------------
# Topic config
# ---------------------------------------------------------------------------


class TopicConfig(BaseModel):
    """Full validated topic configuration.

    Every pipeline stage that depends on the active topic reads from this
    object, not from scattered config files or hardcoded strings.

    Required fields (topic_id, name, thesis, audience_ref) are the minimum
    needed to start any pipeline run. All other fields have sensible defaults
    so that a minimal topic config is still valid.
    """

    # Core identity — required
    topic_id: str
    name: str
    thesis: str
    audience_ref: str

    # Time scope — separate horizons for bootstrap deep-research vs. live ingestion
    bootstrap_horizon: str | None = None
    signal_horizon: str | None = None

    # Signal filtering
    scope_in: list[str] = Field(default_factory=list)
    scope_out: list[str] = Field(default_factory=list)
    signal_classes: list[SignalClass] = Field(default_factory=list)

    # Source priorities — ordered most-to-least preferred
    source_priorities: list[str] = Field(default_factory=list)

    # Active adapters for live ingestion — subset of source_priorities that
    # have a registered SourceAdapter implementation.
    enabled_sources: list[str] = Field(default_factory=list)

    # RSS feeds per adapter type — verified reachable at config authoring time.
    arxiv_feeds: list[FeedConfig] = Field(default_factory=list)
    blog_feeds: list[FeedConfig] = Field(default_factory=list)

    # Knowledge organisation
    taxonomy: list[TaxonomyEntry] = Field(default_factory=list)

    # Scoring rubrics — one set per pass
    pass1_dimensions: list[ScoringDimension] = Field(default_factory=list)
    pass2_dimensions: list[ScoringDimension] = Field(default_factory=list)

    # Actions
    action_vocabulary: list[ActionLabel] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_topic_config(topic_md_path: Path) -> TopicConfig:
    """Parse topic.md frontmatter and return a validated TopicConfig.

    Args:
        topic_md_path: Path to a topic.md file with YAML frontmatter.

    Returns:
        A validated TopicConfig.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the frontmatter is missing, not valid YAML, or fails
            schema validation.
    """
    try:
        fm_dict, _ = load_frontmatter(topic_md_path)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Invalid YAML frontmatter in {topic_md_path}: {exc}"
        ) from exc

    if not fm_dict:
        raise ValueError(f"{topic_md_path} has no YAML frontmatter block")

    try:
        config = TopicConfig(**fm_dict)
    except ValidationError as exc:
        raise ValueError(
            f"topic.md frontmatter does not match TopicConfig schema: {exc}"
        ) from exc

    logger.info("Loaded topic config: %s (%s)", config.topic_id, config.name)
    return config


def load_audience_profile(audience_md_path: Path) -> AudienceProfile:
    """Parse an audience profile Markdown file and return a validated AudienceProfile.

    Args:
        audience_md_path: Path to an audience .md file with YAML frontmatter.

    Returns:
        A validated AudienceProfile.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the frontmatter is missing, not valid YAML, or fails
            schema validation.
    """
    try:
        fm_dict, _ = load_frontmatter(audience_md_path)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Invalid YAML frontmatter in {audience_md_path}: {exc}"
        ) from exc

    if not fm_dict:
        raise ValueError(f"{audience_md_path} has no YAML frontmatter block")

    try:
        profile = AudienceProfile(**fm_dict)
    except ValidationError as exc:
        raise ValueError(
            f"Audience profile does not match AudienceProfile schema: {exc}"
        ) from exc

    logger.info("Loaded audience profile: %s", profile.audience_id)
    return profile
