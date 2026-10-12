"""Offline checks for the local demo's two provider timeout budgets."""

import pytest

from app.config import read_timeout_config


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({}, (38000, 9000)),
        ({"GEMINI_TIMEOUT_MS": "35000"}, (35000, 9000)),
        ({"GEMINI_TIMEOUT_MS": "60000", "GEMINI_GENERATION_TIMEOUT_MS": "39000", "RAG_TIMEOUT_MS": "10000"}, (39000, 10000)),
        ({"GEMINI_GENERATION_TIMEOUT_MS": "40000", "RAG_TIMEOUT_MS": "10000"}, (40000, 10000)),
    ],
)
def test_valid_timeout_config(values, expected):
    assert read_timeout_config(values) == expected


@pytest.mark.parametrize(
    "values",
    [
        {"GEMINI_GENERATION_TIMEOUT_MS": "1.5"},
        {"RAG_TIMEOUT_MS": "invalid"},
        {"GEMINI_GENERATION_TIMEOUT_MS": "0"},
        {"GEMINI_GENERATION_TIMEOUT_MS": "-1"},
        {"RAG_TIMEOUT_MS": "0"},
        {"RAG_TIMEOUT_MS": "-5"},
        {"GEMINI_GENERATION_TIMEOUT_MS": "45001"},
        {"RAG_TIMEOUT_MS": "15001"},
        {"GEMINI_GENERATION_TIMEOUT_MS": "45000", "RAG_TIMEOUT_MS": "15000"},
        {"GEMINI_TIMEOUT_MS": "60000"},
    ],
)
def test_invalid_timeout_config_is_clear_and_secret_free(values):
    sentinel = "should-never-appear-in-errors"
    with pytest.raises(ValueError) as caught:
        read_timeout_config({**values, "GEMINI_API_KEY": sentinel})
    assert "timeout" in str(caught.value).lower()
    assert sentinel not in str(caught.value)
