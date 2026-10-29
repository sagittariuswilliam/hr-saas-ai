<template>
  <el-dialog
    :model-value="modelValue"
    title="面试链接已生成 · 复制话术发送给候选人"
    width="560px"
    append-to-body
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="sd-link">
      <el-input :model-value="candidateUrl" readonly class="sd-link-input" />
      <el-button size="small" @click="copy(candidateUrl, '候选人专属链接已复制')">复制链接</el-button>
    </div>
    <div class="sd-label">预填话术（哪个渠道收的简历就用哪个渠道回）：</div>
    <div class="sd-script">{{ scriptWithUrl }}</div>
    <div class="sd-tip">复制后请到微信/短信粘贴发送。链接 72 小时内有效，一人一条请勿转发。</div>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">关闭</el-button>
      <el-button type="primary" @click="copy(scriptWithUrl, '话术已复制（含链接），去微信/短信粘贴发送')">
        📋 一键复制话术（含链接）
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { buildCandidateUrl, copyTextToClipboard, type SendResult } from '@/api/interview'

const props = defineProps<{
  modelValue: boolean
  scriptData: SendResult | null
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const candidateUrl = computed(() => {
  if (!props.scriptData) return ''
  return buildCandidateUrl(props.scriptData.link, props.scriptData.token)
})

// 后端话术里链接是相对路径，替换为可直接打开的完整 URL
const scriptWithUrl = computed(() => {
  if (!props.scriptData) return ''
  return props.scriptData.script.replace(props.scriptData.link, candidateUrl.value)
})

async function copy(text: string, okMsg: string) {
  const ok = await copyTextToClipboard(text)
  ok ? ElMessage.success(okMsg) : ElMessage.error('复制失败，请手动选择文本复制')
}
</script>

<style scoped>
.sd-link { display: flex; gap: 8px; margin-bottom: 14px; }
.sd-link-input :deep(input) { color: var(--brand-primary-500); background: var(--brand-primary-50); font-size: 13px; }
.sd-label { font-size: 12.5px; color: var(--ink-500); margin-bottom: 6px; }
.sd-script { background: var(--ink-50); border: 1px solid var(--ink-100); border-radius: 4px; padding: 14px; font-size: 13.5px; color: var(--ink-700); white-space: pre-wrap; line-height: 1.8; }
.sd-tip { font-size: 12px; color: var(--ink-500); margin-top: 12px; }
</style>
