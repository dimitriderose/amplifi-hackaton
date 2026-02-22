import { useState, useRef } from 'react'
import { A } from '../theme'
import { GenerationState } from '../hooks/usePostGeneration'
import { useVideoGeneration } from '../hooks/useVideoGeneration'
import PlatformPreview from './PlatformPreview'

interface Props {
  state: GenerationState
  dayBrief?: {
    platform: string
    pillar: string
    content_theme: string
  }
  brandId?: string
  onApprove?: (postId: string) => void
  onRegenerate?: () => void
}

const PLATFORM_ICONS: Record<string, string> = {
  instagram: '📸',
  linkedin: '💼',
  twitter: '🐦',
  facebook: '👥',
}

const VIDEO_PLATFORMS = new Set(['instagram', 'tiktok', 'reels', 'story', 'stories'])

export default function PostGenerator({ state, dayBrief, brandId, onApprove, onRegenerate }: Props) {
  const [copied, setCopied] = useState(false)
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { status, statusMessage, captionChunks, caption, hashtags, imageUrl, postId, error } = state

  const displayCaption = status === 'generating' && captionChunks.length > 0
    ? captionChunks.join('')
    : caption

  const handleCopy = () => {
    if (!navigator.clipboard) return
    const tags = hashtags.map(h => `#${h.replace(/^#/, '')}`).join(' ')
    const fullText = [caption, tags].filter(Boolean).join('\n\n')
    navigator.clipboard.writeText(fullText)
      .then(() => {
        if (copyTimerRef.current) clearTimeout(copyTimerRef.current)
        setCopied(true)
        copyTimerRef.current = setTimeout(() => setCopied(false), 1500)
      })
      .catch(() => {})
  }

  const platformIcon = PLATFORM_ICONS[dayBrief?.platform || ''] || '📱'

  const showVideoButton = status === 'complete' && postId && brandId &&
    VIDEO_PLATFORMS.has(dayBrief?.platform?.toLowerCase() ?? '')

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

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

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

          {/* Caption text box */}
          <div style={{
            minHeight: 120, padding: '12px 14px 12px', borderRadius: 10,
            background: A.surfaceAlt, border: `1px solid ${A.border}`,
            fontSize: 14, color: A.text, lineHeight: 1.6,
            position: 'relative',
            paddingRight: status === 'complete' && caption ? 72 : 14,
          }}>
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
            {status === 'complete' && caption && (
              <button
                type="button"
                onClick={handleCopy}
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

          {/* Platform preview — character count, fold/truncation, image crop simulation */}
          {status === 'complete' && caption && dayBrief?.platform && (
            <PlatformPreview
              platform={dayBrief.platform}
              caption={caption}
              imageUrl={imageUrl ?? undefined}
              hashtagCount={hashtags.length}
            />
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

          {/* Action buttons */}
          {status === 'complete' && postId && (
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              {onApprove && (
                <button
                  onClick={() => onApprove(postId)}
                  style={{
                    flex: 1, padding: '10px', borderRadius: 8, border: 'none',
                    background: `linear-gradient(135deg, ${A.emerald}, #059669)`,
                    color: 'white', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  }}
                >
                  ✓ Approve Post
                </button>
              )}
              {onRegenerate && (
                <button
                  onClick={onRegenerate}
                  style={{
                    padding: '10px 16px', borderRadius: 8,
                    border: `1px solid ${A.border}`,
                    background: 'transparent', color: A.textSoft,
                    fontSize: 13, cursor: 'pointer',
                  }}
                >
                  ↺ Regenerate
                </button>
              )}
            </div>
          )}

          {/* Video generation — only for video-eligible platforms */}
          {showVideoButton && (
            <div style={{
              marginTop: 4, padding: '12px 14px', borderRadius: 10,
              border: `1px solid ${A.border}`, background: A.surfaceAlt,
            }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: A.textSoft, margin: '0 0 8px' }}>
                🎬 Video Clip (Veo 3)
              </p>

              {videoStatus === 'idle' && (
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
              )}

              {videoStatus === 'generating' && (
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
              )}

              {videoStatus === 'complete' && videoUrl && (
                <video
                  src={videoUrl}
                  controls
                  autoPlay
                  muted
                  loop
                  style={{ width: '100%', borderRadius: 8, marginTop: 4 }}
                />
              )}

              {videoStatus === 'error' && (
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
              )}
            </div>
          )}
        </div>

        {/* Right: Image */}
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

      </div>
    </div>
  )
}

