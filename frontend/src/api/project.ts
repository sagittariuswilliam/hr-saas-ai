import { request } from '@/utils/request'
import type { ApiResponse, PageResponse } from './auth'

// 项目类型 - 与后端保持一致
export interface Project {
  id: number
  project_name: string
  client_name?: string
  description?: string
  recruiter_id?: number
  deliverer_id?: number
  status: number  // 1:启用 2:暂停 3:已完成
  created_by: number
  created_at: string
  updated_at: string
}

// 项目查询参数
export interface ProjectQueryParams {
  page?: number
  page_size?: number
  keyword?: string
}

// 项目表单数据
export interface ProjectFormData {
  id?: number
  project_name: string
  client_name?: string
  description?: string
  recruiter_id?: number
  deliverer_id?: number
  status?: number
}

// 获取项目列表
export const getProjectListApi = (params?: ProjectQueryParams) => {
  return request.get<ApiResponse<PageResponse<Project>>>('/projects', { params })
}

// 获取项目详情
export const getProjectDetailApi = (id: number) => {
  return request.get<ApiResponse<Project>>(`/projects/${id}`)
}

// 获取所有项目（用于下拉选择）
export const getAllProjectsApi = () => {
  return request.get<ApiResponse<Project[]>>('/projects/all')
}

// 创建项目
export const createProjectApi = (data: ProjectFormData) => {
  return request.post<ApiResponse<{ id: number }>>('/projects', data)
}

// 更新项目
export const updateProjectApi = (id: number, data: ProjectFormData) => {
  return request.put<ApiResponse<Project>>(`/projects/${id}`, data)
}

// 删除项目
export const deleteProjectApi = (id: number) => {
  return request.delete<ApiResponse<void>>(`/projects/${id}`)
}
