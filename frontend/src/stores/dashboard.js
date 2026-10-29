import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import { getAllProjectsApi } from '@/api/project'
import { getAllPositionsApi } from '@/api/position'
import { request } from '@/utils/request'

/**
 * Dashboard Pinia Store (V1.2 准备工作)
 *
 * 职责：
 *   - 维护 3 个筛选条件：项目 / 职位 / 时间范围
 *   - 缓存 4 个 dashboard API 的数据
 *   - 缓存项目列表和职位列表（用于筛选下拉）
 *   - 提供统一的 filterParams getter，供 4 个 load action 共用
 *
 * 与 V1.1 视图的关系：
 *   - 本 store 不被 views/dashboard/index.vue 引用
 *   - subagent 3 才会把 V1.1 视图改成消费本 store
 *   - 当前任务只加新文件，不动旧文件
 */

export const useDashboardStore = defineStore('dashboard', () => {
  // ========== State: 筛选条件 ==========
  const filterProjectId = ref(null)        // null = 全部项目
  const filterPositionId = ref(null)       // null = 全部职位
  const filterRange = ref('month')         // 'month' | 'quarter' | 'year'

  // ========== State: 数据缓存 ==========
  const realtime = ref(null)
  // 结构：{ today_resumes, today_onboardings, today_interviews, today_active_positions, today_new_positions }

  const trend = ref(null)
  // 结构：{ range, data: [{ date, resumes, onboardings, interviews }], total }

  const funnel = ref(null)
  // 结构：{ range, stages: [...], rates: [...], counts: [...], note }

  const aiScore = ref(null)
  // 结构：{ range, avg_score, sample_count, vs_last_period, distribution }

  // ========== State: 维度数据 ==========
  const projects = ref([])    // 从 /projects/all 拉
  const positions = ref([])   // 从 /positions/all?project_id=xxx 拉

  // ========== State: 加载状态 ==========
  const loading = reactive({
    realtime: false,
    trend: false,
    funnel: false,
    aiScore: false,
    projects: false,
    positions: false
  })

  // ========== Getters ==========

  /**
   * 当前筛选条件打包，供 4 个 dashboard API 共用
   * 注意：保持 null 而非 undefined，与后端约定一致（后端用 null 表示"不过滤"）
   */
  const filterParams = computed(() => ({
    project_id: filterProjectId.value,
    position_id: filterPositionId.value,
    range: filterRange.value
  }))

  /**
   * 当前是否有筛选生效（用于 UI 显示"已筛选"标识）
   */
  const hasFilter = computed(() => {
    return filterProjectId.value !== null || filterPositionId.value !== null
  })

  // ========== Actions: 维度数据 ==========

  /**
   * 拉取所有项目，用于筛选下拉
   */
  const loadProjects = async () => {
    loading.projects = true
    try {
      const res = await getAllProjectsApi()
      // 后端约定：{ code, message, data }，code=0 成功
      projects.value = res.data || []
    } catch (err) {
      console.error('[dashboard store] loadProjects failed:', err)
      projects.value = []
    } finally {
      loading.projects = false
    }
  }

  /**
   * 拉取职位列表，可按项目过滤
   * @param {number|null} projectId 传 null 拉全部；传数字则只拉该项目下的职位
   */
  const loadPositions = async (projectId = null) => {
    loading.positions = true
    try {
      const params = projectId !== null && projectId !== undefined
        ? { project_id: projectId }
        : {}
      const res = await getAllPositionsApi(params)
      positions.value = res.data || []
    } catch (err) {
      console.error('[dashboard store] loadPositions failed:', err)
      positions.value = []
    } finally {
      loading.positions = false
    }
  }

  // ========== Actions: dashboard API ==========

  /**
   * 实时今日数据：今日新简历 / 入职 / 面试 / 活跃职位
   */
  const loadRealtime = async () => {
    loading.realtime = true
    try {
      const res = await request.get('/dashboard/realtime', {
        params: {
          project_id: filterProjectId.value,
          position_id: filterPositionId.value
        }
      })
      realtime.value = res.data || null
    } catch (err) {
      console.error('[dashboard store] loadRealtime failed:', err)
      realtime.value = null
    } finally {
      loading.realtime = false
    }
  }

  /**
   * 趋势数据：时间序列简历/入职/面试
   */
  const loadTrend = async () => {
    loading.trend = true
    try {
      const res = await request.get('/dashboard/trend', {
        params: filterParams.value
      })
      trend.value = res.data || null
    } catch (err) {
      console.error('[dashboard store] loadTrend failed:', err)
      trend.value = null
    } finally {
      loading.trend = false
    }
  }

  /**
   * 漏斗数据：招聘流程各阶段转化
   */
  const loadFunnel = async () => {
    loading.funnel = true
    try {
      const res = await request.get('/dashboard/funnel', {
        params: filterParams.value
      })
      funnel.value = res.data || null
    } catch (err) {
      console.error('[dashboard store] loadFunnel failed:', err)
      funnel.value = null
    } finally {
      loading.funnel = false
    }
  }

  /**
   * AI 评分均值与对比
   */
  const loadAiScore = async () => {
    loading.aiScore = true
    try {
      const res = await request.get('/dashboard/ai-score', {
        params: filterParams.value
      })
      aiScore.value = res.data || null
    } catch (err) {
      console.error('[dashboard store] loadAiScore failed:', err)
      aiScore.value = null
    } finally {
      loading.aiScore = false
    }
  }

  /**
   * 一键拉全部 4 个 dashboard 数据
   * 用于初次进入或全量刷新场景
   */
  const loadAll = async () => {
    await Promise.all([
      loadRealtime(),
      loadTrend(),
      loadFunnel(),
      loadAiScore()
    ])
  }

  // ========== Actions: 筛选变更 ==========

  /**
   * 改变项目筛选，会自动重置职位筛选（项目变了职位要重选）
   * @param {number|null} projectId
   */
  const setProject = async (projectId) => {
    filterProjectId.value = projectId
    filterPositionId.value = null   // 联动重置
    // 联动 reload 职位列表
    await loadPositions(projectId)
  }

  /**
   * 改变职位筛选
   * @param {number|null} positionId
   */
  const setPosition = (positionId) => {
    filterPositionId.value = positionId
  }

  /**
   * 改变时间范围
   * @param {'month'|'quarter'|'year'} range
   */
  const setRange = (range) => {
    if (['month', 'quarter', 'year'].includes(range)) {
      filterRange.value = range
    }
  }

  /**
   * 清空全部筛选，恢复默认
   */
  const reset = () => {
    filterProjectId.value = null
    filterPositionId.value = null
    filterRange.value = 'month'
    realtime.value = null
    trend.value = null
    funnel.value = null
    aiScore.value = null
  }

  return {
    // state
    filterProjectId,
    filterPositionId,
    filterRange,
    realtime,
    trend,
    funnel,
    aiScore,
    projects,
    positions,
    loading,

    // getters
    filterParams,
    hasFilter,

    // actions
    loadProjects,
    loadPositions,
    loadRealtime,
    loadTrend,
    loadFunnel,
    loadAiScore,
    loadAll,
    setProject,
    setPosition,
    setRange,
    reset
  }
})