import {
  Eye, Heart, MessageCircle, Share2, Star, RefreshCw, TrendingUp,
  Youtube, Instagram, Music2
} from 'lucide-react'

interface PlatformMetric {
  platform: string
  views: number
  likes: number
  comments: number
  shares: number
  engagement_rate: number | null
  fetched_at: string
}

interface MetricsSummaryData {
  total_views: number
  total_likes: number
  total_comments: number
  total_shares: number
  avg_engagement_rate: number | null
  author_rating: number | null
  platforms: PlatformMetric[]
}

interface MetricsSummaryProps {
  metrics: MetricsSummaryData | null
  authorRating: number | null
  onRefresh: () => void
  onSetRating: (rating: number) => void
}

function formatMetricNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K'
  }
  return num.toString()
}

function getPlatformIcon(platform: string) {
  switch (platform) {
    case 'youtube':
      return <Youtube className="h-5 w-5 text-red-500" />
    case 'instagram':
      return <Instagram className="h-5 w-5 text-pink-500" />
    case 'tiktok':
      return <Music2 className="h-5 w-5 text-black" />
    default:
      return null
  }
}

export default function MetricsSummary({
  metrics,
  authorRating,
  onRefresh,
  onSetRating,
}: MetricsSummaryProps) {
  const currentRating = metrics?.author_rating || authorRating || 0

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
                  currentRating >= star
                    ? 'text-yellow-400'
                    : 'text-gray-300 hover:text-yellow-300'
                }`}
              >
                <Star className="h-5 w-5 fill-current" />
              </button>
            ))}
          </div>
        </div>
        {currentRating > 0 && (
          <p className="text-xs text-purple-700 mt-1">
            Rated {currentRating}/5 potential
          </p>
        )}
      </div>

      {/* Totals */}
      {metrics && (metrics.total_views > 0 || metrics.total_likes > 0) ? (
        <>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <Eye className="h-6 w-6 mx-auto mb-2 text-blue-500" />
              <div className="text-2xl font-bold text-gray-900">
                {formatMetricNumber(metrics.total_views)}
              </div>
              <div className="text-xs text-gray-500">Views</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <Heart className="h-6 w-6 mx-auto mb-2 text-red-500" />
              <div className="text-2xl font-bold text-gray-900">
                {formatMetricNumber(metrics.total_likes)}
              </div>
              <div className="text-xs text-gray-500">Likes</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <MessageCircle className="h-6 w-6 mx-auto mb-2 text-green-500" />
              <div className="text-2xl font-bold text-gray-900">
                {formatMetricNumber(metrics.total_comments)}
              </div>
              <div className="text-xs text-gray-500">Comments</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <Share2 className="h-6 w-6 mx-auto mb-2 text-purple-500" />
              <div className="text-2xl font-bold text-gray-900">
                {formatMetricNumber(metrics.total_shares)}
              </div>
              <div className="text-xs text-gray-500">Shares</div>
            </div>
          </div>

          {/* Engagement Rate */}
          {metrics.avg_engagement_rate && (
            <div className="mb-6 p-4 bg-green-50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-green-900">Avg Engagement Rate</span>
                <span className="text-2xl font-bold text-green-600">
                  {metrics.avg_engagement_rate.toFixed(2)}%
                </span>
              </div>
            </div>
          )}

          {/* Per-Platform Breakdown */}
          {metrics.platforms && metrics.platforms.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-gray-700">By Platform</h4>
              {metrics.platforms.map((pm) => (
                <div key={pm.platform} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getPlatformIcon(pm.platform)}
                      <span className="font-medium capitalize">{pm.platform}</span>
                    </div>
                    {pm.engagement_rate && (
                      <span className="text-sm text-green-600">
                        {pm.engagement_rate.toFixed(2)}% ER
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-xs text-gray-500">
                    <div>
                      <Eye className="h-3 w-3 inline mr-1" />
                      {formatMetricNumber(pm.views)}
                    </div>
                    <div>
                      <Heart className="h-3 w-3 inline mr-1" />
                      {formatMetricNumber(pm.likes)}
                    </div>
                    <div>
                      <MessageCircle className="h-3 w-3 inline mr-1" />
                      {formatMetricNumber(pm.comments)}
                    </div>
                    <div>
                      <Share2 className="h-3 w-3 inline mr-1" />
                      {formatMetricNumber(pm.shares)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <TrendingUp className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p>No metrics yet</p>
          <p className="text-sm">Publish your video to start tracking performance</p>
        </div>
      )}
    </div>
  )
}
