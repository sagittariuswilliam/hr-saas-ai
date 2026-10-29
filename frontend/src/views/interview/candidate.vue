<template>
  <div class="cand-page">
    <div class="cand-wrap">
      <!-- 顶栏 -->
      <div class="cand-top">
        <span>AI 初筛面试</span>
        <span class="cand-prog" v-if="total">{{ progText }}</span>
      </div>

      <div class="cand-voice">🎙 支持使用手机输入法语音输入，说完自动转文字</div>

      <!-- 主体 -->
      <div class="cand-body" ref="bodyRef" v-loading="initLoading">
        <template v-if="!initError">
          <!-- 开场白 -->
          <div class="bubble" v-if="items.length">
            <div class="avatar ai">AI</div>
            <div class="bub">
              你好，我是本次初筛的 AI 面试官。接下来共 {{ total }} 道题，约 15 分钟，你可以随时中断，进度会自动保存。
              <template v-if="expiresText"><br>链接 {{ expiresText }}内有效。</template>
            </div>
          </div>

          <!-- 气泡流 -->
          <div v-for="it in items" :key="it.key" class="bubble" :class="{ me: it.me }">
            <div class="avatar" :class="it.me ? 'me-a' : 'ai'">{{ it.me ? '我' : 'AI' }}</div>
            <div class="bub">
              <template v-if="it.kind === 'question'"><b>第 {{ it.index }} 题：</b></template>
              <template v-if="it.kind === 'followup'"><b>追问：</b><span class="fu-tag">追问 1/1</span></template>
              {{ it.text }}
            </div>
          </div>

          <!-- 交卷后只读 -->
          <div class="done-card" v-if="readonly">
            <div class="done-ic">✅</div>
            <div class="done-t">已完成，结果将由 HR 反馈</div>
            <div class="done-s">你的作答已提交成功，后续安排请以 HR 通知为准，感谢参与。</div>
          </div>

          <!-- 当前题作答区 -->
          <div class="compose" v-else-if="answering">
            <div class="compose-hint">
              <template v-if="phase === 'main' && answering.min_words">建议作答 ≥{{ answering.min_words }} 字 · 本题用时 {{ fmtDur(elapsed) }}</template>
              <template v-else>请补充回答上面的追问（1/1）</template>
            </div>
            <el-input
              v-model="draft"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 8 }"
              :placeholder="phase === 'main' ? '输入回答，或按住手机键盘麦克风说话…' : '补充回答追问…'"
              @paste="onPaste"
            />
            <div class="rec-bar" v-if="canRecord">
              <template v-if="!recording && !transcribing">
                <button class="rec-btn" @click="startRecording">🎤 语音作答</button>
                <span class="rec-tip">点击开始录音（单题最长 60 秒），说完自动转文字，可修改后发送</span>
              </template>
              <template v-else-if="recording">
                <button class="rec-btn recording" @click="stopRecording">
                  <span class="rec-dot"></span>录音中 {{ recSeconds }}s · 点击停止
                </button>
                <button class="rec-cancel" @click="cancelRecording">取消</button>
              </template>
              <template v-else>
                <span class="rec-transcribing">⏳ 转写中，请稍候…</span>
              </template>
            </div>
            <div class="compose-foot">
              <span class="paste-warn" v-if="pasteDetected">⚠ 检测到大段粘贴，将随答案留痕</span>
              <span class="voice-tag" v-if="pendingVoiceUrl">🎙 本题为语音作答转写</span>
              <el-button type="primary" :loading="submitting" :disabled="transcribing" @click="sendAnswer">
                {{ phase === 'followup' ? '回答追问' : (allAnswered ? '发送并交卷' : '发送') }}
              </el-button>
            </div>
          </div>
        </template>

        <div class="err-card" v-if="initError">
          <div class="err-ic">🔒</div>
          <div>{{ initError }}</div>
        </div>
      </div>

      <div class="cand-foot" v-if="!readonly && !initError && items.length">
        支持输入法语音输入 · 进度自动保存，可中途离开后再回来继续
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  candidateFetchApi,
  candidateAnswerApi,
  candidateSubmitApi,
  candidateTranscribeVoiceApi,
  candidateVoiceConsentApi,
  type CandidateQuestionItem
} from '@/api/interview'
import { VoiceRecorder, isRecordingSupported } from '@/utils/voice-recorder'

