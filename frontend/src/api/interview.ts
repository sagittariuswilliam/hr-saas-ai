import axios from 'axios'
import { request } from '@/utils/request'
import { API_BASE } from '@/utils/api-base'
import type { ApiResponse } from './auth'

// ==================== 类型 ====================

export interface InterviewQuestion {
  index: number
  type: string
  text: string
  rubric: string[]
  weak_answer_hint?: string
  min_words: number
}

export interface InterviewSession {
  id: number
  resume_id: number
  position_id: number | null
  token: string | null
  status: 'draft' | 'sent' | 'in_progress' | 'submitted' | 'report_ready' | 'expired'
  questions_json: InterviewQuestion[] | null
  created_by: number
  sent_at: string | null
  expires_at: string | null
  submitted_at: string | null
  created_at: string | null
  total_questions?: number
  answered_count?: number
}

export interface SendResult {
  token: string
  link: string
  script: string
}

export interface ReportPerQuestion {
  index: number
  score: number
  max_score: number
  comment?: string
}

export interface InterviewReport {
  session_id: number
  resume_id: number
  position_id: number | null
  total_score: number
  verdict: 'recommend' | 'pending' | 'reject'
  per_question: ReportPerQuestion[]
  highlights: string[]
  concerns: string[]
  paste_warnings: string[]
  hr_followup: string[]
  generated_at: string | null
  // VR-12 原声试听：下标 = 题号-1
  voice_urls?: (string | null)[]
  voice_available?: boolean[]
}

// 候选人公开接口返回
export interface CandidateQuestionItem {
  index: number
  type?: string
  text?: string
  min_words?: number
  status: 'answered' | 'current' | 'locked'
  answer_text?: string | null
  followup_question?: string | null
  followup_answer?: string | null
}

export interface CandidateView {
  status: string
  readonly: boolean
  expires_at: string | null
  voice_consent_at: string | null
  questions: CandidateQuestionItem[]
}

// ==================== HR 侧接口（JWT） ====================

// 创建会话（LLM 出题实测可达 60-70s，超时留足余量）
export const createInterviewSessionApi = (resume_id: number) => {
  return request.post<ApiResponse<InterviewSession>>(
    '/interview/sessions',
    { resume_id },
    { timeout: 120000 }
  )
}

// HR 审定题目（仅 draft 可改）
export const updateInterviewQuestionsApi = (sessionId: number, questions: InterviewQuestion[]) => {
  return request.put<ApiResponse<InterviewSession>>(
    `/interview/sessions/${sessionId}/questions`,
    { questions }
  )
}

// 发送链接（生成 token + 话术）
export const sendInterviewSessionApi = (sessionId: number) => {
  return request.post<ApiResponse<SendResult>>(`/interview/sessions/${sessionId}/send`)
}

// 某候选人的会话列表
export const getInterviewSessionsApi = (resumeId: number) => {
  return request.get<ApiResponse<InterviewSession[]>>(`/interview/resumes/${resumeId}/sessions`)
}

export interface InterviewSummaryItem {
  session_id: number
  status: string
  total_score: number | null
}

// 批量面试摘要（简历列表 badge）
export const getInterviewSummaryApi = (resumeIds: number[]) => {
  return request.get<ApiResponse<Record<string, InterviewSummaryItem>>>(
    '/interview/resumes/summary',
    { params: { resume_ids: resumeIds.join(',') } }
  )
}

// 面试报告（未交卷 404）
export const getInterviewReportApi = (sessionId: number) => {
  return request.get<ApiResponse<InterviewReport>>(`/interview/sessions/${sessionId}/report`)
}

// VR-12 HR 试听原声：blob 拉取（共享实例拦截器按 JSON code 判断，对 blob 会误报，故裸 axios + 手动带 token）
export const fetchSessionVoiceBlobApi = async (sessionId: number, qIndex: number): Promise<Blob> => {
  const tk = localStorage.getItem('token') || ''
  const res = await axios.get(`${API_BASE}/interview/sessions/${sessionId}/voice/${qIndex}`, {
    headers: tk ? { Authorization: `Bearer ${tk}` } : {},
    responseType: 'blob',
    timeout: 60000,
  })
  return res.data as Blob
}

// ==================== 候选人公开接口（凭 token，无鉴权） ====================

export const candidateFetchApi = (token: string) => {
  return request.get<ApiResponse<CandidateView>>(`/interview/i/${token}`)
}

export const candidateAnswerApi = (
  token: string,
  payload: {
    question_index: number
    answer_text: string
    elapsed_seconds?: number
    paste_detected?: boolean
    followup_answer?: string
    voice_url?: string
  }
) => {
  return request.post<ApiResponse<{
    question_index: number
    followup_question: string | null
    has_followup_answer: boolean
  }>>(`/interview/i/${token}/answer`, payload)
}

// VR-02 语音作答单独同意（首次授权弹窗"同意并录音"后调用；服务端落 voice_consent_at，
// 未同意时 transcribe-voice 会 403）。走共享实例（JSON body，无 FormData）
export const candidateVoiceConsentApi = (token: string) => {
  return request.post<ApiResponse<{ voice_consent_at: string }>>(
    `/interview/i/${token}/voice-consent`
  )
}

// 两步式语音作答第 1 步：上传录音 → 服务端转写 → 返回文本（不落答案库，候选人确认后走 answer 提交）
// 与 resume.ts uploadBatchApi 同模式：FormData 必须裸 axios，
// 共享实例默认头是 application/json，axios 1.x 会把 FormData 序列化成 "{}"（字段全丢）
export const candidateTranscribeVoiceApi = async (
  token: string,
  questionIndex: number,
  wavBlob: Blob
): Promise<{
    question_index: number
    transcription_ok: boolean
    transcript: string | null
    voice_url: string
  }> => {
  const fd = new FormData()
  fd.append('question_index', String(questionIndex))
  fd.append('file', wavBlob, 'answer.wav')
  const baseURL = API_BASE
  const res = await axios.post(`${baseURL}/interview/i/${token}/transcribe-voice`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  const body = res.data
  if (body && body.code !== 0 && body.code !== 200) {
    throw new Error(body.message || '转写请求失败')
  }
  return body.data
}

export const candidateSubmitApi = (token: string) => {
  return request.post<ApiResponse<null>>(`/interview/i/${token}/submit`)
}

// ==================== 工具 ====================

// 后端 link 是相对路径（/interview/i/<token>），前端公开路由是 /i/:token，
// hash 模式下统一拼成 /#/i/<token>（直接用后端 link 会命中兜底路由被弹回登录页）
export const buildCandidateUrl = (link: string, token: string): string => {
  const base = `${location.origin}${location.pathname}`.replace(/\/$/, '')
  const t = token || (link && link.split('/').pop()) || ''
  return `${base}/#/i/${t}`
}

// 复制文本（clipboard API + execCommand 兜底）
export const copyTextToClipboard = async (text: string): Promise<boolean> => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    /* 走兜底 */
  }
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}
