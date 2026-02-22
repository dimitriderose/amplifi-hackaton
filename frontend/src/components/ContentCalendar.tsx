import React from 'react'
import { A } from '../theme'

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

export interface DayBrief {
  day_index: number
  platform: string
  pillar: string
  content_theme: string
  caption_hook: string
  key_message: string
  image_prompt: string
  hashtags: string[]
  derivative_type?: string
  event_anchor?: string | null
}

interface Props {
  plan: { plan_id: string; days: DayBrief[] }
  onGeneratePost?: (planId: string, dayIndex: number) => void
}

export default function ContentCalendar({ plan, onGeneratePost }: Props) {
  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

  return (
    <div>
      {/* Calendar header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: A.text, margin: 0 }}>7-Day Content Calendar</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {Object.entries(PILLAR_COLORS).map(([pillar, color]) => (
            <span
              key={pillar}
              style={{ fontSize: 11, color: A.textSoft, display: 'flex', alignItems: 'center', gap: 4 }}
            >
              <span style={{ width: 8, height: 8, borderRadius: 2, background: color, display: 'inline-block', flexShrink: 0 }} />
              {pillar.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      </div>

      {/* 7-day grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 8 }}>
        {plan.days.map((day, i) => (
          <DayCard
            key={day.day_index ?? i}
            day={day}
            dayName={DAY_NAMES[i % 7]}
            onGenerate={() => onGeneratePost?.(plan.plan_id, day.day_index ?? i)}
          />
        ))}
      </div>
    </div>
  )
}

interface DayCardProps {
  day: DayBrief
  dayName: string
  onGenerate: () => void
}

function DayCard({ day, dayName, onGenerate }: DayCardProps) {
  const pillarColor = PILLAR_COLORS[day.pillar] || A.indigo
  const platformIcon = PLATFORM_ICONS[day.platform] || '📱'

  return (
    <div
      style={{
        borderRadius: 10,
        background: A.surface,
        border: `1px solid ${A.border}`,
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'transform 0.15s, box-shadow 0.15s',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-2px)'
        e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.08)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      {/* Pillar color bar */}
      <div style={{ height: 3, background: pillarColor }} />

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
            marginBottom: 8,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
          }}
        >
          {day.pillar?.replace(/_/g, ' ')}
        </div>

        {/* Event anchor badge */}
        {day.event_anchor && (
          <div style={{
            fontSize: 10, color: A.amber, background: A.amber + '15',
            padding: '2px 6px', borderRadius: 8, marginTop: 4,
            border: `1px solid ${A.amber}30`,
            display: 'inline-block', marginBottom: 8,
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

        {/* Hook preview */}
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
          }}
        >
          Generate ✨
        </button>
      </div>
    </div>
  )
}
