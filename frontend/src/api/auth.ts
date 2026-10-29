import { request } from '@/utils/request'

// 登录请求参数
export interface LoginParams {
  username: string
  password: string
}

// 登录响应数据
export interface LoginResponseData {
  access_token: string
  token_type: string
  user: UserInfo
}

// 登录响应 - 统一格式
export interface LoginResponse {
  code: number
  message: string
  data: LoginResponseData
}

// 通用响应
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 用户信息
export interface UserInfo {
  id: number
  username: string
  real_name: string
  role: string
  email?: string
  phone?: string
  status: number
  last_login_at?: string
}

// 登录
export const loginApi = (data: LoginParams) => {
  return request.post<LoginResponse>('/auth/login', data)
}

// 获取当前用户信息
export const getUserInfoApi = () => {
  return request.get<ApiResponse<UserInfo>>('/auth/me')
}
