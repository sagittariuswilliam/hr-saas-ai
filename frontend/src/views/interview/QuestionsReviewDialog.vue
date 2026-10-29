<template>
  <el-dialog
    :model-value="modelValue"
    title="审定面试题目"
    width="680px"
    top="6vh"
    :close-on-click-modal="false"
    append-to-body
    @update:model-value="emit('update:modelValue', $event)"
    @open="initFromSession"
  >
    <div class="qr-sub">
      AI 已根据「{{ positionName }} + {{ resumeName }} 简历」生成 {{ questions.length }} 题初稿 · 确认后才会生成候选人专属链接
    </div>
    <div class="qr-note">题干点击可编辑；每 1 题允许 AI 按评分要点自动追问 1 轮；红线（婚育/年龄/宗教等）已在出题时屏蔽，仍建议通读一遍。</div>

    <div class="qr-list" v-loading="saving">
      <div class="qr-card" v-for="(q, i) in questions" :key="i">
        <div class="qr-card-head">
          <span class="qr-no">Q{{ i + 1 }}</span>
          <el-tag size="small" effect="plain">{{ typeLabel(q.type) }}</el-tag>
          <span class="qr-spacer"></span>
          <el-button link type="danger" size="small" :disabled="questions.length <= 1" @click="questions.splice(i, 1)">删除</el-button>
        </div>
        <div class="qr-card-body">
          <el-input v-model="q.text" type="textarea" :autosize="{ minRows: 2, maxRows: 6}" class="qr-text" />
          <div class="qr-rubric" v-if="q.rubric && q.rubric.length">
            <div class="qr-rubric-t">评分要点（好答案应覆盖）</div>
            <ol>
              <li v-for="(r, ri) in q.rubric" :key="ri">{{ r }}</li>
            </ol>
            <div class="qr-rubric-weak" v-if="q.weak_answer_hint">常见水答案：{{ q.weak_answer_hint }}</div>
          </div>
          <div class="qr-meta">
            <span>建议作答 ≥{{ q.min_words }} 字</span>
            <span>低于 {{ q.min_words }} 字报告将标「回答过简」</span>
          </div>
        </div>
      </div>

      <el-button class="qr-add" @click="addQuestion">＋ 手动补充一题</el-button>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button :loading="saving" @click="saveOnly">仅保存修订</el-button>
      <el-button type="primary" :loading="sending" @click="saveAndSend">确认发出 →</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  updateInterviewQuestionsApi,
  sendInterviewSessionApi,
  type InterviewSession,
  type InterviewQuestion
} from '@/api/interview'

const props = defineProps<{
  modelValue: boolean
  session: InterviewSession | null
  resume?: any
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved', s: InterviewSession): void
  (e: 'sent', r: { token: string; link: string; script: string }): void
}>()

const questions = ref<InterviewQuestion[]>([])
const saving = ref(false)
const sending = ref(false)
const positionName = ref('职位')
const resumeName = ref('候选人')

function initFromSession() {
  questions.value = JSON.parse(JSON.stringify(props.session?.questions_json || []))
  positionName.value = props.resume?.position_name || '职位 JD'
  resumeName.value = props.resume?.candidate_name || '候选人'
}

const TYPE_MAP: Record<string, string> = {
  project_deep_dive: '项目深挖',
  hard_skill: '岗位硬技能',
  scenario: '情境题',
  behavioral: '行为协作',
  motivation: '动机稳定性',
  other: '其他',
}
function typeLabel(t?: string) {
  return TYPE_MAP[t || 'other'] || '其他'
}

function addQuestion() {
  questions.value.push({
    index: questions.value.length + 1,
    type: 'other',
    text: '',
    rubric: ['回答具体可信', '有细节与数据', '逻辑清晰'],
    weak_answer_hint: '',
    min_words: 100,
  })
}

async function saveOnly() {
  const err = validate()
  if (err) return ElMessage.warning(err)
  saving.value = true
  try {
    const res = await updateInterviewQuestionsApi(props.session!.id, questions.value)
    emit('saved', res.data)
    ElMessage.success('题目修订已保存')
  } finally {
    saving.value = false
  }
}

async function saveAndSend() {
  const err = validate()
  if (err) return ElMessage.warning(err)
  sending.value = true
  try {
    await updateInterviewQuestionsApi(props.session!.id, questions.value)
    const res = await sendInterviewSessionApi(props.session!.id)
    emit('sent', res.data)
  } catch (e) {
    console.error('发送失败:', e)
  } finally {
    sending.value = false
  }
}

function validate(): string | null {
  if (!questions.value.length) return '至少保留 1 道题'
  const empty = questions.value.findIndex((q) => !q.text || !q.text.trim())
  if (empty >= 0) return `第 ${empty + 1} 题题干为空`
  return null
}
</script>

<style scoped>
.qr-sub { font-size: 13px; color: var(--ink-500); margin-bottom: 6px; }
.qr-note { font-size: 12.5px; color: var(--ink-500); background: var(--brand-primary-50); border-radius: 4px; padding: 8px 12px; margin-bottom: 14px; }
.qr-list { max-height: 56vh; overflow-y: auto; padding-right: 4px; }
.qr-card { border: 1px solid var(--ink-100); border-radius: var(--radius-sm, 6px); margin-bottom: 12px; overflow: hidden; }
.qr-card-head { display: flex; align-items: center; gap: 10px; padding: 9px 14px; background: var(--ink-50); border-bottom: 1px solid var(--ink-100); }
.qr-no { font-weight: 600; color: var(--brand-primary-500); }
.qr-spacer { flex: 1; }
.qr-card-body { padding: 12px 14px; }
.qr-text :deep(textarea) { font-size: 14px; }
.qr-rubric { background: var(--brand-primary-50); border-radius: 4px; padding: 10px 12px; font-size: 12.5px; color: #375c66; margin-top: 10px; }
.qr-rubric-t { font-weight: 600; margin-bottom: 4px; color: var(--brand-primary-500); }
.qr-rubric ol { padding-left: 18px; margin: 0; }
.qr-rubric li { margin-bottom: 2px; }
.qr-rubric-weak { margin-top: 5px; opacity: 0.8; }
.qr-meta { display: flex; gap: 16px; margin-top: 8px; color: var(--ink-500); font-size: 12px; }
.qr-add { width: 100%; border-style: dashed; color: var(--brand-primary-500); }
</style>
