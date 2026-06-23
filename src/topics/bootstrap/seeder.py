"""Bootstrap seeder — writes initial topic wiki files from a ParsedDossier.

Given a validated ParsedDossier (from parser.py) and a target topic directory,
the seeder creates:

  themes/{theme_id}.md       — one file per theme (frontmatter + full prose section)
  entities.json              — flat JSON array of entity records
  timeline.json              — flat JSON array of timeline entries
  hypotheses.json            — flat JSON array of uniform-prior hypothesis records
  overview.md                — intro prose + theme list + low-evidence hypotheses
  dossiers/bootstrap_{date}.md — archived raw dossier text

Idempotency contract:
  - theme files are skipped if a file with the same id already exists.
  - entities.json, timeline.json, hypotheses.json: load → merge by id → write.
    New ids are appended; existing ids are unchanged.
  - overview.md is always rewritten from current state (deterministic render).
  - The raw dossier is archived with a date-based name; existing archives are
    never overwritten (a suffix counter is appended if needed).

No file is written if parse_dossier() has already rejected the input — the caller
must always call parse_dossier() before seed_topic().

Usage (CLI — from the project root, venv active):
    source .venv/bin/activate
    PYTHONPATH=src python -m topics.bootstrap.seeder \
        --dossier data/research_topics/data_advantage/dossiers/bootstrap_2026-04-25.md

    # --topic-dir defaults to the dossier's grandparent (dossiers/../..)
    # --date     defaults to today (YYYY-MM-DD); also accepts an explicit value:
    PYTHONPATH=src python -m topics.bootstrap.seeder \
        --dossier  data/research_topics/data_advantage/dossiers/bootstrap_2026-04-25.md \
        --topic-dir data/research_topics/data_advantage \
        --date 2026-04-25

Usage (Python API):
    from topics.bootstrap.parser import parse_dossier
    from topics.bootstrap.seeder import seed_topic
    from pathlib import Path

    dossier_path = Path("data/research_topics/data_advantage/dossiers/bootstrap_2026-04-25.md")
    topic_dir    = Path("data/research_topics/data_advantage")

    dossier_text = dossier_path.read_text()
    parsed = parse_dossier(dossier_text)
    seed_topic(topic_dir, parsed, dossier_raw=dossier_text, dossier_date="2026-04-25")
"""

import argparse
import datetime
import logging
import sys
from pathlib import Path

from topics.bootstrap.parser import DossierPayload, ParsedDossier, parse_dossier
from topics.frontmatter import (
    OverviewFrontmatter,
    ThemeFrontmatter,
    load_frontmatter,
    write_with_frontmatter,
)
from topics.storage import load_json_array, merge_by_id, save_json_array

logger = logging.getLogger(__name__)

_ACTION_POSTURE_ORDER = {"invest": 0, "prototype": 1, "monitor": 2, "ignore": 3}
_TOP_HYPOTHESES_N = 5


def seed_topic(
    topic_dir: Path,
    parsed: ParsedDossier,
    dossier_raw: str,
    dossier_date: str,
    dossier_source: Path | None = None,
) -> None:
    """Seed a topic wiki directory from a validated ParsedDossier.

    Args:
        topic_dir: Root directory for the topic (e.g. data/research_topics/data_advantage).
        parsed: Validated ParsedDossier produced by parse_dossier().
        dossier_raw: Original raw dossier text to archive.
        dossier_date: ISO date string (YYYY-MM-DD) used to name the archived dossier.
        dossier_source: Optional path to the source dossier file. When provided and
            the file already lives inside topic_dir/dossiers/, the archive step is
            skipped to avoid creating a redundant copy.

    Raises:
        OSError: if any file write fails.
    """
    topic_dir.mkdir(parents=True, exist_ok=True)
    _archive_dossier(topic_dir, dossier_raw, dossier_date, source=dossier_source)
    _seed_themes(topic_dir, parsed, dossier_date)
    _seed_entities_json(topic_dir, parsed.payload)
    _seed_timeline_json(topic_dir, parsed.payload)
    _seed_hypotheses_json(topic_dir, parsed.payload, dossier_date)
    _seed_overview(topic_dir, parsed, dossier_date)
    logger.info("Seeding complete for topic directory: %s", topic_dir)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _archive_dossier(
    topic_dir: Path, raw_text: str, date: str, source: Path | None = None
) -> None:
    """Archive the raw dossier text under dossiers/bootstrap_{date}.md.

    Skips the copy if source is already inside topic_dir/dossiers/ — the file
    is already in the right place and duplicating it would create noise.
    If the target filename already exists, appends a numeric suffix.
    """
    dossiers_dir = topic_dir / "dossiers"
    dossiers_dir.mkdir(exist_ok=True)

    if source is not None and source.resolve().parent == dossiers_dir.resolve():
        logger.debug("Dossier already in dossiers/ — skipping archive copy")
        return

    base_name = f"bootstrap_{date}"
    dest = dossiers_dir / f"{base_name}.md"
    counter = 1
    while dest.exists():
        dest = dossiers_dir / f"{base_name}_{counter}.md"
        counter += 1
    dest.write_text(raw_text, encoding="utf-8")
    logger.debug("Archived dossier → %s", dest)


def _seed_themes(topic_dir: Path, parsed: ParsedDossier, date: str) -> None:
    themes_dir = topic_dir / "themes"
    themes_dir.mkdir(exist_ok=True)
    for theme in parsed.payload.themes:
        dest = themes_dir / f"{theme.id}.md"
        if dest.exists():
            logger.debug("Theme already exists, skipping: %s", theme.id)
            continue
        fm = ThemeFrontmatter(
            id=theme.id,
            name=theme.name,
            description=theme.description,
            taxonomy_ref=theme.taxonomy_ref,
            key_entity_ids=theme.key_entity_ids,
            created_at=date,
            updated_at=date,
        )
        body = parsed.theme_sections[theme.id]
        write_with_frontmatter(dest, fm.model_dump(exclude_none=True), body)
        logger.debug("Seeded theme: %s", theme.id)


