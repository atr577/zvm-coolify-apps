import { MessageCircle } from 'lucide-react'
import type { KeyMoment, PlatformAdaptation } from '@/types'

interface StepContentRendererProps {
  stepType: string
  content: Record<string, any> | null
}

export default function StepContentRenderer({ stepType, content }: StepContentRendererProps) {
  if (!content) return <p className="text-gray-500 italic">No content</p>

  // Check if feedback was applied during regeneration
  const feedbackHistory: string[] = content._meta?.feedback_history || []
  const iterationCount = feedbackHistory.length
  const FeedbackBadge = iterationCount > 0 ? (
    <div className="mb-2 group relative">
      <div className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full cursor-help">
        <MessageCircle className="h-3 w-3 mr-1" />
        {iterationCount === 1 ? 'Feedback applied' : `${iterationCount} feedback iterations`}
      </div>
      {/* Tooltip with feedback history */}
      <div className="absolute left-0 top-full mt-1 hidden group-hover:block z-10 w-64 p-2 bg-gray-800 text-white text-xs rounded shadow-lg">
        {feedbackHistory.map((fb, i) => (
          <div key={i} className={i > 0 ? 'mt-1 pt-1 border-t border-gray-600' : ''}>
            <span className="text-blue-300">#{i + 1}:</span> {fb}
          </div>
        ))}
      </div>
    </div>
  ) : null

  try {
    switch (stepType.toLowerCase()) {
      case 'story':
        return (
          <div className="space-y-2">
            {FeedbackBadge}
            {content.concept && <div><span className="font-medium">Concept:</span> {content.concept}</div>}
            {content.hook && <div><span className="font-medium">Hook:</span> {content.hook} <span className="text-gray-500">({content.hook_type})</span></div>}
            {content.climax && <div><span className="font-medium">Climax:</span> {content.climax}</div>}
            {content.tone && <div><span className="font-medium">Tone:</span> {content.tone}</div>}
            {content.pacing && <div><span className="font-medium">Pacing:</span> {content.pacing}</div>}
            {content.emotional_trigger && <div><span className="font-medium">Emotion:</span> {content.emotional_trigger}</div>}
            {content.duration && <div><span className="font-medium">Duration:</span> {content.duration}s</div>}
          </div>
        )
      case 'description':
        return (
          <div className="space-y-2">
            {FeedbackBadge}
            {content.scene_summary && <div><span className="font-medium">Scene:</span> {content.scene_summary}</div>}
            {content.main_subject?.description && <div><span className="font-medium">Main Subject:</span> {content.main_subject.description}</div>}
            {content.environment && (
              <div>
                <span className="font-medium">Environment:</span>
                <span className="text-sm ml-1">
                  {[content.environment.location, content.environment.time_of_day, content.environment.weather].filter(Boolean).join(', ')}
                </span>
              </div>
            )}
            {content.visual_style && (
              <div>
                <span className="font-medium">Style:</span>
                <span className="text-sm ml-1">
                  {typeof content.visual_style === 'string'
                    ? content.visual_style
                    : [content.visual_style.mood, content.visual_style.lighting, content.visual_style.aesthetic].filter(Boolean).join(', ')}
                </span>
              </div>
            )}
            {content.key_details && Array.isArray(content.key_details) && (
              <div><span className="font-medium">Details:</span> {content.key_details.join(', ')}</div>
            )}
          </div>
        )
      case 'prompt':
        return (
          <div className="space-y-2">
            {FeedbackBadge}
            {content.main_prompt && <div><span className="font-medium">Prompt:</span> <span className="text-sm">{content.main_prompt}</span></div>}
            {content.negative_prompt && <div><span className="font-medium">Negative:</span> <span className="text-sm text-gray-600">{content.negative_prompt}</span></div>}
            {content.style_keywords && <div><span className="font-medium">Style:</span> {Array.isArray(content.style_keywords) ? content.style_keywords.join(', ') : content.style_keywords}</div>}
          </div>
        )
      case 'image':
        return (
          <div className="space-y-2">
            {content.image_url && (
              <img
                src={content.image_url}
                alt="Generated"
                className="w-full max-w-md rounded-lg shadow-lg"
                style={{ maxHeight: '400px', objectFit: 'contain' }}
              />
            )}
          </div>
        )
      case 'scenario':
        return (
          <div className="space-y-2">
            {FeedbackBadge}
            {content.motion_prompt && <div><span className="font-medium">Motion:</span> <span className="text-sm">{content.motion_prompt}</span></div>}
            {content.camera_movement && (
              <div>
                <span className="font-medium">Camera:</span>{' '}
                {typeof content.camera_movement === 'object'
                  ? `${content.camera_movement.type} (${content.camera_movement.speed}) - ${content.camera_movement.description}`
                  : content.camera_movement}
              </div>
            )}
            {content.subject_action && <div><span className="font-medium">Action:</span> {content.subject_action}</div>}
            {content.key_moments && Array.isArray(content.key_moments) && (
              <div>
                <span className="font-medium">Key Moments:</span>
                <ul className="list-disc list-inside ml-2 text-sm">
                  {content.key_moments.map((m: KeyMoment, i: number) => (
                    <li key={i}>{m.timestamp}: {m.action}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )
      case 'video':
        return (
          <div className="space-y-2">
            {content.video_url && (
              <video
                src={content.video_url}
                controls
                className="w-full max-w-md rounded-lg shadow-lg"
                style={{ maxHeight: '400px' }}
              />
            )}
            {content.task_id && (
              <div className="text-xs text-gray-400">Task ID: {content.task_id}</div>
            )}
          </div>
        )
      case 'adaptation':
        return (
          <div className="space-y-2">
            {FeedbackBadge}
            {Object.entries(content)
              .filter(([key]) => key !== '_meta')
              .map(([platform, data]: [string, PlatformAdaptation | undefined]) => (
                <div key={platform} className="border-l-2 border-purple-300 pl-3">
                  <div className="font-medium capitalize">{platform}</div>
                  {data?.title && <div className="text-sm"><span className="text-gray-500">Title:</span> {data.title}</div>}
                  {data?.description && <div className="text-sm"><span className="text-gray-500">Description:</span> {data.description}</div>}
                  {data?.hashtags && <div className="text-sm"><span className="text-gray-500">Hashtags:</span> {data.hashtags}</div>}
                </div>
              ))}
          </div>
        )
      default:
        return (
          <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-40">
            {JSON.stringify(content, null, 2)}
          </pre>
        )
    }
  } catch (e) {
    // Fallback to JSON if rendering fails
    return (
      <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-40">
        {JSON.stringify(content, null, 2)}
      </pre>
    )
  }
}
