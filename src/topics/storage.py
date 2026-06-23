"""Canonical storage front door for a topic workspace.

Downstream stages import their storage operations from here, not from helpers
scattered across the codebase. The module is organised in layers:

  Layer 1 — file primitives
    - frontmatter read/write/update, re-exported from `topics.frontmatter`
      (the wiki narrative files: topic.md, themes/*.md, overview.md).
    - flat JSON-array load / save / merge-by-id, lifted out of the bootstrap
      seeder so there is exactly one copy (entities.json, timeline.json, and
      the belief-graph stores all share it).

  Layer 2 — belief-graph accessors
    - load / save for hypotheses.json and evidence.json.
    - the credibility-weighted `strength` increment with provenance append.
    - the Beta `alpha`/`beta` belief update.
    These are pure storage *mechanics*: the *decision* of which hypothesis a
    signal's evidence attaches to (and stance resolution, dedup, hypothesis
    creation) belongs to the wiki/hypothesis updater in Plan 9.

  Raw payloads
    - persist an original fetched payload under raw/ in its native format.

Signal-specific storage (a SignalFrontmatter model, signal read, and the
classification / theme_id_assigned write-back) is intentionally NOT here — it
lives with its consumer, the wiki updater, in Plan 9. The seam: this module
owns *how the belief graph is stored and safely mutated*; Plan 9 owns *what
changes when a signal arrives*.

Usage:
    from pathlib import Path
    from topics import storage

    hyps = storage.load_hypotheses(topic_dir)
    ev = storage.load_evidence(topic_dir)

    # Fold one signal's contribution into an evidence record (pure mechanic):
    ev_record = storage.add_signal_to_evidence(
        ev_record, signal_id="arxiv_2026-05-01_b9c3d4e2fa", source_credibility=9.0
    )
    # Move the hypothesis belief by that same contribution:
    hyp["belief"] = storage.apply_belief_update(
        hyp["belief"], stance="for", strength=storage.credibility_to_weight(9.0)
    )
"""

import json
import logging
from pathlib import Path

# Re-export the frontmatter primitives so callers have a single storage import.
from topics.frontmatter import (  # noqa: F401  (re-exported on purpose)
    load_frontmatter,
    update_frontmatter,
    write_with_frontmatter,
)

logger = logging.getLogger(__name__)

# Fallback weight for a signal whose source credibility could not be determined
# (no affiliation matched the credibility table → `source_credibility is None`).
# Such a signal still counts, but at a discounted weight on the 0–1 per-signal
# scale rather than as a fully-credible confirmation. Plan 9 references this
# constant and may re-home it.
NEUTRAL_CREDIBILITY_WEIGHT = 0.2

# Source credibility is scored 0–10 (see topics.credibility); the per-signal
# evidence weight normalises it onto the 0–1 scale.
_CREDIBILITY_SCALE = 10.0

HYPOTHESES_FILENAME = "hypotheses.json"
EVIDENCE_FILENAME = "evidence.json"


# ---------------------------------------------------------------------------
# Layer 1 — flat JSON-array primitives
# ---------------------------------------------------------------------------


def load_json_array(path: Path) -> list[dict]:
    """Load a flat JSON array of records from disk.

    Args:
        path: Path to a JSON file expected to contain a top-level array.

    Returns:
        The list of records, or an empty list if the file does not exist, is
        empty, is unreadable, or does not contain a top-level JSON array. The
        contract is deliberately lenient so a missing store behaves like an
        empty one for first-run callers.
    """
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read JSON array at %s (%s) — treating as empty", path, exc)
        return []
    if not isinstance(data, list):
        logger.warning("Expected a JSON array at %s, got %s — treating as empty", path, type(data))
        return []
    return data


