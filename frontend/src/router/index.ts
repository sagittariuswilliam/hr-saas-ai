import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layout/index.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '数据看板', icon: 'DataLine' }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/projects/index.vue'),
        meta: { title: '项目管理', icon: 'Folder' }
      },
      {
        path: 'positions',
        name: 'Positions',
        component: () => import('@/views/positions/index.vue'),
        meta: { title: '职位管理', icon: 'Briefcase' }
      },
      {
        path: 'resumes',
        name: 'Resumes',
        component: () => import('@/views/resumes/index.vue'),
        meta: { title: '简历管理', icon: 'Document' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/index.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['admin'] }
      }
    ]
  },
  {
    // 候选人 AI 面试作答页（公开，凭 token，免登录；hash 模式下 URL 为 /#/i/<token>）
    path: '/i/:token',
    name: 'InterviewCandidate',
    component: () => import('@/views/interview/candidate.vue'),
    meta: { title: 'AI 初筛面试', requiresAuth: false }
  },
  {
    // 兼容已外发的旧话术链接（后端 link 为 /interview/i/<token>），重定向到公开作答页，免登录
    path: '/interview/i/:token',
    redirect: (to: any) => ({ path: `/i/${to.params.token}` }),
    meta: { requiresAuth: false }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const token = userStore.token

  // 需要登录的页面
  if (to.meta.requiresAuth !== false) {
    if (!token) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }

    // 检查角色权限
    const roles = to.meta.roles as string[]
    if (roles && roles.length > 0) {
      const userRole = userStore.userInfo?.role
      if (!userRole || !roles.includes(userRole)) {
        ElMessage?.error?.('没有权限访问该页面')
        next(from.path)
        return
      }
    }
  }

  // 已登录用户访问登录页，跳转到首页
  if (to.path === '/login' && token) {
    next('/')
    return
  }

  next()
})

export default router
