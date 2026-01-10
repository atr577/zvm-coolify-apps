---
id: T30
title: "Frontend Polling & Lifecycle"
status: todo
priority: medium
created: 2026-01-10
updated: 2026-01-10
tags: ['frontend']
depends_on: ['T24', 'T22']
estimate: "8h"
branch: ""
---

# Task 30: Frontend Polling & Lifecycle

> **Источник:** [TARGET_WORKFLOW.md](../../docs/TARGET_WORKFLOW.md) секция 15

---

## Цель

Реализовать полный frontend lifecycle:
- Polling strategy для async operations
- Status-based UI rendering
- Proper handling всех workflow states
- Return to page recovery

---

## Задачи

### 30.1 useVideoPolling hook (2h)

**Файл:** `frontend/src/hooks/useVideoPolling.ts` (NEW)

```typescript
import { useState, useEffect, useCallback, useRef } from 'react';
import { Video, VideoStatus } from '../types/video';
import { api } from '../services/api';

interface UseVideoPollingOptions {
  pollInterval?: number;
  onStatusChange?: (status: VideoStatus) => void;
  onComplete?: (video: Video) => void;
  onError?: (video: Video) => void;
}

interface UseVideoPollingResult {
  video: Video | null;
  isPolling: boolean;
  error: Error | null;
  startPolling: () => void;
  stopPolling: () => void;
  refetch: () => Promise<void>;
}

export function useVideoPolling(
  videoId: number,
  options: UseVideoPollingOptions = {}
): UseVideoPollingResult {
  const {
    pollInterval = 3000,
    onStatusChange,
    onComplete,
    onError
  } = options;

  const [video, setVideo] = useState<Video | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const previousStatusRef = useRef<VideoStatus | null>(null);

  const fetchVideo = useCallback(async () => {
    try {
      const response = await api.get(`/videos/${videoId}`);
      const fetchedVideo = response.data;

      setVideo(fetchedVideo);
      setError(null);

      // Notify on status change
      if (previousStatusRef.current !== fetchedVideo.status) {
        onStatusChange?.(fetchedVideo.status);
        previousStatusRef.current = fetchedVideo.status;
      }

      // Handle terminal states
      if (fetchedVideo.status === 'completed') {
        onComplete?.(fetchedVideo);
        return true; // Stop polling
      }

      if (fetchedVideo.status === 'failed') {
        onError?.(fetchedVideo);
        return true; // Stop polling
      }

      if (fetchedVideo.status === 'awaiting_approval') {
        return true; // Stop polling, user action needed
      }

      return false; // Continue polling

    } catch (err) {
      setError(err as Error);
      return true; // Stop polling on error
    }
  }, [videoId, onStatusChange, onComplete, onError]);

  const startPolling = useCallback(() => {
    if (intervalRef.current) return;

    setIsPolling(true);

    const poll = async () => {
      const shouldStop = await fetchVideo();
      if (shouldStop) {
        stopPolling();
      }
    };

    // Initial fetch
    poll();

    // Set up interval
    intervalRef.current = setInterval(poll, pollInterval);
  }, [fetchVideo, pollInterval]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const refetch = useCallback(async () => {
    await fetchVideo();
  }, [fetchVideo]);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return {
    video,
    isPolling,
    error,
    startPolling,
    stopPolling,
    refetch
  };
}
```

---

### 30.2 useStepVariants hook (1h)

**Файл:** `frontend/src/hooks/useStepVariants.ts` (NEW)

```typescript
import { useState, useCallback } from 'react';
import { Variant, StepType } from '../types/workflow';
import { api } from '../services/api';

interface UseStepVariantsResult {
  variants: Variant[];
  selectedVariantId: number | null;
  isLoading: boolean;
  error: Error | null;
  fetchVariants: () => Promise<void>;
  selectVariant: (variantId: number) => Promise<void>;
  approve: (continueWorkflow?: boolean) => Promise<void>;
  regenerate: (feedback?: string) => Promise<void>;
}

export function useStepVariants(
  videoId: number,
  stepType: StepType
): UseStepVariantsResult {
  const [variants, setVariants] = useState<Variant[]>([]);
  const [selectedVariantId, setSelectedVariantId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchVariants = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.get(`/workflow/${videoId}/${stepType}/variants`);
      const allVariants = response.data.variants || [];
      setVariants(allVariants);

      // Find selected variant
      const selected = allVariants.find((v: Variant) => v.is_selected);
      setSelectedVariantId(selected?.id || null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, [videoId, stepType]);

  const selectVariant = useCallback(async (variantId: number) => {
    try {
      await api.post(`/workflow/${videoId}/${stepType}/select-variant`, {
        variant_id: variantId
      });
      setSelectedVariantId(variantId);
    } catch (err) {
      setError(err as Error);
      throw err;
    }
  }, [videoId, stepType]);

  const approve = useCallback(async (continueWorkflow = true) => {
    try {
      await api.post(`/workflow/${videoId}/${stepType}/approve`, {
        continue_workflow: continueWorkflow
      });
    } catch (err) {
      setError(err as Error);
      throw err;
    }
  }, [videoId, stepType]);

  const regenerate = useCallback(async (feedback?: string) => {
    if (!selectedVariantId) {
      throw new Error('No variant selected for regeneration');
    }
    try {
      await api.post(`/workflow/${videoId}/${stepType}/regenerate`, {
        variant_id: selectedVariantId,
        feedback
      });
    } catch (err) {
      setError(err as Error);
      throw err;
    }
  }, [videoId, stepType, selectedVariantId]);

  return {
    variants,
    selectedVariantId,
    isLoading,
    error,
    fetchVariants,
    selectVariant,
    approve,
    regenerate
  };
}
```

