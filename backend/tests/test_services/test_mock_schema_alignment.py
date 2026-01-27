"""
Tests that mock data aligns with LLM response schemas.

If these fail, it means mock data is out of sync with what we expect from LLM.
"""

import pytest
from pydantic import ValidationError

from app.schemas.llm import (
    LLMImagePromptResponse,
    LLMScenarioResponse,
    LLMValidationResponse,
    LLMPublishingMetaResponse,
    LLMContentVariantsResponse,
)


# ============ mock_data.py (used in mock mode) ============

def test_mock_data_prompt_matches_schema():
    from app.services.mock_data import MOCK_PROMPT
    validated = LLMImagePromptResponse.model_validate(MOCK_PROMPT)
    assert validated.main_prompt
    assert validated.style_suffix
    assert validated.negative_prompt


def test_mock_data_scenario_matches_schema():
    from app.services.mock_data import MOCK_SCENARIO
    validated = LLMScenarioResponse.model_validate(MOCK_SCENARIO)
    assert validated.motion_prompt
    assert validated.camera_movement.type
    assert validated.subject_action
    assert len(validated.key_moments) > 0
    assert validated.key_moments[0].timestamp


def test_mock_data_validation_matches_schema():
    from app.services.mock_data import MOCK_VALIDATION_RESULT
    validated = LLMValidationResponse.model_validate(MOCK_VALIDATION_RESULT)
    assert validated.status == "pass"
    assert 0 <= validated.score <= 100
    for name, cr in validated.criteria_results.items():
        assert cr.comment  # not "feedback"


# ============ mock_responses.py (used in tests) ============

def test_mock_responses_prompt_matches_schema():
    from tests.fixtures.mock_responses import MOCK_PROMPT
    validated = LLMImagePromptResponse.model_validate(MOCK_PROMPT)
    assert validated.main_prompt
    assert validated.style_suffix
    assert validated.negative_prompt


def test_mock_responses_scenario_matches_schema():
    from tests.fixtures.mock_responses import MOCK_SCENARIO
    validated = LLMScenarioResponse.model_validate(MOCK_SCENARIO)
    assert validated.motion_prompt
    assert validated.camera_movement.type
    assert validated.subject_action
    assert len(validated.key_moments) > 0
    assert validated.key_moments[0].timestamp


def test_mock_responses_validation_pass_matches_schema():
    from tests.fixtures.mock_responses import MOCK_VALIDATION_PASS
    validated = LLMValidationResponse.model_validate(MOCK_VALIDATION_PASS)
    assert validated.status == "pass"
    for name, cr in validated.criteria_results.items():
        assert cr.comment


def test_mock_responses_validation_warnings_matches_schema():
    from tests.fixtures.mock_responses import MOCK_VALIDATION_PASS_WITH_WARNINGS
    validated = LLMValidationResponse.model_validate(MOCK_VALIDATION_PASS_WITH_WARNINGS)
    assert validated.status == "pass_with_warnings"
    assert len(validated.warnings) > 0


def test_mock_responses_validation_fail_matches_schema():
    from tests.fixtures.mock_responses import MOCK_VALIDATION_FAIL
    validated = LLMValidationResponse.model_validate(MOCK_VALIDATION_FAIL)
    assert validated.status == "fail"
    assert len(validated.errors) > 0