interface BubbleItem {
  key: string
  me: boolean
  kind: 'question' | 'answer' | 'followup' | 'followup_answer'
  index?: number
  text: string
}

const route = useRoute()
const token = String(route.params.token || '')

const initLoading = ref(true)
const initError = ref('')
const readonly = ref(false)
const submitting = ref(false)

const questions = ref<CandidateQuestionItem[]>([])
const items = ref<BubbleItem[]>([])
const draft = ref('')
const phase = ref<'main' | 'followup'>('main')
const pasteDetected = ref(false)
const elapsed = ref(0)
const expiresAt = ref<string | null>(null)
// VR-02 语音授权状态（load 时从后端取；未同意时首次点🎤弹授权，同意才录）
const voiceConsent = ref(false)
const bodyRef = ref<HTMLElement>()

let timer: number | undefined

// ---- 语音作答（两步式：录音→转写→候选人确认/修改→随 answer 提交 voice_url）----
const canRecord = isRecordingSupported()
const recorder = new VoiceRecorder()
const recording = ref(false)
const transcribing = ref(false)
const recSeconds = ref(0)
const pendingVoiceUrl = ref<string | null>(null)
let recTimer: number | undefined
const REC_MAX = 60

const total = computed(() => questions.value.length)
const current = computed(() => questions.value.find((q) => q.status === 'current') || null)
// 作答目标题：followup 阶段为带未答追问的题，否则为 current 题
const fuQuestion = ref<CandidateQuestionItem | null>(null)
const answering = computed(() => (phase.value === 'followup' ? fuQuestion.value : current.value))
const answeredCount = computed(() => questions.value.filter((q) => q.status === 'answered').length)
const allAnswered = computed(() => total.value > 0 && answeredCount.value >= total.value)
const progText = computed(() => {
  if (readonly.value) return `已完成 · 共 ${total.value} 题`
  const idx = current.value?.index ?? total.value
  return `第 ${Math.min(idx, total.value)} / ${total.value} 题${expiresText.value ? ' · 剩余 ' + expiresText.value : ''}`
})
const expiresText = computed(() => {
  if (!expiresAt.value) return ''
  const left = (new Date(expiresAt.value).getTime() - Date.now()) / 3600000
  if (left <= 0) return ''
  if (left >= 24) return `${Math.floor(left / 24)} 天 ${Math.floor(left % 24)} 小时`
  return `${Math.max(1, Math.floor(left))} 小时`
})

function fmtDur(s: number) {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return m > 0 ? `${m} 分 ${String(sec).padStart(2, '0')} 秒` : `${sec} 秒`
}

function startTimer() {
  stopTimer()
  timer = window.setInterval(() => (elapsed.value += 1), 1000)
}
function stopTimer() {
  if (timer) window.clearInterval(timer)
  timer = undefined
}

function scrollToBottom() {
  nextTick(() => {
    if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  })
}

function pushAnswerBubbles(q: CandidateQuestionItem) {
  if (q.answer_text) {
    items.value.push({ key: `a${q.index}`, me: true, kind: 'answer', text: q.answer_text })
  }
  if (q.followup_question) {
    items.value.push({ key: `fq${q.index}`, me: false, kind: 'followup', text: q.followup_question })
  }
  if (q.followup_answer) {
    items.value.push({ key: `fa${q.index}`, me: true, kind: 'followup_answer', text: q.followup_answer })
  }
}

