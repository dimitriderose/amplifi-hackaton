import { useState, useEffect, useRef } from 'react'
import { A } from '../theme'
import { api } from '../api/client'

interface EngagementScores {
  hook_strength: number
  relevance: number
  cta_effectiveness: number
  platform_fit: number
}

interface ReviewResult {
  score: number
  brand_alignment: 'strong' | 'moderate' | 'weak'
  strengths: string[]
  improvements: string[]
  approved: boolean
  revised_caption: string | null
  engagement_scores?: EngagementScores
  engagement_prediction?: 'low' | 'medium' | 'high' | 'viral'
}

interface Props {
  brandId: string
  postId: string
  onApproved?: () => void
}

const ALIGNMENT_COLORS = {
  strong: A.emerald,
  moderate: A.amber,
  weak: A.coral,
}

const PREDICTION_COLORS = {
  low: A.coral,
  medium: A.amber,
  high: A.emerald,
  viral: A.violet,
}

const PREDICTION_LABELS = {
  low: '📉 Low',
  medium: '📊 Medium',
  high: '📈 High',
  viral: '🚀 Viral',
}

const ENGAGEMENT_LABELS: Record<string, string> = {
  hook_strength: 'Hook',
  relevance: 'Relevance',
  cta_effectiveness: 'CTA',
  platform_fit: 'Platform Fit',
}

