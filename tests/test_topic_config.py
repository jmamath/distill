"""Tests for the topic configuration contract (Task 15.1).

Covers: loading the first real topic config, required-field enforcement,
audience profile loading, enum validation, and schema genericity.

Run from the project root with the virtualenv active:
    source .venv/bin/activate
    PYTHONPATH=src pytest tests/test_topic_config.py
"""

from pathlib import Path

import pytest

from topics.config import (
    ActionLabel,
    AudienceProfile,
    SignalClass,
    TopicConfig,
    load_audience_profile,
    load_topic_config,
)

# Paths to real data files — tests read them but never write.
_REPO_ROOT = Path(__file__).parent.parent
_DATA_ROOT = _REPO_ROOT / "data"
_TOPIC_PATH = _DATA_ROOT / "research_topics" / "data_advantage" / "topic.md"
_AUDIENCE_PATH = _DATA_ROOT / "audiences" / "technical_decision_makers.md"


# ---------------------------------------------------------------------------
# Load real topic config
# ---------------------------------------------------------------------------


def test_load_data_advantage_config():
    """The real data_advantage/topic.md loads and validates without error."""
    config = load_topic_config(_TOPIC_PATH)

    assert isinstance(config, TopicConfig)
    assert config.topic_id == "data_advantage"
    assert config.name == "Emerging Data Advantages in AI"
    assert config.audience_ref == "technical_decision_makers"
    assert config.thesis  # non-empty string
    assert len(config.taxonomy) > 0
    assert len(config.scoring_dimensions) > 0
    assert len(config.signal_classes) > 0
    assert len(config.action_vocabulary) > 0


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing_field", ["topic_id", "name", "thesis", "audience_ref"])
def test_required_fields_enforced(tmp_path, missing_field):
    """Loading a topic.md missing a required field raises ValueError.

    Each required field is tested independently so the error message can name
    the missing field clearly.
    """
    full = {
        "topic_id": "test_topic",
        "name": "Test Topic",
        "thesis": "A test thesis.",
        "audience_ref": "some_audience",
    }
    full.pop(missing_field)

    # Write a minimal topic.md without the missing field.
    import yaml

    fm_yaml = yaml.safe_dump(full, default_flow_style=False)
    topic_file = tmp_path / "topic.md"
    topic_file.write_text(f"---\n{fm_yaml}---\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_topic_config(topic_file)


# ---------------------------------------------------------------------------
# Audience profile
# ---------------------------------------------------------------------------


def test_load_audience_profile():
    """The real technical_decision_makers.md loads and has all required fields."""
    profile = load_audience_profile(_AUDIENCE_PATH)

    assert isinstance(profile, AudienceProfile)
    assert profile.audience_id == "technical_decision_makers"
    assert profile.name
    assert profile.persona
    assert profile.scope
    assert profile.tone


# ---------------------------------------------------------------------------
# Enum validation
# ---------------------------------------------------------------------------


def test_invalid_signal_class_rejected(tmp_path):
    """A topic.md containing an unrecognised signal class raises ValueError."""
    import yaml

    fm = {
        "topic_id": "test",
        "name": "Test",
        "thesis": "A thesis.",
        "audience_ref": "some_audience",
        "signal_classes": ["paper", "not_a_real_class"],
    }
    topic_file = tmp_path / "topic.md"
    topic_file.write_text(f"---\n{yaml.safe_dump(fm)}---\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_topic_config(topic_file)


def test_invalid_action_label_rejected(tmp_path):
    """A topic.md containing an unrecognised action label raises ValueError."""
    import yaml

    fm = {
        "topic_id": "test",
        "name": "Test",
        "thesis": "A thesis.",
        "audience_ref": "some_audience",
        "action_vocabulary": ["ignore", "yolo"],
    }
    topic_file = tmp_path / "topic.md"
    topic_file.write_text(f"---\n{yaml.safe_dump(fm)}---\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_topic_config(topic_file)


# ---------------------------------------------------------------------------
# Schema genericity
# ---------------------------------------------------------------------------


def test_different_topic_validates(tmp_path):
    """A minimal config for a different topic validates without error.

    If the schema is coupled to data_advantage, this test will fail — proving
    that topic swaps require a code change rather than a config change.
    """
    import yaml

    fm = {
        "topic_id": "agent_reliability",
        "name": "Agent Reliability in Production",
        "thesis": "A brief on what makes agentic systems fail and how to fix it.",
        "audience_ref": "technical_decision_makers",
    }
    topic_file = tmp_path / "topic.md"
    topic_file.write_text(f"---\n{yaml.safe_dump(fm)}---\n", encoding="utf-8")

    config = load_topic_config(topic_file)
    assert config.topic_id == "agent_reliability"
    # Optional fields should default gracefully.
    assert config.taxonomy == []
    assert config.scoring_dimensions == []
    assert config.signal_classes == []
    assert config.action_vocabulary == []


def test_all_signal_classes_in_enum():
    """All SignalClass values are the expected set — no accidental omissions."""
    expected = {"paper", "lab_post", "dataset_release", "benchmark_release",
                "engineering_writeup", "startup_launch"}
    actual = {c.value for c in SignalClass}
    assert actual == expected


def test_all_action_labels_in_enum():
    """All ActionLabel values are the expected set — no accidental omissions."""
    expected = {"ignore", "monitor", "prototype", "invest"}
    actual = {a.value for a in ActionLabel}
    assert actual == expected
