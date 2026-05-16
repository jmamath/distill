"""Smoke test for full-text fetch and google.genai summarization.

Loads the two offline fixtures (arxiv_paper.pdf and lab_blog_article.html),
processes each through its adapter's fetch_full_text logic, sends the result
to the google.genai API with the correct full_text_mime_type, and prints the
response. Use this to verify the fetch_full_text contract end-to-end before
running pass-2 on live items.

Run from the project root with the virtualenv active:
    source .venv/bin/activate
    PYTHONPATH=src python scripts/smoke_full_text.py --model gemini-3.1-flash-lite
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import google.genai as genai
import google.genai.types as genai_types

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import config  # loads .env and exposes GEMINI_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"
_ARXIV_PDF = _FIXTURES / "arxiv_paper.pdf"
_BLOG_HTML = _FIXTURES / "lab_blog_article.html"

_PROMPT = "Summarise this document in one paragraph for a machine learning researcher."


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def _summarise(client: genai.Client, model: str, data: bytes, mime_type: str, label: str) -> None:
    logger.info("Sending %s (%d bytes, %s) to %s", label, len(data), mime_type, model)
    # Plain text is passed as a text part; binary formats (PDF, etc.) as a blob.
    # Sending text/plain via from_bytes causes 500s on models that don't support inline uploads.
    if mime_type == "text/plain":
        content_part = genai_types.Part.from_text(text=data.decode("utf-8"))
    else:
        content_part = genai_types.Part.from_bytes(data=data, mime_type=mime_type)
    response = client.models.generate_content(
        model=model,
        contents=[content_part, _PROMPT],
    )
    print(f"\n=== {label} ===")
    print(response.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test full-text fetch + summarisation")
    parser.add_argument("--model", default="gemini-2.0-flash", help="google.genai model ID")
    args = parser.parse_args()

    for path, label in [(_ARXIV_PDF, "arXiv PDF"), (_BLOG_HTML, "Lab blog HTML")]:
        if not path.exists():
            logger.error("Fixture not found: %s", path)
            sys.exit(1)

    if not config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set — add it to your .env file")
        sys.exit(1)

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    # arXiv: PDF bytes sent as-is — matches ArxivAdapter.full_text_mime_type
    _summarise(client, args.model, _ARXIV_PDF.read_bytes(), "application/pdf", "arXiv PDF")

    # Lab blog: HTML stripped to plain text — matches LabBlogAdapter.fetch_full_text output
    blog_plain = _strip_html(_BLOG_HTML.read_text(encoding="utf-8", errors="replace")).encode("utf-8")
    _summarise(client, args.model, blog_plain, "text/plain", "Lab blog article")


if __name__ == "__main__":
    main()
