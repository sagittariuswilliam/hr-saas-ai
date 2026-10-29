<template>
  <div class="layout-container">
    <el-container class="main-container">
      <!-- 左侧侧边栏 -->
      <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar" :class="{ 'is-collapse': isCollapse }">
        <div class="logo">
          <el-icon size="32" color="#fff"><OfficeBuilding /></el-icon>
          <span v-if="!isCollapse" class="logo-text">HR-SaaS</span>
        </div>
        
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapse"
          :collapse-transition="false"
          class="sidebar-menu"
          router
          text-color="#bfcbd9"
          active-text-color="#fff"
        >
          <el-menu-item
            v-for="menu in filteredMenus"
            :key="menu.path"
            :index="menu.path"
          >
            <el-icon><component :is="menu.icon" /></el-icon>
            <template #title>{{ menu.title }}</template>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-container class="content-container">
        <!-- 顶部导航栏 -->
        <el-header class="header">
          <div class="header-left">
            <el-icon
              class="collapse-btn"
              :class="{ 'is-active': isCollapse }"
              @click="toggleCollapse"
            >
              <Fold />
            </el-icon>
            
            <span class="system-name">HR-SaaS 人力资源管理平台</span>
            
            <!-- 面包屑 -->
            <el-breadcrumb separator="/" class="breadcrumb">
              <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item v-if="currentRouteName && currentRouteName !== '数据看板'">
                {{ currentRouteName }}
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          
          <div class="header-right">
            <el-dropdown @command="handleCommand" trigger="click">
              <div class="user-info">
                <el-avatar :size="36" :src="userStore.userInfo?.avatar">
                  <el-icon><User /></el-icon>
                </el-avatar>
                <div class="user-detail" v-if="!isMobile">
                  <span class="username">{{ userStore.userInfo?.real_name || '用户' }}</span>
                  <span class="user-role">{{ roleText }}</span>
                </div>
                <el-icon class="arrow-icon"><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">
                    <el-icon><User /></el-icon>
                    个人信息
                  </el-dropdown-item>
                  <el-dropdown-item command="password">
                    <el-icon><Lock /></el-icon>
                    修改密码
                  </el-dropdown-item>
                  <el-dropdown-item divided command="logout">
                    <el-icon><SwitchButton /></el-icon>
                    退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>
        
        <!-- 主内容区 -->
        <el-main class="main-content">
          <router-view v-slot="{ Component }">
            <transition name="fade-transform" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import {
  OfficeBuilding,
  DataLine,
  Folder,
  Briefcase,
  Document,
  Tickets,
  MagicStick,
  User,
  Fold,
  ArrowDown,
  Lock,
  SwitchButton
} from '@element-plus/icons-vue'

interface MenuConfig {
  path: string
  title: string
  icon: string
  roles?: string[]
}

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const isCollapse = ref(false)
const isMobile = ref(false)

// 菜单配置
const menuConfig: MenuConfig[] = [
  { path: '/dashboard', title: '数据看板', icon: 'DataLine' },
  { path: '/projects', title: '项目管理', icon: 'Folder' },
  { path: '/positions', title: '职位管理', icon: 'Briefcase' },
  { path: '/resumes', title: '简历管理', icon: 'Document' },
  { path: '/users', title: '用户管理', icon: 'User', roles: ['admin'] }
]

// 根据角色过滤菜单
const filteredMenus = computed(() => {
  const userRole = userStore.userInfo?.role
  return menuConfig.filter(menu => {
    if (!menu.roles) return true
    return userRole && menu.roles.includes(userRole)
  })
})

// 当前激活的菜单
const activeMenu = computed(() => route.path)

// 当前路由名称
const currentRouteName = computed(() => route.meta.title as string || '')

// 角色文本
const roleText = computed(() => {
  const roleMap: Record<string, string> = {
    admin: '管理员',
    recruiter: '招聘专员',
    deliverer: '交付专员'
  }
  const role = userStore.userInfo?.role
  return roleMap[role] || '未知角色'
})

// 切换侧边栏折叠
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

// 处理屏幕尺寸变化
const handleResize = () => {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    isCollapse.value = true
  }
}

// 处理下拉菜单命令
const handleCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      ElMessage.info('个人信息功能开发中')
      break
    case 'password':
      ElMessage.info('修改密码功能开发中')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--primary'
        })
        userStore.logout()
        ElMessage.success('已退出登录')
        router.push('/login')
      } catch {
        // 用户取消
      }
      break
  }
}

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)
  userStore.initFromStorage()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.layout-container {
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.main-container {
  height: 100%;
}

/* 侧边栏样式 - 深蓝色主题 */
.sidebar {
  background: #1E40AF;
  transition: width 0.3s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sidebar.is-collapse {
  width: 64px !important;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 64px;
  padding: 0 16px;
  background: rgba(0, 0, 0, 0.2);
  gap: 12px;
  flex-shrink: 0;
}

.logo-text {
  color: white;
  font-size: 20px;
  font-weight: 700;
  white-space: nowrap;
  letter-spacing: 1px;
}

.sidebar-menu {
  border: none;
  background: transparent;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-menu .el-menu-item {
  height: 56px;
  line-height: 56px;
  margin: 4px 12px;
  border-radius: 8px;
  width: calc(100% - 24px);
  transition: all 0.3s;
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

.sidebar-menu .el-menu-item.is-active {
  background: rgba(255, 255, 255, 0.25);
  color: white;
}

.sidebar-menu:not(.el-menu--collapse) .el-menu-item {
  padding-left: 20px !important;
}

/* 内容容器 */
.content-container {
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
  overflow: hidden;
}

/* 顶部导航栏 */
.header {
  background: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(30, 64, 175, 0.1);
  height: 64px !important;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: 1;
  min-width: 0;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #1E40AF;
  transition: all 0.3s;
  padding: 8px;
  border-radius: 6px;
  flex-shrink: 0;
}

.collapse-btn:hover {
  background: rgba(30, 64, 175, 0.1);
}

.collapse-btn.is-active {
  transform: rotate(180deg);
}

.system-name {
  font-size: 18px;
  font-weight: 600;
  color: #1E40AF;
  white-space: nowrap;
}

.breadcrumb {
  margin-left: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-shrink: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 8px;
  transition: all 0.3s;
}

.user-info:hover {
  background: rgba(30, 64, 175, 0.08);
}

.user-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  line-height: 1.2;
}

.user-role {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.2;
}

.arrow-icon {
  color: #9ca3af;
  font-size: 14px;
}

/* 主内容区 */
.main-content {
  padding: 24px;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
}

/* 页面过渡动画 */
.fade-transform-leave-active,
.fade-transform-enter-active {
  transition: all 0.3s ease;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .header {
    padding: 0 12px;
  }
  
  .header-left {
    gap: 12px;
  }
  
  .system-name {
    font-size: 14px;
  }
  
  .breadcrumb {
    display: none;
  }
  
  .main-content {
    padding: 16px;
  }
  
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 1000;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  }
  
  .sidebar.is-collapse {
    transform: translateX(-100%);
  }
}

@media (max-width: 480px) {
  .system-name {
    display: none;
  }
}
</style>
