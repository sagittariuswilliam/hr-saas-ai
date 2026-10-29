<!--
  HR-SaaS Dashboard V2.0
  ============================================================================
  设计哲学（基于 Geckoboard 9 + AntV 4 + Carbon 8pt）
  - 谁看 + 为什么：HR Manager，需要决定"今日新简历处理优先级" + "招聘节奏趋势"
  - 16:9 左右分栏，左实时（窄）+ 右全局（宽）
  - 5 区块：3 实时 KPI（左侧） + 漏斗 / 趋势 / AI 评分（右侧）
  - 顶部 1 行筛选器（项目 · 职位 · 时间范围）
  - 颜色 = 深海青 + 琥珀 + Jade（3 色，零 AI Slop 渐变）
  - 数字字体 JetBrains Mono（对齐 + 数据感）
  - 数字取整 vs_yesterday 取整
  - 1px border · 无 shadow（Carbon 风格）
  - 真实数据：Pinia store → 4 个 API · 零 mock
-->
<template>
  <div class="v20-dashboard">
    <!-- ============ 顶部 1 行筛选器 ============ -->
    <header class="v20-header">
      <DashboardFilter @change="onFilterChange" />
      <div class="v20-header__meta">
        <span class="v20-header__label">{{ currentDateText }}</span>
        <span v-if="store.hasFilter" class="v20-header__chip">
          已筛选 · {{ store.filterRange === 'month' ? '月' : store.filterRange === 'quarter' ? '季' : '年' }}
        </span>
      </div>
    </header>

    <!-- ============ 16:9 左右分栏 ============ -->
    <main class="v20-grid">
      <!-- ============ 左列：实时 KPI ============ -->
      <section class="v20-col v20-col--left" aria-label="今日实时指标">
        <!-- KPI 1：今日新简历（最重要，左上角最大化） -->
        <article class="v20-kpi v20-kpi--primary">
          <div class="v20-kpi__head">
            <span class="v20-kpi__label">今日新简历</span>
            <span class="v20-kpi__hint">HR 首要决策点</span>
          </div>
          <div class="v20-kpi__main">
            <span class="v20-kpi__num">{{ kpi1.value }}</span>
            <span class="v20-kpi__unit">份</span>
          </div>
          <div class="v20-kpi__trend">
            较昨日
            <strong :class="kpi1.delta > 0 ? 'is-up' : kpi1.delta < 0 ? 'is-down' : 'is-flat'">
              {{ kpi1.delta > 0 ? '+' : '' }}{{ kpi1.delta }}
              <span class="v20-kpi__arrow">{{ kpi1.delta > 0 ? '↑' : kpi1.delta < 0 ? '↓' : '→' }}</span>
              {{ kpi1.deltaPct }}%
            </strong>
          </div>
        </article>

        <!-- KPI 2：今日入职 -->
        <article class="v20-kpi">
          <div class="v20-kpi__head">
            <span class="v20-kpi__label">今日入职</span>
            <span class="v20-kpi__hint">已发 offer 入职状态变更</span>
          </div>
          <div class="v20-kpi__main">
            <span class="v20-kpi__num">{{ kpi2.value }}</span>
            <span class="v20-kpi__unit">人</span>
          </div>
          <div class="v20-kpi__trend">
            较昨日
            <strong :class="kpi2.delta > 0 ? 'is-up' : kpi2.delta < 0 ? 'is-down' : 'is-flat'">
              {{ kpi2.delta > 0 ? '+' : '' }}{{ kpi2.delta }}
              <span class="v20-kpi__arrow">{{ kpi2.delta > 0 ? '↑' : kpi2.delta < 0 ? '↓' : '→' }}</span>
              {{ kpi2.deltaPct }}%
            </strong>
          </div>
        </article>

        <!-- KPI 3：今日面试 -->
        <article class="v20-kpi">
          <div class="v20-kpi__head">
            <span class="v20-kpi__label">今日面试</span>
            <span class="v20-kpi__hint">已调度 + 进行中状态变更</span>
          </div>
          <div class="v20-kpi__main">
            <span class="v20-kpi__num">{{ kpi3.value }}</span>
            <span class="v20-kpi__unit">场</span>
          </div>
          <div class="v20-kpi__trend">
            较昨日
            <strong :class="kpi3.delta > 0 ? 'is-up' : kpi3.delta < 0 ? 'is-down' : 'is-flat'">
              {{ kpi3.delta > 0 ? '+' : '' }}{{ kpi3.delta }}
              <span class="v20-kpi__arrow">{{ kpi3.delta > 0 ? '↑' : kpi3.delta < 0 ? '↓' : '→' }}</span>
              {{ kpi3.deltaPct }}%
            </strong>
          </div>
        </article>
      </section>

      <!-- ============ 右列：全局视图 ============ -->
      <section class="v20-col v20-col--right" aria-label="招聘全局视图">
        <!-- 区块 4：招聘漏斗 -->
        <article class="v20-card v20-card--funnel">
          <div class="v20-card__head">
            <div>
              <div class="v20-card__title">招聘漏斗</div>
              <div class="v20-card__sub">{{ funnelRangeLabel }} 各状态快照</div>
            </div>
            <div class="v20-card__tip">
              <el-tooltip
                placement="top"
                content="基于当前状态快照，非流程历史。每份简历只计入其当前所在状态。"
              >
                <span class="v20-card__icon" aria-label="口径说明">i</span>
              </el-tooltip>
              <span class="v20-card__tip-text">口径说明</span>
            </div>
          </div>
          <div ref="funnelRef" class="v20-echarts v20-echarts--funnel">
            <div v-if="store.loading.funnel && !store.funnel" class="v20-skel">
              漏斗加载中…
            </div>
          </div>
          <div v-if="funnelRateLabel" class="v20-funnel-foot">
            整体转化 {{ funnelRateLabel }}
            <span class="v20-funnel-foot__rate"> {{ funnelRatePct }}%</span>
            共 {{ funnelTotal }} 份简历
          </div>
        </article>

        <!-- 区块 5：月度入职趋势 -->
        <article class="v20-card v20-card--trend">
          <div class="v20-card__head">
            <div>
              <div class="v20-card__title">月度入职趋势</div>
              <div class="v20-card__sub">{{ trendRangeLabel }} 时间序列</div>
            </div>
            <div class="v20-card__legend">
              <span class="v20-legend">
                <i class="v20-legend__dot v20-legend__dot--primary"></i> 新简历
              </span>
              <span class="v20-legend">
                <i class="v20-legend__dot v20-legend__dot--amber"></i> 入职
              </span>
            </div>
          </div>
          <div ref="trendRef" class="v20-echarts v20-echarts--trend">
            <div v-if="store.loading.trend && !store.trend" class="v20-skel">
              趋势加载中…
            </div>
          </div>
        </article>

        <!-- 区块 6：AI 评分 -->
        <article class="v20-card v20-card--ai">
          <div class="v20-card__head">
            <div>
              <div class="v20-card__title">AI 平均匹配度</div>
              <div class="v20-card__sub">{{ aiRangeLabel }} 全样本均值</div>
            </div>
            <div class="v20-card__tip">
              <el-tooltip
                placement="top"
                content="基于 resumes.match_score 列聚合（0-100 整数），样本量越大越稳定。"
              >
                <span class="v20-card__icon" aria-label="数据口径">i</span>
              </el-tooltip>
              <span class="v20-card__tip-text">数据口径</span>
            </div>
          </div>
          <div class="v20-ai">
            <div class="v20-ai__main">
              <span class="v20-ai__num">{{ aiRounded }}</span>
              <span class="v20-ai__unit">/ 100</span>
            </div>
            <div class="v20-ai__meta">
              <div class="v20-ai__line">
                较上期
                <strong
                  :class="aiDelta > 0 ? 'is-up' : aiDelta < 0 ? 'is-down' : 'is-flat'"
                >
                  {{ aiDelta > 0 ? '+' : '' }}{{ aiDeltaRounded }}
                  <span class="v20-ai__arrow">{{ aiDelta > 0 ? '↑' : aiDelta < 0 ? '↓' : '→' }}</span>
                </strong>
              </div>
              <div class="v20-ai__line v20-ai__line--muted">
                基于 {{ aiSample }} 份简历 · 0-100 整数评分
              </div>
            </div>
          </div>
        </article>
      </section>
    </main>

    <!-- ============ 异常兜底：全局 error banner ============ -->
    <div v-if="hasLoadError" class="v20-error" role="alert">
      部分数据加载失败，下方数字可能为占位。请稍后刷新或检查网络。
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * HR-SaaS Dashboard V2.0 View
 *
 * 数据流：
 *   DashboardFilter (顶部筛选器)
 *     → useDashboardStore (Pinia)
 *       → 4 个 dashboard API (realtime / trend / funnel / ai-score)
 *         → 本视图响应式渲染
 *
 * 视图职责：
 *   - 调用 store.loadAll() 触发初次 / 切换筛选后的全量刷新
 *   - 把 store 中的 reactive 数据映射到 5 区块
 *   - 派生 round、delta、deltaPct 等展示用字段
 *   - ECharts 实例管理：watch → resize，onUnmounted → dispose
 */
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { storeToRefs } from 'pinia'
import DashboardFilter from '@/components/DashboardFilter.vue'
import { useDashboardStore } from '@/stores/dashboard'

