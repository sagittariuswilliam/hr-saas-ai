<template>
  <div class="resumes-page">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <el-select
        v-model="searchParams.project_id"
        placeholder="选择项目"
        style="width: 160px; margin-right: 12px"
        clearable
        @change="loadPositions; loadResumes"
      >
        <el-option
          v-for="item in projectList"
          :key="item.id"
          :label="item.project_name"
          :value="item.id"
        />
      </el-select>
      <el-select
        v-model="searchParams.position_id"
        placeholder="选择职位"
        style="width: 180px; margin-right: 12px"
        clearable
        @change="loadResumes"
      >
        <el-option
          v-for="item in positionList"
          :key="item.id"
          :label="item.position_name"
          :value="item.id"
        />
      </el-select>
      <el-select
        v-model="searchParams.status"
        placeholder="简历状态"
        style="width: 140px; margin-right: 12px"
        clearable
        @change="loadResumes"
      >
        <el-option :value="'submitted'" label="已提交" />
        <el-option :value="'viewed'" label="已查看" />
        <el-option :value="'interview_scheduled'" label="已约面" />
        <el-option :value="'interviewing'" label="面试中" />
        <el-option :value="'hired'" label="已录用" />
        <el-option :value="'onboarded'" label="已入职" />
        <el-option :value="'rejected'" label="已淘汰" />
      </el-select>
      <el-input
        v-model="searchParams.keyword"
        placeholder="搜索姓名/手机号"
        style="width: 200px; margin-right: 12px"
        clearable
        @keyup.enter="loadResumes"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" @click="handleUpload">
        <el-icon><Upload /></el-icon>
        上传简历
      </el-button>
      <el-button @click="refresh">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 简历列表 -->
    <div class="table-container">
      <el-table
        :data="resumeList"
        v-loading="loading"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="candidate_name" label="候选人姓名" width="120" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="email" label="邮箱" width="180" />
        <el-table-column prop="work_years" label="工作年限" width="100" />
        <el-table-column prop="education" label="学历" width="100" />
        <el-table-column prop="project_name" label="项目" width="140" />
        <el-table-column prop="position_name" label="职位" width="160" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="AI匹配度" width="130">
          <template #default="{ row }">
            <div class="match-score" :class="getMatchScoreClass(row.match_score)">
              <template v-if="row.match_score === null || row.match_score === undefined">
                <span class="score">--</span>
                <span class="label">{{ row.position_id ? (isScoring(row) ? '评分中…' : '未分析') : '未分析' }}</span>
              </template>
              <template v-else>
                <span class="score">{{ row.match_score }}</span>
                <span class="label">{{ getMatchLabel(row.match_score) }}</span>
              </template>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="AI面试" width="100">
          <template #default="{ row }">
            <el-tag v-if="ivSummary[row.id]" :type="ivStatusTagType(ivSummary[row.id])" size="small" effect="light">
              {{ ivStatusText(ivSummary[row.id]) }}
            </el-tag>
            <span v-else class="iv-none">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="420" fixed="right">
          <template #default="{ row }">
            <el-dropdown @command="(cmd) => changeStatus(row, cmd)" trigger="click">
              <el-button link type="warning" size="small">
                更改状态
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="submitted">已提交</el-dropdown-item>
                  <el-dropdown-item command="viewed">已查看</el-dropdown-item>
                  <el-dropdown-item command="interview_scheduled">已约面</el-dropdown-item>
                  <el-dropdown-item command="interviewing">面试中</el-dropdown-item>
                  <el-dropdown-item command="hired">已录用</el-dropdown-item>
                  <el-dropdown-item command="onboarded">已入职</el-dropdown-item>
                  <el-dropdown-item divided command="rejected">淘汰</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button link type="primary" size="small" @click="viewMatchDetail(row)">AI分析</el-button>
            <el-button link type="primary" size="small" @click="openAiInterview(row)">AI面试</el-button>
            <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
            <el-button link type="success" size="small" @click="downloadResume(row)">下载</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pageParams.page"
          v-model:page-size="pageParams.page_size"
          :total="pageParams.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadResumes"
          @current-change="loadResumes"
        />
      </div>
    </div>

    <!-- 批量上传弹窗 -->
    <el-dialog v-model="uploadVisible" title="批量上传简历" width="560px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="所属项目">
          <el-select v-model="uploadForm.project_id" placeholder="请选择项目" style="width: 100%" clearable>
            <el-option
              v-for="item in projectList"
              :key="item.id"
              :label="item.project_name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="所属职位">
          <el-select v-model="uploadForm.position_id" placeholder="请选择职位" style="width: 100%" clearable>
            <el-option
              v-for="item in positionList"
              :key="item.id"
              :label="item.position_name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <el-upload
        ref="uploadRef"
        class="batch-uploader"
        :auto-upload="false"
        :multiple="true"
        :limit="10"
        :on-exceed="handleExceed"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        drag
        accept=".pdf,.doc,.docx"
        action="#"
      >
        <el-icon class="batch-uploader__icon"><upload-filled /></el-icon>
        <div class="batch-uploader__text">
          拖拽文件到此处，或 <em>点击选择</em>
        </div>
        <template #tip>
          <div class="batch-uploader__tip">
            支持 PDF / DOC / DOCX，单文件 ≤ 10MB，一次最多 10 份
          </div>
        </template>
      </el-upload>

      <!-- 已选文件清单 -->
      <div class="batch-files" v-if="batchFiles.length">
        <div class="batch-files__head">
          <span class="batch-files__title">已选文件</span>
          <span class="batch-files__count">{{ batchFiles.length }} / 10</span>
        </div>
        <ul class="batch-files__list">
          <li v-for="(f, idx) in batchFiles" :key="f.uid" class="batch-files__item">
            <span class="batch-files__name">{{ f.name }}</span>
            <span class="batch-files__size">{{ formatSize(f.size) }}</span>
            <el-button link type="danger" size="small" :disabled="uploading" @click="removeBatchFile(idx)">移除</el-button>
          </li>
        </ul>
      </div>

      <!-- 上传结果 -->
      <div class="batch-results" v-if="batchResults">
        <div class="batch-results__head">
          <span class="batch-results__title">上传结果</span>
          <span class="batch-results__summary">
            共 {{ batchResults.total }} 份，成功
            <span class="num num--ok">{{ batchResults.succeeded }}</span>
            ，失败
            <span class="num num--err">{{ batchResults.failed }}</span>
          </span>
        </div>
        <ul class="batch-results__list">
          <li
            v-for="r in batchResults.results"
            :key="r.filename"
            class="batch-results__item"
            :class="{ 'is-ok': r.status === 'success', 'is-err': r.status === 'failed' }"
          >
            <span class="batch-results__mark">{{ r.status === 'success' ? '✓' : '✗' }}</span>
            <span class="batch-results__name">{{ r.filename }}</span>
            <span class="batch-results__detail">
              <template v-if="r.status === 'success'">
                ID {{ r.resume_id }}<template v-if="r.candidate_name"> · {{ r.candidate_name }}</template>
              </template>
              <template v-else>{{ r.error }}</template>
            </span>
          </li>
        </ul>
      </div>

      <template #footer>
        <el-button @click="uploadVisible = false" :disabled="uploading">关闭</el-button>
        <el-button
          type="primary"
          :disabled="batchFiles.length === 0 || uploading"
          :loading="uploading"
          @click="submitBatchUpload"
        >
          {{ uploading ? `上传中 ${batchProgress.done}/${batchProgress.total}` : '开始上传' }}
        </el-button>
      </template>
    </el-dialog>
    <!-- AI匹配详情弹窗 -->
    <el-dialog v-model="matchVisible" title="AI简历匹配分析" width="900px">
      <div class="match-detail" v-if="currentMatch">
        <!-- 顶部匹配概览 -->
        <div class="match-overview">
          <div class="match-circle">
            <div class="circle-inner">
              <span class="score">{{ currentMatch.match_score }}</span>
              <span class="unit">分</span>
            </div>
          </div>
          <div class="match-info">
            <h3>{{ currentMatch.candidate_name }} <small>- {{ currentMatch.position_name }}</small></h3>
            <p class="recommendation">
              <el-tag :type="getMatchTagType(currentMatch.match_score)" size="large">
                {{ getMatchLabel(currentMatch.match_score) }}
              </el-tag>
            </p>
            <p class="match-desc">{{ currentMatch.summary || 'AI综合分析简历与职位要求的匹配度' }}</p>
          </div>
        </div>

        <!-- 4个匹配维度 -->
        <div class="match-dimensions">
          <h4>匹配维度分析</h4>
          <div class="dimension-list">
            <div class="dimension-item" v-for="(item, index) in currentMatch.dimensions" :key="index">
              <div class="dimension-header">
                <span class="dimension-name">{{ item.name }}</span>
                <span class="dimension-weight">（权重 {{ item.weight }}%）</span>
                <span class="dimension-score">{{ item.score }}分</span>
              </div>
              <el-progress 
                :percentage="item.score" 
                :color="getDimensionColor(item.score)"
                :stroke-width="8"
              />
            </div>
          </div>
        </div>

        <!-- 匹配点和不匹配点 -->
        <div class="match-points">
          <div class="points-column">
            <h4 class="pros-title">👍 关键匹配点</h4>
            <ul class="points-list">
              <li v-for="(item, index) in currentMatch.pros" :key="index">{{ item }}</li>
            </ul>
          </div>
          <div class="points-column">
            <h4 class="cons-title">⚠️ 需关注的点</h4>
            <ul class="points-list">
              <li v-for="(item, index) in currentMatch.cons" :key="index">{{ item }}</li>
            </ul>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 简历详情弹窗 -->
    <el-dialog v-model="detailVisible" title="简历详情" width="700px">
      <div class="resume-detail" v-if="currentDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="候选人姓名">{{ currentDetail.candidate_name }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ currentDetail.phone }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ currentDetail.email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="工作年限">{{ currentDetail.work_years ? currentDetail.work_years + '年' : '-' }}</el-descriptions-item>
          <el-descriptions-item label="学历">{{ currentDetail.education || '-' }}</el-descriptions-item>
          <el-descriptions-item label="所属项目">{{ currentDetail.project_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="应聘职位">{{ currentDetail.position_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="getStatusType(currentDetail.status)">{{ getStatusText(currentDetail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentDetail.created_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ currentDetail.updated_at || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <!-- AI 面试抽屉 -->
    <AiInterviewDrawer v-model="interviewVisible" :resume="interviewResume" />

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Upload, Refresh, ArrowDown, UploadFilled } from '@element-plus/icons-vue'
import { getAllProjectsApi, type Project } from '@/api/project'
import { getAllPositionsApi, type Position } from '@/api/position'
import {
  getResumeListApi,
  deleteResumeApi,
  downloadResumeApi,
  updateResumeStatusApi,
  analyzeResumeApi,
  getResumeDetailApi,
  uploadBatchResumeApi,
  type BatchUploadResponse,
  type Resume
} from '@/api/resume'
import { useUserStore } from '@/stores/user'
import AiInterviewDrawer from '@/views/interview/AiInterviewDrawer.vue'
import { getInterviewSummaryApi, type InterviewSummaryItem } from '@/api/interview'

// AI 面试状态摘要（简历列表 badge 列）
const ivSummary = reactive<Record<number, InterviewSummaryItem>>({})

const loadInterviewSummary = async (ids: number[]) => {
  if (!ids.length) return
  try {
    const res = await getInterviewSummaryApi(ids)
    Object.keys(ivSummary).forEach(k => delete ivSummary[Number(k)])
    Object.entries(res.data || {}).forEach(([k, v]) => { ivSummary[Number(k)] = v })
  } catch { /* 静默：badge 列非关键路径 */ }
}

const ivStatusText = (item: InterviewSummaryItem) => {
  if (item.total_score !== null && item.total_score !== undefined) return item.total_score + '分'
  return ({ draft: '待出题', sent: '待作答', in_progress: '进行中', submitted: '待评分', report_ready: '待评分', expired: '已过期' } as Record<string, string>)[item.status] || item.status
}

const ivStatusTagType = (item: InterviewSummaryItem) => {
  if (item.total_score !== null && item.total_score !== undefined) {
    return item.total_score >= 75 ? 'success' : item.total_score >= 60 ? 'warning' : 'danger'
  }
  return ({ draft: 'info', sent: 'primary', in_progress: 'warning', report_ready: 'success', submitted: 'success', expired: 'danger' } as Record<string, string>)[item.status] || 'info'
}

const userStore = useUserStore()

// AI 面试抽屉
const interviewVisible = ref(false)
const interviewResume = ref<any>(null)
const openAiInterview = (row: Resume) => {
  interviewResume.value = row
  interviewVisible.value = true
}

// 列表相关
const loading = ref(false)
const currentMatch = ref<any>(null)
const currentDetail = ref<any>(null)
const resumeList = ref<Resume[]>([])
const projectList = ref<Project[]>([])
const positionList = ref<Position[]>([])

const pageParams = reactive({
  page: 1,
  page_size: 10,
  total: 0
})

const searchParams = reactive({
  project_id: null as number | null,
  position_id: null as number | null,
  status: null as string | null,
  keyword: ''
})

// 上传相关
const uploadVisible = ref(false)
const uploadRef = ref()
// 已选文件（来自 el-upload 内部 uploadFiles）
interface BatchFile {
  uid: number
  name: string
  size: number
  raw: File
}
const batchFiles = ref<BatchFile[]>([])
const uploading = ref(false)
const batchResults = ref<BatchUploadResponse | null>(null)
const batchProgress = reactive({ done: 0, total: 0 })

// AI匹配详情相关
const matchVisible = ref(false)
const detailVisible = ref(false)

const uploadForm = reactive({
  project_id: null as number | null,
  position_id: null as number | null
})

// 加载项目列表
const loadProjects = async () => {
  try {
    const res = await getAllProjectsApi()
    projectList.value = res.data
  } catch (error) {
    console.error('加载项目列表失败:', error)
  }
}

// 加载职位列表
const loadPositions = async () => {
  try {
    const params: any = {}
    if (searchParams.project_id) {
      params.project_id = searchParams.project_id
    }
    const res = await getAllPositionsApi(params)
    positionList.value = res.data
  } catch (error) {
    console.error('加载职位列表失败:', error)
  }
}

// 加载简历列表
const scoringIds = ref<Set<number>>(new Set())
let scorePollTimer: ReturnType<typeof setInterval> | null = null

const isScoring = (row: any) => scoringIds.value.has(row.id)

// 方案B：上传后 AI 评分在后台进行，轮询列表直到分数出现（15s 一次，最长 3 分钟）
const startScorePolling = () => {
  const ids = (batchResults.value?.results || [])
    .filter((r) => r.status === 'success' && r.resume_id)
    .map((r) => r.resume_id as number)
  scoringIds.value = new Set(ids)
  if (scorePollTimer) clearInterval(scorePollTimer)
  let ticks = 0
  scorePollTimer = setInterval(async () => {
    ticks++
    await loadResumes()
    const done = resumeList.value
      .filter((r: any) => ids.includes(r.id))
      .every((r: any) => r.match_score !== null && r.match_score !== undefined)
    if (done || ticks >= 12) {
      if (scorePollTimer) clearInterval(scorePollTimer)
      scorePollTimer = null
      scoringIds.value = new Set()
    }
  }, 15000)
}

const loadResumes = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pageParams.page,
      page_size: pageParams.page_size
    }
    if (searchParams.project_id) params.project_id = searchParams.project_id
    if (searchParams.position_id) params.position_id = searchParams.position_id
    if (searchParams.status) params.status = searchParams.status
    if (searchParams.keyword) params.keyword = searchParams.keyword
    
    const res = await getResumeListApi(params)
    resumeList.value = res.data.items
    pageParams.total = res.data.total
    loadInterviewSummary(res.data.items.map((r: any) => r.id))
  } catch (error) {
    console.error('加载简历列表失败:', error)
    ElMessage.error('加载简历列表失败')
  } finally {
    loading.value = false
  }
}

// 刷新
const refresh = () => {
  loadResumes()
}

// 打开上传弹窗
const handleUpload = () => {
  // 重置表单
  uploadForm.project_id = null
  uploadForm.position_id = null
  batchFiles.value = []
  batchResults.value = null
  batchProgress.done = 0
  batchProgress.total = 0
  // 清空 el-upload 内部 fileList（下次宏任务执行，等 ref 准备好）
  setTimeout(() => {
    uploadRef.value?.clearFiles?.()
  }, 0)
  // 先加载所有职位（不筛选项目）
  loadPositionsForUpload()
  uploadVisible.value = true
}

const ALLOWED_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]
const ALLOWED_EXT = ['.pdf', '.doc', '.docx']

const isAllowedFile = (file: File) => {
  const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
  if (ALLOWED_EXT.includes(ext)) return true
  return ALLOWED_TYPES.includes(file.type)
}

const isAllowedSize = (file: File) => file.size / 1024 / 1024 < 10

const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

// el-upload on-change：维护我们自己的 batchFiles 列表
const handleFileChange = (file: any, fileList: any[]) => {
  const raw = file.raw as File
  // 单文件级校验（仅提示，不阻止入列；后端会按文件级报错）
  if (!isAllowedFile(raw)) {
    ElMessage.warning(`「${raw.name}」格式不支持，已忽略`)
    // 从 el-upload 内部 fileList 移除（设置响应式原数组）
    const idx = fileList.findIndex((f: any) => f.uid === file.uid)
    if (idx >= 0) fileList.splice(idx, 1)
    return
  }
  if (!isAllowedSize(raw)) {
    ElMessage.warning(`「${raw.name}」超过 10MB，已忽略`)
    const idx = fileList.findIndex((f: any) => f.uid === file.uid)
    if (idx >= 0) fileList.splice(idx, 1)
    return
  }
  // 从 el-upload 的 fileList 同步到我们的 batchFiles
  batchFiles.value = fileList
    .filter((f: any) => f.status !== 'fail')
    .map((f: any) => ({
      uid: f.uid,
      name: f.name,
      size: f.size,
      raw: f.raw as File
    }))
}

const handleFileRemove = (file: any, fileList: any[]) => {
  batchFiles.value = fileList.map((f: any) => ({
    uid: f.uid,
    name: f.name,
    size: f.size,
    raw: f.raw as File
  }))
}

const removeBatchFile = (idx: number) => {
  batchFiles.value.splice(idx, 1)
}

const handleExceed = () => {
  ElMessage.warning('一次最多上传 10 份简历，请分批操作')
}

// 提交批量上传（1 次 HTTP）
const submitBatchUpload = async () => {
  if (batchFiles.value.length === 0) return
  if (!uploadForm.project_id || !uploadForm.position_id) {
    ElMessage.warning('请先选择项目和职位')
    return
  }
  uploading.value = true
  batchResults.value = null
  batchProgress.done = 0
  batchProgress.total = batchFiles.value.length
  const files = batchFiles.value.map((f) => f.raw)
  try {
    const data = await uploadBatchResumeApi(
      files,
      uploadForm.project_id,
      uploadForm.position_id
    )
    batchResults.value = data
    batchProgress.done = data.total
    if (data.failed === 0) {
      ElMessage.success(
        uploadForm.position_id
          ? `上传成功 ${data.succeeded} 份，AI 评分进行中，约 1 分钟内陆续出分`
          : `上传完成：成功 ${data.succeeded} 份`
      )
    } else if (data.succeeded === 0) {
      ElMessage.error(`上传失败：${data.failed} 份文件全部失败`)
    } else {
      ElMessage.warning(`部分成功：成功 ${data.succeeded} 份，失败 ${data.failed} 份`)
    }
    if (data.succeeded > 0) {
      loadResumes()
      // 方案B：AI 评分转为后台任务，轮询刷新直到分数出现（最长约 3 分钟）
      if (uploadForm.position_id) startScorePolling()
    }
  } catch (err: any) {
    ElMessage.error(err?.message || '上传失败，请稍后重试')
    batchProgress.done = batchProgress.total
  } finally {
    uploading.value = false
  }
}

// 加载上传用的职位列表
const loadPositionsForUpload = async (project_id: number | null = null) => {
  try {
    const params: any = {}
    if (project_id) {
      params.project_id = project_id
    }
    const res = await getAllPositionsApi(params)
    positionList.value = res.data
  } catch (error) {
    console.error('加载职位列表失败:', error)
  }
}

// 监听项目变化，筛选职位
watch(
  () => uploadForm.project_id,
  (newProjectId) => {
    // 清空已选职位
    uploadForm.position_id = null
    // 加载该项目下的职位（或全部）
    loadPositionsForUpload(newProjectId)
  }
)


// 状态文本和样式
const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    'submitted': '已提交',
    'viewed': '已查看',
    'interview_scheduled': '已约面',
    'interviewing': '面试中',
    'hired': '已录用',
    'rejected': '已淘汰',
    'onboarded': '已入职'
  }
  return map[status] || '待审核'
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    'submitted': 'info',
    'viewed': 'primary',
    'interview_scheduled': 'warning',
    'interviewing': 'warning',
    'hired': 'success',
    'rejected': 'danger',
    'onboarded': 'success'
  }
  return map[status] || 'info'
}
const getMatchScoreClass = (score: number | undefined | null) => {
  if (score === undefined || score === null) return 'poor'
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  if (score >= 40) return 'normal'
  return 'poor'
}

