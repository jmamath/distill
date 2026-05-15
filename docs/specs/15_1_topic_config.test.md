---
name: Topic Configuration Contract
plan: "15_1"
executor: script
kind: regression
status: passed
last_run: 2026-04-21
script: tests/test_topic_config.py
---

## Preconditions

- Virtual environment is active: `source sonaryn_env/bin/activate`
- Working directory is the project root
- `research_briefing/src/` is on `PYTHONPATH`
- `research_briefing/data/research_topics/data_advantage/topic.md` exists and contains the full 15.1 frontmatter
- `research_briefing/data/audiences/technical_decision_makers.md` exists

## Steps

1. **First topic config loads and validates without errors**
   - Run `pytest research_briefing/tests/test_topic_config.py::test_load_data_advantage_config`
   - Expect: test passes; returned `TopicConfig` has the correct `topic_id`, `name`, `thesis`, and `audience_ref`
   > **Why:** If the actual `topic.md` is invalid against the schema, no task in this system can start for the data_advantage topic — scoring, wiki updates, and brief generation all require a valid config at entry.

2. **Required fields are enforced with clear validation errors**
   - Run `pytest research_briefing/tests/test_topic_config.py::test_required_fields_enforced`
   - Expect: test passes; loading a minimal dict missing `topic_id`, `name`, `thesis`, or `audience_ref` raises `ValueError` with a message that names the missing field
   > **Why:** A topic config with a missing thesis or no audience reference would silently produce wrong scoring and briefs with no guidance on what went wrong. Operators need to know exactly which field is absent.

3. **Audience profile loads and validates without errors**
   - Run `pytest research_briefing/tests/test_topic_config.py::test_load_audience_profile`
   - Expect: test passes; returned `AudienceProfile` has `audience_id`, `name`, `persona`, `scope`, and `tone` fields populated
   > **Why:** If the audience profile cannot be loaded, the scoring pipeline has no persona context and the brief has no tone guidance — the output degrades to a generic summary with no audience-specific framing.

4. **Signal classes are validated against the known enum**
   - Run `pytest research_briefing/tests/test_topic_config.py::test_invalid_signal_class_rejected`
   - Expect: test passes; a `TopicConfig` containing an unrecognised signal class value raises `ValueError`
   > **Why:** An unrecognised signal class silently disables that class of input in the pipeline. A paper from arXiv would be dropped as if it were out of scope, with no error to alert the operator.

5. **Action vocabulary is validated against the known enum**
   - Run `pytest research_briefing/tests/test_topic_config.py::test_invalid_action_label_rejected`
   - Expect: test passes; a `TopicConfig` containing an unknown action label raises `ValueError`
   > **Why:** An unknown action recommendation would reach the brief and confuse the reader — the editorial structure assumes a fixed vocabulary and the operator would have no signal that the label was wrong.

6. **Schema is generic enough to support a different topic**
   - Run `pytest research_briefing/tests/test_topic_config.py::test_different_topic_validates`
   - Expect: test passes; a fixture config for a different topic (e.g. `agent_reliability`) with only the four required fields validates without error
   > **Why:** The entire modularity argument depends on topic swaps being cheap. If the schema hard-codes anything about `data_advantage`, the first pivot will require a code change instead of a config change.

## Teardown

No disk writes. All tests use in-memory fixtures or the real data files under `research_briefing/data/`.