async function load() {
  try {
    const res = await candidateFetchApi(token)
    const data = res.data
    questions.value = data.questions || []
    readonly.value = !!data.readonly || data.status === 'submitted' || data.status === 'report_ready'
    expiresAt.value = data.expires_at
    voiceConsent.value = !!data.voice_consent_at

    // 重建气泡流
    items.value = []
    for (const q of questions.value) {
      if (q.status === 'locked') continue
      if (q.text) items.value.push({ key: `q${q.index}`, me: false, kind: 'question', index: q.index, text: q.text })
      if (q.status === 'answered') pushAnswerBubbles(q)
    }

    if (readonly.value) return

    // 恢复当前题状态
    const cur = questions.value.find((q) => q.status === 'current')
    if (cur) {
      // 服务端逐题放出：current 题若已带 followup_question 且无 followup_answer → 处于追问阶段
      if (cur.followup_question && !cur.followup_answer) {
        phase.value = 'followup'
        fuQuestion.value = cur
      } else {
        phase.value = 'main'
        fuQuestion.value = null
      }
      draft.value = ''
      elapsed.value = 0
      pasteDetected.value = false
      startTimer()
    } else {
      // 断点恢复：后端把「已答主答案但追问未答」的题标为 answered 且无 current 放出，
      // 此处找回该题进入追问阶段，避免续答时没有输入框
      const pendingFu = [...questions.value].reverse().find(
        (q) => q.status === 'answered' && q.followup_question && !q.followup_answer
      )
      if (pendingFu) {
        pendingFu.status = 'current'
        phase.value = 'followup'
        fuQuestion.value = pendingFu
        draft.value = ''
        elapsed.value = 0
        pasteDetected.value = false
        startTimer()
      }
    }
    scrollToBottom()
  } catch (e: any) {
    const status = e?.response?.status
    if (status === 410) initError.value = '该面试链接已过期（72 小时有效），请联系 HR 重新发送'
    else if (status === 404) initError.value = '链接无效，请联系 HR 确认'
    else initError.value = '加载失败，请刷新页面重试'
  } finally {
    initLoading.value = false
    scrollToBottom()
  }
}

function onPaste(e: ClipboardEvent) {
  const text = e.clipboardData?.getData('text') || ''
  if (text.length > 500) {
    pasteDetected.value = true
  }
}

function stopRecTimer() {
  if (recTimer) window.clearInterval(recTimer)
  recTimer = undefined
}

