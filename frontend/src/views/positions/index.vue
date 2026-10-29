<template>
  <div class="positions-page">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <el-select
        v-model="searchParams.project_id"
        placeholder="按项目筛选"
        style="width: 180px; margin-right: 12px"
        clearable
        @change="loadPositions"
      >
        <el-option
          v-for="item in projectList"
          :key="item.id"
          :label="item.project_name"
          :value="item.id"
        />
      </el-select>
      <el-select
        v-model="searchParams.status"
        placeholder="状态筛选"
        style="width: 140px; margin-right: 12px"
        clearable
        @change="loadPositions"
      >
        <el-option :value="1" label="启用" />
        <el-option :value="2" label="暂停" />
        <el-option :value="3" label="已关闭" />
      </el-select>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        新增职位
      </el-button>
    </div>

    <!-- 职位列表 -->
    <div class="table-container">
      <el-table
        :data="positionList"
        v-loading="loading"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="position_name" label="职位名称" min-width="180" />
        <el-table-column prop="project_name" label="所属项目" width="150" />
        <el-table-column prop="salary_range" label="薪资范围" width="120" />
        <el-table-column prop="work_location" label="工作地点" width="120" />
        <el-table-column prop="hiring_count" label="招聘人数" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="success" size="small" @click="viewResumes(row)">查看简历</el-button>
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
          @size-change="loadPositions"
          @current-change="loadPositions"
        />
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑职位' : '新增职位'"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="positionForm"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="所属项目" prop="project_id">
          <el-select
            v-model="positionForm.project_id"
            placeholder="请选择项目"
            style="width: 100%"
          >
            <el-option
              v-for="item in projectList"
              :key="item.id"
              :label="item.project_name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="职位名称" prop="position_name">
          <el-input v-model="positionForm.position_name" placeholder="请输入职位名称" />
        </el-form-item>
        <el-form-item label="薪资范围" prop="salary_range">
          <el-input v-model="positionForm.salary_range" placeholder="如：25k-40k" />
        </el-form-item>
        <el-form-item label="工作地点" prop="work_location">
          <el-input v-model="positionForm.work_location" placeholder="如：北京" />
        </el-form-item>
        <el-form-item label="招聘人数" prop="hiring_count">
          <el-input-number v-model="positionForm.hiring_count" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="职位描述" prop="jd_content">
          <el-input
            v-model="positionForm.jd_content"
            type="textarea"
            :rows="4"
            placeholder="请输入职位描述和要求"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="positionForm.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="2">暂停</el-radio>
            <el-radio :value="3">关闭</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import {
  getPositionListApi,
  createPositionApi,
  updatePositionApi,
  deletePositionApi,
  type Position,
  type PositionForm
} from '@/api/position'
import { getAllProjectsApi, type Project } from '@/api/project'

const router = useRouter()

// 列表相关
const loading = ref(false)
const positionList = ref<Position[]>([])
const projectList = ref<Project[]>([])

const pageParams = reactive({
  page: 1,
  page_size: 10,
  total: 0
})

const searchParams = reactive({
  project_id: null as number | null,
  status: null as number | null
})

// 表单相关
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()

const positionForm = reactive<PositionForm>({
  project_id: 0,
  position_name: '',
  salary_range: '',
  work_location: '',
  jd_content: '',
  hiring_count: 1
})

const formRules: FormRules = {
  project_id: [
    { required: true, message: '请选择项目', trigger: 'change' }
  ],
  position_name: [
    { required: true, message: '请输入职位名称', trigger: 'blur' },
    { min: 2, max: 100, message: '职位名称长度在 2 到 100 个字符', trigger: 'blur' }
  ]
}

// 获取项目列表（用于下拉选择）
const loadProjects = async () => {
  try {
    const res = await getAllProjectsApi()
    projectList.value = res.data
  } catch (error) {
    console.error('获取项目列表失败:', error)
    ElMessage.error('获取项目列表失败')
  }
}

// 获取职位列表
const loadPositions = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pageParams.page,
      page_size: pageParams.page_size
    }
    if (searchParams.project_id) {
      params.project_id = searchParams.project_id
    }
    if (searchParams.status) {
      params.status = searchParams.status
    }
    
    const result = await getPositionListApi(params)
    positionList.value = result.data.items
    pageParams.total = result.data.total
  } catch (error) {
    console.error('获取职位列表失败:', error)
    ElMessage.error('获取职位列表失败')
  } finally {
    loading.value = false
  }
}

// 打开新增弹窗
const openCreateDialog = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

// 打开编辑弹窗
const openEditDialog = (row: Position) => {
  isEdit.value = true
  Object.assign(positionForm, {
    id: row.id,
    project_id: row.project_id,
    position_name: row.position_name,
    salary_range: row.salary_range,
    work_location: row.work_location,
    jd_content: row.jd_content,
    hiring_count: row.hiring_count,
    status: row.status
  })
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(positionForm, {
    project_id: 0,
    position_name: '',
    salary_range: '',
    work_location: '',
    jd_content: '',
    hiring_count: 1,
    status: 1
  })
  formRef.value?.clearValidate()
}

// 提交表单
const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitLoading.value = true
    try {
      if (isEdit.value) {
        await updatePositionApi(positionForm.id!, positionForm)
        ElMessage.success('更新成功')
      } else {
        const res = await createPositionApi(positionForm)
        positionForm.id = res.data.id  // 保存新增后的 id
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      loadPositions()
    } catch (error) {
      console.error('提交失败:', error)
      ElMessage.error('提交失败，请稍后重试')
    } finally {
      submitLoading.value = false
    }
  })
}

// 删除职位
const handleDelete = (row: Position) => {
  ElMessageBox.confirm(
    `确定要删除职位「${row.position_name}」吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deletePositionApi(row.id)
      ElMessage.success('删除成功')
      loadPositions()
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 查看简历
const viewResumes = (row: Position) => {
  router.push(`/resumes?position_id=${row.id}`)
}

// 状态类型
const getStatusType = (status: number) => {
  const map: Record<number, string> = {
    1: 'success',
    2: 'warning',
    3: 'info'
  }
  return map[status] || 'info'
}

// 状态文本
const getStatusText = (status: number) => {
  const map: Record<number, string> = {
    1: '启用',
    2: '暂停',
    3: '关闭'
  }
  return map[status] || '未知'
}

onMounted(() => {
  loadProjects()
  loadPositions()
})
</script>

<style scoped lang="scss">
.positions-page {
  padding: 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
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
</style>