// ============ Store ============
const store = useDashboardStore()
const { filterRange } = storeToRefs(store)

// ============ ECharts refs ============
const funnelRef = ref<HTMLDivElement | null>(null)
const trendRef = ref<HTMLDivElement | null>(null)
let funnelChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null

// ============ 视图数据（响应式）============
const realtime = computed<any>(() => store.realtime || {})
const trend = computed<any>(() => store.trend || { series: [], range: 'month' })
const funnel = computed<any>(() => store.funnel || {
  stages: {}, total: 0, rates: {}, range: 'month'
})
const aiScore = computed<any>(() => store.aiScore || {
  avg_score: 0, sample_count: 0, vs_last_period: 0, range: 'month'
})

// ============ KPI 1 / 2 / 3 派生 ============
function buildKpi(metric: any) {
  const value = Number(metric?.value ?? 0)
  const rawDelta = Number(metric?.vs_yesterday ?? 0)
  // delta 与 vs_yesterday 同步（后端已经返回 today - yest）
  const delta = Math.round(rawDelta)
  // 同比百分比：delta 与昨日值的相对变化；昨日为 0 时退化为 -- 占位
  const yestVal = value - rawDelta
  let deltaPct = '--'
  if (Math.abs(yestVal) >= 1) {
    deltaPct = Math.round((rawDelta / yestVal) * 100)
  } else if (rawDelta > 0) {
    deltaPct = '+∞'
  } else if (rawDelta < 0) {
    deltaPct = '-∞'
  }
  return { value: Math.round(value), delta, deltaPct }
}

