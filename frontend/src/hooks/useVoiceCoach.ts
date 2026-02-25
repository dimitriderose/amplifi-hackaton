import { useState, useRef, useCallback, MutableRefObject } from 'react'

export type VoiceCoachStatus = 'idle' | 'connecting' | 'active' | 'error'

interface UseVoiceCoachResult {
  status: VoiceCoachStatus
  isAISpeaking: boolean
  transcript: string | null
  error: string | null
  startSession: (brandId: string) => Promise<void>
  stopSession: () => void
}

// AudioWorklet processor — inlined as a blob; no separate file needed.
// Uses the global `sampleRate` (AudioContext's actual rate) to downsample to 16kHz,
// so the resampling works correctly regardless of the OS audio device rate.
const WORKLET_SRC = `
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    // sampleRate is a global in AudioWorkletGlobalScope = AudioContext.sampleRate
    this._ratio = sampleRate / 16000
    this._phase = 0
  }
  process(inputs) {
    const channel = inputs[0]?.[0]
    if (!channel || channel.length === 0) return true

    const ratio = this._ratio
    const outputLength = Math.floor((channel.length - this._phase) / ratio)
    if (outputLength <= 0) {
      this._phase -= channel.length
      return true
    }

    const pcm = new Int16Array(outputLength)
    for (let i = 0; i < outputLength; i++) {
      const srcIdx = this._phase + i * ratio
      const lo = Math.floor(srcIdx)
      const hi = Math.min(lo + 1, channel.length - 1)
      const frac = srcIdx - lo
      const sample = channel[lo] * (1 - frac) + channel[hi] * frac
      const s = Math.max(-1, Math.min(1, sample))
      pcm[i] = s < 0 ? s * 32768 : s * 32767
    }
    this._phase = (this._phase + outputLength * ratio) - channel.length
    this.port.postMessage(pcm.buffer, [pcm.buffer])
    return true
  }
}
registerProcessor('pcm-processor', PCMProcessor)
`

export function useVoiceCoach(): UseVoiceCoachResult {
  const [status, setStatus] = useState<VoiceCoachStatus>('idle')
  const [isAISpeaking, setIsAISpeaking] = useState(false)
  const [transcript, setTranscript] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const captureCtxRef = useRef<AudioContext | null>(null)
  const playbackCtxRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const playNextTimeRef = useRef<number>(0)
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null)  // CRIT-5
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const aiSpeakingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // CRIT-4: synchronous guard to prevent double-tap launching two sessions
  const isStartingRef = useRef(false)

  const stopSession = useCallback(() => {
    // Null out the WS ref first so the onclose handler knows this is user-initiated
    const ws = wsRef.current
    wsRef.current = null
    if (ws) ws.close()

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    // CRIT-5: disconnect source node explicitly so mic indicator clears immediately
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect()
      sourceNodeRef.current = null
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
    isStartingRef.current = false
    setIsAISpeaking(false)
    setTranscript(null)
    setStatus('idle')
  }, [])

  const startSession = useCallback(async (brandId: string) => {
    // CRIT-4: use a ref guard (not state) to prevent double-tap races
    if (isStartingRef.current) return
    if (status !== 'idle' && status !== 'error') return
    isStartingRef.current = true

    setError(null)
    setTranscript(null)
    setStatus('connecting')

    // 1. Request microphone — do NOT constrain sampleRate (MINOR-4:
    //    getUserMedia sampleRate is advisory and misleading; AudioContext handles resampling)
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
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
      isStartingRef.current = false
      return
    }
    streamRef.current = stream

    // 2. Capture AudioContext at native device rate — worklet resamples to 16kHz
    const captureCtx = new AudioContext()
    captureCtxRef.current = captureCtx

    // 3. Playback AudioContext at 24kHz (Gemini Live output rate)
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
      // stopSession first (resets to idle), then override with error state.
      // React 18 batching ensures the last setStatus wins.
      stopSession()
      setError('Connection failed. Check that the backend is running.')
      setStatus('error')
    }

    // MINOR-3: unexpected server-side close must clean up fully via stopSession
    ws.onclose = () => {
      if (wsRef.current !== null) {
        // wsRef is still set → this was NOT user-initiated → clean up everything
        stopSession()
        setError('Session ended unexpectedly.')
        setStatus('error')
      }
      // If wsRef is null, stopSession() already ran (user clicked Stop)
    }

    ws.onmessage = async (event) => {
      if (event.data instanceof ArrayBuffer) {
        // Binary PCM audio from Gemini (24kHz, 16-bit mono)
        // MINOR-1: guard against playback after context has been closed
        const pCtx = playbackCtxRef.current
        if (pCtx && pCtx.state !== 'closed') {
          schedulePCMChunk(event.data, pCtx, playNextTimeRef)
        }

        // PM-CRIT-1: 1200ms debounce (was 500ms) to prevent orb flicker mid-sentence
        setIsAISpeaking(true)
        if (aiSpeakingTimerRef.current) clearTimeout(aiSpeakingTimerRef.current)
        aiSpeakingTimerRef.current = setTimeout(() => setIsAISpeaking(false), 1200)
      } else {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'connected') {
            setStatus('active')
            // CRIT-3: catch startMicCapture failures so the session surfaces an error
            try {
              await startMicCapture(captureCtx, stream, ws, workletNodeRef, sourceNodeRef)
            } catch (err: any) {
              setError(`Microphone setup failed: ${err.message}`)
              setStatus('error')
              stopSession()
            }
          } else if (msg.type === 'turn_complete') {
            // MINOR-2: backend now forwards turn_complete; clear speaking immediately
            if (aiSpeakingTimerRef.current) clearTimeout(aiSpeakingTimerRef.current)
            setIsAISpeaking(false)
          } else if (msg.type === 'transcript') {
            setTranscript(msg.text ?? null)
          } else if (msg.type === 'error') {
            setError(msg.message || 'Voice session error')
            setStatus('error')
            stopSession()
          }
        } catch {
          // ignore malformed control messages
        }
      }
    }
  }, [status, stopSession])

  return { status, isAISpeaking, transcript, error, startSession, stopSession }
}

// ── Audio helpers ──────────────────────────────────────────────────────────

async function startMicCapture(
  ctx: AudioContext,
  stream: MediaStream,
  ws: WebSocket,
  workletNodeRef: MutableRefObject<AudioWorkletNode | null>,
  sourceNodeRef: MutableRefObject<MediaStreamAudioSourceNode | null>,  // CRIT-5
) {
  const blob = new Blob([WORKLET_SRC], { type: 'application/javascript' })
  const blobUrl = URL.createObjectURL(blob)

  try {
    await ctx.audioWorklet.addModule(blobUrl)
  } finally {
    URL.revokeObjectURL(blobUrl)
  }

  const source = ctx.createMediaStreamSource(stream)
  sourceNodeRef.current = source  // CRIT-5: store so stopSession can disconnect it

  const worklet = new AudioWorkletNode(ctx, 'pcm-processor')
  workletNodeRef.current = worklet

  worklet.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(e.data)
    }
  }

  // Connect: source → worklet only (NOT to destination — prevents mic feedback)
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
