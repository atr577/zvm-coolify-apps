---
id: SPEC-T14
title: Unified LLM response validation pattern for all OpenAI service methods
status: draft
created: 2026-01-27
task: T14
target_sections: [backend, llm-validation, error-handling]
pydantic_version: "2.5.3"
---

# Technical Specification: Unified LLM Response Validation Pattern

## Overview

This spec introduces a unified validation pattern for all LLM JSON responses across 7 methods in `openai_service.py`. Currently, all methods return raw LLM output without validation, causing production failures when OpenAI returns non-deterministic JSON (missing fields, wrong types, unexpected structure). The new pattern enforces: `prompt → LLM → parse → validate (Pydantic) → normalize → return typed`, with 1 retry on validation failure.

**Key principles:**
- **Two schema layers:** LLM schemas (`backend/app/schemas/llm.py`) vs API schemas (what we return to client)
- **Validation always on:** including custom prompts — no exceptions
- **Pydantic v2 syntax:** project uses pydantic 2.5.3

## Architecture

### Component Diagram
```
┌─────────────────────────────────────────────────────────────────┐
│                      openai_client.py                            │
│  generate_validated_json(prompt, schema, system_prompt)         │
│    ↓                                                             │
│    1. Call generate_json() → raw Dict                           │
│    2. Validate with Pydantic schema → model instance            │
│    3. If ValidationError → retry once with error context        │
│    4. Return validated model instance                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      openai_service.py                           │
│  7 methods call generate_validated_json() with LLM schemas      │
│    ↓                                                             │
│    - generate_image_prompt() → LLMImagePromptResponse           │
│    - generate_scenario() → LLMScenarioResponse                  │
│    - generate_scenario_from_description() → LLMScenarioResponse │
│    - generate_scenario_from_template() → LLMScenarioResponse    │
│    - validate_content() → LLMValidationResponse                 │
│    - generate_publishing_meta() → LLMPublishingMetaResponse     │
│    - generate_content_variants() → LLMContentVariantsResponse   │
│    ↓                                                             │
│  Return .model_dump() for backward compatibility                │
│  Validation applies ALWAYS — including custom_prompt calls      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      API endpoints                               │
│  Server-side normalization (e.g., add id to variants)           │
│  Convert LLM models to API response schemas                     │
└─────────────────────────────────────────────────────────────────┘
```

### Changes Required

| Component | File | Change Type |
|-----------|------|-------------|
| LLM Client | `backend/app/services/openai_client.py` | Add `generate_validated_json()` + helper methods |
| LLM Schemas | `backend/app/schemas/llm.py` | **NEW FILE** — Pydantic v2 models |
| OpenAI Service | `backend/app/services/openai_service.py` | Migrate 7 methods, remove dead helpers |
| API Endpoint | `backend/app/api/ai_generation.py` | Add server-side `id` normalization |
| Prompt Template | `backend/app/services/prompts/variants.py` | Remove `id` from examples |
| Prompt Template | `backend/app/services/prompts/publishing.py` | Strengthen format to require flat dict |

## Data Structures

### New LLM Schemas (`backend/app/schemas/llm.py`)

**IMPORTANT: All code uses Pydantic v2 syntax (project has pydantic 2.5.3)**