---

### 30.3 VideoWorkflowPage component (3h)

**Файл:** `frontend/src/pages/VideoWorkflow.tsx` (NEW or REFACTOR)

```typescript
import React, { useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useVideoPolling } from '../hooks/useVideoPolling';
import { useStepVariants } from '../hooks/useStepVariants';
import { api } from '../services/api';

// Sub-components
import { WorkflowProgress } from '../components/WorkflowProgress';
import { StepApproval } from '../components/StepApproval';
import { VideoComplete } from '../components/VideoComplete';
import { VideoError } from '../components/VideoError';
import { LoadingSpinner } from '../components/LoadingSpinner';

export function VideoWorkflowPage() {
  const { videoId } = useParams<{ videoId: string }>();
  const id = parseInt(videoId!, 10);

  const {
    video,
    isPolling,
    error,
    startPolling,
    refetch
  } = useVideoPolling(id, {
    onStatusChange: (status) => {
      console.log('Status changed to:', status);
    }
  });

  // Auto-start polling if video is in-progress
  useEffect(() => {
    if (video?.status === 'in_progress') {
      startPolling();
    }
  }, [video?.status, startPolling]);

  // Initial fetch
  useEffect(() => {
    refetch();
  }, [refetch]);

  const handleStartGeneration = useCallback(async () => {
    try {
      await api.post('/workflow/auto-generate-to-video', { video_id: id });
      startPolling();
    } catch (err) {
      if ((err as any).response?.status === 409) {
        // Already in progress, just start polling
        startPolling();
      } else {
        throw err;
      }
    }
  }, [id, startPolling]);

  const handleApproveAndContinue = useCallback(async () => {
    await refetch();
    if (video?.status !== 'completed') {
      startPolling();
    }
  }, [refetch, video?.status, startPolling]);

  const handleRetry = useCallback(async () => {
    if (!video?.current_step) return;
    await api.post(`/workflow/${id}/${video.current_step}/retry`);
    startPolling();
  }, [id, video?.current_step, startPolling]);

  if (error) {
    return <div className="error">Error loading video: {error.message}</div>;
  }

  if (!video) {
    return <LoadingSpinner />;
  }

  // Render based on status
  switch (video.status) {
    case 'pending':
      return (
        <div className="video-workflow">
          <h1>Ready to Generate</h1>
          <p>Mode: {video.workflow_mode}</p>
          <button onClick={handleStartGeneration}>
            Start Generation
          </button>
        </div>
      );

    case 'in_progress':
      return (
        <div className="video-workflow">
          <WorkflowProgress
            currentStep={video.current_step}
            stepsCompleted={video.steps_completed || []}
            isPolling={isPolling}
          />
        </div>
      );

    case 'awaiting_approval':
      return (
        <div className="video-workflow">
          <StepApproval
            videoId={id}
            stepType={video.current_step!}
            video={video}
            onApprove={handleApproveAndContinue}
          />
        </div>
      );

    case 'completed':
      return (
        <div className="video-workflow">
          <VideoComplete video={video} />
        </div>
      );

    case 'failed':
      return (
        <div className="video-workflow">
          <VideoError
            video={video}
            onRetry={handleRetry}
          />
        </div>
      );

    default:
      return <div>Unknown status: {video.status}</div>;
  }
}
```

---

### 30.4 StepApproval component (1.5h)

**Файл:** `frontend/src/components/StepApproval.tsx` (NEW or REFACTOR)

