import { useState, useEffect } from 'react'
import { onAuthStateChanged, type User } from 'firebase/auth'
import { auth, ensureAnonymousAuth } from '../api/firebase'

/**
 * React hook that manages Firebase Anonymous Auth.
 * On first mount it triggers anonymous sign-in (or restores a cached session).
 * Returns { uid, loading }.
 */
export function useAuth() {
  const [uid, setUid] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Listen for auth state changes
    const unsubscribe = onAuthStateChanged(auth, (user: User | null) => {
      setUid(user?.uid ?? null)
      setLoading(false)
    })

    // Trigger anonymous auth
    ensureAnonymousAuth().catch((err) => {
      console.error('Anonymous auth failed:', err)
      setLoading(false)
    })

    return unsubscribe
  }, [])

  return { uid, loading }
}