```python
from pydantic import BaseModel, Field, ConfigDict, RootModel
from typing import Dict, Any, List, Optional


# 1. Image Prompt Generation
class LLMImagePromptResponse(BaseModel):
    """LLM response for image prompt generation."""
    model_config = ConfigDict(extra="allow")

    main_prompt: str
    style_suffix: str
    negative_prompt: str
    recommended_aspect_ratio: str = Field(default="9:16")


# 2. Scenario Generation (3 methods share this schema)
class CameraMovement(BaseModel):
    """Camera movement descriptor."""
    model_config = ConfigDict(extra="allow")

    type: str
    speed: str
    description: str


class KeyMoment(BaseModel):
    """Timeline moment in scenario."""
    model_config = ConfigDict(extra="allow")

    timestamp: str
    action: str


class LLMScenarioResponse(BaseModel):
    """LLM response for scenario generation.

    Used by:
    - generate_scenario()
    - generate_scenario_from_description()
    - generate_scenario_from_template() — adds image_prompt
    """
    model_config = ConfigDict(extra="allow")

    # Core fields (always present)
    motion_prompt: str
    camera_movement: CameraMovement
    subject_action: str
    key_moments: List[KeyMoment]

    # Optional fields (only in generate_scenario_from_template)
    image_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    atmosphere_change: Optional[str] = None


# 3. Content Validation
class CriteriaResult(BaseModel):
    """Validation result for single criterion."""
    model_config = ConfigDict(extra="allow")

    score: int = Field(ge=0, le=100)
    comment: str


class LLMValidationResponse(BaseModel):
    """LLM response for content validation."""
    model_config = ConfigDict(extra="allow")

    status: str  # "pass" | "pass_with_warnings" | "fail" — kept as str, not Literal
    score: int = Field(ge=0, le=100)
    criteria_results: Dict[str, CriteriaResult]
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# 4. Publishing Metadata
class PlatformMeta(BaseModel):
    """Publishing metadata for single platform."""
    model_config = ConfigDict(extra="allow")

    title: str
    description: str
    hashtags: str


class LLMPublishingMetaResponse(RootModel[Dict[str, PlatformMeta]]):
    """LLM response for publishing metadata.

    Flat dict: {"instagram": {...}, "tiktok": {...}}
    Prompt enforces this format. Validation + retry if LLM wraps it.

    Usage:
        validated = LLMPublishingMetaResponse.model_validate(raw_dict)
        data = validated.root  # Dict[str, PlatformMeta]
    """
    pass


# 5. Content Variants
class LLMContentVariant(BaseModel):
    """Single content variant WITHOUT server-side id."""
    model_config = ConfigDict(extra="allow")

    description: str
    content_variables: Dict[str, Any]  # Intentionally dynamic


class LLMContentVariantsResponse(BaseModel):
    """LLM response for content variants generation."""
    model_config = ConfigDict(extra="allow")

    variants: List[LLMContentVariant]
```

### Storage

No database changes — validation happens in-memory before returning to API.

## API Changes

### New Method in `openai_client.py`

```python
from pydantic import BaseModel, ValidationError
from typing import Type

async def generate_validated_json(
    self,
    prompt: str,
    response_schema: Type[BaseModel],
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_retries: int = 1
) -> BaseModel:
    """
    Generate JSON response with Pydantic validation.

    Validation is ALWAYS applied — including custom prompts.

    Args:
        prompt: User prompt
        response_schema: Pydantic v2 model class to validate against
        system_prompt: System prompt
        model: LLM model override
        temperature: Temperature for generation
        max_retries: Number of validation retries (default 1)

    Returns:
        Validated Pydantic model instance

    Raises:
        OpenAIClientError: If validation fails after retries
    """
    for attempt in range(max_retries + 1):
        try:
            # Generate JSON
            raw_response = await self.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature
            )

            # Validate with Pydantic v2
            validated = response_schema.model_validate(raw_response)

            logger.info(
                f"LLM response validated: "
                f"{response_schema.__name__} (attempt {attempt + 1})"
            )
            return validated

        except ValidationError as e:
            if attempt < max_retries:
                error_details = self._format_validation_error(e)
                prompt = self._build_retry_prompt(
                    original_prompt=prompt,
                    validation_error=error_details,
                    expected_schema=response_schema
                )

                logger.warning(
                    f"LLM validation failed (attempt {attempt + 1}), "
                    f"retrying: {error_details}"
                )
                continue
            else:
                error_details = self._format_validation_error(e)
                logger.error(
                    f"LLM validation failed after {max_retries + 1} attempts: "
                    f"{error_details}"
                )
                raise OpenAIClientError(
                    f"LLM response validation failed: {error_details}"
                )


def _format_validation_error(self, e: ValidationError) -> str:
    """Format Pydantic v2 validation error for logging and retry."""
    errors = []
    for err in e.errors():
        field = ".".join(str(x) for x in err["loc"])
        msg = err["msg"]
        errors.append(f"{field}: {msg}")
    return "; ".join(errors)


def _build_retry_prompt(
    self,
    original_prompt: str,
    validation_error: str,
    expected_schema: Type[BaseModel]
) -> str:
    """Build retry prompt with validation error context."""
    # Pydantic v2: model_json_schema() instead of schema_json()
    import json
    schema_str = json.dumps(expected_schema.model_json_schema(), indent=2)

    return f"""{original_prompt}

IMPORTANT: Previous response had validation errors:
{validation_error}

Expected JSON schema:
{schema_str}

Please fix the errors and return valid JSON matching this schema exactly."""
```

### Migration Pattern for openai_service.py

Each method follows this pattern:

