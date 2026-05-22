"""End-to-end smoke script for the pass-1 → pass-2 scoring pipeline.

Fetches a real paper by URL, runs the scoring pipeline against the live
Gemini API, and prints the results. Use this after any change to the
prompts, schema, or credibility logic to verify the pipeline end-to-end
with real content that mocks cannot cover.

Supported sources:
  arxiv    — any https://arxiv.org/abs/<id> URL
  lab_blog — any research lab blog post URL

Pass selection:
  --pass 1     Score the abstract only; print the Pass1Score and exit.
  --pass 2     Skip pass-1 and score the full text directly; write the signal.
  (default)    Run both passes end-to-end.

Run from the project root with the virtualenv active:
    source .venv/bin/activate
    PYTHONPATH=src python scripts/smoke_pass2.py --url https://arxiv.org/abs/<id>
    PYTHONPATH=src python scripts/smoke_pass2.py --url https://arxiv.org/abs/<id> --pass 1
    PYTHONPATH=src python scripts/smoke_pass2.py --url https://arxiv.org/abs/<id> --pass 2
    PYTHONPATH=src python scripts/smoke_pass2.py --url https://arxiv.org/abs/<id> --model gemini-3.1-flash-lite
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import config  # noqa: E402 — loads .env and exposes GEMINI_API_KEY
from sources.arxiv import ArxivAdapter
from sources.lab_blog import LabBlogAdapter
from sources.base import NormalizedItem, SourceAdapter
from topics.config import load_topic_config
from topics.models import Pass1Score
from topics.scoring import load_theme_definitions, pass1_score, pass2_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent
_TOPIC_DIR = _PROJECT_ROOT / "data" / "research_topics" / "data_advantage"


# ---------------------------------------------------------------------------
# Live item fetchers
# ---------------------------------------------------------------------------


def _fetch_arxiv_item(url: str) -> tuple[NormalizedItem, SourceAdapter]:
    """Fetch real metadata for an arXiv paper via ArxivAdapter.fetch_item."""
    adapter = ArxivAdapter()
    return adapter.fetch_item(url), adapter


def _fetch_lab_blog_item(url: str) -> tuple[NormalizedItem, SourceAdapter]:
    """Fetch metadata for a single lab blog post via LabBlogAdapter.fetch_item."""
    adapter = LabBlogAdapter()
    return adapter.fetch_item(url), adapter


# ---------------------------------------------------------------------------
# Pass runners
# ---------------------------------------------------------------------------


def _run_pass1(
    item: NormalizedItem,
    topic_config,
    theme_defs: dict[str, str],
) -> Pass1Score | None:
    """Run pass-1 scoring and print the result.

    Returns:
        The Pass1Score if the item clears the threshold, None if dropped.
    """
    results = pass1_score([item], topic_config, theme_defs)
    if not results:
        print("\nPass-1 result: DROPPED (below relevance threshold)")
        return None
    _, score = results[0]
    print(f"\nPass-1 result: PASSED")
    print(f"  relevance : {score.relevance}/10")
    print(f"  reason    : {score.reason}")
    return score


def _run_pass2(
    item: NormalizedItem,
    p1_score: Pass1Score,
    topic_config,
    topic_dir: Path,
    adapter: SourceAdapter,
) -> None:
    """Run pass-2 scoring and print the written signal file."""
    written = pass2_score([(item, p1_score)], topic_config, topic_dir, adapter)
    if not written:
        print("\nPass-2: no signal file written (fetch or LLM failure)")
        return
    for path in written:
        print(f"\nSignal written → {path}\n")
        print("=" * 60)
        print(path.read_text())
        print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke-test the pass-1 and/or pass-2 scoring pipeline with a real URL"
    )
    parser.add_argument("--url", required=True, help="URL of the paper or blog post to score")
    parser.add_argument(
        "--pass",
        dest="pass_mode",
        choices=["1", "2"],
        default=None,
        help="Run only pass-1 or only pass-2. Omit to run both end-to-end.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override SCORING_MODEL for this run (e.g. gemini-2.5-pro)",
    )
    args = parser.parse_args()

    if not config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set — add it to your .env file")
        sys.exit(1)

    if args.model:
        import topics.scoring as _scoring
        _scoring._MODELS = [args.model, config.SCORING_FALLBACK_MODEL]
        logger.info("Model override: %s", args.model)

    # Detect source from URL.
    if "arxiv.org" in args.url:
        item, adapter = _fetch_arxiv_item(args.url)
    else:
        item, adapter = _fetch_lab_blog_item(args.url)

    logger.info("Item: %r (%s)", item.title, item.source_id)

    topic_config = load_topic_config(_TOPIC_DIR / "topic.md")
    theme_defs = load_theme_definitions(_TOPIC_DIR / "themes")

    if args.pass_mode == "1":
        _run_pass1(item, topic_config, theme_defs)
        return

    if args.pass_mode == "2":
        # Bypass pass-1: create a synthetic score so pass2_score receives a valid pair.
        synthetic = Pass1Score(relevance=10, reason="bypassed via --pass 2")
        _run_pass2(item, synthetic, topic_config, _TOPIC_DIR, adapter)
        return

    # End-to-end: pass-1 gates pass-2.
    p1_score = _run_pass1(item, topic_config, theme_defs)
    if p1_score is None:
        return
    _run_pass2(item, p1_score, topic_config, _TOPIC_DIR, adapter)


if __name__ == "__main__":
    main()
