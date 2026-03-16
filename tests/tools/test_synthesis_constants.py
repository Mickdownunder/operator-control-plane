"""Unit tests for tools/synthesis/constants.py."""
from unittest.mock import patch

from tools.synthesis.constants import (
    MAX_FINDINGS,
    EXCERPT_CHARS,
    SOURCE_CONTENT_CHARS,
    SECTION_WORDS_MIN,
    SECTION_WORDS_MAX,
    SYNTHESIZE_CHECKPOINT,
    _model,
)


def test_constants_defined():
    assert MAX_FINDINGS == 80
    assert EXCERPT_CHARS == 2000
    assert SOURCE_CONTENT_CHARS == 6000
    assert SECTION_WORDS_MIN == 500
    assert SECTION_WORDS_MAX == 1500
    assert SYNTHESIZE_CHECKPOINT == "synthesize_checkpoint.json"


def test_model_returns_lane_model():
    with patch("tools.synthesis.constants.model_for_lane", return_value="gpt-4o") as m:
        assert _model() == "gpt-4o"
        m.assert_called_once_with("synthesize")
