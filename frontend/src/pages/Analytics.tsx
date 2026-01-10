import { useState } from 'react'
import { useQuery } from 'react-query'
import { useNavigate } from 'react-router-dom'
import {
  TrendingUp, Eye, Heart, MessageCircle, Share2,
  Trophy, Star, ArrowUp, ArrowDown,
  BarChart3, Filter
} from 'lucide-react'
import { metricsApi, videosApi } from '@/services/api'
import type { MetricsPeriod } from '@/types'

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K'
  }
  return num.toString()
}

type SortBy = 'views' | 'likes' | 'comments' | 'shares' | 'engagement_rate'

export default function Analytics() {
  const navigate = useNavigate()
  const [period, setPeriod] = useState<MetricsPeriod>('7d')
  const [sortBy, setSortBy] = useState<SortBy>('views')

  // Fetch leaderboard
  const { data: leaderboard, isLoading } = useQuery(
    ['leaderboard', period, sortBy],
    () => metricsApi.getLeaderboard(period, sortBy, 20).then(res => res.data)
  )

  // Fetch video titles for leaderboard
  const videoIds = leaderboard?.map(m => m.video_id) || []
  const { data: videos } = useQuery(
    ['videos-for-leaderboard', videoIds.join(',')],
    async () => {
      if (videoIds.length === 0) return {}
      const results: Record<number, { title: string; image_url?: string }> = {}
      for (const id of videoIds) {
        try {
          const video = await videosApi.get(id).then(res => res.data)
          results[id] = { title: video.title, image_url: video.image_url || undefined }
        } catch {
          results[id] = { title: `Video #${id}` }
        }
      }
      return results
    },
    { enabled: videoIds.length > 0 }
  )

  // Calculate totals
  const totals = leaderboard?.reduce(
    (acc, m) => ({
      views: acc.views + m.total_views,
      likes: acc.likes + m.total_likes,
      comments: acc.comments + m.total_comments,
      shares: acc.shares + m.total_shares,
    }),
    { views: 0, likes: 0, comments: 0, shares: 0 }
  ) || { views: 0, likes: 0, comments: 0, shares: 0 }

  const periods: { value: MetricsPeriod; label: string }[] = [
    { value: '30m', label: '30 min' },
    { value: '6h', label: '6 hours' },
    { value: '24h', label: '24 hours' },
    { value: '7d', label: '7 days' },
  ]

  const sortOptions: { value: SortBy; label: string; icon: typeof Eye }[] = [
    { value: 'views', label: 'Views', icon: Eye },
    { value: 'likes', label: 'Likes', icon: Heart },
    { value: 'comments', label: 'Comments', icon: MessageCircle },
    { value: 'shares', label: 'Shares', icon: Share2 },
    { value: 'engagement_rate', label: 'Engagement', icon: TrendingUp },
  ]

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <BarChart3 className="h-7 w-7 mr-3 text-purple-600" />
            Analytics
          </h1>
          <p className="text-gray-500 mt-1">Track performance across all your videos</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-between">
            <Eye className="h-8 w-8 text-blue-500" />
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">{period}</span>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-bold text-gray-900">{formatNumber(totals.views)}</div>
            <div className="text-sm text-gray-500">Total Views</div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-between">
            <Heart className="h-8 w-8 text-red-500" />
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">{period}</span>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-bold text-gray-900">{formatNumber(totals.likes)}</div>
            <div className="text-sm text-gray-500">Total Likes</div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-between">
            <MessageCircle className="h-8 w-8 text-green-500" />
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">{period}</span>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-bold text-gray-900">{formatNumber(totals.comments)}</div>
            <div className="text-sm text-gray-500">Total Comments</div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-between">
            <Share2 className="h-8 w-8 text-purple-500" />
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">{period}</span>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-bold text-gray-900">{formatNumber(totals.shares)}</div>
            <div className="text-sm text-gray-500">Total Shares</div>
          </div>
        </div>
      </div>

      {/* Leaderboard */}
      <div className="bg-white rounded-xl shadow-sm border">
        {/* Filters */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center">
            <Trophy className="h-5 w-5 mr-2 text-yellow-500" />
            Top Performing Videos
          </h2>

          <div className="flex items-center gap-4">
            {/* Period Filter */}
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <select
                value={period}
                onChange={(e) => setPeriod(e.target.value as MetricsPeriod)}
                className="text-sm border-gray-200 rounded-lg focus:ring-purple-500 focus:border-purple-500"
              >
                {periods.map(p => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>

            {/* Sort By */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              {sortOptions.map(option => {
                const Icon = option.icon
                return (
                  <button
                    key={option.value}
                    onClick={() => setSortBy(option.value)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1 transition ${
                      sortBy === option.value
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="h-3 w-3" />
                    {option.label}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : leaderboard && leaderboard.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-500 border-b bg-gray-50">
                  <th className="px-4 py-3 w-12">#</th>
                  <th className="px-4 py-3">Video</th>
                  <th className="px-4 py-3 text-center">Rating</th>
                  <th className="px-4 py-3 text-right">Views</th>
                  <th className="px-4 py-3 text-right">Likes</th>
                  <th className="px-4 py-3 text-right">Comments</th>
                  <th className="px-4 py-3 text-right">Shares</th>
                  <th className="px-4 py-3 text-right">Engagement</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((item, index) => {
                  const videoInfo = videos?.[item.video_id]
                  return (
                    <tr
                      key={item.video_id}
                      onClick={() => navigate(`/video/${item.video_id}`)}
                      className="border-b last:border-0 hover:bg-gray-50 cursor-pointer transition"
                    >
                      <td className="px-4 py-4">
                        {index === 0 ? (
                          <span className="text-yellow-500 font-bold text-lg">1</span>
                        ) : index === 1 ? (
                          <span className="text-gray-400 font-bold text-lg">2</span>
                        ) : index === 2 ? (
                          <span className="text-orange-400 font-bold text-lg">3</span>
                        ) : (
                          <span className="text-gray-400">{index + 1}</span>
                        )}
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          {videoInfo?.image_url ? (
                            <img
                              src={videoInfo.image_url}
                              alt=""
                              className="w-12 h-12 rounded-lg object-cover"
                            />
                          ) : (
                            <div className="w-12 h-12 rounded-lg bg-gray-200" />
                          )}
                          <span className="font-medium text-gray-900 truncate max-w-[200px]">
                            {videoInfo?.title || `Video #${item.video_id}`}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center justify-center gap-0.5">
                          {item.author_rating ? (
                            <>
                              {[1, 2, 3, 4, 5].map(star => (
                                <Star
                                  key={star}
                                  className={`h-3 w-3 ${
                                    star <= item.author_rating!
                                      ? 'text-yellow-400 fill-current'
                                      : 'text-gray-300'
                                  }`}
                                />
                              ))}
                            </>
                          ) : (
                            <span className="text-gray-400 text-xs">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-4 text-right font-medium">
                        {formatNumber(item.total_views)}
                      </td>
                      <td className="px-4 py-4 text-right">
                        {formatNumber(item.total_likes)}
                      </td>
                      <td className="px-4 py-4 text-right">
                        {formatNumber(item.total_comments)}
                      </td>
                      <td className="px-4 py-4 text-right">
                        {formatNumber(item.total_shares)}
                      </td>
                      <td className="px-4 py-4 text-right">
                        {item.avg_engagement_rate ? (
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            item.avg_engagement_rate >= 5
                              ? 'bg-green-100 text-green-700'
                              : item.avg_engagement_rate >= 2
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-gray-100 text-gray-700'
                          }`}>
                            {item.avg_engagement_rate.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center">
            <TrendingUp className="h-16 w-16 mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No metrics yet</h3>
            <p className="text-gray-500">
              Publish some videos and metrics will appear here automatically
            </p>
          </div>
        )}
      </div>

      {/* Rating vs Performance Insight */}
      {leaderboard && leaderboard.length > 0 && (
        <div className="mt-8 bg-purple-50 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-purple-900 mb-4">
            Rating vs Performance Insight
          </h3>
          <div className="grid grid-cols-3 gap-6">
            {/* High rated, high performing */}
            <div className="bg-white rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <ArrowUp className="h-5 w-5 text-green-500" />
                <span className="font-medium text-gray-900">Predicted Well</span>
              </div>
              <p className="text-sm text-gray-500">
                Videos rated 4-5 that performed above average
              </p>
              <div className="mt-2 text-2xl font-bold text-green-600">
                {leaderboard.filter(v =>
                  (v.author_rating || 0) >= 4 &&
                  v.total_views > (totals.views / leaderboard.length)
                ).length}
              </div>
            </div>

            {/* Low rated, high performing */}
            <div className="bg-white rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-5 w-5 text-yellow-500" />
                <span className="font-medium text-gray-900">Surprise Hits</span>
              </div>
              <p className="text-sm text-gray-500">
                Videos rated 1-3 that performed above average
              </p>
              <div className="mt-2 text-2xl font-bold text-yellow-600">
                {leaderboard.filter(v =>
                  (v.author_rating || 3) <= 3 &&
                  v.total_views > (totals.views / leaderboard.length)
                ).length}
              </div>
            </div>

            {/* High rated, low performing */}
            <div className="bg-white rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <ArrowDown className="h-5 w-5 text-red-500" />
                <span className="font-medium text-gray-900">Underperformed</span>
              </div>
              <p className="text-sm text-gray-500">
                Videos rated 4-5 that performed below average
              </p>
              <div className="mt-2 text-2xl font-bold text-red-600">
                {leaderboard.filter(v =>
                  (v.author_rating || 0) >= 4 &&
                  v.total_views < (totals.views / leaderboard.length)
                ).length}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
