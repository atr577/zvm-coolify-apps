import { Volume2 } from 'lucide-react'
import PublishingSettings from '@/components/PublishingSettings'
import PublishingMetaEditor from '@/components/PublishingMetaEditor'
import MetricsSection from './MetricsSection'
import StepsListV3 from './StepsListV3'
import type { Video, VideoMetricsSummary } from '@/types'

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
            {(video.video_with_audio_url || video.video_url) && (
              <div className="relative aspect-[9/16] bg-black rounded-lg overflow-hidden">
                <video
                  src={video.video_with_audio_url ?? video.video_url ?? undefined}
                  controls
                  className="w-full h-full object-contain"
                />
                {video.video_with_audio_url && video.video_with_audio_url !== video.video_url && (
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
              platforms={video.project?.platforms || []}
              initialMeta={video.publishing_meta || video.adaptation_data || null}
            />

            <div className="mt-4">
              <PublishingSettings
                videoId={videoId}
                publishingStepId={0}
                adaptationData={video.publishing_meta || video.adaptation_data || {}}
                platforms={video.project?.platforms || []}
                videoUrl={video.video_with_audio_url || video.video_url || ''}
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
      <StepsListV3 video={video} />
    </div>
  )
}