const kpi1 = computed(() => buildKpi(realtime.value?.today_resumes))
const kpi2 = computed(() => buildKpi(realtime.value?.today_onboardings))
const kpi3 = computed(() => buildKpi(realtime.value?.today_interviews))

// ============ 漏斗派生 ============
const funnelTotal = computed(() => Number(funnel.value?.total || 0))
const funnelOnboarded = computed(() => Number(funnel.value?.stages?.onboarded || 0))

const funnelRateLabel = computed(() => {
  return funnelTotal.value > 0 ? '从初筛到入职' : null
})
const funnelRatePct = computed(() => {
  if (funnelTotal.value === 0) return 0
  return Math.round((funnelOnboarded.value / funnelTotal.value) * 100)
})

// ============ AI 评分派生 ============
const aiRounded = computed(() => {
  // Geckoboard #8：数字取整，46.4 → 46
  return Math.round(Number(aiScore.value?.avg_score ?? 0))
})
const aiDelta = computed(() => Number(aiScore.value?.vs_last_period ?? 0))
const aiDeltaRounded = computed(() => Math.round(aiDelta.value))
const aiSample = computed(() => Number(aiScore.value?.sample_count || 0))

// ============ 文本 ============
const currentDateText = computed(() => {
  const d = new Date()
  const weekDays = ['日', '一', '二', '三', '四', '五', '六']
  return `招聘驾驶舱 · ${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日 · 周${weekDays[d.getDay()]}`
})
const funnelRangeLabel = computed(() =>
  filterRange.value === 'month' ? '本月'
    : filterRange.value === 'quarter' ? '本季度'
    : '本年度'
)
const trendRangeLabel = computed(() => funnelRangeLabel.value)
const aiRangeLabel = computed(() => funnelRangeLabel.value)

