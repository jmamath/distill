"""Frontmatter models and file helpers for topic wiki Markdown files.

Every wiki file (topic.md, themes/*.md, overview.md) is Markdown with a YAML
frontmatter block.  Reference data (entities, timeline, open_questions) lives as
flat JSON arrays at the topic root, not as per-file Markdown.

This module provides:
  - Pydantic models that define the expected frontmatter schema per file type.
  - load_frontmatter(path)  — parse frontmatter + body from an existing file.
  - write_with_frontmatter(path, frontmatter, body) — write a file atomically.
  - update_frontmatter(path, updates) — merge a dict into existing frontmatter.

Usage:
    from topics.frontmatter import load_frontmatter, ThemeFrontmatter
    fm_dict, body = load_frontmatter(path)
    theme = ThemeFrontmatter(**fm_dict)
"""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_DELIMITER = "---"
_FENCE_OPEN = f"{_DELIMITER}\n"
_FENCE_SEP = f"\n{_DELIMITER}\n"


# ---------------------------------------------------------------------------
# Frontmatter Pydantic models
# ---------------------------------------------------------------------------


class TopicFrontmatter(BaseModel):
    """Frontmatter for topic.md — the top-level topic configuration file."""

    topic_id: str
    name: str
    thesis: str
    audience_ref: str | None = None
    bootstrap_horizon: str | None = None
    scope_in: list[str] = Field(default_factory=list)
    scope_out: list[str] = Field(default_factory=list)


class ThemeFrontmatter(BaseModel):
    """Frontmatter for themes/{theme_id}.md."""

    id: str
    name: str
    description: str
    taxonomy_ref: str | None = None
    origin: str = "bootstrap"
    novelty_status: str = "globally_novel"
    key_entity_ids: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class OverviewFrontmatter(BaseModel):
    """Frontmatter for overview.md."""

    topic_id: str
    generated_at: str
    origin: str = "bootstrap"


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def load_frontmatter(path: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter and Markdown body from a file.

    Args:
        path: Path to an existing Markdown file.

    Returns:
        A (frontmatter_dict, body_str) tuple. frontmatter_dict is empty if
        the file has no frontmatter delimiters.

    Raises:
        FileNotFoundError: if path does not exist.
        yaml.YAMLError: if the frontmatter block is not valid YAML.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith(_FENCE_OPEN):
        return {}, text

    try:
        end = text.index(_FENCE_SEP, len(_FENCE_OPEN))
    except ValueError:
        # Opening --- exists but closing --- not found; treat whole file as body.
        logger.warning("Unclosed frontmatter block in %s — treating as body only", path)
        return {}, text

    fm_text = text[len(_FENCE_OPEN) : end]
    body = text[end + len(_FENCE_SEP) :]
    fm_dict: dict = yaml.safe_load(fm_text) or {}
    return fm_dict, body


def write_with_frontmatter(path: Path, frontmatter: dict, body: str) -> None:
    """Write a Markdown file with YAML frontmatter.

    Creates parent directories if they do not exist.

    Args:
        path: Destination file path.
        frontmatter: Dictionary to serialize as YAML frontmatter.
        body: Markdown body text (written after the closing --- delimiter).

    Raises:
        OSError: if the file cannot be written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.safe_dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    path.write_text(f"{_FENCE_OPEN}{yaml_text}{_DELIMITER}\n{body}", encoding="utf-8")
    logger.debug("Wrote %s", path)


def update_frontmatter(path: Path, updates: dict) -> None:
    """Merge updates into the frontmatter of an existing file, preserving body.

    Args:
        path: Path to an existing Markdown file with frontmatter.
        updates: Dict of keys to overwrite or add in the frontmatter.

    Raises:
        FileNotFoundError: if path does not exist.
        yaml.YAMLError: if the existing frontmatter is not valid YAML.
    """
    fm, body = load_frontmatter(path)
    fm.update(updates)
    write_with_frontmatter(path, fm, body)
    logger.debug("Updated frontmatter in %s", path)
