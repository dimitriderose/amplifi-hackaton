import { useParams, useNavigate } from 'react-router-dom'
import { A } from '../theme'
import { useBrandProfile } from '../hooks/useBrandProfile'
import BrandProfileCard from '../components/BrandProfileCard'

export default function DashboardPage() {
  const { brandId } = useParams<{ brandId: string }>()
  const navigate = useNavigate()
  const { brand, loading, error, updateBrand } = useBrandProfile(brandId)

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200 }}>
        <p style={{ color: A.textSoft }}>Loading brand profile...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <p style={{ color: A.coral }}>{error}</p>
        <button onClick={() => navigate('/onboard')} style={{ marginTop: 16, padding: '8px 16px', borderRadius: 8, background: A.indigo, color: 'white', border: 'none', cursor: 'pointer' }}>
          Start Over
        </button>
      </div>
    )
  }

  if (!brand) return null

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: A.text, marginBottom: 4 }}>
            {brand.business_name || 'Your Brand'} — Dashboard
          </h1>
          <p style={{ fontSize: 14, color: A.textSoft }}>
            Manage your brand profile and content calendar
          </p>
        </div>
        <button
          onClick={() => navigate('/onboard')}
          style={{ padding: '8px 16px', borderRadius: 8, border: `1px solid ${A.border}`, background: 'transparent', cursor: 'pointer', fontSize: 13, color: A.textSoft }}
        >
          + New Brand
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24, alignItems: 'start' }}>
        {/* Brand Profile Card */}
        <BrandProfileCard brand={brand} onUpdate={updateBrand} />

        {/* Content Calendar placeholder */}
        <div style={{ padding: 24, borderRadius: 12, background: A.surface, border: `1px solid ${A.border}` }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: A.text, marginBottom: 16 }}>
            Content Calendar
          </h3>
          <div style={{ padding: 32, textAlign: 'center', background: A.surfaceAlt, borderRadius: 8 }}>
            <p style={{ fontSize: 14, color: A.textSoft, marginBottom: 16 }}>
              Content calendar coming in the next feature
            </p>
            <button style={{
              padding: '10px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
              color: 'white', fontSize: 14, fontWeight: 500,
            }}>
              Generate Content Calendar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
