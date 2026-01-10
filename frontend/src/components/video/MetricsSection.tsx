import { Eye, Heart, MessageCircle, Share2, Star, RefreshCw, TrendingUp, Youtube, Instagram, Music2 } from 'lucide-react'
import { formatMetricNumber } from '@/utils/video'
import type { VideoMetricsSummary } from '@/types'

interface MetricsSectionProps {
  metricsSummary: VideoMetricsSummary | undefined
  authorRating: number | null | undefined
  onRefresh: () => void
  onSetRating: (rating: number) => void
}

export default function MetricsSection({
  metricsSummary,
  authorRating,
  onRefresh,
  onSetRating
}: MetricsSectionProps) {
  const PlatformIcon = ({ platform }: { platform: string }) => {
    if (platform === 'youtube') return <Youtube className="h-4 w-4 text-red-600 mr-1" />
    if (platform === 'instagram') return <Instagram className="h-4 w-4 text-pink-600 mr-1" />
    if (platform === 'tiktok') return <Music2 className="h-4 w-4 text-black mr-1" />
    return <span className="text-gray-600 mr-1">•</span>
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          <TrendingUp className="h-5 w-5 mr-2 text-purple-600" />
          Performance Metrics
        </h3>
        <button
          onClick={onRefresh}
          className="p-2 hover:bg-gray-100 rounded-lg transition"
          title="Refresh metrics"
        >
          <RefreshCw className="h-4 w-4 text-gray-500" />
        </button>
      </div>

      {/* Author Rating */}
      <div className="mb-6 p-4 bg-purple-50 rounded-lg">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-purple-900">Your Rating (before publish)</span>
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                onClick={() => onSetRating(star)}
                className={`p-1 transition ${
                  (metricsSummary?.author_rating || authorRating || 0) >= star
                    ? 'text-yellow-400'
                    : 'text-gray-300 hover:text-yellow-300'
                }`}
              >
                <Star className="h-5 w-5 fill-current" />
              </button>
            ))}
          </div>
        </div>
        {(metricsSummary?.author_rating || authorRating) && (
          <p className="text-xs text-purple-700 mt-1">
            Rated {metricsSummary?.author_rating || authorRating}/5 potential
          </p>
        )}
      </div>

      {/* Totals */}
      {metricsSummary && (metricsSummary.total_views > 0 || metricsSummary.total_likes > 0) ? (
        <>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <Eye className="h-6 w-6 mx-auto mb-2 text-blue-500" />
              <div className="text-2xl font-bold text-gray-900">
                {formatMetricNumber(metricsSummary.total_views)}
              </div>
              <div className="text-xs text-gray-500">Views</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <Heart className="h-6 w-6 mx-auto mb-2 text-red-500" />
              <div className="text-2xl font-bold text-gray-900">
                {formatMetricNumber(metricsSummary.total_likes)}
              </div>
              <div className="text-xs text-gray-500">Likes</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <MessageCircle className="h-6 w-6 mx-auto mb-2 text-green-500" />
              <div className="text-2xl font-bold text-gray-900">
                {formatMetricNumber(metricsSummary.total_comments)}
              </div>
              <div className="text-xs text-gray-500">Comments</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <Share2 className="h-6 w-6 mx-auto mb-2 text-purple-500" />
              <div className="text-2xl font-bold text-gray-900">
                {formatMetricNumber(metricsSummary.total_shares)}
              </div>
              <div className="text-xs text-gray-500">Shares</div>
            </div>
          </div>

          {/* Engagement Rate */}
          {metricsSummary.avg_engagement_rate && (
            <div className="mb-6 p-4 bg-green-50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-green-900">Engagement Rate</span>
                <span className="text-xl font-bold text-green-700">
                  {metricsSummary.avg_engagement_rate.toFixed(2)}%
                </span>
              </div>
            </div>
          )}

          {/* Per Period Table */}
          {Object.keys(metricsSummary.platforms).length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">By Period</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="pb-2 w-20">Period</th>
                      <th className="pb-2">Views</th>
                      <th className="pb-2">Likes</th>
                      <th className="pb-2">Comments</th>
                      <th className="pb-2">Shares</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(['30m', '6h', '24h', '7d'] as const).map(period => {
                      const platformMetrics: { platform: string; views: number; likes: number; comments: number; shares: number }[] = []
                      Object.entries(metricsSummary.platforms).forEach(([platformName, periods]) => {
                        if (periods[period]) {
                          const m = periods[period]
                          platformMetrics.push({ platform: platformName, views: m.views, likes: m.likes, comments: m.comments, shares: m.shares })
                        }
                      })
                      if (platformMetrics.length === 0) return null

                      return (
                        <tr key={period} className="border-b last:border-0">
                          <td className="py-3 font-medium text-gray-700">{period}</td>
                          <td className="py-3">
                            <div className="flex flex-col gap-1">
                              {platformMetrics.map(m => (
                                <span key={m.platform} className="flex items-center">
                                  <PlatformIcon platform={m.platform} />
                                  <span>{m.views.toLocaleString()}</span>
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-3">
                            <div className="flex flex-col gap-1">
                              {platformMetrics.map(m => (
                                <span key={m.platform} className="flex items-center">
                                  <PlatformIcon platform={m.platform} />
                                  <span>{m.likes.toLocaleString()}</span>
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-3">
                            <div className="flex flex-col gap-1">
                              {platformMetrics.map(m => (
                                <span key={m.platform} className="flex items-center">
                                  <PlatformIcon platform={m.platform} />
                                  <span>{m.comments.toLocaleString()}</span>
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-3">
                            <div className="flex flex-col gap-1">
                              {platformMetrics.map(m => (
                                <span key={m.platform} className="flex items-center">
                                  <PlatformIcon platform={m.platform} />
                                  <span>{m.shares.toLocaleString()}</span>
                                </span>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <TrendingUp className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p>No metrics yet</p>
          <p className="text-sm mt-1">Metrics will be collected automatically after publishing</p>
        </div>
      )}
    </div>
  )
}
