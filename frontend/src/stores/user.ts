import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 用户信息类型 - 与后端保持一致
export interface UserInfo {
  id: number
  username: string
  real_name: string
  role: 'admin' | 'recruiter' | 'deliverer'
  email?: string
  phone?: string
  status: number
}

// 菜单项类型
export interface MenuItem {
  id: number
  name: string
  path: string
  icon: string
  roles: string[]
}

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<UserInfo | null>(null)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const userRole = computed(() => userInfo.value?.role)

  // 设置 Token
  const setToken = async (loginToken: string) => {
    token.value = loginToken
    localStorage.setItem('token', loginToken)
  }

  // 设置用户信息
  const setUserInfo = async (user: UserInfo) => {
    userInfo.value = user
    localStorage.setItem('userInfo', JSON.stringify(user))
  }

  // 退出登录
  const logout = () => {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }

  // 初始化本地存储的数据
  const initFromStorage = () => {
    const storedUser = localStorage.getItem('userInfo')
    if (storedUser) {
      try {
        userInfo.value = JSON.parse(storedUser)
      } catch (e) {
        console.error('解析用户信息失败:', e)
      }
    }
  }

  // 根据角色获取菜单
  const getMenusByRole = (): MenuItem[] => {
    const allMenus: MenuItem[] = [
      {
        id: 1,
        name: '数据看板',
        path: '/dashboard',
        icon: 'DataLine',
        roles: ['admin', 'recruiter', 'deliverer']
      },
      {
        id: 2,
        name: '项目管理',
        path: '/projects',
        icon: 'Folder',
        roles: ['admin', 'recruiter', 'deliverer']
      },
      {
        id: 3,
        name: '职位管理',
        path: '/positions',
        icon: 'Briefcase',
        roles: ['admin', 'recruiter', 'deliverer']
      },
      {
        id: 4,
        name: '简历管理',
        path: '/resumes',
        icon: 'Document',
        roles: ['admin', 'recruiter', 'deliverer']
      },
      {
        id: 5,
        name: '用户管理',
        path: '/users',
        icon: 'User',
        roles: ['admin']
      }
    ]

    const role = userRole.value
    return role ? allMenus.filter(menu => menu.roles.includes(role)) : []
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    userRole,
    setToken,
    setUserInfo,
    logout,
    initFromStorage,
    getMenusByRole
  }
})
