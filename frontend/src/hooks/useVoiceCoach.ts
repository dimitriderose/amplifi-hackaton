import { useState, useRef, useCallback, MutableRefObject } from 'react'

export type VoiceCoachStatus = 'idle' | 'connecting' | 'active' | 'error'

interface UseVoiceCoachResult {
  status: VoiceCoachStatus
  isAISpeaking: boolean
  error: string | null
  startSession: (brandId: string) => Promise<void>
  stopSession: () => void
}

// AudioWorklet processor — inlined as a blob to avoid needing a separate file in the build
const WORKLET_SRC = `
class PCMProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0]?.[0]
    if (channel && channel.length > 0) {
      const pcm = new Int16Array(channel.length)
      for (let i = 0; i < channel.length; i++) {
        const s = Math.max(-1, Math.min(1, channel[i]))
        pcm[i] = s < 0 ? s * 32768 : s * 32767
      }
      this.port.postMessage(pcm.buffer, [pcm.buffer])
    }
    return true
  }
}
registerProcessor('pcm-processor', PCMProcessor)
`

export function useVoiceCoach(): UseVoiceCoachResult {
  const [status, setStatus] = useState<VoiceCoachStatus>('idle')
  const [isAISpeaking, setIsAISpeaking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const captureCtxRef = useRef<AudioContext | null>(null)
  const playbackCtxRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const playNextTimeRef = useRef<number>(0)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const aiSpeakingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const stopSession = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect()
      workletNodeRef.current = null
    }
    if (captureCtxRef.current) {
      captureCtxRef.current.close().catch(() => {})
      captureCtxRef.current = null
    }
    if (playbackCtxRef.current) {
      playbackCtxRef.current.close().catch(() => {})
      playbackCtxRef.current = null
    }
    if (aiSpeakingTimerRef.current) {
      clearTimeout(aiSpeakingTimerRef.current)
      aiSpeakingTimerRef.current = null
    }
    playNextTimeRef.current = 0
    setIsAISpeaking(false)
    setStatus('idle')
  }, [])

  const startSession = useCallback(async (brandId: string) => {
    if (status !== 'idle' && status !== 'error') return

    setError(null)
    setStatus('connecting')

    // 1. Request microphone access
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
    } catch (err: any) {
      const msg = err.name === 'NotAllowedError'
        ? 'Microphone permission denied. Please allow microphone access and try again.'
        : `Microphone error: ${err.message}`
      setError(msg)
      setStatus('error')
      return
    }
    streamRef.current = stream

    // 2. Capture AudioContext at 16kHz (Gemini input)
    const captureCtx = new AudioContext({ sampleRate: 16000 })
    captureCtxRef.current = captureCtx

    // 3. Playback AudioContext at 24kHz (Gemini audio output rate)
    const playbackCtx = new AudioContext({ sampleRate: 24000 })
    playbackCtxRef.current = playbackCtx
    playNextTimeRef.current = playbackCtx.currentTime

    // 4. Open WebSocket to backend
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${proto}://${window.location.host}/api/brands/${brandId}/voice-coaching`
    const ws = new WebSocket(wsUrl)
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws

    ws.onerror = () => {
      setError('Connection failed. Check that the backend is running.')
      setStatus('error')
      stopSession()
    }

    ws.onclose = (evt) => {
      // Only treat as error if we were still active (not a user-initiated close)
      if (wsRef.current !== null) {
        setStatus('idle')
      }
    }

    ws.onmessage = async (event) => {
      if (event.data instanceof ArrayBuffer) {
        // Binary = PCM audio from Gemini (24kHz, 16-bit mono)
        schedulePCMChunk(event.data, playbackCtx, playNextTimeRef)

        // Track AI speaking state: consider AI silent 500ms after last audio chunk
        setIsAISpeaking(true)
        if (aiSpeakingTimerRef.current) clearTimeout(aiSpeakingTimerRef.current)
        aiSpeakingTimerRef.current = setTimeout(() => setIsAISpeaking(false), 500)
      } else {
        try {
          const msg = JSON.parse(event.data as string)
          if (msg.type === 'connected') {
            setStatus('active')
            await startMicCapture(captureCtx, stream, ws, workletNodeRef)
          } else if (msg.type === 'error') {
            setError(msg.message || 'Voice session error')
            setStatus('error')
            stopSession()
          }
          // 'transcript' messages are available for future UI display
        } catch {
          // ignore malformed control messages
        }
      }
    }
  }, [status, stopSession])

  return { status, isAISpeaking, error, startSession, stopSession }
}

// ── Audio helpers ──────────────────────────────────────────────────────────

async function startMicCapture(
  ctx: AudioContext,
  stream: MediaStream,
  ws: WebSocket,
  workletNodeRef: MutableRefObject<AudioWorkletNode | null>,
) {
  const blob = new Blob([WORKLET_SRC], { type: 'application/javascript' })
  const blobUrl = URL.createObjectURL(blob)

  try {
    await ctx.audioWorklet.addModule(blobUrl)
  } finally {
    URL.revokeObjectURL(blobUrl)
  }

  const source = ctx.createMediaStreamSource(stream)
  const worklet = new AudioWorkletNode(ctx, 'pcm-processor')
  workletNodeRef.current = worklet

  worklet.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(e.data)
    }
  }

  // Connect source → worklet (do NOT connect worklet to destination; we don't want mic playback)
  source.connect(worklet)
}

function schedulePCMChunk(
  buffer: ArrayBuffer,
  ctx: AudioContext,
  nextTimeRef: MutableRefObject<number>,
) {
  const int16 = new Int16Array(buffer)
  if (int16.length === 0) return

  const float32 = new Float32Array(int16.length)
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 32768
  }

  const audioBuffer = ctx.createBuffer(1, float32.length, ctx.sampleRate)
  audioBuffer.getChannelData(0).set(float32)

  const source = ctx.createBufferSource()
  source.buffer = audioBuffer
  source.connect(ctx.destination)

  // Queue-schedule to prevent gaps; reset if we've fallen too far behind
  const now = ctx.currentTime
  if (nextTimeRef.current < now) {
    nextTimeRef.current = now + 0.05  // small jitter buffer
  }
  source.start(nextTimeRef.current)
  nextTimeRef.current += audioBuffer.duration
}
