"""Prompt builders for the topic-aware signal scoring pipeline.

Pass-1, pass-2, triage, and stance prompts are kept here so the orchestration
modules stay focused and the prompt text is independently readable and
testable.

Prompt templates are written as triple-quoted blocks passed through
`textwrap.dedent`, so the source reads like the rendered prompt. Substitution
uses `string.Template` (`$placeholders`) rather than `str.format` so the
literal JSON-schema braces in the templates need no escaping; substituted
values are inserted verbatim and never re-interpreted.

Public API:
    build_pass1_prompt(item, topic_config) → str
    build_pass2_prompt(item, topic_config, theme_definitions) → str
    build_triage_prompt(claim, candidate_hypotheses, candidate_themes, topic_config) → str
    build_stance_prompt(claim, matched_hypothesis) → str
"""

from collections.abc import Mapping
from string import Template
from textwrap import dedent

from sources.base import NormalizedItem
from topics.config import TopicConfig


def build_pass1_prompt(
    item: NormalizedItem,
    topic_config: TopicConfig,
    theme_definitions: dict[str, str],
) -> str:
    """Build the pass-1 relevance scoring prompt.

    Context included: topic thesis, scope_in/out lists, taxonomy subtopics,
    and the item's title + abstract. Full text is intentionally excluded —
    that is pass-2's input.

    Args:
        item: The normalized signal to evaluate.
        topic_config: The active topic configuration.
        theme_definitions: Mapping of theme_id → description (single source of
            truth, loaded from themes/*.md frontmatter).

    Returns:
        A prompt string ready for the scoring LLM.
    """
    subtopics = "\n".join(
        f"  - {name}: {desc}" for name, desc in theme_definitions.items()
    )
    scope_in = "\n".join(f"  - {s}" for s in topic_config.scope_in)
    scope_out = "\n".join(f"  - {s}" for s in topic_config.scope_out)
    rubric = "\n".join(
        f"  - {d.id} (0–10): {d.description}" for d in topic_config.pass1_dimensions
    )

    template = Template(dedent("""\
        Topic: $topic_name
        Thesis: $thesis

        In scope:
        $scope_in

        Out of scope:
        $scope_out

        Taxonomy subtopics:
        $subtopics

        Signal to evaluate:
        Title: $title
        Source type: $source_type
        Abstract: $summary

        Scoring rubric:
        $rubric

        Respond strictly as JSON: {"topical_relevance": <integer 0-10>, "reason": "<one sentence>"}"""))

    return template.substitute(
        topic_name=topic_config.name,
        thesis=topic_config.thesis,
        scope_in=scope_in,
        scope_out=scope_out,
        subtopics=subtopics,
        title=item.title,
        source_type=item.source_type,
        summary=item.summary,
        rubric=rubric,
    )


def build_pass2_prompt(
    item: NormalizedItem,
    topic_config: TopicConfig,
    theme_definitions: dict[str, str],
) -> str:
    """Build the pass-2 full-text scoring prompt.

    The full text bytes are passed separately as a multimodal part — this
    prompt provides topic context and theme definitions only.  Theme bodies
    and existing wiki evidences are intentionally excluded to avoid anchoring
    the model on current knowledge state.

    Args:
        item: The normalized signal whose full text will be scored.
        topic_config: The active topic configuration.
        theme_definitions: Mapping of theme_id → description (no bodies).

    Returns:
        A prompt string ready for the scoring LLM.
    """
    themes_block = "\n".join(
        f"  - {tid}: {desc}" for tid, desc in theme_definitions.items()
    )
    authors = ", ".join(item.authors) if item.authors else "unknown"
    rubric = "\n".join(
        f"  - {d.id} (0–10): {d.description}" for d in topic_config.pass2_dimensions
    )

    template = Template(dedent("""\
        Topic: $topic_name
        Thesis: $thesis

        Available themes (id: description):
        $themes_block

        Signal metadata:
          Title: $title
          Source type: $source_type
          Authors: $authors
          URL: $url

        The full text of this signal is attached. Score each dimension in the rubric and identify up to three themes it best supports.

        Scoring rubric:
        $rubric

        Respond strictly as JSON with this exact schema:
        {
          "applicability_score": <integer 0-10>,
          "applicability_rationale": "<one sentence: why this applicability score>",
          "strategic_significance": <integer 0-10>,
          "strategic_significance_rationale": "<one sentence: why this strategic significance score>",
          "paper_audience": "<free text: who would benefit most from reading this>",
          "candidate_themes": [
            {"theme_id": "<id from the list above>", "confidence": <0-10>, "rationale": "<one sentence: why this confidence level>"}
          ],
          "claims": ["<one concrete, self-contained claim>"],
          "affiliations": ["<author organization as cited in the source>"],
          "rationale": "<markdown paragraph explaining the applicability score>"
        }

        Rules:
        - candidate_themes: at most 3 entries, sorted by descending confidence.
        - Only use theme_ids from the list above; omit themes with confidence < 4.
        - claims: extract concrete findings or assertions without assigning a stance; direction is resolved later against a specific hypothesis.
        - affiliations: list author organizations exactly as cited — do not infer or expand.
        - rationale: written for a research analyst; focus on what is novel and why it matters."""))

    return template.substitute(
        topic_name=topic_config.name,
        thesis=topic_config.thesis,
        themes_block=themes_block,
        title=item.title,
        source_type=item.source_type,
        authors=authors,
        url=item.url,
        rubric=rubric,
    )