// ============ 加载错误兜底 ============
const hasLoadError = computed(() => {
  // 4 个主数据源，任一持续为 null 且 loading=false 则提示
  return !store.realtime && !store.trend && !store.funnel && !store.aiScore &&
    !store.loading.realtime && !store.loading.trend &&
    !store.loading.funnel && !store.loading.aiScore
})

// ============ 事件 ============
async function onFilterChange() {
  await store.loadAll()
}

onMounted(async () => {
  await store.loadAll()
  await nextTick()
  initCharts()
})

onUnmounted(() => {
  // 避免内存泄漏（dashboard-design skill §7.B 重要提醒）
  try {
    funnelChart?.dispose()
    trendChart?.dispose()
  } catch (_) {
    /* ignore */
  }
  funnelChart = null
  trendChart = null
})

// ============ ECharts：funnel ============
function initFunnelChart() {
  if (!funnelRef.value) return
  if (!funnelChart) funnelChart = echarts.init(funnelRef.value)
  renderFunnel()
}

function renderFunnel() {
  if (!funnelChart) return
  // stages 字段完全没收到才画空状态（fallback）；全 0 也要画漏斗
  if (!funnel.value || funnel.value.stages == null) {
    funnelChart.clear()
    funnelChart.setOption({
      title: {
        text: '暂无快照数据',
        subtext: funnelRangeLabel.value,
        left: 'center',
        top: 'middle',
        textStyle: { color: '#64748B', fontSize: 14, fontWeight: 500, fontFamily: 'Noto Sans SC' },
        subtextStyle: { color: '#94A3B8', fontSize: 12, fontFamily: 'Noto Sans SC' }
      }
    })
    return
  }
  const stages = funnel.value.stages || {}
  // 5 阶段显示顺序（按真实流程顺序，与后端 stages 字段一致）
  const ordered = [
    { name: '已提交', value: Math.round(Number(stages.submitted || 0)) },
    { name: '已查看', value: Math.round(Number(stages.viewed || 0)) },
    { name: '安排面试', value: Math.round(Number(stages.interview_scheduled || 0)) },
    { name: '面试中', value: Math.round(Number(stages.interviewing || 0)) },
    { name: '已入职', value: Math.round(Number(stages.onboarded || 0)) }
  ]
  funnelChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => {
        return `<strong>${p.name}</strong><br/>${p.value} 份 (${p.percent}%)`
      },
      backgroundColor: '#FFFFFF',
      borderColor: '#E2E8F0',
      borderWidth: 1,
      textStyle: { color: '#0F172A', fontFamily: 'Noto Sans SC', fontSize: 13 }
    },
    series: [{
      name: '招聘漏斗',
      type: 'funnel',
      left: '10%',
      right: '10%',
      top: 16,
      bottom: 16,
      min: 0,
      max: Math.max(...ordered.map(s => s.value), 1),
      minSize: '20%',
      maxSize: '100%',
      sort: 'descending',
      gap: 2,
      label: {
        show: true,
        position: 'inside',
        formatter: (p: any) => `${p.name}  ${p.value}`,
        color: '#FFFFFF',
        fontFamily: 'Noto Sans SC',
        fontSize: 13,
        fontWeight: 500
      },
      labelLine: { show: false },
      itemStyle: {
        borderColor: '#FFFFFF',
        borderWidth: 1
      },
      // 深海青主色阶（5 段色阶渐进，明度递减 → 海青 → 琥珀）
      data: ordered.map((s, i) => ({
        ...s,
        itemStyle: {
          color: ['#0F4C5C', '#2E6D7F', '#5C8FA0', '#9BAE7A', '#D97706'][i]
        }
      })),
      emphasis: {
        label: { fontSize: 14, fontWeight: 600 },
        itemStyle: { shadowBlur: 0 }
      }
    }]
  }, true)
}

