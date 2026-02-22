import React from 'react'
import { A } from '../theme'
import { api } from '../api/client'
import PostCard from './PostCard'
import { usePostLibrary } from '../hooks/usePostLibrary'

type Filter = 'all' | 'approved' | 'complete' | 'generating' | 'failed'

interface Props {
  brandId: string
  planId?: string
}

export default function PostLibrary({ brandId, planId }: Props) {
  const { posts, loading, error, refresh } = usePostLibrary(brandId, planId)
  const [filter, setFilter] = React.useState<Filter>('all')
  const [exporting, setExporting] = React.useState(false)

  const FILTERS: { key: Filter; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'approved', label: '✓ Approved' },
    { key: 'complete', label: 'Ready' },
    { key: 'generating', label: 'Generating' },
    { key: 'failed', label: 'Failed' },
  ]

  const filtered = filter === 'all' ? posts : posts.filter(p => p.status === filter)

  const handleBulkExport = async () => {
    if (!planId) return
    setExporting(true)
    try {
      await api.exportPlan(planId, brandId)
    } catch (err: any) {
      alert('Export failed: ' + err.message)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div>
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: A.text, margin: 0 }}>
          Post Library
          {posts.length > 0 && (
            <span style={{ marginLeft: 8, fontSize: 12, fontWeight: 400, color: A.textMuted }}>
              {posts.length} posts
            </span>
          )}
        </h3>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={refresh} style={{
            padding: '5px 10px', borderRadius: 6, border: `1px solid ${A.border}`,
            background: 'transparent', color: A.textSoft, fontSize: 12, cursor: 'pointer',
          }}>↻ Refresh</button>
          {planId && (
            <button
              onClick={handleBulkExport}
              disabled={exporting}
              style={{
                padding: '5px 12px', borderRadius: 6, border: 'none', cursor: exporting ? 'not-allowed' : 'pointer',
                background: exporting ? A.surfaceAlt : `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
                color: exporting ? A.textMuted : 'white', fontSize: 12, fontWeight: 600,
              }}
            >
              {exporting ? 'Exporting...' : '↓ Export All'}
            </button>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' }}>
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              padding: '4px 10px', borderRadius: 16, fontSize: 12, cursor: 'pointer',
              border: filter === f.key ? 'none' : `1px solid ${A.border}`,
              background: filter === f.key ? A.indigo : 'transparent',
              color: filter === f.key ? 'white' : A.textSoft,
              fontWeight: filter === f.key ? 600 : 400,
            }}
          >
            {f.label}
            {f.key !== 'all' && posts.filter(p => p.status === f.key).length > 0 && (
              <span style={{ marginLeft: 4, opacity: 0.7 }}>
                ({posts.filter(p => p.status === f.key).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Loading / error / empty states */}
      {loading && (
        <div style={{ padding: 40, textAlign: 'center', color: A.textSoft, fontSize: 14 }}>
          Loading posts...
        </div>
      )}
      {error && !loading && (
        <div style={{ padding: 20, borderRadius: 8, background: A.coral + '15', color: A.coral, fontSize: 13 }}>
          {error}
        </div>
      )}
      {!loading && !error && filtered.length === 0 && (
        <div style={{
          padding: 40, textAlign: 'center', background: A.surfaceAlt,
          borderRadius: 10, color: A.textMuted, fontSize: 13,
        }}>
          {posts.length === 0
            ? 'No posts yet — generate some from the calendar above!'
            : `No ${filter} posts`}
        </div>
      )}

      {/* Grid */}
      {!loading && filtered.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: 16,
        }}>
          {filtered.map(post => (
            <PostCard
              key={post.post_id}
              post={post}
              brandId={brandId}
              onApproved={refresh}
            />
          ))}
        </div>
      )}
    </div>
  )
}
