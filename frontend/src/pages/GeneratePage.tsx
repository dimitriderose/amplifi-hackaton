import { useEffect } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { A } from '../theme'
import { usePostGeneration } from '../hooks/usePostGeneration'
import PostGenerator from '../components/PostGenerator'

export default function GeneratePage() {
  const { planId, dayIndex } = useParams<{ planId: string; dayIndex: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const brandId = searchParams.get('brand_id') || ''

  const { state, generate, reset } = usePostGeneration()

  // Auto-start generation on mount
  useEffect(() => {
    if (planId && dayIndex !== undefined && brandId) {
      generate(planId, parseInt(dayIndex, 10), brandId)
    }
  }, [planId, dayIndex, brandId]) // note: 'generate' is stable via useCallback

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
          onApprove={handleApprove}
          onRegenerate={handleRegenerate}
        />
      </div>
    </div>
  )
}
