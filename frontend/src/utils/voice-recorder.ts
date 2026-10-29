// 浏览器录音 → 16kHz 单声道 WAV
// 不依赖 MediaRecorder 格式差异（Chrome=webm / Safari=mp4a 服务器不好统一处理），
// 直接 AudioContext 采 PCM 自己编码 WAV，全平台输出一致，后端 ASR 只吃一种格式。
// 注意：getUserMedia 需要安全上下文（HTTPS 或 localhost）。

export function isRecordingSupported(): boolean {
  return (
    (window.isSecureContext || location.hostname === 'localhost' || location.hostname === '127.0.0.1') &&
    !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) &&
    !!(window.AudioContext || (window as any).webkitAudioContext)
  )
}

const TARGET_RATE = 16000

export class VoiceRecorder {
  private ctx: AudioContext | null = null
  private stream: MediaStream | null = null
  private node: ScriptProcessorNode | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private chunks: Float32Array[] = []
  private chunkLen = 0
  private _running = false

  get running() {
    return this._running
  }

  async start(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const AC = window.AudioContext || (window as any).webkitAudioContext
    this.ctx = new AC()
    if (this.ctx.state === 'suspended') await this.ctx.resume()
    this.source = this.ctx.createMediaStreamSource(this.stream)
    // ScriptProcessor 兼容性最好（AudioWorklet 在老 Safari 上麻烦），单线程量级足够
    this.node = this.ctx.createScriptProcessor(4096, 1, 1)
    this.chunks = []
    this.chunkLen = 0
    const inRate = this.ctx.sampleRate
    const step = inRate / TARGET_RATE
    let idx = 0 // 全局源采样下标（浮点，跨缓冲连续）
    let totalSrc = 0 // 已收到的源采样总数
    this.node.onaudioprocess = (e: AudioProcessingEvent) => {
      const input = e.inputBuffer.getChannelData(0)
      const base = totalSrc
      totalSrc += input.length
      const n = Math.max(0, Math.ceil((totalSrc - idx) / step))
      const out = new Float32Array(n)
      for (let i = 0; i < n; i++) {
        const src = Math.floor(idx + i * step)
        // 末帧可能超出当前缓冲，钳到最后一个有效采样
        out[i] = input[Math.min(src - base, input.length - 1)]
      }
      idx += n * step
      this.chunks.push(out)
      this.chunkLen += out.length
    }
    this.source.connect(this.node)
    this.node.connect(this.ctx.destination)
    this._running = true
  }

  // 停止并返回 WAV Blob（约 32KB/秒 @16k 16bit）
  async stop(): Promise<Blob> {
    if (!this._running) throw new Error('未在录音')
    this._running = false
    if (this.node) {
      this.node.onaudioprocess = null
      this.node.disconnect()
    }
    if (this.source) this.source.disconnect()
    // PCM 已按 TARGET_RATE 降采样,头必须写 TARGET_RATE;
    // 曾误写 ctx.sampleRate(48k)导致音频被按3倍速解读、ASR转写全乱(2026-10-13 修复)
    const rate = TARGET_RATE
    if (this.ctx) await this.ctx.close()
    if (this.stream) this.stream.getTracks().forEach((t) => t.stop())
    this.stream = null
    this.node = null
    this.source = null
    this.ctx = null
    const pcm = new Int16Array(this.chunkLen)
    let off = 0
    for (const c of this.chunks) {
      for (let i = 0; i < c.length; i++) {
        let s = c[i]
        s = Math.max(-1, Math.min(1, s))
        pcm[off++] = s < 0 ? s * 0x8000 : s * 0x7fff
      }
    }
    this.chunks = []
    this.chunkLen = 0
    return this.encodeWav(pcm, rate)
  }

  cancel(): void {
    // 丢弃当前录音（重新录时使用），不返回数据
    try {
      if (this.node) this.node.onaudioprocess = null
      if (this.stream) this.stream.getTracks().forEach((t) => t.stop())
      if (this.ctx) this.ctx.close().catch(() => {})
    } catch {
      /* ignore */
    }
    this._running = false
    this.chunks = []
    this.chunkLen = 0
    this.stream = null
    this.node = null
    this.source = null
    this.ctx = null
  }

  private encodeWav(pcm: Int16Array, sampleRate: number): Blob {
    const dataLen = pcm.length * 2
    const buf = new ArrayBuffer(44 + dataLen)
    const view = new DataView(buf)
    const wstr = (o: number, s: string) => {
      for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i))
    }
    wstr(0, 'RIFF')
    view.setUint32(4, 36 + dataLen, true)
    wstr(8, 'WAVE')
    wstr(12, 'fmt ')
    view.setUint32(16, 16, true)
    view.setUint16(20, 1, true) // PCM
    view.setUint16(22, 1, true) // mono
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, sampleRate * 2, true)
    view.setUint16(32, 2, true)
    view.setUint16(34, 16, true)
    wstr(36, 'data')
    view.setUint32(40, dataLen, true)
    for (let i = 0; i < pcm.length; i++) view.setInt16(44 + i * 2, pcm[i], true)
    return new Blob([buf], { type: 'audio/wav' })
  }
}