def build_triage_prompt(
    claim: str,
    candidate_hypotheses: list[dict],
    candidate_themes: list[str],
    topic_config: TopicConfig,
) -> str:
    """Build the triage prompt for one claim (Plan 9, Decision 1).

    Each candidate hypothesis is shown by its identity only — id, statement,
    theme_ids, and comparison subjects. Belief state (alpha/beta), evidence,
    and posture are intentionally withheld: a matcher that sees a hypothesis
    is already confident will over-attach to it. The claim's candidate themes
    ride along as a prefilter hint; the model still ranks over the full set.

    Args:
        claim: The claim text extracted by pass-2.
        candidate_hypotheses: Hypothesis records (hypotheses.json shape); only
            identity fields are included in the prompt.
        candidate_themes: Theme ids the claim's signal touches (may be empty).
        topic_config: The active topic configuration.

    Returns:
        A prompt string ready for the triage LLM.
    """
    if candidate_hypotheses:
        lines = []
        for hyp in candidate_hypotheses:
            entry = f"  - id: {hyp['id']}\n    statement: {hyp['statement']}"
            theme_ids = hyp.get("theme_ids") or []
            if theme_ids:
                entry += f"\n    themes: {', '.join(theme_ids)}"
            comparison = hyp.get("comparison")
            if comparison:
                entry += (
                    f"\n    comparison: {comparison['subject_a']}"
                    f" vs {comparison['subject_b']}"
                )
            lines.append(entry)
        hypotheses_block = "\n".join(lines)
    else:
        hypotheses_block = "  (none yet)"

    themes_hint = ", ".join(candidate_themes) if candidate_themes else "(none)"

    template = Template(dedent("""\
        Topic: $topic_name
        Thesis: $thesis

        You are triaging one claim extracted from a research signal. Decide where it goes in the topic's belief graph.

        Claim: $claim
        Themes the claim's signal touches (hint only): $themes_hint

        Current hypotheses (the bets the system tracks):
        $hypotheses_block

        Pick exactly one decision:
        - attach: the claim is evidence bearing on one of the hypotheses above — it supports, opposes, or complicates that bet. Name its hypothesis_id.
        - open: no hypothesis matches, and the claim names a standing question the field genuinely disagrees on — worth its own bet even with one piece of evidence so far. Write new_statement as a single directional, resolvable bet two reviewers could settle the same way once evidence arrives.
        - route: the claim is not evidence for any bet, but registers a noteworthy artifact — a dataset, benchmark, or model release — that is the central subject of the claim, not a passing mention. Provide entity.
        - drop: none of the above (an incidental mention, or a lone measurement answering no standing question).

        Rules:
        - A result (a single measurement a paper reports) is evidence, never a new bet: attach it to the hypothesis whose question it speaks to. Never open a hypothesis named after one measurement — nothing else will ever attach to it.
        - comparison: only on open, and only when the new bet is a head-to-head between two named subjects; give subject_a and subject_b.
        - entity: required on route; also include it on attach/open when the claim's central subject is a named artifact (a release claim that also carries a result does both).
        - Omit every field that does not apply to your decision.

        Respond strictly as JSON with this exact schema:
        {
          "decision": "attach | open | route | drop",
          "hypothesis_id": "<existing id — required when attach>",
          "new_statement": "<a resolvable, directional bet — required when open>",
          "comparison": {"subject_a": "...", "subject_b": "..."},
          "entity": {"name": "...", "entity_type": "lab | company | dataset | method | benchmark | product", "description": "..."},
          "rationale": "<one sentence>"
        }"""))

    return template.substitute(
        topic_name=topic_config.name,
        thesis=topic_config.thesis,
        claim=claim,
        themes_hint=themes_hint,
        hypotheses_block=hypotheses_block,
    )


def build_stance_prompt(
    claim: str,
    matched_hypothesis: Mapping[str, object],
) -> str:
    """Build the stance prompt for one claim against one named hypothesis.

    The prompt contains only the matched hypothesis's identity. It excludes
    the candidate set, belief state, and evidence history so the model judges
    how the claim bears on this specific bet without being anchored by current
    confidence.

    Args:
        claim: The claim text extracted by pass-2.
        matched_hypothesis: The chosen hypothesis record; it must contain `id`
            and `statement`.

    Returns:
        A prompt string ready for the stance-resolution LLM.

    Raises:
        KeyError: if the matched hypothesis lacks `id` or `statement`.
    """
    template = Template(dedent("""\
        You are resolving how one research claim bears on one specific hypothesis.

        Claim: $claim

        Matched hypothesis:
          id: $hypothesis_id
          statement: $hypothesis_statement

        Decide the claim's stance against the hypothesis above:
        - for: the claim supports the directional bet.
        - against: the claim opposes the bet, including a null or no-difference result against a directional claim.
        - mixed: the claim contains genuinely conflicting evidence for and against the bet.

        A neutral verdict is not valid here. A claim that is irrelevant to the hypothesis should have been rejected during triage; every claim reaching this step must resolve to for, against, or mixed.

        Respond strictly as JSON with this exact schema:
        {"stance": "for | against | mixed", "rationale": "<one sentence>"}"""))

    return template.substitute(
        claim=claim,
        hypothesis_id=matched_hypothesis["id"],
        hypothesis_statement=matched_hypothesis["statement"],
    )