async function startRecording() {
  if (transcribing.value) return
  const cur = answering.value
  if (!cur) return
  // VR-02 合规门槛：首次使用语音作答前必须单独同意（三要素授权弹窗），拒绝则只能打字
  if (!voiceConsent.value) {
    try {
      await ElMessageBox.confirm(
        '使用语音作答前，请阅读并确认以下说明：\n\n' +
        '1. 您的录音仅用于转成本次面试的文字答案，转写文本经您本人确认后才提交；\n' +
        '2. 录音与转写内容不会用于任何模型训练，也不会向第三方提供；\n' +
        '3. 原声保留 30 天后自动删除，您可以随时拒绝语音作答，改用打字，不影响面试评估。\n\n' +
        '点击"同意并开始录音"即表示您单独授权本次面试使用语音作答。',
        '语音作答授权',
        {
          confirmButtonText: '同意并开始录音',
          cancelButtonText: '不同意，改用打字',
          type: 'info',
          customClass: 'consent-box',
          dangerouslyUseHTMLString: false,
        }
      )
    } catch {
      ElMessage.info('未授权语音作答，您可以直接打字作答')
      return
    }
    try {
      await candidateVoiceConsentApi(token)
      voiceConsent.value = true
    } catch (e: any) {
      ElMessage.error('授权登记失败，请重试或改用打字作答')
      return
    }
  }
  try {
    await recorder.start()
    recording.value = true
    recSeconds.value = 0
    stopRecTimer()
    recTimer = window.setInterval(() => {
      recSeconds.value += 1
      if (recSeconds.value >= REC_MAX) stopRecording() // 到 60s 自动停
    }, 1000)
  } catch (e: any) {
    if (e && (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError')) {
      ElMessage.error('麦克风权限被拒绝，请在浏览器设置中允许录音，或改用输入法语音输入')
    } else {
      ElMessage.error('无法开始录音：' + (e?.message || '请检查麦克风'))
    }
  }
}

async function stopRecording() {
  if (!recording.value) return
  stopRecTimer()
  recording.value = false
  let blob: Blob
  try {
    blob = await recorder.stop()
  } catch (e: any) {
    ElMessage.error('录音失败，请重试')
    return
  }
  if (blob.size < 8000) {
    ElMessage.warning('录音太短（不足 0.3 秒），请重新录')
    return
  }
  const cur = answering.value
  if (!cur) return
  transcribing.value = true
  try {
    const data = await candidateTranscribeVoiceApi(token, cur.index, blob)
    if (data.transcription_ok && data.transcript) {
      pendingVoiceUrl.value = data.voice_url
      // 转写文本填入输入框，候选人可修改后发送
      draft.value = draft.value.trim() ? draft.value.trim() + '\n' + data.transcript : data.transcript
      ElMessage.success('转写完成，可修改文字后点击发送')
    } else {
      ElMessage.error('转写失败，可重试或直接输入文字作答')
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '转写服务暂时不可用，请重试或改用文字输入'
    ElMessage.error(msg)
  } finally {
    transcribing.value = false
    scrollToBottom()
  }
}

function cancelRecording() {
  stopRecTimer()
  recorder.cancel()
  recording.value = false
}

async function sendAnswer() {
  const cur = answering.value
  if (!cur) return
  const text = draft.value.trim()
  if (!text) return ElMessage.warning('请先输入回答')

  submitting.value = true
  try {
    if (phase.value === 'main') {
      const res = await candidateAnswerApi(token, {
        question_index: cur.index,
        answer_text: text,
        elapsed_seconds: elapsed.value,
        paste_detected: pasteDetected.value,
        voice_url: pendingVoiceUrl.value || undefined,
      })
      cur.status = 'answered'
      cur.answer_text = text
      items.value.push({ key: `a${cur.index}`, me: true, kind: 'answer', text })

      const fu = res.data?.followup_question
      if (fu) {
        // 进入追问阶段（题已 answered，输入框改挂到 fuQuestion 上）
        cur.followup_question = fu
        fuQuestion.value = cur
        items.value.push({ key: `fq${cur.index}`, me: false, kind: 'followup', text: fu })
        phase.value = 'followup'
        draft.value = ''
        pasteDetected.value = false
        elapsed.value = 0
        pendingVoiceUrl.value = null
        startTimer()
        scrollToBottom()
        return
      }
      afterQuestionDone()
    } else {
      await candidateAnswerApi(token, {
        question_index: cur.index,
        answer_text: cur.answer_text || text,
        followup_answer: text,
        voice_url: pendingVoiceUrl.value || undefined,
      })
      cur.followup_answer = text
      items.value.push({ key: `fa${cur.index}`, me: true, kind: 'followup_answer', text })
      phase.value = 'main'
      afterQuestionDone()
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '提交失败，请重试'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}

async function afterQuestionDone() {
  draft.value = ''
  pasteDetected.value = false
  elapsed.value = 0
  fuQuestion.value = null
  pendingVoiceUrl.value = null
  stopTimer()
  // locked 题在后端不泄露题干，本地 push 会是空题目；必须重新拉取让服务端放出带完整题干的 current 题
  await load()
  scrollToBottom()
  if (allAnswered.value) {
    ElMessageBox.confirm('全部题目已作答完成，是否现在交卷？交卷后不可再修改答案。', '作答完成', {
      confirmButtonText: '立即交卷',
      cancelButtonText: '再检查一下',
      type: 'success',
    })
      .then(doSubmit)
      .catch(() => {})
  }
}

async function doSubmit() {
  submitting.value = true
  try {
    await candidateSubmitApi(token)
    readonly.value = true
    stopTimer()
    ElMessage.success('交卷成功，感谢参与！')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '交卷失败，请重试'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}

onMounted(load)
onBeforeUnmount(() => {
  stopTimer()
  stopRecTimer()
  if (recording.value) recorder.cancel()
})
</script>

<style scoped>
.cand-page { min-height: 100vh; background: #f0f3f5; padding: 0; }
.cand-wrap {
  max-width: 560px;
  margin: 0 auto;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  box-shadow: 0 0 24px rgba(15, 76, 92, 0.08);
}
.cand-top {
  background: var(--brand-primary-500);
  color: #fff;
  padding: 13px 16px;
  font-size: 14.5px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 5;
}
.cand-prog { font-size: 12px; opacity: 0.85; }
.cand-voice { font-size: 12px; color: var(--ink-500); text-align: center; padding: 8px 12px; background: var(--brand-primary-50); }
.cand-body { flex: 1; padding: 16px 14px; background: #f7f9fa; overflow-y: auto; }

.bubble { display: flex; margin-bottom: 14px; gap: 8px; }
.bubble .avatar {
  width: 30px; height: 30px; border-radius: 50%;
  background: var(--brand-primary-500); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; flex-shrink: 0;
}
.bubble .bub {
  max-width: 78%; padding: 10px 13px;
  border-radius: 0 10px 10px 10px;
  background: #fff; font-size: 13.5px; line-height: 1.7;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  word-break: break-word; white-space: pre-wrap;
}
.bubble.me { flex-direction: row-reverse; }
.bubble.me .avatar { background: var(--brand-primary-300); }
.bubble.me .bub { border-radius: 10px 0 10px 10px; background: var(--brand-primary-100); }
.fu-tag { display: inline-block; font-size: 11px; background: #f0f2f5; color: var(--ink-500); border-radius: 3px; padding: 0 6px; margin-left: 6px; }

.compose { background: #fff; border-top: 1px solid var(--ink-100); padding: 10px 12px; position: sticky; bottom: 0; }
.compose-hint { font-size: 12px; color: var(--ink-500); margin-bottom: 6px; }
.compose-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.rec-bar { display: flex; align-items: center; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
.rec-btn {
  border: 1px solid #d5dbe1; background: #fff; color: var(--ink-700, #333);
  border-radius: 999px; padding: 6px 14px; font-size: 13px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 6px;
}
.rec-btn:hover { border-color: #4a90d9; color: #4a90d9; }
.rec-btn.recording { border-color: #e05c5c; color: #e05c5c; background: #fdf3f3; }
.rec-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #e05c5c;
  animation: rec-blink 1s infinite;
}
@keyframes rec-blink { 0%,100% { opacity: 1; } 50% { opacity: 0.25; } }
.rec-cancel { border: none; background: transparent; color: #999; font-size: 13px; cursor: pointer; }
.rec-tip { font-size: 12px; color: var(--ink-500, #777); }
.rec-transcribing { font-size: 13px; color: #4a90d9; }
.voice-tag { font-size: 12px; color: #4a90d9; }
.paste-warn { font-size: 12px; color: var(--warning-500); }

.done-card { text-align: center; padding: 34px 16px; background: #fff; border-radius: 8px; margin: 8px 4px; }
.done-ic { font-size: 36px; margin-bottom: 8px; }
.done-t { font-size: 16px; font-weight: 600; color: var(--brand-primary-500); margin-bottom: 6px; }
.done-s { font-size: 13px; color: var(--ink-500); }

.err-card { text-align: center; padding: 48px 16px; color: var(--ink-500); font-size: 14px; }
.err-ic { font-size: 36px; margin-bottom: 10px; opacity: 0.5; }

.cand-foot { font-size: 11.5px; color: var(--ink-500); text-align: center; padding: 8px 12px; background: #fff; border-top: 1px solid var(--ink-100); }

@media (max-width: 600px) {
  .cand-wrap { box-shadow: none; }
  .bubble .bub { max-width: 82%; }
}
</style>
