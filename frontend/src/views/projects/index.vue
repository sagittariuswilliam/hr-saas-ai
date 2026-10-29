<template>
  <div class="projects-page">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索项目名"
        style="width: 250px; margin-right: 16px"
        clearable
        @keyup.enter="loadProjects"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        新增项目
      </el-button>
    </div>

    <!-- 项目列表 -->
    <div class="table-container">
      <el-table
        :data="projectList"
        v-loading="loading"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="project_name" label="项目名称" min-width="180" />
        <el-table-column prop="client_name" label="客户名称" width="150" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="success" size="small" @click="viewPositions(row)">查看职位</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadProjects"
          @current-change="loadProjects"
        />
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑项目' : '新增项目'"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="projectForm"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="项目名称" prop="project_name">
          <el-input v-model="projectForm.project_name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="客户名称" prop="client_name">
          <el-input v-model="projectForm.client_name" placeholder="请输入客户名称" />
        </el-form-item>
        <el-form-item label="项目描述" prop="description">
          <el-input
            v-model="projectForm.description"
            type="textarea"
            :rows="4"
            placeholder="请输入项目描述"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="projectForm.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="2">暂停</el-radio>
            <el-radio :value="3">已完成</el-radio>
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
import { Search, Plus } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import {
  getProjectListApi,
  createProjectApi,
  updateProjectApi,
  deleteProjectApi,
  type Project,
  type ProjectFormData
} from '@/api/project'

const router = useRouter()

// 列表相关
const loading = ref(false)
const projectList = ref<Project[]>([])
const searchKeyword = ref('')

const pagination = reactive({
  page: 1,
  page_size: 10,
  total: 0
})

// 表单相关
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()

const projectForm = reactive<ProjectFormData>({
  project_name: '',
  client_name: '',
  description: '',
  status: 1
})

const formRules: FormRules = {
  project_name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 2, max: 100, message: '项目名称长度在 2 到 100 个字符', trigger: 'blur' }
  ]
}

// 获取项目列表
const loadProjects = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }
    
    const result = await getProjectListApi(params)
    projectList.value = result.data.items
    pagination.total = result.data.total
  } catch (error) {
    console.error('获取项目列表失败:', error)
    ElMessage.error('获取项目列表失败')
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
const openEditDialog = (row: Project) => {
  isEdit.value = true
  Object.assign(projectForm, {
    id: row.id,
    project_name: row.project_name,
    client_name: row.client_name,
    description: row.description,
    status: row.status
  })
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(projectForm, {
    project_name: '',
    client_name: '',
    description: '',
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
      if (isEdit.value && projectForm.id) {
        await updateProjectApi(projectForm.id, projectForm)
        ElMessage.success('更新成功')
      } else {
        await createProjectApi(projectForm)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      loadProjects()
    } catch (error) {
      console.error('提交失败:', error)
      ElMessage.error('提交失败，请稍后重试')
    } finally {
      submitLoading.value = false
    }
  })
}

// 删除项目
const handleDelete = (row: Project) => {
  ElMessageBox.confirm(
    `确定要删除项目「${row.project_name}」吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteProjectApi(row.id)
      ElMessage.success('删除成功')
      loadProjects()
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 查看职位
const viewPositions = (row: Project) => {
  router.push(`/positions?project_id=${row.id}`)
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
    3: '已完成'
  }
  return map[status] || '未知'
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped lang="scss">
.projects-page {
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
