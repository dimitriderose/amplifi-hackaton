import { useNavigate } from 'react-router-dom'
import { A } from '../theme'

export default function LandingPage() {
  const navigate = useNavigate()
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '80px 24px', textAlign: 'center' }}>
      <h1 style={{ fontSize: 48, fontWeight: 800, color: A.text, lineHeight: 1.1, marginBottom: 20 }}>
        Your AI creative director.<br />
        <span style={{
          background: `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        }}>One brand. Infinite content.</span>
      </h1>
      <p style={{ fontSize: 18, color: A.textSoft, maxWidth: 540, margin: '0 auto 40px' }}>
        Paste your website URL. Watch captions and images stream together in real time.
        A full week of on-brand social content in minutes.
      </p>
      <button onClick={() => navigate('/onboard')} style={{
        padding: '14px 32px', borderRadius: 10, border: 'none', cursor: 'pointer',
        background: `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
        color: 'white', fontSize: 16, fontWeight: 600,
      }}>
        Build My Brand Profile →
      </button>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24, marginTop: 80 }}>
        {[
          { step: '1', title: 'Paste your URL', desc: 'We analyze your brand colors, tone, and audience automatically.' },
          { step: '2', title: 'Get your calendar', desc: 'A 7-day content strategy with platform-specific themes and pillars.' },
          { step: '3', title: 'Watch it generate', desc: 'Captions and matching images stream together in real time.' },
        ].map(({ step, title, desc }) => (
          <div key={step} style={{
            padding: 24, borderRadius: 12, background: A.surface, border: `1px solid ${A.border}`, textAlign: 'left',
          }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8, marginBottom: 12,
              background: `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'white', fontWeight: 700, fontSize: 14,
            }}>{step}</div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: A.text, marginBottom: 8 }}>{title}</h3>
            <p style={{ fontSize: 14, color: A.textSoft, lineHeight: 1.5 }}>{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