def save_json_array(path: Path, records: list[dict]) -> None:
    """Write a flat JSON array of records to disk, creating parent dirs.

    Args:
        path: Destination JSON file.
        records: List of records to serialise as a top-level JSON array.

    Raises:
        OSError: if the file cannot be written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.debug("Wrote %d records → %s", len(records), path)


def merge_by_id(
    existing: list[dict],
    incoming: list[dict],
    *,
    id_key: str = "id",
) -> list[dict]:
    """Merge incoming records into existing ones, keyed by a stable id.

    Existing records are preserved unchanged; only incoming records whose id is
    not already present are appended (in input order). This makes the merge
    idempotent: merging the same incoming list twice yields the same result, so
    re-running the seeder or replaying a batch never duplicates or mutates rows.
    Updating an existing record is a separate, deliberate operation (load → edit
    the record in place → save), not a side effect of merging.

    Args:
        existing: Records already on disk.
        incoming: Candidate new records.
        id_key: The field holding each record's stable identifier.

    Returns:
        A new list: all existing records followed by the not-yet-seen incoming
        records.

    Raises:
        KeyError: if any record is missing `id_key`.
    """
    existing_ids = {record[id_key] for record in existing}
    new_records = [record for record in incoming if record[id_key] not in existing_ids]
    if new_records:
        logger.debug(
            "merge_by_id: %d existing + %d new (of %d incoming)",
            len(existing), len(new_records), len(incoming),
        )
    return existing + new_records


# ---------------------------------------------------------------------------
# Layer 2 — belief-graph accessors (hypotheses.json, evidence.json)
# ---------------------------------------------------------------------------


def load_hypotheses(topic_dir: Path) -> list[dict]:
    """Load the durable hypothesis records for a topic.

    Args:
        topic_dir: Root directory for the topic.

    Returns:
        The list of hypothesis records (empty if the store does not exist yet).
    """
    return load_json_array(topic_dir / HYPOTHESES_FILENAME)


def save_hypotheses(topic_dir: Path, records: list[dict]) -> None:
    """Persist the durable hypothesis records for a topic.

    Args:
        topic_dir: Root directory for the topic.
        records: Full hypothesis array to write.

    Raises:
        OSError: if the file cannot be written.
    """
    save_json_array(topic_dir / HYPOTHESES_FILENAME, records)


def load_evidence(topic_dir: Path) -> list[dict]:
    """Load the evidence records for a topic.

    Args:
        topic_dir: Root directory for the topic.

    Returns:
        The list of evidence records (empty if the store does not exist yet).
    """
    return load_json_array(topic_dir / EVIDENCE_FILENAME)


def save_evidence(topic_dir: Path, records: list[dict]) -> None:
    """Persist the evidence records for a topic.

    Args:
        topic_dir: Root directory for the topic.
        records: Full evidence array to write.

    Raises:
        OSError: if the file cannot be written.
    """
    save_json_array(topic_dir / EVIDENCE_FILENAME, records)


def credibility_to_weight(source_credibility: float | None) -> float:
    """Normalise a 0–10 source credibility to a 0–1 per-signal evidence weight.

    A maximally-credible signal (credibility 10) contributes a weight of 1.0;
    `None` credibility (no affiliation matched the table) falls back to the
    neutral NEUTRAL_CREDIBILITY_WEIGHT rather than 0, so an unknown source still
    counts.

    Args:
        source_credibility: Credibility on the 0–10 scale, or None when unknown.

    Returns:
        The per-signal weight on the 0–1 scale.
    """
    if source_credibility is None:
        return NEUTRAL_CREDIBILITY_WEIGHT
    return source_credibility / _CREDIBILITY_SCALE


def add_signal_to_evidence(
    evidence: dict,
    signal_id: str,
    source_credibility: float | None,
) -> dict:
    """Fold one signal's contribution into an evidence record.

    Does not dedup: calling it twice for the same signal counts it twice.
    Whether a signal has already contributed to a claim is the updater's
    decision (Plan 9).

    Args:
        evidence: Evidence record to extend; an absent `strength` / `provenance`
            is treated as 0.0 / [].
        signal_id: Stable id of the contributing signal.
        source_credibility: Signal credibility on the 0–10 scale, or None if unknown.

    Returns:
        A new evidence record (input not mutated) with the signal appended to
        `provenance` and its weight added to `strength`.
    """
    weight_applied = credibility_to_weight(source_credibility)
    updated = dict(evidence)
    provenance = list(evidence.get("provenance", []))
    provenance.append({"signal_id": signal_id, "weight_applied": weight_applied})
    updated["provenance"] = provenance
    updated["strength"] = float(evidence.get("strength", 0.0)) + weight_applied
    return updated


def apply_belief_update(belief: dict, stance: str, strength: float) -> dict:
    """Move a Beta belief by one evidence contribution, directed by stance.

    `strength` must be the *incremental* contribution — one signal's
    `weight_applied`, not an evidence record's running total — or prior evidence
    is counted twice.

    Args:
        belief: Belief dict with `alpha` / `beta`; absent values default to the
            uniform prior 1.0.
        stance: One of `for | against | mixed | neutral`.
        strength: Non-negative contribution to apply.

    Returns:
        A new belief dict; the input is not mutated.

    Raises:
        ValueError: if `stance` is not a recognised value.
    """
    alpha = float(belief.get("alpha", 1.0))
    beta = float(belief.get("beta", 1.0))

    if stance == "for":
        alpha += strength
    elif stance == "against":
        beta += strength
    elif stance == "mixed":
        # Split raises evidence mass without moving the mean: entrenched conflict, not ignorance.
        alpha += strength / 2
        beta += strength / 2
    elif stance == "neutral":
        pass  # defensive no-op; neutral should be filtered at link time (Plan 9)
    else:
        raise ValueError(
            f"Unknown evidence stance {stance!r}; expected for | against | mixed | neutral"
        )

    return {"alpha": alpha, "beta": beta}


# ---------------------------------------------------------------------------
# Raw payloads
# ---------------------------------------------------------------------------


def save_raw_payload(
    topic_dir: Path,
    payload: bytes,
    *,
    date: str,
    source_name: str,
    extension: str,
) -> Path:
    """Persist an original fetched payload under raw/ in its native format.

    Raw payloads are kept for traceability, partitioned by fetch date and named
    by source. They are stored exactly as fetched (XML, HTML, …) — never coerced
    to JSON — so the original bytes remain auditable.

    Layout: raw/{date}/{source_name}{extension}

    Args:
        topic_dir: Root directory for the topic.
        payload: Raw bytes exactly as fetched from the source.
        date: Fetch date as YYYY-MM-DD; names the partition directory.
        source_name: Source identifier; names the file stem.
        extension: File extension including or excluding the leading dot
            (e.g. ".xml", "html").

    Returns:
        The path the payload was written to.

    Raises:
        OSError: if the file cannot be written.
    """
    suffix = extension if extension.startswith(".") else f".{extension}"
    dest = topic_dir / "raw" / date / f"{source_name}{suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload)
    logger.debug("Wrote raw payload (%d bytes) → %s", len(payload), dest)
    return dest
