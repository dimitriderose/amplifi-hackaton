import { useState, useRef, useEffect } from 'react'
import { A } from '../theme'
import { GenerationState } from '../hooks/usePostGeneration'
import { useVideoGeneration } from '../hooks/useVideoGeneration'
import PlatformPreview from './PlatformPreview'
import { api } from '../api/client'

interface Props {
  state: GenerationState
  dayBrief?: {
    platform: string
    pillar: string
    content_theme: string
  }
  brandId?: string
  // H-2: onApprove removed — approval is handled solely by ReviewPanel to avoid duplicate flows
  onRegenerate?: (instructions?: string) => void
  byopRecommendation?: string
}

const PLATFORM_ICONS: Record<string, string> = {
  instagram: '📸',
  linkedin: '💼',
  twitter: '🐦',
  facebook: '👥',
}

const VIDEO_PLATFORMS = new Set(['instagram', 'tiktok', 'reels', 'story', 'stories'])
// Text-first platforms where video section defaults to collapsed to reduce visual noise
const TEXT_PLATFORMS = new Set(['linkedin', 'x', 'twitter', 'facebook'])

// RegenerateButton with optional instructions input
function RegenerateButton({ onRegenerate }: { onRegenerate: (instructions?: string) => void }) {
  const [showInput, setShowInput] = useState(false)
  const [instructions, setInstructions] = useState('')

  const handleConfirm = () => {
    onRegenerate(instructions.trim() || undefined)
    setShowInput(false)
    setInstructions('')
  }

  if (!showInput) {
    return (
      <button
        type="button"
        onClick={() => setShowInput(true)}
        style={{
          padding: '10px 16px', borderRadius: 8,
          border: `1px solid ${A.border}`,
          background: 'transparent', color: A.textSoft,
          fontSize: 13, cursor: 'pointer',
        }}
      >
        ↺ Regenerate
      </button>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <input
        autoFocus
        type="text"
        placeholder="Optional: describe what to change…"
        value={instructions}
        onChange={e => setInstructions(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter') handleConfirm()
          if (e.key === 'Escape') setShowInput(false)
        }}
        style={{
          width: '100%', padding: '8px 10px', borderRadius: 7,
          border: `1px solid ${A.border}`, fontSize: 12,
          color: A.text, background: A.surface, boxSizing: 'border-box' as const,
        }}
      />
      <div style={{ display: 'flex', gap: 6 }}>
        <button
          type="button"
          onClick={handleConfirm}
          style={{
            padding: '6px 14px', borderRadius: 7, border: 'none',
            background: A.indigo, color: 'white', fontSize: 12, fontWeight: 600, cursor: 'pointer',
          }}
        >
          Regenerate
        </button>
        <button
          type="button"
          onClick={() => setShowInput(false)}
          style={{
            padding: '6px 12px', borderRadius: 7,
            border: `1px solid ${A.border}`,
            background: 'transparent', color: A.textSoft,
            fontSize: 12, cursor: 'pointer',
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

/** BYOP risk warning with caption-only mode toggle. M-3: toggle actually hides the image via callback. */
function CaptionOnlyBanner({ recommendation, onToggle }: { recommendation: string; onToggle: (captionOnly: boolean) => void }) {
  const [captionOnly, setCaptionOnly] = useState(false)

  const toggle = () => {
    const next = !captionOnly
    setCaptionOnly(next)
    onToggle(next)
  }

  return (
    <div style={{
      padding: '10px 14px', borderRadius: 8,
      background: `${A.amber}18`, border: `1px solid ${A.amber}44`,
      fontSize: 12, color: A.text, lineHeight: 1.5,
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <span style={{ color: A.amber, marginRight: 6 }}>⚠️</span>
          {recommendation}
        </div>
        <button
          onClick={toggle}
          title="Caption-only mode: hide AI-generated image"
          style={{
            flexShrink: 0, padding: '3px 10px', borderRadius: 20, fontSize: 11, cursor: 'pointer',
            border: `1px solid ${captionOnly ? A.amber : A.border}`,
            background: captionOnly ? A.amber + '22' : 'transparent',
            color: captionOnly ? A.amber : A.textSoft, fontWeight: captionOnly ? 600 : 400,
            whiteSpace: 'nowrap',
          }}
        >
          {captionOnly ? '✓ Caption-only' : 'Caption-only mode'}
        </button>
      </div>
      {captionOnly && (
        <p style={{ margin: '6px 0 0', color: A.textSoft }}>
          AI image hidden. Upload your own photo from the content calendar for best results.
        </p>
      )}
    </div>
  )
}

export default function PostGenerator({ state, dayBrief, brandId, onRegenerate, byopRecommendation }: Props) {
  const [copied, setCopied] = useState(false)
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [editingCaption, setEditingCaption] = useState(false)
  const [draftCaption, setDraftCaption] = useState('')
  const [localCaption, setLocalCaption] = useState<string | null>(null)
  const [captionSaving, setCaptionSaving] = useState(false)
  const [captionSaveError, setCaptionSaveError] = useState<string | null>(null)
  // M-3: Caption-only mode state lifted up to actually hide the image panel
  const [captionOnly, setCaptionOnly] = useState(false)
  // Video section collapsed by default on text-first platforms (LinkedIn, X, etc.)
  const [videoExpanded, setVideoExpanded] = useState(false)

  // Refs for focus management and race-condition guard
  const cancelledRef = useRef(false)
  const captionRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { status, statusMessage, captionChunks, caption, hashtags, imageUrl, postId, error } = state

  // Reset editing state when postId changes (new generation or day switch)
  useEffect(() => {
    setLocalCaption(null)
    setEditingCaption(false)
    setDraftCaption('')
    setCaptionSaveError(null)
    setCaptionSaving(false)
    setCaptionOnly(false)
    setVideoExpanded(false)
    cancelledRef.current = false
  }, [postId])

  // Focus textarea when entering edit mode
  useEffect(() => {
    if (editingCaption) {
      textareaRef.current?.focus()
    }
  }, [editingCaption])

  // localCaption overrides the server caption after a user edit
  const savedCaption = localCaption ?? caption
  const displayCaption = status === 'generating' && captionChunks.length > 0
    ? captionChunks.join('')
    : savedCaption

  const handleCopy = () => {
    if (!navigator.clipboard) return
    const tags = hashtags.map(h => `#${h.replace(/^#/, '')}`).join(' ')
    const fullText = [savedCaption, tags].filter(Boolean).join('\n\n')
    navigator.clipboard.writeText(fullText)
      .then(() => {
        if (copyTimerRef.current) clearTimeout(copyTimerRef.current)
        setCopied(true)
        copyTimerRef.current = setTimeout(() => setCopied(false), 1500)
      })
      .catch(() => {})
  }

  const handleCaptionEdit = () => {
    setDraftCaption(savedCaption || '')
    setCaptionSaveError(null)
    setEditingCaption(true)
  }

  const handleCaptionSave = async () => {
    if (!postId || !brandId) {
      setLocalCaption(draftCaption)
      setEditingCaption(false)
      return
    }
    cancelledRef.current = false
    setCaptionSaving(true)
    setCaptionSaveError(null)
    try {
      await api.updatePost(brandId, postId, { caption: draftCaption })
      if (!cancelledRef.current) {
        setLocalCaption(draftCaption)
        setEditingCaption(false)
      }
    } catch (err: unknown) {
      if (!cancelledRef.current) {
        setCaptionSaveError(err instanceof Error ? err.message : 'Save failed')
      }
    } finally {
      if (!cancelledRef.current) {
        setCaptionSaving(false)
      }
    }
  }

  const handleCaptionCancel = () => {
    cancelledRef.current = true
    setEditingCaption(false)
    setDraftCaption('')
    setCaptionSaveError(null)
    setCaptionSaving(false)
    // Return focus to caption box
    setTimeout(() => captionRef.current?.focus(), 0)
  }

  const platformIcon = PLATFORM_ICONS[dayBrief?.platform || ''] || '📱'
  const platform = dayBrief?.platform?.toLowerCase() ?? ''
  const isVideoPlatform = VIDEO_PLATFORMS.has(platform)
  const isTextPlatform = TEXT_PLATFORMS.has(platform)

  const showVideoSection = status === 'complete' && postId && brandId

  const { status: videoStatus, videoUrl, progress, error: videoError, startGeneration } =
    useVideoGeneration(postId ?? '', brandId ?? '')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Status bar */}
      {(status === 'generating' || statusMessage) && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 14px', borderRadius: 8,
          background: A.indigoLight, border: `1px solid ${A.indigo}20`,
        }}>
          {status === 'generating' && (
            <div style={{
              width: 14, height: 14, borderRadius: '50%',
              border: `2px solid ${A.indigoLight}`,
              borderTopColor: A.indigo,
              animation: 'spin 0.8s linear infinite',
              flexShrink: 0,
            }} />
          )}
          {status === 'complete' && <span style={{ color: A.emerald }}>✓</span>}
          <span style={{ fontSize: 13, color: A.indigo, fontWeight: 500 }}>{statusMessage}</span>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div style={{
          padding: '12px 16px', borderRadius: 8,
          background: '#FFF0F0', border: `1px solid ${A.coral}30`,
          fontSize: 13, color: A.coral,
        }}>
          {error}
        </div>
      )}

      {/* M-3: When captionOnly, collapse to 1-column so caption fills the width */}
      <div style={{ display: 'grid', gridTemplateColumns: captionOnly ? '1fr' : '1fr 1fr', gap: 20 }}>

        {/* Left: Caption */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Platform + theme header */}
          {dayBrief && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 20 }}>{platformIcon}</span>
              <div>
                <p style={{ fontSize: 13, fontWeight: 600, color: A.text, margin: 0 }}>
                  {dayBrief.platform.charAt(0).toUpperCase() + dayBrief.platform.slice(1)}
                </p>
                <p style={{ fontSize: 11, color: A.textMuted, margin: 0 }}>{dayBrief.content_theme}</p>
              </div>
            </div>
          )}

          {/* Caption text box — editable when post is complete */}
          {editingCaption ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <textarea
                ref={textareaRef}
                value={draftCaption}
                onChange={e => setDraftCaption(e.target.value)}
                rows={6}
                style={{
                  width: '100%', padding: '10px 12px', borderRadius: 10,
                  border: `1.5px solid ${A.indigo}`, fontSize: 14, color: A.text,
                  lineHeight: 1.6, resize: 'vertical', background: A.surface,
                  boxSizing: 'border-box',
                }}
              />
              {captionSaveError && (
                <p role="alert" style={{ fontSize: 11, color: A.coral, margin: 0 }}>{captionSaveError}</p>
              )}
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  onClick={handleCaptionSave}
                  disabled={captionSaving}
                  style={{
                    padding: '6px 14px', borderRadius: 7, border: 'none', cursor: captionSaving ? 'not-allowed' : 'pointer',
                    background: A.indigo, color: 'white', fontSize: 12, fontWeight: 600,
                    opacity: captionSaving ? 0.7 : 1,
                  }}
                >
                  {captionSaving ? 'Saving…' : 'Save'}
                </button>
                <button
                  type="button"
                  onClick={handleCaptionCancel}
                  style={{
                    padding: '6px 14px', borderRadius: 7, border: `1px solid ${A.border}`,
                    background: 'transparent', cursor: 'pointer', fontSize: 12, color: A.textSoft,
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div>
              <div
                ref={captionRef}
                role={status === 'complete' && savedCaption ? 'button' : undefined}
                tabIndex={status === 'complete' && savedCaption ? 0 : undefined}
                onClick={status === 'complete' && savedCaption ? handleCaptionEdit : undefined}
                onKeyDown={status === 'complete' && savedCaption ? (e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    handleCaptionEdit()
                  }
                } : undefined}
                aria-label={status === 'complete' && savedCaption ? 'Edit caption' : undefined}
                style={{
                  minHeight: 120, padding: '12px 14px', borderRadius: 10,
                  background: A.surfaceAlt, border: `1px solid ${A.border}`,
                  fontSize: 14, color: A.text, lineHeight: 1.6,
                  position: 'relative',
                  paddingRight: status === 'complete' && savedCaption ? 72 : 14,
                  cursor: status === 'complete' && savedCaption ? 'text' : 'default',
                }}
              >
                {displayCaption || (
                  <span style={{ color: A.textMuted, fontStyle: 'italic' }}>
                    {status === 'idle' ? 'Caption will appear here...' : 'Writing caption...'}
                  </span>
                )}
                {/* Blinking cursor during streaming */}
                {status === 'generating' && captionChunks.length > 0 && (
                  <span style={{
                    display: 'inline-block', width: 2, height: 16,
                    background: A.indigo, marginLeft: 2, verticalAlign: 'text-bottom',
                    animation: 'blink 1s step-end infinite',
                  }} />
                )}
                <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
                {/* Copy button — visible when caption is ready */}
                {status === 'complete' && savedCaption && (
                  <button
                    type="button"
                    onClick={e => { e.stopPropagation(); handleCopy() }}
                    aria-label={copied ? 'Copied to clipboard' : 'Copy caption to clipboard'}
                    title="Copy caption + hashtags"
                    style={{
                      position: 'absolute', top: 8, right: 8,
                      padding: '3px 8px', borderRadius: 6,
                      background: copied ? A.emeraldLight : 'rgba(255,255,255,0.8)',
                      border: `1px solid ${copied ? A.emerald : A.border}`,
                      color: copied ? A.emerald : A.textMuted,
                      fontSize: 11, cursor: 'pointer', transition: 'all 0.2s',
                    }}
                  >
                    {copied ? '✓ Copied' : '⎘ Copy'}
                  </button>
                )}
              </div>
              {/* Edit hint — below caption, not overlapping text */}
              {status === 'complete' && savedCaption && (
                <p style={{ fontSize: 10, color: A.textMuted, margin: '4px 0 0', opacity: 0.7, userSelect: 'none' }}>
                  ✏️ Click caption to edit
                </p>
              )}
            </div>
          )}

          {/* BYOP recommendation — shown when brand is high-risk for AI image generation */}
          {byopRecommendation && status === 'complete' && imageUrl && (
            <CaptionOnlyBanner recommendation={byopRecommendation} onToggle={setCaptionOnly} />
          )}

          {/* L-4: Label the platform preview section */}
          {status === 'complete' && savedCaption && dayBrief?.platform && !editingCaption && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 600, color: A.textMuted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
                How this looks on {dayBrief.platform.charAt(0).toUpperCase() + dayBrief.platform.slice(1)}
              </p>
              <PlatformPreview
                platform={dayBrief.platform}
                caption={savedCaption}
                imageUrl={imageUrl ?? undefined}
                hashtagCount={hashtags.length}
              />
            </div>
          )}

          {/* Hashtags */}
          {hashtags.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {hashtags.map((tag, i) => (
                <span key={i} style={{
                  fontSize: 12, padding: '3px 8px', borderRadius: 20,
                  background: A.indigoLight, color: A.indigo,
                  border: `1px solid ${A.indigo}20`,
                }}>
                  #{tag.replace(/^#/, '')}
                </span>
              ))}
            </div>
          )}

          {/* H-2: Removed "Approve Post" button — approval is now handled exclusively by ReviewPanel */}
          {status === 'complete' && postId && onRegenerate && (
            <div style={{ marginTop: 4 }}>
              <RegenerateButton onRegenerate={(instructions) => {
                setLocalCaption(null)
                onRegenerate(instructions)
              }} />
            </div>
          )}

          {/* H-6: Video section — collapsed for text-first platforms (LinkedIn/X), full for video platforms */}
          {showVideoSection && isTextPlatform && !videoExpanded && (
            <button
              type="button"
              onClick={() => setVideoExpanded(true)}
              style={{
                marginTop: 4, width: '100%', padding: '8px 14px', borderRadius: 10,
                border: `1px solid ${A.borderLight}`, background: 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                cursor: 'pointer',
              }}
            >
              <span style={{ fontSize: 11, color: A.textMuted }}>🎬 Video Clip (not typical for this platform)</span>
              <span style={{ fontSize: 11, color: A.textMuted }}>›</span>
            </button>
          )}

          {showVideoSection && (!isTextPlatform || videoExpanded) && (
            <div style={{
              marginTop: 4, padding: '12px 14px', borderRadius: 10,
              border: `1px solid ${isVideoPlatform ? A.border : A.borderLight}`,
              background: isVideoPlatform ? A.surfaceAlt : A.bg,
              opacity: isVideoPlatform ? 1 : 0.55,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <p style={{ fontSize: 12, fontWeight: 600, color: A.textSoft, margin: 0 }}>
                  🎬 Video Clip (Veo 3)
                </p>
                {isTextPlatform && videoExpanded && (
                  <button
                    type="button"
                    onClick={() => setVideoExpanded(false)}
                    style={{
                      border: 'none', background: 'transparent', color: A.textMuted,
                      fontSize: 11, cursor: 'pointer', padding: 0,
                    }}
                  >
                    ‹ collapse
                  </button>
                )}
              </div>

              {!isVideoPlatform ? (
                <p style={{ fontSize: 11, color: A.textMuted, margin: 0 }}>
                  Video generation is available for Instagram, TikTok, and Reels posts.
                </p>
              ) : videoStatus === 'idle' ? (
                <button
                  onClick={() => startGeneration('fast')}
                  style={{
                    width: '100%', padding: '8px', borderRadius: 7, border: 'none',
                    background: `linear-gradient(135deg, ${A.violet}, ${A.indigo})`,
                    color: 'white', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                  }}
                >
                  Generate 8-sec Clip →
                </button>
              ) : videoStatus === 'generating' ? (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 11, color: A.textMuted }}>Generating… (~2.5 min)</span>
                    <span style={{ fontSize: 11, color: A.textMuted }}>{Math.round(progress)}%</span>
                  </div>
                  <div style={{ height: 6, borderRadius: 3, background: A.border }}>
                    <div style={{
                      height: 6, borderRadius: 3,
                      background: `linear-gradient(90deg, ${A.violet}, ${A.indigo})`,
                      width: `${progress}%`,
                      transition: 'width 0.5s ease',
                    }} />
                  </div>
                </div>
              ) : videoStatus === 'complete' && videoUrl ? (
                <video
                  src={videoUrl}
                  controls
                  autoPlay
                  muted
                  loop
                  style={{ width: '100%', borderRadius: 8, marginTop: 4 }}
                />
              ) : videoStatus === 'error' ? (
                <div>
                  <p style={{ fontSize: 11, color: A.coral, margin: '0 0 6px' }}>
                    {videoError || 'Video generation failed'}
                  </p>
                  <button
                    onClick={() => startGeneration('fast')}
                    style={{
                      fontSize: 11, color: A.coral, background: 'transparent',
                      border: `1px solid ${A.coral}40`, borderRadius: 6,
                      padding: '4px 10px', cursor: 'pointer',
                    }}
                  >
                    Retry
                  </button>
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Right: Image — M-3: hidden when captionOnly is active */}
        {!captionOnly && (
          <div style={{
            borderRadius: 12, overflow: 'hidden',
            background: A.surfaceAlt, border: `1px solid ${A.border}`,
            aspectRatio: '1 / 1', display: 'flex', alignItems: 'center', justifyContent: 'center',
            position: 'relative',
          }}>
            {imageUrl ? (
              <img
                src={imageUrl}
                alt="Generated post image"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: 20 }}>
                {status === 'generating' ? (
                  <>
                    {/* Image skeleton shimmer */}
                    <div style={{
                      width: 48, height: 48, borderRadius: '50%',
                      border: `3px solid ${A.indigoLight}`,
                      borderTopColor: A.indigo,
                      margin: '0 auto 12px',
                      animation: 'spin 1s linear infinite',
                    }} />
                    <p style={{ fontSize: 12, color: A.textMuted }}>Generating image...</p>
                  </>
                ) : (
                  <>
                    <span style={{ fontSize: 32 }}>🖼️</span>
                    <p style={{ fontSize: 12, color: A.textMuted, marginTop: 8 }}>Image will appear here</p>
                  </>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}