const getMatchLabel = (score: number | undefined | null) => {
  if (score === undefined || score === null) return '未分析'
  if (score >= 80) return '强烈推荐'
  if (score >= 60) return '推荐'
  if (score >= 40) return '考虑'
  return '不匹配'
}

// 匹配度标签样式
const getMatchTagType = (score: number | undefined | null) => {
  if (score === undefined || score === null) return 'info'
  if (score >= 80) return 'success'
  if (score >= 60) return 'primary'
  if (score >= 40) return 'warning'
  return 'danger'
}

// 维度进度条颜色
const getDimensionColor = (score: number) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#409eff'
  if (score >= 40) return '#e6a23c'
  return '#f56c6c'
}


const changeStatus = async (row: Resume, status: string) => {
  try {
    await updateResumeStatusApi(row.id, status)
    ElMessage.success('状态更新成功')
    loadResumes()
  } catch (error) {
    console.error('状态更新失败:', error)
    ElMessage.error('状态更新失败')
  }
}

// 问题4修复：AI分析详情弹窗
const viewMatchDetail = async (row: Resume) => {
  try {
    const res = await analyzeResumeApi(row.id)
    currentMatch.value = res.data
    matchVisible.value = true
  } catch (error) {
    console.error('获取AI分析结果失败:', error)
    ElMessage.error('获取AI分析结果失败')
  }
}

