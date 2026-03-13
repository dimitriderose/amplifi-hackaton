import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import PostHistory from '../components/PostHistory'

export default function PostHistoryPage() {
  const { brandId } = useParams<{ brandId: string }>()
  const navigate = useNavigate()
  const { isSignedIn, loading: authLoading } = useAuth()

  useEffect(() => {
    if (!authLoading && !isSignedIn) navigate('/')
  }, [authLoading, isSignedIn, navigate])

  if (!brandId) return null

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>
      <PostHistory brandId={brandId} />
    </div>
  )
}
