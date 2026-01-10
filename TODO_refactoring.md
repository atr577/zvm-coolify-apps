# Refactoring Plan

## File Size Guidelines

| Type | Recommended | Maximum | Action if exceeded |
|------|-------------|---------|-------------------|
| React Component | 100-200 | 300-400 | Split into subcomponents |
| React Page | 200-400 | 500-600 | Extract sections to components |
| React Hook | 50-150 | 200 | Split by functionality |
| Python API Router | 200-400 | 500 | Use sub-routers |
| Python Service | 300-500 | 700 | Split by domain |

---

## Frontend Refactoring

### CRITICAL: VideoDetail.tsx (1320 lines)
**Target: 400-500 lines**

Extract to separate components:
- [ ] `components/video/VideoPlayer.tsx` - video preview with audio badge
- [ ] `components/video/MetricsSection.tsx` - performance metrics display
- [ ] `components/video/AudioVariantSelector.tsx` - audio variant tabs and selection
- [ ] `components/video/StepApprovalControls.tsx` - approve/reject buttons with feedback
- [ ] `components/video/StepsProgress.tsx` - collapsible steps list
- [ ] `components/video/StepContentRenderer.tsx` - renderStepContent logic
- [ ] `components/video/ManualWorkflowStart.tsx` - first step for MANUAL mode

Extract hooks:
- [ ] `hooks/useVideoWorkflow.ts` - mutations (approve, regenerate, audio select)
- [ ] `hooks/useVideoMetrics.ts` - metrics fetching and rating

### HIGH: Dashboard.tsx (593 lines)
**Target: 300-400 lines**

- [ ] `components/dashboard/ProjectSection.tsx` - project card with videos list
- [ ] `components/dashboard/VideoCard.tsx` - single video in list
- [ ] `components/dashboard/EmptyState.tsx` - no projects/videos state

### MEDIUM: Files 400-500 lines
- [ ] `VideoWorkflowView.tsx` (418) - consider splitting step renderers
- [ ] `Workspaces.tsx` (423) - extract WorkspaceCard, MembersList

### OK: Files under 400 lines
- Settings.tsx (370)
- Analytics.tsx (368)
- PublishingSettings.tsx (348)
- ProjectForm.tsx (323)

---

## Backend Refactoring

### CRITICAL: openai_service.py (1017 lines)
**Target: 500-600 lines**

Split into:
- [ ] `services/llm/base.py` - OpenAIService base class
- [ ] `services/llm/story_generator.py` - generate_story, generate_story_from_template
- [ ] `services/llm/description_generator.py` - generate_description
- [ ] `services/llm/prompt_generator.py` - generate_image_prompt
- [ ] `services/llm/scenario_generator.py` - generate_scenario
- [ ] `services/llm/meta_generator.py` - generate_publishing_meta
- [ ] `services/llm/validator.py` - validate_content

Alternative (simpler):
- [ ] Move all prompt templates to `services/prompts/` directory
- [ ] Keep generators in openai_service but import prompts

### HIGH: workflow.py API (885 lines)
**Target: 400-500 lines**

Split into sub-routers:
- [ ] `api/workflow/generation.py` - generate-* endpoints
- [ ] `api/workflow/approval.py` - approve-step, auto-generate
- [ ] `api/workflow/publishing.py` - generate-meta, update-meta, adapt-for-platforms
- [ ] `api/workflow/__init__.py` - combine routers

### MEDIUM: piapi_client.py (700 lines)
**Target: 400-500 lines**

- [ ] Already has models_config.py extracted
- [ ] Consider splitting image/video/audio methods into separate files

### OK: Files under 500 lines
- auth.py (529) - slightly over, but auth is cohesive
- metrics.py (479)
- prompt_builders.py (407)
- publishing.py (350)

---

## Priority Order

1. **VideoDetail.tsx** - most complex, hardest to maintain
2. **openai_service.py** - core AI logic, growing with each feature
3. **workflow.py** - many endpoints, hard to navigate
4. **Dashboard.tsx** - user-facing, needs to stay maintainable

---

## Implementation Notes

### When splitting React components:
```tsx
// Before: everything in VideoDetail.tsx
// After:
import { MetricsSection } from '@/components/video/MetricsSection'
import { StepsProgress } from '@/components/video/StepsProgress'
// etc.
```

### When splitting Python services:
```python
# Before: everything in openai_service.py
# After:
from app.services.llm.story_generator import StoryGenerator
from app.services.llm.meta_generator import MetaGenerator
# etc.
```

### File organization after refactoring:
```
frontend/src/
  components/
    video/           # VideoDetail subcomponents
    dashboard/       # Dashboard subcomponents
  hooks/
    useVideoWorkflow.ts
    useVideoMetrics.ts

backend/app/
  api/
    workflow/        # Split workflow endpoints
  services/
    llm/             # Split AI services
    prompts/         # Prompt templates
```

---

## Definition of Done

- [ ] No file exceeds maximum line count
- [ ] Each file has single responsibility
- [ ] Imports are clean (no circular dependencies)
- [ ] Tests still pass
- [ ] No functionality changes