**BEFORE:**
```python
async def generate_image_prompt(...) -> Dict[str, Any]:
    # ...
    if custom_prompt:
        result = await self.client.generate_json(
            prompt=custom_prompt.user_prompt,
            system_prompt=custom_prompt.system_prompt,
        )
    else:
        result = await self.client.generate_json(...)
    return result  # ← No validation
```

**AFTER:**
```python
async def generate_image_prompt(...) -> Dict[str, Any]:
    # ...
    if custom_prompt:
        validated = await self.client.generate_validated_json(
            prompt=custom_prompt.user_prompt,
            response_schema=LLMImagePromptResponse,  # ← Always validate
            system_prompt=custom_prompt.system_prompt,
            temperature=0.6
        )
    else:
        validated = await self.client.generate_validated_json(
            prompt=prompt,
            response_schema=LLMImagePromptResponse,
            system_prompt=IMAGE_PROMPT_SYSTEM_PROMPT,
            temperature=0.6
        )
    return validated.model_dump()  # ← Pydantic v2
```

**Key rule: validation applies to ALL code paths, including custom_prompt.**

### Publishing Meta Migration (special case)

**BEFORE:**
```python
async def generate_publishing_meta(...) -> Dict[str, Dict[str, str]]:
    result = await self.client.generate_json(...)
    platform_data = self._extract_platform_data(result, platforms)  # ← Workaround
    for platform in platforms:
        if platform not in platform_data:
            platform_data[platform] = {"title": "Untitled", ...}  # ← Defaults
    return platform_data
```

**AFTER:**
```python
async def generate_publishing_meta(...) -> Dict[str, Dict[str, str]]:
    validated = await self.client.generate_validated_json(
        prompt=prompt,
        response_schema=LLMPublishingMetaResponse,
        system_prompt="You are an SMM expert...",
        temperature=0.7
    )
    platform_data = validated.root  # ← RootModel: Dict[str, PlatformMeta]

    # Fill missing platforms with defaults
    result = {}
    for platform in platforms:
        if platform in platform_data:
            result[platform] = platform_data[platform].model_dump()
        else:
            result[platform] = {"title": "Untitled", "description": "", "hashtags": ""}
    return result
```

### Server-side Normalization Example

In `backend/app/api/ai_generation.py`:

```python
@router.post("/generate-variants", response_model=VariantsResponse)
async def generate_content_variants(...):
    # Get validated LLM response (no 'id' field)
    llm_variants = await openai_service.generate_content_variants(...)

    # Server-side normalization: add 'id' field
    api_variants = [
        {"id": idx, **v}
        for idx, v in enumerate(llm_variants, start=1)
    ]

    return {"variants": api_variants}
```

## Dead Code Removal

After migration, the following helpers become unused and must be **deleted**:

| Method | File | Reason |
|--------|------|--------|
| `_extract_list_from_response()` | `openai_service.py` | Replaced by `validated.variants` direct access |
| `_extract_platform_data()` | `openai_service.py` | Replaced by `validated.root` + strict prompt format |

## Implementation Steps

### Phase 1: Infrastructure

1. **[STEP 1] Create `backend/app/schemas/llm.py`**
   - Pydantic v2 syntax: `model_config = ConfigDict(extra="allow")`, `RootModel`
   - DRAFT schemas based on prompt templates
   - Validate required fields, allow optional/extra fields

2. **[STEP 2] Add `generate_validated_json()` to `openai_client.py`**
   - Pydantic v2: `model_validate()`, `model_json_schema()`
   - Import `ValidationError` from `pydantic`
   - Add `_format_validation_error()` and `_build_retry_prompt()` helpers
   - Retry once with error context on ValidationError
   - Raise OpenAIClientError if all retries fail

3. **[STEP 3] Unit tests for `generate_validated_json()`**
   - Test: valid data → passes validation → returns model
   - Test: invalid data → retry → second attempt valid → returns model
   - Test: invalid data → retry → still invalid → raises OpenAIClientError
   - Test: `_format_validation_error()` produces readable output
   - Mock `generate_json()` to control LLM responses

### Phase 2: Migration (all 7 methods)

4. **[STEP 4] Migrate `generate_image_prompt()` in `openai_service.py`**
   - Use `LLMImagePromptResponse` schema
   - Validate both standard AND custom_prompt paths
   - Return `validated.model_dump()`