// ============ ECharts：line ============
function initTrendChart() {
  if (!trendRef.value) return
  if (!trendChart) trendChart = echarts.init(trendRef.value)
  renderTrend()
}

function renderTrend() {
  if (!trendChart) return
  // series 字段完全没收到才画空状态（fallback）；全 0 也要画 line
  if (!trend.value || !Array.isArray(trend.value.series)) {
    trendChart.clear()
    trendChart.setOption({
      title: {
        text: '暂无时间序列数据',
        subtext: trendRangeLabel.value,
        left: 'center',
        top: 'middle',
        textStyle: { color: '#64748B', fontSize: 14, fontWeight: 500, fontFamily: 'Noto Sans SC' },
        subtextStyle: { color: '#94A3B8', fontSize: 12, fontFamily: 'Noto Sans SC' }
      }
    })
    return
  }
  const series = trend.value.series
  const dates = series.map((p: any) => p.date)
  const submissions = series.map((p: any) => Math.round(Number(p.submissions || 0)))
  const onboardings = series.map((p: any) => Math.round(Number(p.onboardings || 0)))

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#FFFFFF',
      borderColor: '#E2E8F0',
      borderWidth: 1,
      textStyle: { color: '#0F172A', fontFamily: 'Noto Sans SC', fontSize: 13 },
      axisPointer: { type: 'line', lineStyle: { color: '#CBD5E1', type: 'dashed' } },
      formatter: (params: any[]) => {
        const lines = params.map(p =>
          `<strong style="color:${p.color}">${p.seriesName}</strong> ${p.value}`
        )
        return `<strong>${params[0].axisValueLabel}</strong><br/>` + lines.join('<br/>')
      }
    },
    grid: { left: 40, right: 16, top: 24, bottom: 28, containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#E2E8F0' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#64748B',
        fontFamily: 'JetBrains Mono',
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitNumber: 4,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#F1F5F9', type: 'solid' } },
      axisLabel: {
        color: '#94A3B8',
        fontFamily: 'JetBrains Mono',
        fontSize: 11
      }
    },
    series: [
      {
        name: '新简历',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        lineStyle: { color: '#0F4C5C', width: 2 },
        itemStyle: { color: '#0F4C5C', borderColor: '#FFFFFF', borderWidth: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            // 单色透明渐变，无紫青粉杂色（避免 AI Slop）
            colorStops: [
              { offset: 0, color: 'rgba(15, 76, 92, 0.18)' },
              { offset: 1, color: 'rgba(15, 76, 92, 0)' }
            ]
          }
        },
        data: submissions
      },
      {
        name: '入职',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        lineStyle: { color: '#D97706', width: 2 },
        itemStyle: { color: '#D97706', borderColor: '#FFFFFF', borderWidth: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(217, 119, 6, 0.18)' },
              { offset: 1, color: 'rgba(217, 119, 6, 0)' }
            ]
          }
        },
        data: onboardings
      }
    ]
  }, true)
}

// ============ ECharts 初始化 / 响应 ============
function initCharts() {
  initFunnelChart()
  initTrendChart()
}

// 数据更新时重新渲染（监听 store 中 reactive 数据）
watch(() => funnel.value, () => renderFunnel(), { deep: true })
watch(() => trend.value, () => renderTrend(), { deep: true })

// 筛选范围变化时，store 已经自行重拉数据，我们只需 nextTick 后重渲染
watch(filterRange, async () => {
  await nextTick()
  renderFunnel()
  renderTrend()
})

