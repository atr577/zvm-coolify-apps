import { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle, Circle } from 'lucide-react'
import StepContentRenderer from './StepContentRenderer'
import { getStepLabel, getImageUrl, getVideoUrl, getAudioUrl } from '@/utils/video'
import type { Video } from '@/types'

interface StepsListProps {
  video: Video
}

interface StepData {
  type: string
  label: string
  content: Record<string, any> | null
  hasData: boolean
}

function buildStepsFromVideo(video: Video): StepData[] {
  const isRemix = video.project?.project_type === 'remix'
  const includeAudio = video.project?.audio_mode !== 'none'

  const allSteps: StepData[] = []

  if (!isRemix) {
    // Discover workflow: scenario → image → video → audio
    // scenario generates image_prompt + motion_prompt from story_template + content_variables
    allSteps.push({
      type: 'scenario',
      label: getStepLabel('scenario'),
      content: video.scenario_data,
      hasData: !!video.scenario_data
    })
    allSteps.push({
      type: 'image',
      label: getStepLabel('image'),
      content: getImageUrl(video) ? { image_url: getImageUrl(video) } : null,
      hasData: !!video.image_url || !!video.local_image_path
    })
    allSteps.push({
      type: 'video',
      label: getStepLabel('video'),
      content: getVideoUrl(video) ? { video_url: getVideoUrl(video) } : null,
      hasData: !!video.video_url || !!video.local_video_path
    })
  } else {
    // Remix workflow: image → video → audio
    allSteps.push({
      type: 'image',
      label: getStepLabel('image'),
      content: getImageUrl(video) ? { image_url: getImageUrl(video) } : null,
      hasData: !!video.image_url || !!video.local_image_path
    })
    allSteps.push({
      type: 'video',
      label: getStepLabel('video'),
      content: getVideoUrl(video) ? { video_url: getVideoUrl(video) } : null,
      hasData: !!video.video_url || !!video.local_video_path
    })
  }

  // Add audio step if enabled
  if (includeAudio) {
    allSteps.push({
      type: 'audio',
      label: getStepLabel('audio'),
      content: getAudioUrl(video) ? { video_url: getAudioUrl(video) } : null,
      hasData: !!video.video_with_audio_url || !!video.local_audio_path
    })
  }

  return allSteps
}

export default function StepsList({ video }: StepsListProps) {
  const [showAllSteps, setShowAllSteps] = useState(false)
  const [expandedStep, setExpandedStep] = useState<string | null>(null)

  const steps = buildStepsFromVideo(video)
  const completedCount = steps.filter(s => s.hasData).length
  const totalSteps = steps.length

  return (
    <div className="bg-white rounded-xl shadow-sm border">
      <button
        onClick={() => setShowAllSteps(!showAllSteps)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition"
      >
        <div className="flex items-center space-x-3">
          <span className="font-medium text-gray-700">
            Generation Steps ({completedCount}/{totalSteps} completed)
          </span>
          <div className="flex items-center space-x-1">
            {steps.map((step, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  step.hasData ? 'bg-green-500' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
        </div>
        {showAllSteps ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
      </button>

      {showAllSteps && (
        <div className="border-t">
          {steps.map((step, index) => (
            <div key={step.type} className="border-b last:border-0">
              <button
                onClick={() => setExpandedStep(expandedStep === step.type ? null : step.type)}
                className={`w-full flex items-center space-x-3 px-4 py-3 hover:bg-gray-50 transition ${
                  expandedStep === step.type ? 'bg-gray-50' : ''
                }`}
              >
                {step.hasData ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <Circle className="h-5 w-5 text-gray-300" />
                )}
                <span className="text-sm text-gray-500 w-16">Step {index + 1}</span>
                <span className="text-sm font-medium text-gray-700">
                  {step.label}
                </span>
                <span className="text-xs text-gray-400 ml-auto mr-2">
                  {step.hasData ? 'completed' : 'pending'}
                </span>
                {step.content && (
                  expandedStep === step.type
                    ? <ChevronDown className="h-4 w-4 text-gray-400" />
                    : <ChevronRight className="h-4 w-4 text-gray-400" />
                )}
              </button>
              {expandedStep === step.type && step.content && (
                <div className="px-4 pb-4 pt-2 bg-gray-50 border-t">
                  <div className="text-sm text-gray-700">
                    <StepContentRenderer stepType={step.type} content={step.content} />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
