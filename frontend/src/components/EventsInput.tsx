import { useState } from 'react'
import { A } from '../theme'

interface Props {
  onGenerate: (events: string) => void
  generating: boolean
}

export default function EventsInput({ onGenerate, generating }: Props) {
  const [events, setEvents] = useState('')

  return (
    <div style={{ padding: 24, borderRadius: 12, background: A.surface, border: `1px solid ${A.border}` }}>
      <h3 style={{ fontSize: 16, fontWeight: 600, color: A.text, marginBottom: 4 }}>
        Content Calendar
      </h3>
      <p style={{ fontSize: 13, color: A.textSoft, marginBottom: 16 }}>
        Generate a personalised 7-day content plan tailored to your brand.
      </p>

      {/* Events input */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, fontWeight: 600, color: A.textSoft, textTransform: 'uppercase', letterSpacing: 0.5, display: 'block', marginBottom: 6 }}>
          What's happening this week? <span style={{ color: A.textMuted, fontWeight: 400, textTransform: 'none' }}>(optional)</span>
        </label>
        <textarea
          value={events}
          onChange={e => setEvents(e.target.value)}
          placeholder="e.g. Launching lavender croissant Tuesday, farmer's market booth Saturday, staff birthday Wednesday"
          rows={2}
          style={{
            width: '100%', padding: '10px 12px', borderRadius: 8, fontSize: 13, lineHeight: 1.5,
            border: `1px solid ${A.border}`, background: A.surfaceAlt, color: A.text,
            resize: 'none', boxSizing: 'border-box',
          }}
        />
        <p style={{ fontSize: 11, color: A.textMuted, marginTop: 4 }}>
          Real events become content pillars — launches, markets, specials, milestones.
        </p>
      </div>

      {generating ? (
        <div style={{
          padding: 32, textAlign: 'center', background: A.surfaceAlt,
          borderRadius: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
        }}>
          <div style={{
            width: 28, height: 28, borderRadius: '50%',
            border: `3px solid ${A.indigo}`, borderTopColor: 'transparent',
            animation: 'spin 0.8s linear infinite',
          }} />
          <p style={{ fontSize: 14, color: A.textSoft, margin: 0 }}>Building your content plan...</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      ) : (
        <button
          onClick={() => onGenerate(events)}
          style={{
            padding: '10px 24px', borderRadius: 8, border: 'none', cursor: 'pointer',
            background: `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
            color: 'white', fontSize: 14, fontWeight: 600,
          }}
        >
          Generate Content Calendar ✨
        </button>
      )}
    </div>
  )
}