// 窗口 resize
function handleResize() {
  funnelChart?.resize()
  trendChart?.resize()
}
onMounted(() => {
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
/* ============================================================================
 * V2.0 Dashboard - 局部样式
 * 全部 token 走 theme.css，颜色仅 3 色（深海青 / 琥珀 / Jade 状态）
 * 1px border · 无 shadow · 无渐变标题 · 无装饰 SVG
 * 字号对比：主 KPI 56pt、次 KPI 40pt、卡片标题 15px · 数字字号强调差异化
 * ========================================================================== */
.v20-dashboard {
  width: 100%;
  min-height: 100%;
  padding: 8px 0 32px;
  font-family: var(--font-body);
  color: var(--ink-900);
}

/* ============ 顶部 1 行筛选器 + 元信息 ============ */
.v20-header {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  margin-bottom: var(--space-lg);
}
.v20-header__meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-left: auto;
}
.v20-header__label {
  font-family: var(--font-body);
  font-size: var(--font-size-caption, 13px);
  color: var(--ink-500);
  letter-spacing: 0.02em;
}
.v20-header__chip {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  padding: 2px 10px;
  color: var(--brand-primary-700);
  background: var(--brand-primary-50);
  border: 1px solid var(--brand-primary-100);
  border-radius: var(--radius-sm);
}

/* ============ 16:9 左右分栏 ============ */
.v20-grid {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: var(--space-lg);
  align-items: stretch;
}

/* ============ 左列：3 个 KPI（主 + 2 次）============ */
.v20-col--left {
  display: grid;
  grid-template-rows: 1.6fr 1fr 1fr;
  gap: var(--space-lg);
  min-width: 0;
}
.v20-kpi {
  background: var(--paper);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: border-color 200ms var(--ease-smooth);
}
.v20-kpi:hover {
  border-color: var(--brand-primary-300);
}

/* 主 KPI（左上角最大）*/
.v20-kpi--primary {
  border-color: var(--brand-primary-300);
  background:
    linear-gradient(180deg, var(--brand-primary-50) 0%, var(--paper) 60%);
}
.v20-kpi__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.v20-kpi__label {
  font-family: var(--font-body);
  font-size: var(--font-size-body, 15px);
  font-weight: var(--font-weight-medium, 500);
  color: var(--ink-700);
  letter-spacing: 0.02em;
}
.v20-kpi__hint {
  font-family: var(--font-body);
  font-size: 11px;
  color: var(--ink-500);
  letter-spacing: 0.02em;
}
.v20-kpi__main {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 4px;
  margin-bottom: auto;
}
.v20-kpi__num {
  font-family: var(--font-number);
  font-size: 48px;
  font-weight: var(--font-weight-bold, 700);
  color: var(--ink-900);
  line-height: 1;
  letter-spacing: -0.02em;
}
.v20-kpi__unit {
  font-family: var(--font-body);
  font-size: 18px;
  color: var(--ink-500);
  font-weight: 500;
}
.v20-kpi__trend {
  font-family: var(--font-body);
  font-size: var(--font-size-caption, 13px);
  color: var(--ink-500);
  letter-spacing: 0.02em;
  padding-top: 8px;
  border-top: 1px dashed var(--ink-100);
  margin-top: 4px;
}
.v20-kpi__trend strong {
  font-family: var(--font-number);
  font-weight: var(--font-weight-bold, 700);
  margin-left: 4px;
}
.v20-kpi__arrow {
  font-family: var(--font-number);
  margin-right: 2px;
}
.v20-kpi__trend .is-up {
  color: var(--success-500);
}
.v20-kpi__trend .is-down {
  color: var(--danger-500);
}
.v20-kpi__trend .is-flat {
  color: var(--ink-500);
}

/* 主 KPI 数字放大（Geckoboard #3：左上角最大）*/
.v20-kpi--primary .v20-kpi__num {
  font-size: 56px;
}

/* ============ 右列：3 个卡片（漏斗 / 趋势 / AI）============ */
.v20-col--right {
  display: grid;
  grid-template-rows: 1.1fr 1fr 0.8fr;
  gap: var(--space-lg);
  min-width: 0;
}

.v20-card {
  background: var(--paper);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-lg);
  padding: 18px 22px 14px;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  transition: border-color 200ms var(--ease-smooth);
}
.v20-card:hover {
  border-color: var(--ink-300);
}
.v20-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}
.v20-card__title {
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: var(--font-weight-semibold, 600);
  color: var(--ink-900);
  letter-spacing: 0.02em;
}
.v20-card__sub {
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--ink-500);
  margin-top: 2px;
  letter-spacing: 0.02em;
}
.v20-card__tip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--ink-500);
  white-space: nowrap;
}
.v20-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--ink-100);
  color: var(--ink-500);
  font-family: var(--font-number);
  font-style: italic;
  font-size: 11px;
  font-weight: 600;
  cursor: help;
}
.v20-card__tip-text {
  letter-spacing: 0.02em;
}

