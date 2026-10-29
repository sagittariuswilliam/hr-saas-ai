<template>
  <div class="user-management">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索用户名/姓名"
        style="width: 250px; margin-right: 16px"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select v-model="searchRole" placeholder="角色筛选" style="width: 150px; margin-right: 16px" clearable>
        <el-option label="招聘人员" value="recruiter" />
        <el-option label="交付人员" value="deliverer" />
        <el-option label="管理员" value="admin" />
      </el-select>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新增用户
      </el-button>
    </div>

    <!-- 用户列表表格 -->
    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="real_name" label="姓名" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)">{{ getRoleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              @change="handleStatusChange(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="handleResetPassword(row)">重置密码</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pageParams.page"
          v-model:page-size="pageParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑用户弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="500px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" placeholder="请输入用户名" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!isEdit">
          <el-input v-model="formData.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="formData.real_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="formData.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="formData.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="formData.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="招聘人员" value="recruiter" />
            <el-option label="交付人员" value="deliverer" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog
      v-model="passwordDialogVisible"
      title="重置密码"
      width="400px"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordFormRules"
        label-width="100px"
      >
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitPassword">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { getUserListApi, createUserApi, updateUserApi, deleteUserApi, changeUserStatusApi, resetUserPasswordApi } from '@/api/user'
import type { User, UserForm } from '@/api/user'

// 搜索
const searchKeyword = ref('')
const searchRole = ref<string>('')

// 表格
const loading = ref(false)
const tableData = ref<User[]>([])
const total = ref(0)
const pageParams = reactive({
  page: 1,
  page_size: 10
})

// 弹窗
const dialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()
const passwordFormRef = ref<FormInstance>()

const formData = reactive<UserForm>({
  username: '',
  password: '',
  real_name: '',
  email: '',
  phone: '',
  role: 'recruiter'
})

const passwordForm = reactive({
  new_password: ''
})

const formRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 个字符', trigger: 'blur' }
  ],
  real_name: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

const passwordFormRules: FormRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 个字符', trigger: 'blur' }
  ]
}

// 获取角色标签
const getRoleLabel = (role: string) => {
  const map: Record<string, string> = {
    recruiter: '招聘人员',
    deliverer: '交付人员',
    admin: '管理员'
  }
  return map[role] || role
}

// 获取角色标签颜色
const getRoleType = (role: string) => {
  const map: Record<string, any> = {
    recruiter: 'primary',
    deliverer: 'success',
    admin: 'danger'
  }
  return map[role] || ''
}

// 格式化日期
const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const params: any = { ...pageParams }
    if (searchRole.value) params.role = searchRole.value
    const res = await getUserListApi(params)
    if (res.code === 0) {
      tableData.value = res.data.items
      total.value = res.data.total
    }
  } catch (error) {
    console.error('加载用户列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pageParams.page = 1
  loadData()
}

// 分页变化
const handleSizeChange = (size: number) => {
  pageParams.page_size = size
  loadData()
}

const handleCurrentChange = (page: number) => {
  pageParams.page = page
  loadData()
}

// 新增用户
const handleCreate = () => {
  isEdit.value = false
  dialogVisible.value = true
}

// 编辑用户
const editingUserId = ref<number | null>(null)
const handleEdit = (row: User) => {
  isEdit.value = true
  editingUserId.value = row.id
  Object.assign(formData, {
    username: row.username,
    real_name: row.real_name,
    email: row.email,
    phone: row.phone,
    role: row.role
  })
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  formData.username = ''
  formData.password = ''
  formData.real_name = ''
  formData.email = ''
  formData.phone = ''
  formData.role = 'recruiter'
  formRef.value?.resetFields()
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      // 准备提交数据，将空字符串转为 null，避免后端验证失败
      const submitData = { ...formData }
      if (submitData.email === '') submitData.email = null
      if (submitData.phone === '') submitData.phone = null
      
      if (isEdit.value && editingUserId.value) {
        // 问题8修复：编辑用户
        await updateUserApi(editingUserId.value, submitData)
        ElMessage.success('更新成功')
      } else {
        // 新增
        await createUserApi(submitData)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      loadData()
    } catch (error) {
      console.error('提交失败:', error)
      ElMessage.error('操作失败')
    } finally {
      submitLoading.value = false
    }
  })
}

// 状态切换
const handleStatusChange = async (row: User) => {
  try {
    await changeUserStatusApi(row.id, row.status)
    ElMessage.success('状态更新成功')
  } catch (error) {
    row.status = row.status === 1 ? 0 : 1 // 回滚
    console.error('状态更新失败:', error)
    ElMessage.error('状态更新失败')
  }
}

// 重置密码
const resettingUserId = ref<number | null>(null)
const handleResetPassword = (row: User) => {
  resettingUserId.value = row.id
  passwordForm.new_password = ''
  passwordDialogVisible.value = true
}

const handleSubmitPassword = async () => {
  if (!passwordFormRef.value || !resettingUserId.value) return
  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      await resetUserPasswordApi(resettingUserId.value, passwordForm.new_password)
      ElMessage.success('密码重置成功')
      passwordDialogVisible.value = false
    } catch (error) {
      console.error('重置密码失败:', error)
      ElMessage.error('重置密码失败')
    }
  })
}

// 删除用户
const handleDelete = (row: User) => {
  ElMessageBox.confirm(
    `确定要删除用户 "${row.username}" 吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      // 问题9修复：调用删除API
      await deleteUserApi(row.id)
      ElMessage.success('删除成功')
      loadData()
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.user-management {
  .toolbar {
    margin-bottom: 16px;
    display: flex;
    align-items: center;
  }

  .table-card {
    :deep(.el-card__body) {
      padding-top: 0;
    }
  }

  .pagination-wrapper {
    margin-top: 20px;
    text-align: right;
  }
}
</style>
