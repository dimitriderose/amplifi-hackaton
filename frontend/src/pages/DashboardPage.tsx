import { useParams, useNavigate } from 'react-router-dom'
import { A } from '../theme'
import { useBrandProfile } from '../hooks/useBrandProfile'
import { useContentPlan } from '../hooks/useContentPlan'
import BrandProfileCard from '../components/BrandProfileCard'
import ContentCalendar from '../components/ContentCalendar'

export default function DashboardPage() {
  const { brandId } = useParams<{ brandId: string }>()
  const navigate = useNavigate()
  const { brand, loading: brandLoading, error: brandError, updateBrand } = useBrandProfile(brandId)
  const { plan, generating, error: planError, generatePlan } = useContentPlan(brandId ?? '')

  if (brandLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200 }}>
        <p style={{ color: A.textSoft }}>Loading brand profile...</p>
      </div>
    )
  }

  if (brandError) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <p style={{ color: A.coral }}>{brandError}</p>
        <button
          onClick={() => navigate('/onboard')}
          style={{
            marginTop: 16, padding: '8px 16px', borderRadius: 8,
            background: A.indigo, color: 'white', border: 'none', cursor: 'pointer',
          }}
        >
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
          style={{
            padding: '8px 16px', borderRadius: 8, border: `1px solid ${A.border}`,
            background: 'transparent', cursor: 'pointer', fontSize: 13, color: A.textSoft,
          }}
        >
          + New Brand
        </button>
      </div>

      {/* 1:2 grid layout — left: brand card, right: calendar */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24, alignItems: 'start' }}>
        {/* Left column: Brand Profile Card */}
        <BrandProfileCard brand={brand} onUpdate={updateBrand} />

        {/* Right column: Content Calendar or generate prompt */}
        <div style={{ padding: 24, borderRadius: 12, background: A.surface, border: `1px solid ${A.border}` }}>
          {plan ? (
            /* Calendar view */
            <ContentCalendar
              plan={{ plan_id: plan.plan_id, days: plan.days }}
              brandId={brandId ?? ''}
              onGeneratePost={(planId, dayIndex) =>
                navigate(`/generate/${planId}/${dayIndex}`)
              }
            />
          ) : (
            /* No plan yet — show generate CTA */
            <>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: A.text, marginBottom: 16 }}>
                Content Calendar
              </h3>

              {generating ? (
                /* Spinner while generating */
                <div
                  style={{
                    padding: 40,
                    textAlign: 'center',
                    background: A.surfaceAlt,
                    borderRadius: 8,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 16,
                  }}
                >
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      border: `3px solid ${A.indigo}`,
                      borderTopColor: 'transparent',
                      animation: 'spin 0.8s linear infinite',
                    }}
                  />
                  <p style={{ fontSize: 14, color: A.textSoft, margin: 0 }}>
                    Building your 7-day content plan...
                  </p>
                  <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                </div>
              ) : (
                /* Generate button + optional error */
                <div style={{ padding: 32, textAlign: 'center', background: A.surfaceAlt, borderRadius: 8 }}>
                  {planError && (
                    <p style={{ fontSize: 13, color: A.coral, marginBottom: 12 }}>
                      {planError}
                    </p>
                  )}
                  <p style={{ fontSize: 14, color: A.textSoft, marginBottom: 16 }}>
                    Generate a personalised 7-day content plan tailored to your brand.
                  </p>
                  <button
                    onClick={() => generatePlan(7)}
                    style={{
                      padding: '10px 24px',
                      borderRadius: 8,
                      border: 'none',
                      cursor: 'pointer',
                      background: `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
                      color: 'white',
                      fontSize: 14,
                      fontWeight: 600,
                    }}
                  >
                    Generate Content Calendar ✨
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