```typescript
import React, { useEffect, useState } from 'react';
import { useStepVariants } from '../hooks/useStepVariants';
import { Video, StepType } from '../types';

interface StepApprovalProps {
  videoId: number;
  stepType: StepType;
  video: Video;
  onApprove: () => void;
}

export function StepApproval({ videoId, stepType, video, onApprove }: StepApprovalProps) {
  const {
    variants,
    selectedVariantId,
    isLoading,
    fetchVariants,
    selectVariant,
    approve,
    regenerate
  } = useStepVariants(videoId, stepType);

  const [feedbackMode, setFeedbackMode] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchVariants();
  }, [fetchVariants]);

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await approve(true); // continue_workflow = true
      onApprove();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegenerate = async () => {
    setIsSubmitting(true);
    try {
      await regenerate(feedback);
      setFeedbackMode(false);
      setFeedback('');
      // Will trigger polling in parent
      onApprove();
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <div>Loading variants...</div>;
  }

  const isSingleVariant = variants.length === 1;
  const selectedVariant = variants.find(v => v.id === selectedVariantId);

  return (
    <div className="step-approval">
      <h2>Step: {stepType}</h2>

      {isSingleVariant ? (
        // Single variant UI
        <div className="single-variant">
          <div className="variant-preview">
            <VariantContent variant={variants[0]} stepType={stepType} />
          </div>

          <div className="actions">
            <button
              onClick={handleApprove}
              disabled={isSubmitting}
              className="btn-approve"
            >
              Approve & Continue
            </button>

            <button
              onClick={() => setFeedbackMode(true)}
              disabled={isSubmitting}
              className="btn-refine"
            >
              Refine with Feedback
            </button>
          </div>
        </div>
      ) : (
        // Multi-variant UI
        <div className="multi-variant">
          <div className="variant-grid">
            {variants.map(variant => (
              <div
                key={variant.id}
                className={`variant-card ${variant.id === selectedVariantId ? 'selected' : ''}`}
                onClick={() => selectVariant(variant.id)}
              >
                <VariantContent variant={variant} stepType={stepType} />
                {variant.id === selectedVariantId && <span className="checkmark">✓</span>}
              </div>
            ))}
          </div>

          {selectedVariantId && (
            <div className="actions">
              <button
                onClick={handleApprove}
                disabled={isSubmitting}
                className="btn-approve"
              >
                Approve Selected
              </button>

              <button
                onClick={() => setFeedbackMode(true)}
                disabled={isSubmitting}
                className="btn-refine"
              >
                Refine Selected
              </button>
            </div>
          )}
        </div>
      )}

      {feedbackMode && (
        <div className="feedback-modal">
          <h3>Refine with Feedback</h3>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="What would you like to change?"
          />
          <div className="modal-actions">
            <button onClick={() => setFeedbackMode(false)}>Cancel</button>
            <button onClick={handleRegenerate} disabled={isSubmitting}>
              Regenerate
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function VariantContent({ variant, stepType }: { variant: Variant; stepType: StepType }) {
  // Render based on step type
  switch (stepType) {
    case 'IMAGE':
      return <img src={variant.content.url} alt="Generated" />;
    case 'VIDEO':
      return <video src={variant.content.url} controls />;
    case 'AUDIO':
      return <audio src={variant.content.url} controls />;
    default:
      return <pre>{JSON.stringify(variant.content, null, 2)}</pre>;
  }
}
```

---

### 30.5 Return to page recovery (0.5h)

**Файл:** `frontend/src/pages/VideoWorkflow.tsx`

```typescript
// Already handled by the status-based rendering:
// - User closes browser with video IN_PROGRESS
// - User returns, fetches video → status = IN_PROGRESS → startPolling()
// - OR status = AWAITING_APPROVAL → show approval UI
// - OR status = COMPLETED → show result

// The useEffect that auto-starts polling handles this:
useEffect(() => {
  if (video?.status === 'in_progress') {
    startPolling();
  }
}, [video?.status, startPolling]);
```

---

## Acceptance Criteria

- [ ] Polling starts automatically when video is IN_PROGRESS
- [ ] Polling stops on terminal states (COMPLETED, FAILED, AWAITING_APPROVAL)
- [ ] Single-variant UI shows Approve/Refine buttons
- [ ] Multi-variant UI shows selection + Approve
- [ ] Feedback modal allows text input for regeneration
- [ ] Return to page resumes from current state
- [ ] 409 Conflict handled gracefully

---

## Тестирование

```typescript
// Jest/RTL tests
describe('useVideoPolling', () => {
  it('should start polling and stop on completion', async () => {
    const onComplete = jest.fn();
    const { result } = renderHook(() =>
      useVideoPolling(1, { onComplete })
    );

    // Mock API responses
    mockApi.get.mockResolvedValueOnce({ data: { status: 'in_progress' } });
    mockApi.get.mockResolvedValueOnce({ data: { status: 'completed' } });

    result.current.startPolling();

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled();
      expect(result.current.isPolling).toBe(false);
    });
  });
});

describe('StepApproval', () => {
  it('should show single variant UI for 1 variant', () => {
    const { getByText } = render(
      <StepApproval
        videoId={1}
        stepType="STORY"
        video={mockVideo}
        onApprove={jest.fn()}
      />
    );

    expect(getByText('Approve & Continue')).toBeInTheDocument();
  });

  it('should show multi variant UI for multiple variants', () => {
    mockUseStepVariants.mockReturnValue({
      variants: [{ id: 1 }, { id: 2 }, { id: 3 }],
      // ...
    });

    const { getAllByTestId } = render(<StepApproval ... />);
    expect(getAllByTestId('variant-card')).toHaveLength(3);
  });
});
```

---

## Checklist

- [ ] 30.1 useVideoPolling hook
- [ ] 30.2 useStepVariants hook
- [ ] 30.3 VideoWorkflowPage component
- [ ] 30.4 StepApproval component (single + multi variant)
- [ ] 30.5 Return to page recovery verified
- [ ] Error handling for 409 Conflict
- [ ] Loading states
- [ ] Tests pass
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
