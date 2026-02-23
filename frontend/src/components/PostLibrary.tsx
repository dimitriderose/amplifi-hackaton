import React from 'react'
import { A } from '../theme'
import { api } from '../api/client'
import PostCard from './PostCard'
import { usePostLibrary } from '../hooks/usePostLibrary'

type Filter = 'all' | 'approved' | 'complete' | 'generating' | 'failed'

interface Props {
  brandId: string
  planId?: string
  /** M-8: allow ExportPage to default to 'approved' filter */
  defaultFilter?: Filter
}

export default function PostLibrary({ brandId, planId, defaultFilter = 'all' }: Props) {
  const { posts, loading, error, refresh } = usePostLibrary(brandId, planId)
  const [filter, setFilter] = React.useState<Filter>(defaultFilter)
  const [exporting, setExporting] = React.useState(false)
  // DK-5: Track locally dismissed post IDs (stuck generating/failed) — no server call needed
  const [dismissed, setDismissed] = React.useState<Set<string>>(new Set())
  // H-7: Inline export error instead of alert
  const [exportError, setExportError] = React.useState<string | null>(null)
  // Copy All Captions — clipboard with 1.5s confirmation flash
  const [copyAllDone, setCopyAllDone] = React.useState(false)
  const copyAllTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  // Snapshot count at click time to avoid drift if posts update during the 1.5s flash
  const copiedCountRef = React.useRef(0)

  // Cleanup timer on unmount
  React.useEffect(() => {
    return () => { if (copyAllTimerRef.current) clearTimeout(copyAllTimerRef.current) }
  }, [])

  const FILTERS: { key: Filter; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'approved', label: '✓ Approved' },
    { key: 'complete', label: 'Ready' },
    { key: 'generating', label: 'Generating' },
    { key: 'failed', label: 'Failed' },
  ]

  const visiblePosts = posts.filter(p => !dismissed.has(p.post_id))
  const filtered = filter === 'all' ? visiblePosts : visiblePosts.filter(p => p.status === filter)

  const handleCopyAll = () => {
    if (!navigator.clipboard || filtered.length === 0) return
    const withCaption = filtered.filter(p => p.caption)
    copiedCountRef.current = withCaption.length
    const lines = withCaption.map((p, i) => {
      const tags = (p.hashtags || []).map((h: string) => `#${h.replace(/^#/, '')}`).join(' ')
      const header = `[${i + 1}] ${p.platform ? p.platform.charAt(0).toUpperCase() + p.platform.slice(1) : 'Post'} · Day ${(p.day_index ?? 0) + 1}`
      return [header, p.caption, tags].filter(Boolean).join('\n\n')
    })
    const text = lines.join('\n\n---\n\n')
    navigator.clipboard.writeText(text).then(() => {
      if (copyAllTimerRef.current) clearTimeout(copyAllTimerRef.current)
      setCopyAllDone(true)
      copyAllTimerRef.current = setTimeout(() => setCopyAllDone(false), 1500)
    }).catch(() => {})
  }

  const handleBulkExport = async () => {
    if (!planId) return
    setExporting(true)
    setExportError(null)
    try {
      await api.exportPlan(planId, brandId)
    } catch (err: any) {
      setExportError(err.message || 'Export failed')
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
          {visiblePosts.length > 0 && (
            <span style={{ marginLeft: 8, fontSize: 12, fontWeight: 400, color: A.textMuted }}>
              {visiblePosts.length} posts
            </span>
          )}
        </h3>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={refresh} style={{
            padding: '5px 10px', borderRadius: 6, border: `1px solid ${A.border}`,
            background: 'transparent', color: A.textSoft, fontSize: 12, cursor: 'pointer',
          }}>↻ Refresh</button>
          {filtered.length > 0 && (
            <button
              onClick={handleCopyAll}
              style={{
                padding: '5px 12px', borderRadius: 6,
                border: `1px solid ${copyAllDone ? A.emerald : A.border}`,
                background: copyAllDone ? A.emeraldLight : 'transparent',
                color: copyAllDone ? A.emerald : A.textSoft,
                fontSize: 12, fontWeight: copyAllDone ? 600 : 400, cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              {copyAllDone ? `✓ Copied ${copiedCountRef.current}` : '📋 Copy All'}
            </button>
          )}
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

      {/* L-5: Inline export error */}
      {exportError && (
        <div style={{ marginBottom: 12, padding: '8px 12px', borderRadius: 6, background: A.coral + '15', color: A.coral, fontSize: 12 }}>
          {exportError}
        </div>
      )}

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
            {f.key !== 'all' && visiblePosts.filter(p => p.status === f.key).length > 0 && (
              <span style={{ marginLeft: 4, opacity: 0.7 }}>
                ({visiblePosts.filter(p => p.status === f.key).length})
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
          {visiblePosts.length === 0
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
              onDismiss={
                post.status === 'generating' || post.status === 'failed'
                  ? () => setDismissed(prev => new Set([...prev, post.post_id]))
                  : undefined
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}