export default function ReviewPanel({ brandId, postId, onApproved }: Props) {
  const [review, setReview] = useState<ReviewResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [approved, setApproved] = useState(false)
  // L-6: copy-to-clipboard state for revised caption
  const [captionCopied, setCaptionCopied] = useState(false)
  const captionCopyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // DK-3: Auto-trigger review on mount so user doesn't have to click a button
  useEffect(() => {
    if (postId && brandId) runReview()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId, brandId])

  const runReview = async (force = false) => {
    // Reset prior results at the start so the re-review button doesn't cause a
    // stale-state flash (setReview(null) outside was async and didn't flush first)
    setReview(null)
    // Clear any in-flight copy timer so a re-review doesn't inherit stale "Copied" state
    if (captionCopyTimerRef.current) {
      clearTimeout(captionCopyTimerRef.current)
      captionCopyTimerRef.current = null
    }
    setCaptionCopied(false)
    setLoading(true)
    setError('')
    try {
      const res = await api.reviewPost(brandId, postId, force) as { review: ReviewResult }
      setReview(res.review)
      // Don't auto-navigate on approval — let the user see the review first
    } catch (err: any) {
      setError(err.message || 'Review failed')
    } finally {
      setLoading(false)
    }
  }

  const handleManualApprove = async () => {
    try {
      await api.approvePost(brandId, postId)
      setApproved(true)
      onApproved?.()
    } catch (err: any) {
      setError(err.message || 'Approval failed')
    }
  }

  if (approved) {
    return (
      <div style={{
        padding: '16px 20px', borderRadius: 10,
        background: A.emeraldLight, border: `1px solid ${A.emerald}30`,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span style={{ fontSize: 20 }}>✅</span>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 14, fontWeight: 600, color: A.emerald, margin: 0 }}>Post Approved</p>
          <p style={{ fontSize: 12, color: A.textSoft, margin: 0 }}>Ready for export</p>
        </div>
        {onApproved && (
          <button
            onClick={onApproved}
            style={{
              padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: A.emerald, color: 'white', fontSize: 13, fontWeight: 600,
            }}
          >
            ← Dashboard
          </button>
        )}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Review trigger */}
      {!review && (
        <button
          onClick={runReview}
          disabled={loading}
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
            background: loading ? A.surfaceAlt : `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
            color: loading ? A.textMuted : 'white',
            fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8,
          }}
        >
          {loading ? (
            <>
              <span style={{
                display: 'inline-block', width: 14, height: 14, borderRadius: '50%',
                border: `2px solid ${A.textMuted}`, borderTopColor: 'transparent',
                animation: 'spin 0.8s linear infinite',
              }} />
              Reviewing...
            </>
          ) : '🔍 AI Review'}
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </button>
      )}

      {error && (
        <p style={{ fontSize: 13, color: A.coral }}>{error}</p>
      )}

      {/* Review results */}
      {review && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Score + alignment */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 16,
            padding: '14px 16px', borderRadius: 10,
            background: A.surfaceAlt, border: `1px solid ${A.border}`,
          }}>
            {/* Score circle */}
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              background: `conic-gradient(${A.indigo} ${review.score * 36}deg, ${A.surfaceAlt} 0deg)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <div style={{
                width: 44, height: 44, borderRadius: '50%',
                background: A.surface,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{ fontSize: 16, fontWeight: 700, color: A.text }}>{review.score}</span>
              </div>
            </div>
            <div>
              <p style={{ fontSize: 14, fontWeight: 600, color: A.text, margin: 0 }}>
                Score {review.score}/10
              </p>
              <span style={{
                fontSize: 11, fontWeight: 500, padding: '2px 8px', borderRadius: 20,
                background: ALIGNMENT_COLORS[review.brand_alignment] + '15',
                color: ALIGNMENT_COLORS[review.brand_alignment],
              }}>
                {review.brand_alignment.toUpperCase()} BRAND ALIGNMENT
              </span>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              {review.approved ? (
                <span style={{ fontSize: 13, color: A.emerald, fontWeight: 600 }}>✓ Auto-approved</span>
              ) : (
                <span style={{ fontSize: 13, color: A.amber }}>Needs review</span>
              )}
            </div>
          </div>

          {/* Engagement prediction */}
          {review.engagement_scores && review.engagement_prediction && (
            <div style={{
              padding: '12px 16px', borderRadius: 10,
              background: A.surfaceAlt, border: `1px solid ${A.border}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <p style={{ fontSize: 12, fontWeight: 600, color: A.textSoft, textTransform: 'uppercase', letterSpacing: 0.5, margin: 0 }}>
                  Engagement Prediction
                </p>
                <span style={{
                  fontSize: 12, fontWeight: 600, padding: '2px 10px', borderRadius: 20,
                  background: PREDICTION_COLORS[review.engagement_prediction] + '18',
                  color: PREDICTION_COLORS[review.engagement_prediction],
                }}>
                  {PREDICTION_LABELS[review.engagement_prediction]}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {(Object.entries(review.engagement_scores) as [string, number][]).map(([key, val]) => (
                  <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 12, color: A.textSoft, width: 90, flexShrink: 0 }}>
                      {ENGAGEMENT_LABELS[key]}
                    </span>
                    <div style={{ flex: 1, height: 6, background: A.border, borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', width: `${val * 10}%`,
                        background: val >= 8 ? A.emerald : val >= 6 ? A.indigo : val >= 4 ? A.amber : A.coral,
                        borderRadius: 3, transition: 'width 0.4s ease',
                      }} />
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 600, color: A.text, width: 24, textAlign: 'right' }}>
                      {val}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Strengths */}
          {review.strengths.length > 0 && (
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: A.textSoft, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
                Strengths
              </p>
              {review.strengths.map((s, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
                  <span style={{ color: A.emerald, fontSize: 14 }}>✓</span>
                  <span style={{ fontSize: 13, color: A.text }}>{s}</span>
                </div>
              ))}
            </div>
          )}

          {/* Improvements */}
          {review.improvements.length > 0 && (
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: A.textSoft, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
                Suggested improvements
              </p>
              {review.improvements.map((imp, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
                  <span style={{ color: A.amber, fontSize: 14 }}>→</span>
                  <span style={{ fontSize: 13, color: A.text }}>{imp}</span>
                </div>
              ))}
            </div>
          )}

          {/* Revised caption if provided */}
          {review.revised_caption && (
            <div style={{ padding: '10px 14px', borderRadius: 8, background: A.indigoLight, border: `1px solid ${A.indigo}20` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <p style={{ fontSize: 12, fontWeight: 600, color: A.indigo, margin: 0, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  AI-revised caption
                </p>
                {/* L-6: Copy revised caption to clipboard */}
                <button
                  onClick={() => {
                    navigator.clipboard?.writeText(review.revised_caption!).then(() => {
                      if (captionCopyTimerRef.current) clearTimeout(captionCopyTimerRef.current)
                      setCaptionCopied(true)
                      captionCopyTimerRef.current = setTimeout(() => setCaptionCopied(false), 1500)
                    }).catch(() => {})
                  }}
                  style={{
                    padding: '3px 10px', borderRadius: 6, border: `1px solid ${captionCopied ? A.emerald : A.indigo}40`,
                    background: captionCopied ? A.emeraldLight : 'white',
                    color: captionCopied ? A.emerald : A.indigo,
                    fontSize: 11, fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s',
                  }}
                >
                  {captionCopied ? '✓ Copied' : '⎘ Use this caption'}
                </button>
              </div>
              <p style={{ fontSize: 13, color: A.text, lineHeight: 1.5, margin: 0 }}>{review.revised_caption}</p>
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 8 }}>
            {review.approved ? (
              <button
                onClick={() => { setApproved(true); onApproved?.() }}
                style={{
                  flex: 1, padding: '10px', borderRadius: 8, border: 'none', cursor: 'pointer',
                  background: `linear-gradient(135deg, ${A.emerald}, #059669)`,
                  color: 'white', fontSize: 13, fontWeight: 600,
                }}
              >
                ✓ Done — Go to Dashboard
              </button>
            ) : (
              <button
                onClick={handleManualApprove}
                style={{
                  flex: 1, padding: '10px', borderRadius: 8, border: 'none', cursor: 'pointer',
                  background: `linear-gradient(135deg, ${A.emerald}, #059669)`,
                  color: 'white', fontSize: 13, fontWeight: 600,
                }}
              >
                ✓ Approve Anyway
              </button>
            )}
            <button
              onClick={() => runReview(true)}
              style={{
                padding: '10px 16px', borderRadius: 8,
                border: `1px solid ${A.border}`,
                background: 'transparent', color: A.textSoft,
                fontSize: 13, cursor: 'pointer',
              }}
            >
              ↺ Re-review
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
