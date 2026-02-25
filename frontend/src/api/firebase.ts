import { initializeApp } from 'firebase/app'
import { getAuth, signInAnonymously, onAuthStateChanged, type User } from 'firebase/auth'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || '',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'amplifi-488503-a0bd0',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || '',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '',
}

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)

/**
 * Sign in anonymously. Firebase persists the UID in IndexedDB,
 * so the same user gets the same UID across page reloads.
 */
export async function ensureAnonymousAuth(): Promise<User> {
  // If already signed in, return immediately
  if (auth.currentUser) return auth.currentUser

  // Wait for auth state to initialize (Firebase may restore from cache)
  const existing = await new Promise<User | null>((resolve) => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      unsubscribe()
      resolve(user)
    })
  })
  if (existing) return existing

  // No cached session — sign in anonymously
  const cred = await signInAnonymously(auth)
  return cred.user
}

export function getUid(): string | null {
  return auth.currentUser?.uid ?? null
}
