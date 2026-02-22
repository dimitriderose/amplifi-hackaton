import React from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { A } from '../theme'
import PostLibrary from '../components/PostLibrary'

export default function ExportPage() {
  const { brandId } = useParams<{ brandId: string }>()
  const [searchParams] = useSearchParams()
  const planId = searchParams.get('plan_id') || undefined

  if (!brandId) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: A.textSoft }}>
        No brand selected.
      </div>
    )
  }

  return (
    <div style={{
      maxWidth: 1100, margin: '0 auto', padding: '32px 24px',
    }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: A.text, margin: 0, marginBottom: 4 }}>
          Export Posts
        </h1>
        <p style={{ fontSize: 14, color: A.textSoft, margin: 0 }}>
          Download individual posts or export an entire plan as a ZIP archive.
        </p>
      </div>

      <div style={{
        padding: 24, borderRadius: 12,
        background: A.surface, border: `1px solid ${A.border}`,
      }}>
        <PostLibrary brandId={brandId} planId={planId} />
      </div>
    </div>
  )
}
