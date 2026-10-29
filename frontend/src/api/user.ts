import { request } from '@/utils/request'
import type { ApiResponse, PageResponse } from './position'

// 用户信息
export interface User {
  id: number
  username: string
  real_name: string
  email?: string
  phone?: string
  role: string
  status: number
  created_at: string
  last_login_at?: string
}

// 创建/更新用户
export interface UserForm {
  username: string
  password?: string
  real_name: string
  email?: string
  phone?: string
  role: string
}

// 分页参数
export interface UserPageParams {
  page: number
  page_size: number
  role?: string
  status?: number
  keyword?: string
}

// 获取用户列表
export const getUserListApi = (params: UserPageParams) => {
  return request.get<ApiResponse<PageResponse<User>>>('/users', { params })
}

// 获取用户详情
export const getUserDetailApi = (id: number) => {
  return request.get<ApiResponse<User>>(`/users/${id}`)
}

// 创建用户
export const createUserApi = (data: UserForm) => {
  return request.post<ApiResponse<{ id: number }>>('/users', data)
}

// 更新用户
export const updateUserApi = (id: number, data: Partial<UserForm>) => {
  return request.put<ApiResponse<User>>(`/users/${id}`, data)
}

// 删除用户
export const deleteUserApi = (id: number) => {
  return request.delete<ApiResponse<void>>(`/users/${id}`)
}

// 修改用户状态
export const changeUserStatusApi = (id: number, status: number) => {
  return request.patch<ApiResponse<void>>(`/users/${id}/status`, { status })
}

// 重置用户密码
export const resetUserPasswordApi = (id: number, new_password: string) => {
  return request.patch<ApiResponse<void>>(`/users/${id}/password`, { new_password })
}
