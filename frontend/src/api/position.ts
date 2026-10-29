import { request } from '@/utils/request'
import type { ApiResponse } from './auth'

// 职位信息
export interface Position {
  id: number
  project_id: number
  position_name: string
  salary_range?: string
  work_location?: string
  jd_content?: string
  required_skills?: string[]
  hiring_count: number
  status: number
  creator_id: number
  created_at: string
  updated_at: string
}

// 创建/更新职位
export interface PositionForm {
  id?: number
  project_id: number
  position_name: string
  salary_range?: string
  work_location?: string
  jd_content?: string
  required_skills?: string[]
  hiring_count: number
  status: number
}

// 分页参数
export interface PageParams {
  page: number
  page_size: number
  project_id?: number
  status?: number
}

// 分页响应
export interface PageResponse<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

// 获取职位列表
export const getPositionListApi = (params: any) => {
  return request.get<ApiResponse<PageResponse<Position>>>('/positions', { params })
}

// 获取所有职位（不分页，用于下拉选择）
export const getAllPositionsApi = (params?: any) => {
  return request.get<ApiResponse<Position[]>>('/positions/all', { params })
}

// 获取职位详情
export const getPositionDetailApi = (id: number) => {
  return request.get<ApiResponse<Position>>(`/positions/${id}`)
}

// 创建职位
export const createPositionApi = (data: PositionForm) => {
  return request.post<ApiResponse<{ id: number }>>('/positions', data)
}

// 更新职位
export const updatePositionApi = (id: number, data: Partial<PositionForm>) => {
  return request.put<ApiResponse<Position>>(`/positions/${id}`, data)
}

// 删除职位
export const deletePositionApi = (id: number) => {
  return request.delete<ApiResponse<void>>(`/positions/${id}`)
}

// 更新职位状态
export const updatePositionStatusApi = (id: number, status: number) => {
  return request.patch<ApiResponse<void>>(`/positions/${id}/status`, { status })
}
