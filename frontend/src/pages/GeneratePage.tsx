import { useEffect, useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { A } from '../theme'
import { usePostGeneration } from '../hooks/usePostGeneration'
import { api } from '../api/client'
import PostGenerator from '../components/PostGenerator'
import ReviewPanel from '../components/ReviewPanel'

export default function GeneratePage() {
  const { planId, dayIndex } = useParams<{ planId: string; dayIndex: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const brandId = searchParams.get('brand_id') || ''

  const { state, generate, reset } = usePostGeneration()

  const [dayBrief, setDayBrief] = useState<{ platform: string; pillar: string; content_theme: string } | undefined>(undefined)

  // Load the day brief so PostGenerator knows the platform (needed for video button eligibility)
  useEffect(() => {
    if (!planId || dayIndex === undefined || !brandId) return
    ;(api.getPlan(brandId, planId) as Promise<any>)
      .then(res => {
        const days: any[] = res.plan_profile?.days || []
        const idx = parseInt(dayIndex, 10)
        if (days[idx]) setDayBrief(days[idx])
      })
      .catch(() => {})
  }, [planId, dayIndex, brandId])

  // Auto-start generation on mount; return cleanup so EventSource closes on unmount
  useEffect(() => {
    if (planId && dayIndex !== undefined && brandId) {
      return generate(planId, parseInt(dayIndex, 10), brandId)
    }
  }, [planId, dayIndex, brandId, generate])

  const handleApprove = (postId: string) => {
    // Navigate back to dashboard with success
    navigate(`/dashboard/${brandId}?approved=${postId}`)
  }

  const handleRegenerate = () => {
    reset()
    if (planId && dayIndex !== undefined && brandId) {
      setTimeout(() => generate(planId, parseInt(dayIndex, 10), brandId), 100)
    }
  }

  return (
    <div style={{
      minHeight: 'calc(100vh - 53px)',
      padding: '32px 24px',
      maxWidth: 960,
      margin: '0 auto',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 28 }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            padding: '6px 12px', borderRadius: 6, border: `1px solid ${A.border}`,
            background: 'transparent', color: A.textSoft, fontSize: 13, cursor: 'pointer',
          }}
        >
          ← Back
        </button>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: A.text, margin: 0 }}>
            Generate Post
          </h1>
          <p style={{ fontSize: 13, color: A.textSoft, margin: 0 }}>
            Day {dayIndex !== undefined ? parseInt(dayIndex, 10) + 1 : '?'}
            {planId && ` · Plan ${planId.slice(-6)}`}
          </p>
        </div>

        {/* Budget indicator — placeholder */}
        <div style={{ marginLeft: 'auto', fontSize: 12, color: A.textMuted }}>
          ✨ AI Generation
        </div>
      </div>

      {/* Generator */}
      <div style={{
        padding: 24, borderRadius: 12,
        background: A.surface, border: `1px solid ${A.border}`,
      }}>
        <PostGenerator
          state={state}
          dayBrief={dayBrief}
          onApprove={handleApprove}
          onRegenerate={handleRegenerate}
          brandId={brandId}
        />
      </div>

      {/* AI Brand Review — shown once generation is complete */}
      {state.status === 'complete' && state.postId && brandId && (
        <div style={{
          marginTop: 16, padding: 24, borderRadius: 12,
          background: A.surface, border: `1px solid ${A.border}`,
        }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: A.text, marginBottom: 14 }}>
            AI Brand Review
          </h3>
          <ReviewPanel
            brandId={brandId}
            postId={state.postId}
            onApproved={() => navigate(`/dashboard/${brandId}`)}
          />
        </div>
      )}
    </div>
  )
}
