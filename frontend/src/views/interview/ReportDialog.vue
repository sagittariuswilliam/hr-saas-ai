<template>
  <el-dialog
    :model-value="modelValue"
    title="AI 初筛面试报告"
    width="720px"
    top="5vh"
    append-to-body
    @update:model-value="emit('update:modelValue', $event)"
    @open="load"
  >
    <div v-loading="loading" class="rp-root">
      <template v-if="report">
        <div class="rp-sub">
          候选人：{{ resumeName }} · 会话 #{{ session?.id }}
          <template v-if="session?.submitted_at"> · 交卷 {{ fmt(session.submitted_at) }}</template>
          <template v-if="report.generated_at"> · 报告生成 {{ fmt(report.generated_at) }}</template>
        </div>

        <!-- 总分 + verdict -->
        <div class="rp-panel">
          <div class="rp-hero">
            <div class="rp-big">{{ report.total_score }} <small>/ 100</small></div>
            <div class="rp-verdict" :class="verdictClass">{{ verdictText }}</div>
            <div class="rp-rules">档位规则：≥80 推荐进面 · 60–79 待定 · &lt;60 不推荐</div>
          </div>
          <div class="rp-bars">
            <div class="rp-bar-row" v-for="q in report.per_question" :key="q.index">
              <span class="rp-bar-name">Q{{ q.index }} {{ typeShort(q.index) }}</span>
              <div class="rp-bar-track">
                <div class="rp-bar-fill" :class="barClass(q)" :style="{ width: barPct(q) + '%' }"></div>
              </div>
              <span class="rp-bar-score">{{ q.score }}/{{ q.max_score }}</span>
            </div>
          </div>
        </div>

        <!-- 亮点 -->
        <div class="rp-panel" v-if="report.highlights?.length">
          <div class="rp-panel-title">亮点</div>
          <div class="rp-finding" v-for="(h, i) in report.highlights" :key="i">{{ h }}</div>
        </div>

        <!-- 存疑 + 粘贴警告 -->
        <div class="rp-panel" v-if="report.concerns?.length || report.paste_warnings?.length">
          <div class="rp-panel-title">存疑</div>
          <div class="rp-finding concern" v-for="(c, i) in report.concerns" :key="i">{{ c }}</div>
          <div class="rp-warn" v-for="(w, i) in report.paste_warnings" :key="'w' + i">⚠ 留痕标记：{{ w }}。不阻断评分，建议真人面请其口头复述。</div>
        </div>

        <!-- HR 追问清单 -->
        <div class="rp-panel" v-if="report.hr_followup?.length">
          <div class="rp-panel-title">建议 HR 真人面追问</div>
          <ol class="rp-followups">
            <li v-for="(f, i) in report.hr_followup" :key="i">{{ f }}</li>
          </ol>
        </div>

        <!-- 逐题回看 -->
        <div class="rp-panel">
          <div class="rp-panel-title">逐题作答回看</div>
          <el-table :data="reviewRows" size="small">
            <el-table-column label="题" width="52">
              <template #default="{ row }">Q{{ row.index }}</template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="92" />
            <el-table-column label="题干" min-width="220">
              <template #default="{ row }">
                <el-popover trigger="click" placement="right" :width="360">
                  <template #reference>
                    <span class="rp-qtext">{{ row.text }}</span>
                  </template>
                  <div class="rp-pop">{{ row.text }}</div>
                </el-popover>
              </template>
            </el-table-column>
            <el-table-column label="AI 评语" min-width="200" prop="comment" show-overflow-tooltip />
            <el-table-column label="得分" width="72" align="right">
              <template #default="{ row }">
                <span :class="row.scoreClass">{{ row.score }}/{{ row.max_score }}</span>
              </template>
            </el-table-column>
            <el-table-column label="作答" width="110" align="center">
              <template #default="{ row }">
                <el-button
                  v-if="row.hasVoice"
                  size="small"
                  :type="playingIndex === row.index ? 'primary' : ''"
                  :loading="voiceLoading === row.index"
                  link
                  @click="togglePlay(row.index)"
                >🎙 {{ playingIndex === row.index ? '播放中' : '试听原声' }}</el-button>
                <span v-else-if="row.voiceExpired" class="rp-voice-expired">🎙 原声已删</span>
                <span v-else class="rp-voice-none">文字</span>
              </template>
            </el-table-column>
          </el-table>
          <audio ref="audioEl" class="rp-audio" controls v-show="playingIndex !== null" @ended="playingIndex = null" />
        </div>
      </template>
      <el-empty v-else-if="!loading" description="暂无报告（候选人未交卷或报告生成失败）" />
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { getInterviewReportApi, fetchSessionVoiceBlobApi, type InterviewReport, type InterviewSession, type ReportPerQuestion } from '@/api/interview'

