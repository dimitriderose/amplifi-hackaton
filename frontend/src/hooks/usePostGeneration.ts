import { useState, useRef, useCallback } from 'react'

export type GenerationStatus = 'idle' | 'generating' | 'complete' | 'error'

export interface GenerationState {
  status: GenerationStatus
  statusMessage: string
  captionChunks: string[]    // streaming caption text pieces
  caption: string            // final complete caption
  hashtags: string[]
  imageUrl: string | null
  imageUrls: string[]        // carousel: all slide URLs
  videoUrl: string | null
  postId: string | null
  error: string | null
}

export function usePostGeneration() {
  const [state, setState] = useState<GenerationState>({
    status: 'idle',
    statusMessage: '',
    captionChunks: [],
    caption: '',
    hashtags: [],
    imageUrl: null,
    imageUrls: [],
    videoUrl: null,
    postId: null,
    error: null,
  })

  const eventSourceRef = useRef<EventSource | null>(null)

  const generate = useCallback((planId: string, dayIndex: number, brandId: string, instructions?: string) => {
    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    setState({
      status: 'generating',
      statusMessage: 'Starting generation...',
      captionChunks: [],
      caption: '',
      hashtags: [],
      imageUrl: null,
      imageUrls: [],
      videoUrl: null,
      postId: null,
      error: null,
    })

    const instructionsParam = instructions ? `&instructions=${encodeURIComponent(instructions)}` : ''
    const url = `/api/generate/${planId}/${dayIndex}?brand_id=${encodeURIComponent(brandId)}${instructionsParam}`
    const es = new EventSource(url)
    eventSourceRef.current = es

    es.addEventListener('status', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      setState(prev => ({ ...prev, statusMessage: data.message }))
    })

    es.addEventListener('caption', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      if (data.chunk) {
        setState(prev => ({
          ...prev,
          captionChunks: [...prev.captionChunks, data.text],
        }))
      } else {
        setState(prev => ({
          ...prev,
          caption: data.text,
          hashtags: data.hashtags || [],
          captionChunks: [],
        }))
      }
    })

    es.addEventListener('image', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      setState(prev => ({
        ...prev,
        imageUrl: prev.imageUrl || data.url,  // first image becomes primary
        imageUrls: [...prev.imageUrls, data.url],
      }))
    })

    es.addEventListener('complete', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      setState(prev => ({
        ...prev,
        status: 'complete',
        postId: data.post_id,
        caption: data.caption || prev.caption,
        hashtags: data.hashtags || prev.hashtags,
        imageUrl: data.image_url || prev.imageUrl,
        imageUrls: data.image_urls?.length ? data.image_urls : prev.imageUrls,
      }))
      es.close()
    })

    es.addEventListener('error', (e: MessageEvent) => {
      // Check if this is a named 'error' SSE event (from our server) or a connection error
      if (e.data) {
        const data = JSON.parse(e.data)
        setState(prev => ({ ...prev, status: 'error', error: data.message }))
      } else {
        setState(prev => ({ ...prev, status: 'error', error: 'Connection lost' }))
      }
      es.close()
    })

    return () => es.close()
  }, [])

  const reset = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }
    setState({
      status: 'idle',
      statusMessage: '',
      captionChunks: [],
      caption: '',
      hashtags: [],
      imageUrl: null,
      imageUrls: [],
      videoUrl: null,
      postId: null,
      error: null,
    })
  }, [])

  /** Load an already-generated post into the state (view mode). */
  const loadExisting = useCallback((post: {
    postId: string
    caption: string
    hashtags: string[]
    imageUrl: string | null
    imageUrls?: string[]
    videoUrl?: string | null
  }) => {
    setState({
      status: 'complete',
      statusMessage: '',
      captionChunks: [],
      caption: post.caption,
      hashtags: post.hashtags,
      imageUrl: post.imageUrl,
      imageUrls: post.imageUrls || (post.imageUrl ? [post.imageUrl] : []),
      videoUrl: post.videoUrl ?? null,
      postId: post.postId,
      error: null,
    })
  }, [])

  return { state, generate, reset, loadExisting }
}
