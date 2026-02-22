import { useNavigate, useLocation } from 'react-router-dom'
import { A } from '../theme'

export default function NavBar() {
  const navigate = useNavigate()
  const location = useLocation()

  // Extract brandId from dashboard or export routes so we can link to /export/:brandId
  const dashboardMatch = location.pathname.match(/^\/dashboard\/([^/]+)/)
  const exportMatch = location.pathname.match(/^\/export\/([^/]+)/)
  const activeBrandId = (dashboardMatch && dashboardMatch[1]) || (exportMatch && exportMatch[1]) || null

  const staticLinks = [
    { path: '/', label: 'Home' },
    { path: '/onboard', label: 'Get Started' },
  ]

  const isActive = (path: string) => location.pathname === path

  return (
    <nav style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '12px 24px', borderBottom: `1px solid ${A.border}`,
      background: A.surface, position: 'sticky', top: 0, zIndex: 50,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
           onClick={() => navigate('/')}>
        <div style={{
          width: 28, height: 28, borderRadius: 7,
          background: `linear-gradient(135deg, ${A.indigo}, ${A.violet})`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, color: 'white', fontWeight: 700,
        }}>A</div>
        <span style={{ fontSize: 17, fontWeight: 700, color: A.text, letterSpacing: -0.3 }}>
          Amplifi
        </span>
      </div>
      <div style={{ display: 'flex', gap: 2 }}>
        {staticLinks.map(({ path, label }) => (
          <button key={path} onClick={() => navigate(path)} style={{
            padding: '5px 12px', borderRadius: 6,
            background: isActive(path) ? A.indigoLight : 'transparent',
            border: 'none', cursor: 'pointer', fontSize: 13,
            color: isActive(path) ? A.indigo : A.textSoft,
            fontWeight: isActive(path) ? 600 : 400,
          }}>{label}</button>
        ))}
        {activeBrandId && (
          <button
            onClick={() => navigate(`/export/${activeBrandId}`)}
            style={{
              padding: '5px 12px', borderRadius: 6,
              background: location.pathname.startsWith('/export/') ? A.indigoLight : 'transparent',
              border: 'none', cursor: 'pointer', fontSize: 13,
              color: location.pathname.startsWith('/export/') ? A.indigo : A.textSoft,
              fontWeight: location.pathname.startsWith('/export/') ? 600 : 400,
            }}
          >
            Export
          </button>
        )}
      </div>
    </nav>
  )
}
