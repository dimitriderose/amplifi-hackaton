import { useState } from 'react'
import { A } from '../theme'

interface BrandProfile {
  brand_id: string
  business_name: string
  business_type: string
  industry: string
  tone: string
  colors: string[]
  target_audience: string
  visual_style: string
  image_style_directive: string
  caption_style_directive: string
  content_themes: string[]
  competitors: string[]
  analysis_status: string
}

interface Props {
  brand: BrandProfile
  onUpdate: (data: Partial<BrandProfile>) => void
}

export default function BrandProfileCard({ brand, onUpdate }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(brand)

  const handleSave = () => {
    onUpdate(draft)
    setEditing(false)
  }

  if (brand.analysis_status === 'analyzing') {
    return (
      <div style={{
        padding: 24, borderRadius: 12, background: A.surface, border: `1px solid ${A.border}`,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          border: `3px solid ${A.indigoLight}`,
          borderTopColor: A.indigo,
          animation: 'spin 1s linear infinite',
        }} />
        <div>
          <p style={{ fontSize: 14, fontWeight: 500, color: A.text }}>Analyzing your brand...</p>
          <p style={{ fontSize: 12, color: A.textSoft }}>This usually takes 30–60 seconds</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  return (
    <div style={{ padding: 24, borderRadius: 12, background: A.surface, border: `1px solid ${A.border}` }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: A.text, marginBottom: 4 }}>
            {brand.business_name || 'Your Brand'}
          </h2>
          <span style={{
            fontSize: 11, fontWeight: 500, padding: '2px 8px', borderRadius: 20,
            background: A.indigoLight, color: A.indigo,
          }}>
            {brand.business_type?.replace('_', ' ').toUpperCase() || 'BRAND'}
          </span>
        </div>
        <button
          onClick={() => setEditing(!editing)}
          style={{
            padding: '6px 14px', borderRadius: 6, border: `1px solid ${A.border}`,
            background: 'transparent', cursor: 'pointer', fontSize: 13, color: A.textSoft,
          }}
        >
          {editing ? 'Cancel' : 'Edit'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Industry */}
        <Field label="Industry" value={brand.industry} editing={editing}
          onChange={v => setDraft(d => ({ ...d, industry: v }))} draft={draft.industry} />

        {/* Tone */}
        <Field label="Tone of Voice" value={brand.tone} editing={editing}
          onChange={v => setDraft(d => ({ ...d, tone: v }))} draft={draft.tone} />

        {/* Target Audience */}
        <div style={{ gridColumn: '1 / -1' }}>
          <Field label="Target Audience" value={brand.target_audience} editing={editing}
            onChange={v => setDraft(d => ({ ...d, target_audience: v }))} draft={draft.target_audience} />
        </div>

        {/* Colors */}
        <div>
          <p style={{ fontSize: 12, fontWeight: 500, color: A.textSoft, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>Brand Colors</p>
          <div style={{ display: 'flex', gap: 8 }}>
            {(brand.colors || []).map((color, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 32, height: 32, borderRadius: 6, background: color, border: `1px solid ${A.border}` }} />
                <span style={{ fontSize: 10, color: A.textMuted }}>{color}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Content Themes */}
        <div>
          <p style={{ fontSize: 12, fontWeight: 500, color: A.textSoft, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>Content Themes</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {(brand.content_themes || []).map((theme, i) => (
              <span key={i} style={{
                fontSize: 11, padding: '3px 8px', borderRadius: 20,
                background: A.surfaceAlt, color: A.textSoft, border: `1px solid ${A.border}`,
              }}>{theme}</span>
            ))}
          </div>
        </div>

        {/* Image Style Directive */}
        <div style={{ gridColumn: '1 / -1' }}>
          <p style={{ fontSize: 12, fontWeight: 500, color: A.textSoft, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Visual Identity Seed
          </p>
          {editing ? (
            <textarea
              value={draft.image_style_directive}
              onChange={e => setDraft(d => ({ ...d, image_style_directive: e.target.value }))}
              rows={2}
              style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: `1px solid ${A.border}`, fontSize: 12, resize: 'vertical' }}
            />
          ) : (
            <p style={{ fontSize: 12, color: A.text, lineHeight: 1.5, padding: '8px 10px', borderRadius: 6, background: A.surfaceAlt }}>
              {brand.image_style_directive || '—'}
            </p>
          )}
        </div>

        {/* Caption Style Directive */}
        <div style={{ gridColumn: '1 / -1' }}>
          <p style={{ fontSize: 12, fontWeight: 500, color: A.textSoft, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Caption Style Directive
          </p>
          {editing ? (
            <textarea
              value={draft.caption_style_directive}
              onChange={e => setDraft(d => ({ ...d, caption_style_directive: e.target.value }))}
              rows={2}
              style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: `1px solid ${A.border}`, fontSize: 12, resize: 'vertical' }}
            />
          ) : (
            <p style={{ fontSize: 12, color: A.text, lineHeight: 1.5, padding: '8px 10px', borderRadius: 6, background: A.surfaceAlt }}>
              {brand.caption_style_directive || '—'}
            </p>
          )}
        </div>
      </div>

      {editing && (
        <button
          onClick={handleSave}
          style={{
            marginTop: 16, padding: '10px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
            background: A.indigo, color: 'white', fontSize: 14, fontWeight: 600,
          }}
        >
          Save Changes
        </button>
      )}
    </div>
  )
}

function Field({ label, value, draft, editing, onChange }: {
  label: string; value: string; draft: string; editing: boolean; onChange: (v: string) => void
}) {
  return (
    <div>
      <p style={{ fontSize: 12, fontWeight: 500, color: A.textSoft, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</p>
      {editing ? (
        <input
          value={draft}
          onChange={e => onChange(e.target.value)}
          style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: `1px solid ${A.border}`, fontSize: 13 }}
        />
      ) : (
        <p style={{ fontSize: 13, color: A.text }}>{value || '—'}</p>
      )}
    </div>
  )
}
