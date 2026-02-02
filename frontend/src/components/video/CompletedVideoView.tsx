import { Volume2 } from 'lucide-react'
import PublishingSettings from '@/components/PublishingSettings'
import PublishingMetaEditor from '@/components/PublishingMetaEditor'
import MetricsSection from './MetricsSection'
import StepsList from './StepsList'
import { getBestVideoUrl } from '@/utils/video'
import type { Video, VideoMetricsSummary, Project } from '@/types'

// Derive platforms from social_accounts (mirrors backend get_project_platforms)
function getEffectivePlatforms(project?: Project): string[] {
  if (!project) return []
  // Priority: active social_accounts > project.platforms
  if (project.social_accounts?.length) {
    const activePlatforms = [...new Set(
      project.social_accounts
        .filter(acc => acc.is_active)
        .map(acc => acc.platform)
    )]
    if (activePlatforms.length > 0) return activePlatforms
  }
  return project.platforms || []
}

interface CompletedVideoViewProps {
  video: Video
  videoId: number
  metricsSummary?: VideoMetricsSummary
  onRefetchMetrics: () => void
  onSetRating: (rating: number) => void
}

export default function CompletedVideoView({
  video,
  videoId,
  metricsSummary,
  onRefetchMetrics,
  onSetRating
}: CompletedVideoViewProps) {
  return (
    <div className="space-y-6">
      {/* Video + Publishing Status */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="grid md:grid-cols-2 gap-6 p-6">
          {/* Video Preview */}
          <div>
            {getBestVideoUrl(video) && (
              <div className="relative aspect-[9/16] bg-black rounded-lg overflow-hidden">
                <video
                  src={getBestVideoUrl(video) ?? undefined}
                  controls
                  preload="metadata"
                  className="w-full h-full object-contain"
                />
                {(video.video_with_audio_url || video.local_audio_path) &&
                 (video.video_with_audio_url !== video.video_url || video.local_audio_path) && (
                  <div className="absolute bottom-2 left-2">
                    <span className="px-2 py-1 bg-green-500 text-white text-xs rounded flex items-center">
                      <Volume2 className="h-3 w-3 mr-1" />
                      With Audio
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Publishing Metadata & Settings */}
          <div className="flex flex-col">
            <PublishingMetaEditor
              videoId={videoId}
              platforms={getEffectivePlatforms(video.project)}
              initialMeta={video.publishing_meta || video.adaptation_data || null}
            />

            <div className="mt-4">
              <PublishingSettings
                videoId={videoId}
                publishingStepId={0}
                adaptationData={video.publishing_meta || video.adaptation_data || {}}
                platforms={getEffectivePlatforms(video.project)}
                videoUrl={getBestVideoUrl(video) || ''}
                projectSocialAccounts={video.project?.social_accounts}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Section */}
      <MetricsSection
        metricsSummary={metricsSummary}
        authorRating={video.author_rating}
        onRefresh={onRefetchMetrics}
        onSetRating={onSetRating}
      />

      {/* Generation Steps */}
      <StepsList video={video} />
    </div>
  )
}