def _seed_entities_json(topic_dir: Path, payload: DossierPayload) -> None:
    dest = topic_dir / "entities.json"
    merged = merge_by_id(load_json_array(dest), [e.model_dump() for e in payload.entities])
    save_json_array(dest, merged)
    logger.debug("Wrote entities.json (%d total)", len(merged))


def _seed_timeline_json(topic_dir: Path, payload: DossierPayload) -> None:
    dest = topic_dir / "timeline.json"
    merged = merge_by_id(load_json_array(dest), [e.model_dump() for e in payload.timeline])
    save_json_array(dest, merged)
    logger.debug("Wrote timeline.json (%d total)", len(merged))


def _seed_hypotheses_json(topic_dir: Path, payload: DossierPayload, date: str) -> None:
    dest = topic_dir / "hypotheses.json"
    incoming = [
        _hypothesis_record(h.model_dump(exclude_none=True), date) for h in payload.hypotheses
    ]
    merged = merge_by_id(load_json_array(dest), incoming)
    save_json_array(dest, merged)
    logger.debug("Wrote hypotheses.json (%d total)", len(merged))


def _seed_overview(topic_dir: Path, parsed: ParsedDossier, date: str) -> None:
    dest = topic_dir / "overview.md"
    fm = OverviewFrontmatter(topic_id=_infer_topic_id(topic_dir), generated_at=date)

    theme_lines = "\n".join(
        f"- [{t.name}](themes/{t.id}.md) — {t.description}"
        for t in parsed.payload.themes
    )

    hypotheses = load_json_array(topic_dir / "hypotheses.json")
    sorted_hypotheses = sorted(
        hypotheses,
        key=lambda h: (
            _evidence_mass(h),
            _ACTION_POSTURE_ORDER.get(h.get("action_posture", "monitor"), 2),
        ),
    )
    top_n = sorted_hypotheses[:_TOP_HYPOTHESES_N]
    hypothesis_lines = "\n".join(
        f"{i + 1}. {h['statement']}" for i, h in enumerate(top_n)
    )

    intro = parsed.intro.strip()
    body = (f"{intro}\n\n" if intro else "") + (
        f"## Themes\n\n{theme_lines}\n\n## Top Open Hypotheses\n\n{hypothesis_lines}\n"
    )

    write_with_frontmatter(dest, fm.model_dump(), body)
    logger.debug("Wrote overview.md")


def _infer_topic_id(topic_dir: Path) -> str:
    """Return the topic_id from topic.md frontmatter, or fall back to dir name."""
    topic_md = topic_dir / "topic.md"
    if topic_md.exists():
        fm, _ = load_frontmatter(topic_md)
        if "topic_id" in fm:
            return str(fm["topic_id"])
    return topic_dir.name


def _hypothesis_record(hypothesis: dict, date: str) -> dict:
    """Return a durable uniform-prior hypothesis record for initial seeding."""
    record = {
        "id": hypothesis["id"],
        "statement": hypothesis["statement"],
        "theme_ids": hypothesis.get("theme_ids", []),
        "status": "active",
        "belief": {"alpha": 1.0, "beta": 1.0},
        "action_posture": hypothesis.get("action_posture", "monitor"),
        "why_it_matters": hypothesis.get("why_it_matters", ""),
        "depends_on": hypothesis.get("depends_on", []),
        "created_at": date,
        "last_updated_at": date,
    }
    for optional_field in ("resolution_criterion", "comparison"):
        if optional_field in hypothesis:
            record[optional_field] = hypothesis[optional_field]
    return record


def _evidence_mass(hypothesis: dict) -> float:
    """Return the total Beta evidence mass for overview ordering."""
    belief = hypothesis.get("belief", {})
    alpha = float(belief.get("alpha", 1.0))
    beta = float(belief.get("beta", 1.0))
    return alpha + beta


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    arg_parser = argparse.ArgumentParser(
        description="Seed a topic wiki directory from a bootstrap dossier."
    )
    arg_parser.add_argument(
        "--dossier",
        required=True,
        help="Path to the dossier Markdown file.",
    )
    arg_parser.add_argument(
        "--topic-dir",
        help=(
            "Path to the topic root directory. "
            "Defaults to the dossier's grandparent (dossiers/../..)."
        ),
    )
    arg_parser.add_argument(
        "--date",
        help="ISO date (YYYY-MM-DD) for the archive filename and frontmatter. Defaults to today.",
    )
    args = arg_parser.parse_args()

    dossier_path = Path(args.dossier)
    if not dossier_path.exists():
        logger.error("Dossier file not found: %s", dossier_path)
        sys.exit(1)

    topic_dir = Path(args.topic_dir) if args.topic_dir else dossier_path.parent.parent
    date = args.date or datetime.date.today().isoformat()

    try:
        dossier_text = dossier_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Could not read dossier: %s", exc)
        sys.exit(1)

    try:
        parsed = parse_dossier(dossier_text)
    except ValueError as exc:
        logger.error("Dossier rejected: %s", exc)
        sys.exit(1)

    try:
        seed_topic(
            topic_dir, parsed,
            dossier_raw=dossier_text,
            dossier_date=date,
            dossier_source=dossier_path,
        )
    except OSError as exc:
        logger.error("Seeding failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    _main()