const props = defineProps<{
  modelValue: boolean
  session: InterviewSession | null
  resumeName?: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const report = ref<InterviewReport | null>(null)
const loading = ref(false)

const TYPE_MAP: Record<string, string> = {
  project_deep_dive: '项目深挖',
  hard_skill: '硬技能',
  scenario: '情境题',
  behavioral: '行为协作',
  motivation: '动机稳定',
}

async function load() {
  report.value = null
  if (!props.session) return
  loading.value = true
  try {
    const res = await getInterviewReportApi(props.session.id)
    report.value = res.data
  } catch (e) {
    console.error('获取报告失败:', e)
  } finally {
    loading.value = false
  }
}

const verdictText = computed(() => {
  switch (report.value?.verdict) {
    case 'recommend': return '🟢 推荐进面 · 建议尽快安排真人面试'
    case 'pending': return '🟡 待定 · 可进面（建议带着追问清单聊）'
    case 'reject': return '🔴 不推荐 · AI 评估未达本轮岗位要求'
    default: return '—'
  }
})
const verdictClass = computed(() => report.value?.verdict || '')

function questionOf(index: number) {
  return (props.session?.questions_json || []).find((q) => q.index === index)
}
function typeShort(index: number) {
  const t = questionOf(index)?.type
  return TYPE_MAP[t || ''] || '题目'
}
function barPct(q: ReportPerQuestion) {
  if (!q.max_score) return 0
  return Math.min(100, Math.round((q.score / q.max_score) * 100))
}
function barClass(q: ReportPerQuestion) {
  const p = barPct(q)
  if (p < 50) return 'low'
  if (p < 70) return 'mid'
  return ''
}
function scoreClassOf(q: ReportPerQuestion) {
  const p = barPct(q)
  return p < 50 ? 'sc-low' : p < 70 ? 'sc-mid' : 'sc-ok'
}

const reviewRows = computed(() => {
  const urls = report.value?.voice_urls || []
  const avail = report.value?.voice_available || []
  return (report.value?.per_question || []).map((q) => ({
    index: q.index,
    type: typeShort(q.index),
    text: questionOf(q.index)?.text || `第 ${q.index} 题`,
    comment: q.comment || '—',
    score: q.score,
    max_score: q.max_score,
    scoreClass: scoreClassOf(q),
    hasVoice: !!avail[q.index - 1],
    // 有录音引用但文件不可用 = 超 30 天已按隐私策略删除
    voiceExpired: !!urls[q.index - 1] && !avail[q.index - 1],
  }))
})

// ---- VR-12 原声试听 ----
const audioEl = ref<HTMLAudioElement | null>(null)
const playingIndex = ref<number | null>(null)
const voiceLoading = ref<number | null>(null)
let objectUrl: string | null = null

function releaseAudio() {
  if (audioEl.value) {
    audioEl.value.pause()
    audioEl.value.removeAttribute('src')
    audioEl.value.load()
  }
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
}

async function togglePlay(index: number) {
  if (playingIndex.value === index) {
    releaseAudio()
    playingIndex.value = null
    return
  }
  if (!props.session) return
  voiceLoading.value = index
  try {
    const blob = await fetchSessionVoiceBlobApi(props.session.id, index)
    releaseAudio()
    objectUrl = URL.createObjectURL(blob)
    playingIndex.value = index
    // 等 v-show 生效后赋值播放
    requestAnimationFrame(() => {
      if (audioEl.value) {
        audioEl.value.src = objectUrl!
        audioEl.value.play().catch(() => ElMessage.warning('浏览器阻止自动播放，请点击播放条'))
      }
    })
  } catch (e: any) {
    const status = e?.response?.status
    if (status === 410) ElMessage.warning('原声已按隐私策略删除（保留 30 天）')
    else if (status === 404) ElMessage.info('该题无录音作答')
    else ElMessage.error('原声加载失败')
  } finally {
    voiceLoading.value = null
  }
}

onBeforeUnmount(releaseAudio)

function fmt(iso: string) {
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}
</script>

<style scoped>
.rp-root { min-height: 200px; }
.rp-sub { font-size: 12.5px; color: var(--ink-500); margin-bottom: 14px; }
.rp-panel { background: var(--paper, #fff); border: 1px solid var(--ink-100); border-radius: var(--radius-sm, 6px); padding: 14px 16px; margin-bottom: 14px; }
.rp-panel-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.rp-panel-title::before { content: ''; width: 3px; height: 14px; background: var(--brand-primary-500); border-radius: 2px; }

.rp-hero { display: flex; align-items: center; gap: 24px; padding: 4px 0 14px; flex-wrap: wrap; }
.rp-big { font-size: 42px; font-weight: 700; color: var(--brand-primary-500); line-height: 1; font-family: var(--font-number); }
.rp-big small { font-size: 15px; color: var(--ink-500); font-weight: 400; }
.rp-verdict { padding: 6px 14px; border-radius: 4px; font-size: 14px; font-weight: 500; }
.rp-verdict.recommend { background: var(--success-50); color: var(--success-500); border: 1px solid #a7e0c5; }
.rp-verdict.pending { background: var(--warning-50); color: var(--accent-clay); border: 1px solid #f3dcb0; }
.rp-verdict.reject { background: var(--danger-50); color: var(--danger-500); border: 1px solid #f9d3d1; }
.rp-rules { margin-left: auto; text-align: right; font-size: 12px; color: var(--ink-500); }

.rp-bar-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; font-size: 13px; }
.rp-bar-name { width: 108px; color: var(--ink-700); flex-shrink: 0; }
.rp-bar-track { flex: 1; height: 8px; background: #eef1f5; border-radius: 4px; overflow: hidden; }
.rp-bar-fill { height: 100%; background: var(--brand-primary-500); border-radius: 4px; transition: width 0.4s var(--ease-smooth); }
.rp-bar-fill.mid { background: var(--warning-500); }
.rp-bar-fill.low { background: var(--danger-500); }
.rp-bar-score { width: 52px; text-align: right; color: var(--ink-500); font-family: var(--font-number); font-size: 12.5px; }

.rp-finding { border-left: 3px solid var(--success-500); background: #f6fbf7; padding: 10px 14px; border-radius: 0 4px 4px 0; margin-bottom: 10px; font-size: 13.5px; color: var(--ink-700); }
.rp-finding.concern { border-left-color: var(--warning-500); background: #fdfaf3; }
.rp-warn { display: flex; align-items: center; gap: 8px; background: var(--danger-50); border: 1px solid #f9d3d1; border-radius: 4px; padding: 9px 14px; font-size: 13px; color: #c2403f; margin-bottom: 10px; }
.rp-followups { margin: 0; padding-left: 20px; }
.rp-followups li { margin: 6px 0; font-size: 13.5px; color: var(--ink-700); }

.rp-qtext { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; cursor: pointer; color: var(--brand-primary-500); }
.rp-voice-expired { font-size: 12px; color: var(--ink-500); }
.rp-voice-none { font-size: 12px; color: var(--ink-300, #b0b6c3); }
.rp-audio { width: 100%; height: 36px; margin-top: 10px; }
.rp-pop { font-size: 13px; line-height: 1.7; color: var(--ink-700); }
.sc-ok { color: var(--success-500); font-weight: 600; }
.sc-mid { color: var(--warning-500); font-weight: 600; }
.sc-low { color: var(--danger-500); font-weight: 600; }
</style>
