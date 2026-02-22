import React from 'react'
import { A } from '../theme'
import { api } from '../api/client'
import type { Post } from '../hooks/usePostLibrary'

const STATUS_COLORS: Record<string, string> = {
  approved: A.emerald,
  complete: A.indigo,
  generating: A.amber,
  failed: A.coral,
  draft: A.textMuted,
}

const STATUS_LABELS: Record<string, string> = {
  approved: '✓ Approved',
  complete: 'Ready',
  generating: '⟳ Generating',
  failed: '✗ Failed',
  draft: 'Draft',
}

interface Props {
  post: Post
  brandId: string
  onApproved?: () => void
}

export default function PostCard({ post, brandId, onApproved }: Props) {
  const color = STATUS_COLORS[post.status] || A.textMuted
  const label = STATUS_LABELS[post.status] || post.status

  const handleExport = async () => {
    try {
      const res = await api.exportPost(post.post_id, brandId) as { download_url?: string; caption?: string }
      if (res.download_url) {
        window.open(res.download_url, '_blank')
      }
    } catch (err: any) {
      alert('Export failed: ' + err.message)
    }
  }

  const handleApprove = async () => {
    try {
      await api.approvePost(brandId, post.post_id)
      onApproved?.()
    } catch (err: any) {
      alert('Approval failed: ' + err.message)
    }
  }

  return (
    <div style={{
      borderRadius: 10, background: A.surface, border: `1px solid ${A.border}`,
      overflow: 'hidden', display: 'flex', flexDirection: 'column',
    }}>
      {/* Image or placeholder */}
      <div style={{
        width: '100%', aspectRatio: '1', background: A.surfaceAlt,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        overflow: 'hidden', position: 'relative',
      }}>
        {post.image_url ? (
          <img
            src={post.image_url}
            alt="Post visual"
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <span style={{ fontSize: 32, opacity: 0.3 }}>🖼️</span>
        )}
        {/* Status badge overlay */}
        <span style={{
          position: 'absolute', top: 8, right: 8,
          fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 12,
          background: color + '22', color, border: `1px solid ${color}44`,
        }}>
          {label}
        </span>
      </div>

      {/* Content */}
      <div style={{ padding: '12px 14px', flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* Platform + Day */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {post.platform && (
            <span style={{
              fontSize: 11, fontWeight: 500, color: A.textSoft,
              background: A.surfaceAlt, padding: '2px 7px', borderRadius: 10,
            }}>
              {post.platform}
            </span>
          )}
          <span style={{ fontSize: 11, color: A.textMuted }}>
            Day {(post.day_index ?? 0) + 1}
          </span>
        </div>

        {/* Caption preview */}
        <p style={{
          fontSize: 12, color: A.textSoft, margin: 0, lineHeight: 1.5,
          display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        } as React.CSSProperties}>
          {post.caption || 'No caption yet'}
        </p>

        {/* Hashtags */}
        {post.hashtags && post.hashtags.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {post.hashtags.slice(0, 3).map((tag, i) => (
              <span key={i} style={{ fontSize: 10, color: A.indigo, background: A.indigoLight, padding: '1px 6px', borderRadius: 8 }}>
                #{tag}
              </span>
            ))}
            {post.hashtags.length > 3 && (
              <span style={{ fontSize: 10, color: A.textMuted }}>+{post.hashtags.length - 3}</span>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div style={{ marginTop: 'auto', display: 'flex', gap: 6, paddingTop: 4 }}>
          {(post.status === 'complete' || post.status === 'approved') && (
            <button
              onClick={handleExport}
              style={{
                flex: 1, padding: '6px', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
                color: 'white', fontSize: 11, fontWeight: 600,
              }}
            >
              ↓ Export
            </button>
          )}
          {post.status === 'complete' && (
            <button
              onClick={handleApprove}
              style={{
                flex: 1, padding: '6px', borderRadius: 6, border: `1px solid ${A.emerald}`,
                background: 'transparent', color: A.emerald, fontSize: 11, fontWeight: 600, cursor: 'pointer',
              }}
            >
              ✓ Approve
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
