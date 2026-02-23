import React, { useRef, useState } from 'react'
import { A } from '../theme'
import { api } from '../api/client'

const PILLAR_COLORS: Record<string, string> = {
  education: A.indigo,
  inspiration: A.violet,
  promotion: A.coral,
  behind_the_scenes: A.emerald,
  user_generated: A.amber,
}

const PLATFORM_ICONS: Record<string, string> = {
  instagram: '📸',
  linkedin: '💼',
  twitter: '🐦',
  facebook: '👥',
}

const DERIVATIVE_LABELS: Record<string, string> = {
  carousel: 'Carousel',
  thread_hook: 'Thread',
  blog_snippet: 'Blog',
  story: 'Story',
}

// Colors for series groups (distinct from pillar colors)
const SERIES_PALETTE = ['#f97316', '#06b6d4', '#ec4899', '#a78bfa']

export interface DayBrief {
  day_index: number
  platform: string
  pillar: string
  pillar_id?: string
  content_theme: string
  caption_hook: string
  key_message: string
  image_prompt: string
  hashtags: string[]
  derivative_type?: string
  event_anchor?: string | null
  custom_photo_url?: string | null
}

interface Props {
  plan: { plan_id: string; days: DayBrief[] }
  brandId?: string
  onGeneratePost?: (planId: string, dayIndex: number) => void
  onPhotoUploaded?: (dayIndex: number, photoUrl: string | null) => void
}

