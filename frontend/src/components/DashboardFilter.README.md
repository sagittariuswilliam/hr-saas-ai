# DashboardFilter 组件说明

> 顶部 1 行筛选器，用于 HR-SaaS Dashboard V1.2 的项目 / 职位 / 时间范围筛选。

## 文件

- 组件源码：`src/components/DashboardFilter.vue`
- 数据源：`src/stores/dashboard.js`（Pinia store）

## 怎么用

### 基础用法

```vue
<template>
  <div class="dashboard-page">
    <DashboardFilter @change="onFilterChange" />

    <!-- 下面是 dashboard 内容 -->
    <KpiCards />
    <TrendChart />
    <FunnelChart />
  </div>
</template>

<script setup>
import DashboardFilter from '@/components/DashboardFilter.vue'
import { useDashboardStore } from '@/stores/dashboard'

const store = useDashboardStore()

const onFilterChange = async (params) => {
  // 筛选变更，重新拉全部 dashboard 数据
  await store.loadAll()
}

// 首次进入拉一次
onMounted(() => {
  store.loadAll()
})
</script>
```

### 带右侧操作按钮

通过 `actions` 插槽可在右侧放自定义按钮（如「刷新」「导出」）：

```vue
<DashboardFilter @change="onFilterChange">
  <template #actions>
    <el-button :icon="Refresh" @click="store.loadAll()">刷新</el-button>
    <el-button :icon="Download" type="primary">导出</el-button>
  </template>
</DashboardFilter>
```

## Props

本组件**不接收 Props**，所有数据从 `useDashboardStore()` 中读取。

这样设计的原因：
- 全局只有 1 个 dashboard，store 单例
- 筛选状态天然全局共享，跨组件访问无需透传
- 父组件无需关心项目/职位列表的拉取细节

## Events

| 事件名 | 触发时机 | Payload | 说明 |
|--------|---------|---------|------|
| `change` | 任一筛选条件变化后 | `FilterParams` | 父组件应监听此事件触发数据重拉 |
| `ready` | 组件挂载完成、项目列表初始化好后 | 无 | 父组件可在此时安全触发首次拉取 |

### FilterParams 结构

```ts
interface FilterParams {
  project_id: number | null    // null = 全部项目
  position_id: number | null   // null = 全部职位
  range: 'month' | 'quarter' | 'year'
}
```

## 联动逻辑

### 1. 项目变更 → 职位自动重置 + 重新拉取

```text
用户选择 "项目A"
  ↓
store.setProject('A')
  ↓
  ├─ filterProjectId = A
  ├─ filterPositionId = null   (自动重置)
  └─ loadPositions(A)          (拉项目A下的职位)
  ↓
emit('change', { project_id: A, position_id: null, range: 'month' })
```

理由：跨项目的职位 ID 没有意义，必须先清空。

### 2. 职位变更 → 仅更新 position_id

```text
用户选择 "职位B"
  ↓
store.setPosition('B')
  ↓
  └─ filterPositionId = B
  ↓
emit('change', { ... })
```

### 3. 时间范围变更 → 仅更新 range

```text
用户点 "季"
  ↓
store.setRange('quarter')
  ↓
  └─ filterRange = 'quarter'
  ↓
emit('change', { ... })
```

### 4. 父组件接收 change 后

由父组件决定如何刷新数据。**推荐做法：**

```js
const onFilterChange = async (params) => {
  // 全量刷新 4 个 dashboard API
  await store.loadAll()
}
```

如果你想做细粒度控制，也可以只刷新某一个：

```js
const onFilterChange = async (params) => {
  // 例如只刷新趋势，不刷新实时
  await store.loadTrend()
  await store.loadFunnel()
}
```

## 视觉规范

| 维度 | 取值 |
|------|------|
| 高度 | 56px |
| 边框 | 1px `var(--border-default)` |
| 圆角 | 6px（`--radius-sm`） |
| 背景 | `var(--paper)` |
| 阴影 | 无（Carbon 风格） |
| 字体 | Noto Sans SC, 14px |
| 主色 | 深海青 `#0F4C5C` |
| 文字色 | `--ink-700`（标签）/ `--ink-900`（选项） |
| 强调色 | 琥珀 `#D97706`（hover/pressed 焦点光晕） |

### 配色约束

- ❌ 不使用紫 / 青 / 粉 / 渐变
- ✅ 主色严格走 `var(--brand-primary-500)` 深海青
- ✅ 强调色严格走 `var(--accent-amber)` 琥珀
- ✅ 中性色严格走 inkstone 轴

### 排版约束

- ✅ 中文单语种，无英文混排
- ✅ 零 em-dash（—）
- ✅ 字号统一 14px body / 13px caption

## 响应式

| 断点 | 行为 |
|------|------|
| `≥ 768px` | 水平排列，固定高度 56px |
| `< 768px` | 自动换行，高度自适应，操作区右对齐 |

## 不动的事

- ❌ 不动 `views/dashboard/index.vue`（V1.1 视图，subagent 3 改）
- ❌ 不动现有 Pinia store
- ❌ 不改 `main.ts` / `router`
- ❌ 不引入新依赖
- ❌ 不动 `dist/`

## 验收

- ✅ `npm run build` 通过
- ✅ 浏览器加载后项目下拉显示 全部项目
- ✅ 切换项目时职位下拉自动清空并 reload
- ✅ 时间范围 3 选 1 互斥
- ✅ 任一变更后 emit('change') 触发父组件

---

*版本：V1.2 预备（2026-07-15）*
*作者：subagent 2 / Pinia store + 顶部筛选器*