<template>
  <el-drawer
    :model-value="modelValue"
    :title="`AI 面试 · ${resume.candidate_name || '候选人'}`"
    size="720px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
    @open="loadSessions"
  >
    <div class="iv-root" v-loading="generating" :element-loading-text="loadingText">
      <!-- 当前会话进度步进条（取最新一条） -->
      <div class="iv-panel" v-if="latest">
        <div class="iv-panel-title">面试进度</div>
        <div class="iv-stepper">
          <template v-for="(s, i) in steps" :key="s.key">
            <div class="iv-step" :class="stepClass(s.key)">
              <span class="iv-step-dot">{{ stepDone(s.key) ? '✓' : i + 1 }}</span>
              <span>{{ s.label }}</span>
            </div>
            <span v-if="i < steps.length - 1" class="iv-step-bar" :class="{ done: stepDone(steps[i + 1].key) }"></span>
          </template>
        </div>
      </div>

      <!-- 会话列表 -->
      <div class="iv-panel">
        <div class="iv-panel-head">
          <span class="iv-panel-title">面试会话</span>
          <el-button type="primary" size="small" :loading="generating" @click="startSession">
            ✦ 发起 AI 面试
          </el-button>
        </div>
        <el-table :data="sessions" size="small" v-loading="listLoading" empty-text="暂无面试会话，点右上角发起 AI 面试">
          <el-table-column label="会话" width="70">
            <template #default="{ row }">#{{ row.id }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small" effect="light">{{ statusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="专属链接" min-width="150">
            <template #default="{ row }">
              <span class="iv-token" v-if="row.token">/i/{{ row.token }}</span>
              <span class="iv-muted" v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="有效期" width="120">
            <template #default="{ row }">{{ expiryText(row) }}</template>
          </el-table-column>
          <el-table-column label="作答进度" width="110">
            <template #default="{ row }">
              <span v-if="row.status === 'draft' || row.status === 'expired' || !row.total_questions">—</span>
              <span v-else>已答 {{ row.answered_count }}/{{ row.total_questions }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'draft'" link type="primary" size="small" @click="openReview(row)">审定题目</el-button>
              <el-button v-if="canCopyLink(row)" link type="primary" size="small" @click="copyLink(row)">复制链接</el-button>
              <el-button v-if="row.status === 'report_ready'" link type="success" size="small" @click="openReport(row)">查看报告</el-button>
              <span v-if="row.status === 'expired' || (row.status === 'draft' && !canCopyLink(row))" class="iv-muted" style="font-size:12px">已失效</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 报告入口 -->
      <div class="iv-panel iv-report-entry" v-if="latest && !hasReport">
        <div class="iv-panel-title">面试报告</div>
        <div class="iv-empty">
          <div class="iv-empty-ic">📄</div>
          <div>
            {{ latest.status === 'draft' ? '链接尚未发送，发送并等候选人交卷后自动生成报告' : '候选人尚未交卷，交卷后 AI 自动生成报告（约 30 秒）' }}
            <div class="iv-empty-sub">报告仅 HR 可见，不对候选人展示</div>
          </div>
        </div>
      </div>
      <div class="iv-panel iv-report-entry" v-else-if="hasReport">
        <div class="iv-panel-head">
          <span class="iv-panel-title">面试报告</span>
          <el-button type="success" size="small" plain @click="openReport(reportReadySession)">查看面试报告 →</el-button>
        </div>
      </div>
    </div>

    <QuestionsReviewDialog v-model="reviewVisible" :session="reviewSession" :resume="resume" @saved="onQuestionsSaved" @sent="onSessionSent" />
    <ScriptDialog v-model="scriptVisible" :script-data="scriptData" />
    <ReportDialog v-model="reportVisible" :session="reportSession" :resume-name="resume?.candidate_name || ''" />
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createInterviewSessionApi,
  getInterviewSessionsApi,
  buildCandidateUrl,
  copyTextToClipboard,
  type InterviewSession,
  type SendResult
} from '@/api/interview'
import QuestionsReviewDialog from './QuestionsReviewDialog.vue'
import ScriptDialog from './ScriptDialog.vue'
import ReportDialog from './ReportDialog.vue'