5. **[STEP 5] Migrate scenario methods (3 methods)**
   - `generate_scenario()` — validate both standard + custom_prompt
   - `generate_scenario_from_description()` — validate both standard + custom_prompt
   - `generate_scenario_from_template()` — no custom_prompt, standard only
   - All use `LLMScenarioResponse` schema

6. **[STEP 6] Migrate `validate_content()`**
   - Use `LLMValidationResponse` schema
   - Validate nested `criteria_results` with `CriteriaResult` model

7. **[STEP 7] Migrate `generate_publishing_meta()`**
   - Use `LLMPublishingMetaResponse` (`RootModel[Dict[str, PlatformMeta]]`)
   - Update `prompts/publishing.py` — strengthen format instructions
   - Remove `_extract_platform_data()` helper
   - Fill missing platforms with defaults after validation

8. **[STEP 8] Migrate `generate_content_variants()`**
   - Use `LLMContentVariantsResponse` schema
   - Add system_prompt (currently missing)
   - Remove `_extract_list_from_response()` helper
   - Return list of dicts via `model_dump()`

9. **[STEP 9] Server-side normalization in `ai_generation.py`**
   - In `/generate-variants` endpoint: add `id` via enumerate
   - In `/regenerate-variants` endpoint: add `id` via enumerate

10. **[STEP 10] Update prompt templates**
    - `prompts/variants.py` — remove `"id"` from example JSON (lines 36, 45, 56)
    - `prompts/publishing.py` — strengthen format to require flat dict without wrapper keys

11. **[STEP 11] Update mock data** _(after STEP 12, based on real LLM output)_
    - Use real LLM responses from STEP 12 as reference for mock data
    - `backend/app/services/mock_data.py` — update to match real field names and structure
    - `backend/tests/fixtures/mock_responses.py` — same, based on real output
    - Known fixes: `time` → `timestamp`, `feedback` → `comment`, add missing `subject_action`
    - Mock data must pass LLM schema validation (verify with `model_validate()`)

### Phase 3: Verification (all before deploy)

12. **[STEP 12] Verify schemas against real LLM output** _(STEP 11 depends on this)_
    - Run each of the 7 methods against real OpenAI API (not mock)
    - Compare actual response fields with schema expectations
    - Fix any schema mismatches found
    - Save real responses as reference for mock data (used in STEP 11)

13. **[STEP 13] Run full test suite**
    - `cd backend && .venv/bin/pytest` — all existing tests pass
    - `cd frontend && npm run build` — no TypeScript errors

14. **[STEP 14] Integration test on staging**
    - Full workflow: create project → generate variants → select variant → generate scenario → verify all steps complete
    - Verify variants have server-side `id` field
    - Verify retry mechanism works (check logs for validation warnings)
    - Verify custom prompts still work with validation

### Phase 4: Deploy

15. **[STEP 15] Deploy all changes together**
    - Single deploy to `dev` with all 7 methods migrated
    - Monitor logs for `"LLM validation failed"` warnings post-deploy
    - If validation failure rate > 10% on any method → investigate schema mismatch

## Edge Cases