// 问题5修复：简历详情弹窗
const viewDetail = async (row: Resume) => {
  try {
    const res = await getResumeDetailApi(row.id)
    currentDetail.value = res.data
    detailVisible.value = true
  } catch (error) {
    console.error('获取简历详情失败:', error)
    ElMessage.error('获取简历详情失败')
  }
}

// 问题6修复：下载简历
const downloadResume = async (row: Resume) => {
  try {
    await downloadResumeApi(row.id)
    ElMessage.success('下载成功')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败')
  }
}

// 删除简历
const handleDelete = (row: Resume) => {
  ElMessageBox.confirm(
    `确定要删除候选人「${row.candidate_name}」的简历吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteResumeApi(row.id)
      ElMessage.success('删除成功')
      loadResumes()
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  })
}

// 查看详情
const handleView = (row: Resume) => {
  ElMessage.info('简历详情功能开发中')
}

// 分页
const handlePageChange = (page: number) => {
  pageParams.page = page
  loadResumes()
}

const handleSizeChange = (size: number) => {
  pageParams.page_size = size
  pageParams.page = 1
  loadResumes()
}

// 筛选
const handleSearch = () => {
  pageParams.page = 1
  loadResumes()
}

const handleReset = () => {
  searchParams.project_id = null
  searchParams.position_id = null
  searchParams.keyword = ''
  pageParams.page = 1
  loadPositions()
  loadResumes()
}

// 监听筛选项目变化，加载职位
watch(
  () => searchParams.project_id,
  () => {
    searchParams.position_id = null
    loadPositions()
  }
)

onMounted(() => {
  loadProjects()
  loadResumes()
})

onUnmounted(() => {
  if (scorePollTimer) clearInterval(scorePollTimer)
})
</script>


/* AI匹配度样式 */
.match-score {
  text-align: center;
}
.match-score .score {
  font-size: 18px;
  font-weight: bold;
  margin-right: 4px;
}
.match-score .label {
  font-size: 12px;
}
.match-score.excellent .score { color: #67c23a; }
.match-score.good .score { color: #409eff; }
.match-score.normal .score { color: #e6a23c; }
.match-score.poor .score { color: #f56c6c; }

/* 匹配详情样式 */
.match-overview {
  display: flex;
  gap: 30px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 24px;
}
.match-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #67c23a);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.circle-inner {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.circle-inner .score {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
  line-height: 1;
}
.circle-inner .unit {
  font-size: 12px;
  color: #909399;
}
.match-info h3 {
  margin: 0 0 8px;
  font-size: 18px;
}
.match-info small {
  color: #909399;
  font-weight: normal;
}
.match-desc {
  color: #606266;
  margin-top: 8px;
}

.match-dimensions h4 {
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}
.dimension-list {
  display: grid;
  gap: 16px;
}
.dimension-item {
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 6px;
}
.dimension-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}
.dimension-name {
  font-weight: 500;
}
.dimension-weight {
  color: #909399;
  font-size: 12px;
  margin-left: 6px;
}
.dimension-score {
  margin-left: auto;
  font-weight: bold;
  color: #409eff;
}

.match-points {
  margin-top: 24px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
.match-points h4 {
  margin: 0 0 12px;
}
.pros-title { color: #67c23a; }
.cons-title { color: #e6a23c; }
.points-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.points-list li {
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 4px;
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.5;
}
.points-list li:last-child {
  margin-bottom: 0;
}
<style scoped lang="scss">
.resumes-page {
  padding: 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}

.table-container {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* ===== 批量上传弹窗样式（V2.0 Carbon 风格） ===== */
.batch-uploader {
  :deep(.el-upload) {
    border: 1px dashed #dcdfe6;
    border-radius: 0;
    background: #fafbfc;
  }
  :deep(.el-upload-dragger) {
    border: none;
    background: transparent;
    padding: 24px 16px;
  }
}
.batch-uploader__icon {
  font-size: 28px;
  color: #606266;
  margin-bottom: 8px;
}
.batch-uploader__text {
  font-size: 14px;
  color: #606266;
  em {
    color: #409eff;
    font-style: normal;
  }
}
.batch-uploader__tip {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

.batch-files {
  margin-top: 16px;
  border: 1px solid #ebeef5;
  &__head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid #ebeef5;
    background: #fafbfc;
  }
  &__title {
    font-size: 13px;
    color: #303133;
    font-weight: 500;
  }
  &__count {
    font-size: 12px;
    color: #606266;
    font-family: var(--font-number);
  }
  &__list {
    list-style: none;
    margin: 0;
    padding: 0;
    max-height: 180px;
    overflow-y: auto;
  }
  &__item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 12px;
    border-bottom: 1px solid #f2f3f5;
    font-size: 13px;
    &:last-child { border-bottom: none; }
  }
  &__name {
    flex: 1;
    color: #303133;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  &__size {
    color: #909399;
    font-family: var(--font-number);
    font-size: 12px;
  }
}

.batch-results {
  margin-top: 16px;
  border: 1px solid #ebeef5;
  &__head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid #ebeef5;
    background: #fafbfc;
  }
  &__title {
    font-size: 13px;
    color: #303133;
    font-weight: 500;
  }
  &__summary {
    font-size: 12px;
    color: #606266;
  }
  .num {
    font-family: var(--font-number);
    font-weight: 600;
    padding: 0 2px;
  }
  .num--ok { color: #27a644; }
  .num--err { color: #d83a3a; }
  &__list {
    list-style: none;
    margin: 0;
    padding: 0;
    max-height: 240px;
    overflow-y: auto;
  }
  &__item {
    display: grid;
    grid-template-columns: 16px 1fr 1fr;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-bottom: 1px solid #f2f3f5;
    font-size: 13px;
    &:last-child { border-bottom: none; }
    &.is-ok .batch-results__mark { color: #27a644; }
    &.is-err .batch-results__mark { color: #d83a3a; }
  }
  &__mark {
    font-family: var(--font-number);
    font-weight: 700;
    text-align: center;
  }
  &__name {
    color: #303133;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  &__detail {
    color: #606266;
    font-size: 12px;
    font-family: var(--font-number);
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
