import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

export interface Post {
  post_id: string
  plan_id: string
  day_index: number
  status: 'draft' | 'generating' | 'complete' | 'failed' | 'approved'
  caption?: string
  hashtags?: string[]
  image_url?: string
  platform?: string
  pillar?: string
  created_at?: string
}

export function usePostLibrary(brandId: string, planId?: string) {
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetch = useCallback(async () => {
    if (!brandId) return
    setLoading(true)
    setError('')
    try {
      const res = await api.listPosts(brandId, planId) as { posts: Post[] }
      setPosts(res.posts || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load posts')
    } finally {
      setLoading(false)
    }
  }, [brandId, planId])

  useEffect(() => { fetch() }, [fetch])

  // H-7: Auto-refresh every 8 seconds when any post is still generating
  useEffect(() => {
    const hasGenerating = posts.some(p => p.status === 'generating')
    if (!hasGenerating) return
    const interval = setInterval(fetch, 8000)
    return () => clearInterval(interval)
  }, [posts, fetch])

  return { posts, loading, error, refresh: fetch }
}
