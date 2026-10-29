<template>
  <div class="dashboard-filter">
    <!-- 项目下拉 -->
    <div class="filter-item">
      <label class="filter-label">项目</label>
      <el-select
        v-model="projectId"
        placeholder="全部项目"
        clearable
        filterable
        :loading="store.loading.projects"
        :disabled="store.loading.projects"
        size="default"
        class="filter-select"
        @change="handleProjectChange"
      >
        <el-option
          v-for="p in store.projects"
          :key="p.id"
          :label="p.project_name"
          :value="p.id"
        />
      </el-select>
    </div>

    <!-- 职位下拉 -->
    <div class="filter-item">
      <label class="filter-label">职位</label>
      <el-select
        v-model="positionId"
        placeholder="全部职位"
        clearable
        filterable
        :loading="store.loading.positions"
        :disabled="store.loading.positions"
        size="default"
        class="filter-select"
        @change="handlePositionChange"
      >
        <el-option
          v-for="pos in store.positions"
          :key="pos.id"
          :label="pos.position_name"
          :value="pos.id"
        />
      </el-select>
    </div>

    <!-- 时间范围切换 -->
    <div class="filter-item">
      <label class="filter-label">时间范围</label>
      <el-radio-group
        v-model="range"
        size="default"
        @change="handleRangeChange"
      >
        <el-radio-button label="month">月</el-radio-button>
        <el-radio-button label="quarter">季</el-radio-button>
        <el-radio-button label="year">年</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 右侧操作区（可放置刷新按钮等，由父组件透传插槽） -->
    <div class="filter-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
/**
 * DashboardFilter - 顶部 1 行筛选器
 *
 * 设计原则（基于 dashboard-design skill §1 + design-taste-frontend §6）：
 *   - Carbon 风格：1px border，无 shadow，无圆角（border-radius: 0）
 *   - 配色：深海青 #0F4C5C（主色）+ 琥珀 #D97706（accent）+ inkstone 中性轴
 *   - 字号 14px（var(--font-size-body)），字体 Noto Sans SC
 *   - 中文单语种，零 em-dash
 *   - 项目变更时自动清空职位并重新拉取
 *
 * 联动逻辑：
 *   1. 用户切换项目 → store.setProject(id) → 自动清空 position + reload positions
 *   2. 用户切换职位 → store.setPosition(id) → 仅更新 position
 *   3. 用户切换时间范围 → store.setRange(range) → 仅更新 range
 *   4. 任何一个变更 → emit('change', filterParams) 让父组件触发 loadAll
 *
 * 注：本组件不触发 dashboard 数据拉取，由父组件监听 'change' 事件决定何时刷新数据。
 */

import { ref, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useDashboardStore } from '@/stores/dashboard'

const emit = defineEmits(['change', 'ready'])

const store = useDashboardStore()
const { filterProjectId, filterPositionId, filterRange } = storeToRefs(store)

// 本地 v-model 副本（保证 el-select / el-radio-group 的双向绑定工作）
const projectId = ref(filterProjectId.value)
const positionId = ref(filterPositionId.value)
const range = ref(filterRange.value)

// 初次挂载：拉取项目列表（职位列表等项目选定后再拉）
onMounted(async () => {
  if (store.projects.length === 0) {
    await store.loadProjects()
  }
  // 如果已有项目筛选（比如从 URL 恢复），拉对应职位
  if (filterProjectId.value !== null) {
    await store.loadPositions(filterProjectId.value)
    positionId.value = filterPositionId.value
  }
  emit('ready')
})

// 监听 store 中 filterProjectId 的变化（例如外部代码重置），同步到本地
watch(filterProjectId, (val) => {
  projectId.value = val
})

watch(filterPositionId, (val) => {
  positionId.value = val
})

watch(filterRange, (val) => {
  range.value = val
})

// ========== 事件处理 ==========

const handleProjectChange = async (val) => {
  // store.setProject 会自动清空 positionId 并 reload positions
  await store.setProject(val)
  // 同步本地 positionId 到清空后的状态
  positionId.value = store.filterPositionId
  emit('change', { ...store.filterParams })
}

const handlePositionChange = (val) => {
  store.setPosition(val)
  emit('change', { ...store.filterParams })
}

const handleRangeChange = (val) => {
  store.setRange(val)
  emit('change', { ...store.filterParams })
}
</script>

<style scoped>
/* ====================================================================
 * DashboardFilter - Carbon 风格 1 行筛选器
 * 1px border，无 shadow，无圆角（与 V1.1 dashboard 主风格一致）
 * 配色严格走 theme.css 已有 token，不引入新色
 * ==================================================================== */

.dashboard-filter {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  height: 56px;
  padding: 0 var(--space-lg);
  background-color: var(--paper);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
}

.filter-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.filter-label {
  font-size: var(--font-size-body, 14px);
  font-weight: var(--font-weight-medium, 500);
  color: var(--ink-700);
  font-family: var(--font-body);
  white-space: nowrap;
  user-select: none;
}

.filter-select {
  width: 200px;
}

.filter-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

/* Element Plus 样式微调：贴合 1px border + 无圆角风格 */
.dashboard-filter :deep(.el-select__wrapper) {
  box-shadow: 0 0 0 1px var(--ink-300) inset !important;
  border-radius: var(--radius-sm) !important;
  background-color: var(--paper);
}

.dashboard-filter :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--brand-primary-500) inset !important;
}

.dashboard-filter :deep(.el-select__wrapper.is-hovering:not(.is-focused)) {
  box-shadow: 0 0 0 1px var(--ink-500) inset !important;
}

.dashboard-filter :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--ink-300) inset !important;
  border-radius: var(--radius-sm) !important;
}

.dashboard-filter :deep(.el-radio-group) {
  display: flex;
}

.dashboard-filter :deep(.el-radio-button__inner) {
  border: 1px solid var(--ink-300) !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  font-size: var(--font-size-body, 14px);
  color: var(--ink-700);
  padding: 8px 16px;
}

.dashboard-filter :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: var(--radius-sm) 0 0 var(--radius-sm) !important;
}

.dashboard-filter :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0 !important;
}

.dashboard-filter :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: var(--brand-primary-500) !important;
  border-color: var(--brand-primary-500) !important;
  color: var(--paper) !important;
  box-shadow: none !important;
}

.dashboard-filter :deep(.el-radio-button__inner:hover) {
  color: var(--brand-primary-700);
}

/* 响应式：窄屏折叠 */
@media (max-width: 768px) {
  .dashboard-filter {
    flex-wrap: wrap;
    height: auto;
    padding: var(--space-md);
    gap: var(--space-md);
  }

  .filter-select {
    width: 160px;
  }

  .filter-actions {
    margin-left: 0;
    width: 100%;
    justify-content: flex-end;
  }
}
</style>