const props = defineProps<{
  modelValue: boolean
  resume: any
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const sessions = ref<InterviewSession[]>([])
const listLoading = ref(false)
const generating = ref(false)
const loadingText = ref('AI 出题中，约需 10-30 秒…')

const reviewVisible = ref(false)
const reviewSession = ref<InterviewSession | null>(null)
const scriptVisible = ref(false)
const scriptData = ref<SendResult | null>(null)
const reportVisible = ref(false)
const reportSession = ref<InterviewSession | null>(null)

const latest = computed(() => sessions.value[0] || null)
const hasReport = computed(() => sessions.value.some((s) => s.status === 'report_ready'))
const reportReadySession = computed(
  () => sessions.value.find((s) => s.status === 'report_ready') || null
)

const steps = [
  { key: 'draft', label: '草稿 · 待审定' },
  { key: 'sent', label: '链接已发送' },
  { key: 'in_progress', label: '候选人作答中' },
  { key: 'submitted', label: '已交卷' },
  { key: 'report_ready', label: '报告已生成' },
]
const order = ['draft', 'sent', 'in_progress', 'submitted', 'report_ready']

function stepIdx() {
  if (!latest.value) return -1
  if (latest.value.status === 'expired') {
    // 过期停留在它到达过的阶段（token 有则算已发送）
    return latest.value.token ? 1 : 0
  }
  return order.indexOf(latest.value.status)
}
function stepDone(key: string) {
  const cur = stepIdx()
  return cur >= 0 && order.indexOf(key) < cur
}
function stepClass(key: string) {
  const cur = stepIdx()
  if (cur < 0) return ''
  if (order[key as number | string] === undefined) return ''
  const i = order.indexOf(key)
  if (i < cur) return 'done'
  if (i === cur) return 'cur' + (latest.value?.status === 'expired' ? ' expired' : '')
  return ''
}

function statusText(s: string) {
  return ({ draft: '草稿', sent: '已发送', in_progress: '进行中', submitted: '已交卷', report_ready: '报告已生成', expired: '已失效' } as Record<string, string>)[s] || s
}
function statusTagType(s: string) {
  return ({ draft: 'info', sent: 'primary', in_progress: 'warning', submitted: 'warning', report_ready: 'success', expired: 'danger' } as Record<string, any>)[s] || 'info'
}
function expiryText(row: InterviewSession) {
  if (!row.expires_at) return '—'
  const left = (new Date(row.expires_at).getTime() - Date.now()) / 3600000
  if (row.status === 'expired' || left <= 0) return '已过期'
  return `剩余 ${Math.max(1, Math.floor(left))} 小时`
}
function canCopyLink(row: InterviewSession) {
  return !!row.token && ['sent', 'in_progress'].includes(row.status)
}

async function loadSessions() {
  if (!props.resume?.id) return
  listLoading.value = true
  try {
    const res = await getInterviewSessionsApi(props.resume.id)
    sessions.value = res.data || []
  } catch (e) {
    console.error('加载面试会话失败:', e)
  } finally {
    listLoading.value = false
  }
}

// 打开抽屉且 resume 就绪时加载（@open 时机过早会漏加载，watch 兜底）
watch(() => [props.modelValue, props.resume?.id] as const, ([open, rid], [wasOpen]) => {
  if (open && rid && !(wasOpen && rid)) loadSessions()
}, { immediate: true })

async function startSession() {
  if (!props.resume?.position_id) {
    ElMessage.warning('该简历尚未匹配职位，无法 AI 出题，请先在简历中关联职位')
    return
  }
  generating.value = true
  loadingText.value = 'AI 出题中，约需 10-30 秒，请稍候…'
  try {
    const res = await createInterviewSessionApi(props.resume.id)
    sessions.value.unshift(res.data)
    ElMessage.success('AI 已生成初稿题目，请审定后发送')
    openReview(res.data)
  } catch (e) {
    console.error('创建面试会话失败:', e)
  } finally {
    generating.value = false
  }
}

function openReview(row: InterviewSession) {
  reviewSession.value = row
  reviewVisible.value = true
}

function onQuestionsSaved(session: InterviewSession) {
  const idx = sessions.value.findIndex((s) => s.id === session.id)
  if (idx >= 0) sessions.value[idx] = { ...sessions.value[idx], ...session }
}

function onSessionSent(result: SendResult) {
  scriptData.value = result
  reviewVisible.value = false
  scriptVisible.value = true
  loadSessions()
}

async function copyLink(row: InterviewSession) {
  const url = buildCandidateUrl(`/interview/i/${row.token}`, row.token || '')
  const ok = await copyTextToClipboard(url)
  ok ? ElMessage.success('候选人专属链接已复制') : ElMessage.error('复制失败，请手动复制')
}

function openReport(row: InterviewSession) {
  reportSession.value = row
  reportVisible.value = true
}
</script>

<style scoped>
.iv-root { padding: 0 2px 20px; }
.iv-panel { background: var(--paper, #fff); border: 1px solid var(--ink-100, #e2e8f0); border-radius: var(--radius-sm, 6px); padding: 14px 16px; margin-bottom: 14px; }
.iv-panel-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.iv-panel-title { font-size: 14px; font-weight: 600; color: var(--ink-900); display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.iv-panel-head .iv-panel-title { margin-bottom: 0; }
.iv-panel-title::before { content: ''; width: 3px; height: 14px; background: var(--brand-primary-500); border-radius: 2px; display: inline-block; }
.iv-muted { color: var(--ink-500); }
.iv-token { font-family: var(--font-mono); font-size: 12px; color: var(--brand-primary-500); }

/* stepper */
.iv-stepper { display: flex; align-items: center; flex-wrap: wrap; gap: 0; }
.iv-step { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--ink-500); }
.iv-step-dot { width: 22px; height: 22px; border-radius: 50%; border: 1.5px solid var(--ink-300); display: inline-flex; align-items: center; justify-content: center; font-size: 11.5px; background: #fff; flex-shrink: 0; }
.iv-step.done { color: var(--brand-primary-500); }
.iv-step.done .iv-step-dot { background: var(--brand-primary-500); border-color: var(--brand-primary-500); color: #fff; }
.iv-step.cur { color: var(--brand-primary-500); font-weight: 500; }
.iv-step.cur .iv-step-dot { border-color: var(--brand-primary-500); color: var(--brand-primary-500); font-weight: 600; }
.iv-step.cur.expired { color: var(--danger-500); }
.iv-step.cur.expired .iv-step-dot { border-color: var(--danger-500); color: var(--danger-500); }
.iv-step-bar { width: 34px; height: 1.5px; background: var(--ink-300); margin: 0 8px; }
.iv-step-bar.done { background: var(--brand-primary-500); }

.iv-report-entry { border: 1px dashed var(--brand-primary-100); background: #fcfdfe; }
.iv-empty { display: flex; gap: 12px; align-items: flex-start; color: var(--ink-500); font-size: 13px; padding: 8px 0; }
.iv-empty-ic { font-size: 30px; opacity: 0.4; }
.iv-empty-sub { font-size: 12px; margin-top: 4px; }
</style>