export default function ContentCalendar({ plan, brandId, onGeneratePost, onPhotoUploaded }: Props) {
  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

  // Compute which pillar_ids form repurposing series (appear on more than one day)
  const pillarIdCounts: Record<string, number> = {}
  for (const day of plan.days) {
    if (day.pillar_id) {
      pillarIdCounts[day.pillar_id] = (pillarIdCounts[day.pillar_id] || 0) + 1
    }
  }
  const seriesIds = Object.keys(pillarIdCounts).filter(id => pillarIdCounts[id] > 1)
  const seriesColorMap: Record<string, string> = {}
  seriesIds.forEach((id, i) => {
    seriesColorMap[id] = SERIES_PALETTE[i % SERIES_PALETTE.length]
  })

  const hasAnySeries = seriesIds.length > 0

  return (
    <div>
      {/* Calendar header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: A.text, margin: 0 }}>{plan.days.length}-Day Content Calendar</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {Object.entries(PILLAR_COLORS).map(([pillar, color]) => (
            <span
              key={pillar}
              style={{ fontSize: 11, color: A.textSoft, display: 'flex', alignItems: 'center', gap: 4 }}
            >
              <span style={{ width: 8, height: 8, borderRadius: 2, background: color, display: 'inline-block', flexShrink: 0 }} />
              {pillar.replace(/_/g, ' ')}
            </span>
          ))}
          {hasAnySeries && (
            <span style={{ fontSize: 11, color: A.textSoft, display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontSize: 10 }}>♻</span>
              repurposed
            </span>
          )}
        </div>
      </div>

      {/* 7-day grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 8 }}>
        {plan.days.map((day, i) => {
          const seriesColor = day.pillar_id ? seriesColorMap[day.pillar_id] : undefined
          return (
            <DayCard
              key={day.day_index ?? i}
              day={day}
              dayName={DAY_NAMES[i % 7]}
              brandId={brandId}
              planId={plan.plan_id}
              seriesColor={seriesColor}
              onGenerate={() => onGeneratePost?.(plan.plan_id, day.day_index ?? i)}
              onPhotoUploaded={(photoUrl) => onPhotoUploaded?.(day.day_index ?? i, photoUrl)}
            />
          )
        })}
      </div>
    </div>
  )
}

interface DayCardProps {
  day: DayBrief
  dayName: string
  brandId?: string
  planId?: string
  seriesColor?: string
  onGenerate: () => void
  onPhotoUploaded: (photoUrl: string | null) => void
}

function DayCard({ day, dayName, brandId, planId, seriesColor, onGenerate, onPhotoUploaded }: DayCardProps) {
  const pillarColor = PILLAR_COLORS[day.pillar] || A.indigo
  const platformIcon = PLATFORM_ICONS[day.platform] || '📱'
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [photoError, setPhotoError] = useState('')

  const dayIndex = day.day_index
  const isDerivative = day.derivative_type && day.derivative_type !== 'original'
  const derivativeLabel = day.derivative_type ? DERIVATIVE_LABELS[day.derivative_type] : null

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !brandId || !planId || dayIndex === undefined) return

    setUploading(true)
    setPhotoError('')
    const fd = new FormData()
    fd.append('file', file)

    try {
      const res = await api.uploadDayPhoto(brandId, planId, dayIndex, fd) as any
      onPhotoUploaded(res.custom_photo_url)
    } catch (err: any) {
      setPhotoError(err.message || 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleRemovePhoto = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!brandId || !planId || dayIndex === undefined) return
    setUploading(true)
    setPhotoError('')
    try {
      await api.deleteDayPhoto(brandId, planId, dayIndex)
      onPhotoUploaded(null)
    } catch (err: any) {
      setPhotoError(err.message || 'Remove failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div
      style={{
        borderRadius: 10,
        background: A.surface,
        border: `1px solid ${A.border}`,
        boxShadow: seriesColor ? `inset 3px 0 0 0 ${seriesColor}` : undefined,
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'transform 0.15s, box-shadow 0.15s',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-2px)'
        e.currentTarget.style.boxShadow = seriesColor
          ? `0 4px 16px rgba(0,0,0,0.08), inset 3px 0 0 0 ${seriesColor}`
          : '0 4px 16px rgba(0,0,0,0.08)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = seriesColor ? `inset 3px 0 0 0 ${seriesColor}` : 'none'
      }}
    >
      {/* Pillar color bar */}
      <div style={{ height: 3, background: pillarColor }} />

      {/* Custom photo thumbnail */}
      {day.custom_photo_url && (
        <div style={{ position: 'relative' }}>
          <img
            src={day.custom_photo_url}
            alt="Custom photo"
            style={{ width: '100%', aspectRatio: '1 / 1', objectFit: 'cover', display: 'block' }}
          />
          <button
            onClick={handleRemovePhoto}
            title="Remove photo"
            style={{
              position: 'absolute', top: 4, right: 4,
              width: 20, height: 20, borderRadius: '50%',
              background: 'rgba(0,0,0,0.55)', border: 'none',
              color: 'white', fontSize: 13, lineHeight: 1,
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            ×
          </button>
          <div style={{
            position: 'absolute', bottom: 4, left: 4,
            fontSize: 9, color: 'white', fontWeight: 600,
            background: 'rgba(0,0,0,0.5)', padding: '1px 5px', borderRadius: 4,
          }}>
            📷 Your photo
          </div>
        </div>
      )}

      <div style={{ padding: '10px 10px 12px' }}>
        {/* Day + platform */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: A.textSoft }}>{dayName}</span>
          <span style={{ fontSize: 14 }}>{platformIcon}</span>
        </div>

        {/* Pillar badge */}
        <div
          style={{
            fontSize: 10,
            fontWeight: 500,
            padding: '2px 6px',
            borderRadius: 4,
            background: pillarColor + '15',
            color: pillarColor,
            display: 'inline-block',
            marginBottom: 6,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
          }}
        >
          {day.pillar?.replace(/_/g, ' ')}
        </div>

        {/* Repurpose badge — only shown when the series grouping is confirmed by seriesColor */}
        {isDerivative && derivativeLabel && seriesColor && (
          <div style={{
            fontSize: 9,
            fontWeight: 600,
            padding: '2px 6px',
            borderRadius: 4,
            background: (seriesColor || A.textMuted) + '18',
            color: seriesColor || A.textMuted,
            border: `1px solid ${(seriesColor || A.textMuted)}30`,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 3,
            marginBottom: 6,
            marginLeft: 4,
            textTransform: 'uppercase',
            letterSpacing: 0.4,
          }}>
            ♻ {derivativeLabel}
          </div>
        )}

        {/* Event anchor badge */}
        {day.event_anchor && (
          <div style={{
            fontSize: 10, color: A.amber, background: A.amber + '15',
            padding: '2px 6px', borderRadius: 8, marginTop: 2,
            border: `1px solid ${A.amber}30`,
            display: 'inline-block', marginBottom: 6,
          }}>
            📅 {day.event_anchor}
          </div>
        )}

        {/* Theme */}
        <p
          style={{
            fontSize: 11,
            color: A.text,
            lineHeight: 1.4,
            marginBottom: 10,
            fontWeight: 500,
            overflow: 'hidden',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
          } as React.CSSProperties}
        >
          {day.content_theme}
        </p>

        {/* Hook preview — hidden when photo thumbnail already fills the card */}
        {!day.custom_photo_url && (
          <p
            style={{
              fontSize: 10,
              color: A.textMuted,
              lineHeight: 1.4,
              marginBottom: 10,
              overflow: 'hidden',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
            } as React.CSSProperties}
          >
            "{day.caption_hook}"
          </p>
        )}

        {/* Upload error */}
        {photoError && (
          <p style={{ fontSize: 10, color: A.coral, margin: '0 0 6px' }}>{photoError}</p>
        )}

        {/* Generate button */}
        <button
          onClick={e => {
            e.stopPropagation()
            onGenerate()
          }}
          style={{
            width: '100%',
            padding: '6px 0',
            borderRadius: 6,
            border: 'none',
            background: `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
            color: 'white',
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
            marginBottom: brandId ? 6 : 0,
          }}
        >
          {day.custom_photo_url ? 'Generate with my photo ✨' : 'Generate ✨'}
        </button>

        {/* BYOP: add / change photo */}
        {brandId && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
            <button
              onClick={e => {
                e.stopPropagation()
                fileInputRef.current?.click()
              }}
              disabled={uploading}
              style={{
                width: '100%',
                padding: '5px 0',
                borderRadius: 6,
                border: `1px solid ${A.border}`,
                background: 'transparent',
                color: uploading ? A.textMuted : A.textSoft,
                fontSize: 10,
                cursor: uploading ? 'not-allowed' : 'pointer',
              }}
            >
              {uploading ? 'Uploading…' : day.custom_photo_url ? '📷 Change photo' : '📷 Add photo'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