/* ============ 通用 ECharts 占位 ============ */
.v20-echarts {
  flex: 1;
  width: 100%;
  min-height: 0;
}
.v20-skel {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--ink-300);
  background: var(--ink-50);
  border-radius: var(--radius-sm);
}

/* ============ 漏斗图专属 ============ */
.v20-echarts--funnel {
  min-height: 180px;
}
.v20-funnel-foot {
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px dashed var(--ink-100);
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--ink-500);
  letter-spacing: 0.02em;
}
.v20-funnel-foot__rate {
  font-family: var(--font-number);
  font-weight: var(--font-weight-bold, 700);
  font-size: 14px;
  color: var(--success-500);
}

/* ============ 趋势图 Legend ============ */
.v20-card__legend {
  display: flex;
  align-items: center;
  gap: 12px;
}
.v20-legend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--ink-500);
  letter-spacing: 0.02em;
}
.v20-legend__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.v20-legend__dot--primary {
  background: var(--brand-primary-500);
}
.v20-legend__dot--amber {
  background: var(--accent-amber);
}

/* ============ AI 评分卡片（数字 + 上下文化）============ */
.v20-ai {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 24px;
  padding-top: 4px;
}
.v20-ai__main {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.v20-ai__num {
  font-family: var(--font-number);
  font-size: 64px;
  font-weight: var(--font-weight-bold, 700);
  color: var(--brand-primary-500);
  line-height: 1;
  letter-spacing: -0.02em;
}
.v20-ai__unit {
  font-family: var(--font-body);
  font-size: 18px;
  color: var(--ink-500);
  font-weight: 500;
}
.v20-ai__meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-left: 1px solid var(--ink-100);
  padding-left: 24px;
}
.v20-ai__line {
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--ink-700);
  letter-spacing: 0.02em;
}
.v20-ai__line strong {
  font-family: var(--font-number);
  font-weight: var(--font-weight-bold, 700);
  margin-left: 4px;
}
.v20-ai__line--muted {
  font-size: 12px;
  color: var(--ink-500);
}
.v20-ai__line .is-up {
  color: var(--success-500);
}
.v20-ai__line .is-down {
  color: var(--danger-500);
}
.v20-ai__line .is-flat {
  color: var(--ink-500);
}
.v20-ai__arrow {
  font-family: var(--font-number);
  margin-right: 2px;
}

/* ============ 错误兜底 ============ */
.v20-error {
  margin-top: var(--space-lg);
  padding: 12px 16px;
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--warning-500);
  background: var(--warning-50);
  border: 1px solid var(--warning-500);
  border-radius: var(--radius-sm);
  letter-spacing: 0.02em;
}

/* ============ 响应式 ============ */
@media (max-width: 1280px) {
  .v20-grid {
    grid-template-columns: 1fr;
  }
  .v20-col--left {
    grid-template-rows: auto;
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 768px) {
  .v20-grid {
    grid-template-columns: 1fr;
  }
  .v20-col--left {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }
  .v20-kpi__num {
    font-size: 40px;
  }
  .v20-kpi--primary .v20-kpi__num {
    font-size: 48px;
  }
  .v20-ai__num {
    font-size: 48px;
  }
}
</style>