| Case | Handling |
|------|----------|
| **LLM returns null for required field** | ValidationError → retry with error context → if fails, raise 500 |
| **LLM returns wrong type (string instead of int)** | Pydantic coerces if possible, else ValidationError → retry |
| **LLM adds extra fields not in schema** | `extra="allow"` in all models → allowed, passed through |
| **LLM returns list instead of dict** | ValidationError → retry with schema example → if fails, raise 500 |
| **content_variables has unknown structure** | `Dict[str, Any]` → no validation, fully dynamic |
| **Retry also fails validation** | Raise `OpenAIClientError` → API returns 500 with error message |
| **Mock mode enabled** | Skip validation, return mock data as-is (existing behavior) |
| **Custom prompt returns unexpected format** | Validation always on → retry with schema → if fails, 500 (user sees their prompt doesn't work) |
| **Platform missing in publishing meta** | Fill with default after validation |
| **Publishing meta wrapped in `{"platforms": {...}}`** | ValidationError (RootModel expects flat dict) → retry → LLM returns flat dict |
| **Variants list is empty** | Valid response (empty list) → return as-is |
| **Old API tests expect raw dicts** | Return `.model_dump()` from Pydantic models (backward compatible) |

## Pydantic v1 → v2 Migration Cheatsheet

| v1 (DON'T USE) | v2 (USE THIS) |
|-----------------|---------------|
| `class Config: extra = "allow"` | `model_config = ConfigDict(extra="allow")` |
| `.parse_obj(data)` | `.model_validate(data)` |
| `.dict()` | `.model_dump()` |
| `.schema_json()` | `json.dumps(model.model_json_schema())` |
| `__root__: Dict[str, T]` | `RootModel[Dict[str, T]]` (access via `.root`) |
| `from pydantic import validator` | `from pydantic import field_validator` |

## Testing

### Unit Tests (`backend/tests/test_services/test_validated_json.py`)
- [ ] `test_valid_data_passes_validation` — correct dict → returns Pydantic model
- [ ] `test_retry_on_validation_error` — first call invalid, second valid → returns model
- [ ] `test_raises_after_max_retries` — all attempts invalid → raises OpenAIClientError
- [ ] `test_format_validation_error_readable` — error message includes field names and reasons
- [ ] `test_retry_prompt_includes_schema` — retry prompt contains JSON schema and error details
- [ ] `test_api_error_not_retried` — OpenAIClientError from generate_json() propagates directly

### Schema Verification (STEP 12 — against real LLM)
- [ ] `generate_image_prompt()` → real output matches `LLMImagePromptResponse`
- [ ] `generate_scenario()` → real output matches `LLMScenarioResponse`
- [ ] `generate_scenario_from_template()` → real output matches `LLMScenarioResponse` (with `image_prompt`)
- [ ] `validate_content()` → real output matches `LLMValidationResponse`
- [ ] `generate_publishing_meta()` → real output matches `LLMPublishingMetaResponse`
- [ ] `generate_content_variants()` → real output matches `LLMContentVariantsResponse`

### Build Verification
- [ ] `cd backend && .venv/bin/pytest` passes
- [ ] `cd frontend && npm run build` passes

### Integration Tests (STEP 14 — staging)
- [ ] Full workflow: create project → variants → scenario → all steps pass
- [ ] Content variants have server-side `id` field
- [ ] Regenerate variants with exclude list → new variants, no duplicates
- [ ] Custom prompt → validation still applies
- [ ] Mock mode → no validation, mock data returned as-is

## Error Handling

### Validation Failure Flow

```
1. generate_validated_json() called with schema
   ↓
2. generate_json() returns raw dict
   ↓
3. Pydantic v2 model_validate() fails (ValidationError)
   ↓
4. IF attempt < max_retries:
     Build retry prompt with error details + schema
     Retry generate_json() with error context
   ELSE:
     Log error
     Raise OpenAIClientError("LLM response validation failed: ...")
   ↓
5. API endpoint catches OpenAIClientError → 500 error
```

## Dependencies

### Existing
- `pydantic==2.5.3` — already installed for FastAPI schemas
- `openai` — already used in openai_client.py

### New
- None (no new packages required)

## Separation of LLM vs API Schemas

| Schema Type | Location | Purpose | Example |
|-------------|----------|---------|---------|
| **LLM Schema** | `backend/app/schemas/llm.py` | What we expect from OpenAI | `LLMContentVariant` (no `id`) |
| **API Schema** | `backend/app/api/ai_generation.py` | What we return to client | `ContentVariant` (has `id`) |

## Known Limitations

### Cache stores invalid responses
`openai_client.py` caches all API responses (write-only, used for mock mode). If LLM returns invalid JSON, it gets cached. This is NOT a blocker because:
- Cache is write-only in production (no read in `generate_json`)
- Retry uses different prompt → different cache key
- Same request repeated later → new LLM call, likely valid

### content_variables is unvalidated
`Dict[str, Any]` — intentionally. LLM creates dynamic keys per template. We validate that the field exists and is a dict, but not its internal structure.

### Mock data was out of sync with prompts
`MOCK_SCENARIO` used `time` instead of `timestamp`, `feedback` instead of `comment`, and lacked `subject_action`. Fixed in STEP 11. Mock mode skips validation, so this was never a runtime issue — but inconsistency between mocks and prompts made schema design harder to trust.

## Open Questions

None — all resolved:
- ✅ NOT using instructor library
- ✅ NOT using OpenAI Structured Outputs strict mode
- ✅ Using json_object + Pydantic v2 + 1 retry
- ✅ Two schema layers (LLM vs API)
- ✅ Server-side normalization for `id` field
- ✅ Pydantic v2 syntax throughout
- ✅ Validation always on (including custom prompts)
- ✅ Dead helpers removed (_extract_list_from_response, _extract_platform_data)
- ✅ Publishing meta: strict prompt format + RootModel validation
