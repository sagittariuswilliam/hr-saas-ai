import { request } from '@/utils/request'
import type { ApiResponse, PageResponse } from './auth'

// 简历信息
export interface Resume {
  id: number
  project_id?: number
  position_id?: number
  candidate_name: string
  phone: string
  email?: string
  work_years?: number
  education?: string
  resume_file?: string
  status: string
  parse_status?: number
  parsed_data?: any
  created_by?: number
  created_at?: string
  updated_at?: string
  project_name?: string
  position_name?: string
  match_score?: number
  match_result?: any
}

// 获取简历列表
export const getResumeListApi = (params: any) => {
  return request.get<ApiResponse<PageResponse<Resume>>>('/resumes', { params })
}

// 获取简历详情
export const getResumeDetailApi = (id: number) => {
  return request.get<ApiResponse<Resume>>(`/resumes/${id}`)
}

// 删除简历
export const deleteResumeApi = (id: number) => {
  return request.delete<ApiResponse<void>>(`/resumes/${id}`)
}

// 下载简历
export const downloadResumeApi = async (id: number) => {
  try {
    // 使用请求获取文件blob，处理认证
    const response = await fetch(`${API_BASE}/resumes/${id}/download`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      }
    })

    if (!response.ok) {
      throw new Error('下载失败')
    }

    // 从响应头获取文件名
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `resume_${id}.pdf`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (match && match[1]) {
        filename = match[1].replace(/['"]/g, '')
        // 解码 UTF-8 文件名
        try {
          filename = decodeURIComponent(filename)
        } catch {}
      }
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('下载失败:', error)
    throw error
  }
}

// 更新简历状态
export const updateResumeStatusApi = (id: number, status: string) => {
  return request.put(`/resumes/${id}/status`, { status })
}

// 获取简历统计数据
export const getResumeStatsApi = () => {
  return request.get('/resumes/stats/summary')
}

// AI分析简历匹配度
export const analyzeResumeApi = (id: number, force = false) => {
  return request.post(`/resumes/${id}/analyze?force=${force}`)
}

// 批量上传简历（1-10 份，1 次 HTTP）
// 使用裸 axios 而非 wrapped request，避免 code=400（全部失败）时被拦截
import axios from 'axios'
import { API_BASE } from '@/utils/api-base'

export interface BatchUploadResultItem {
  filename: string
  status: 'success' | 'failed'
  resume_id?: number
  candidate_name?: string
  error?: string
}

export interface BatchUploadResponse {
  total: number
  succeeded: number
  failed: number
  results: BatchUploadResultItem[]
}

export const uploadBatchResumeApi = async (
  files: File[],
  projectId: number | null,
  positionId: number | null
): Promise<BatchUploadResponse> => {
  const formData = new FormData()
  if (projectId) formData.append('project_id', String(projectId))
  if (positionId) formData.append('position_id', String(positionId))
  files.forEach((f) => formData.append('files', f))

  const baseURL = API_BASE as string
  const token = localStorage.getItem('token') || ''
  const res = await axios.post(`${baseURL}/resumes/upload-batch`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      Authorization: token ? `Bearer ${token}` : ''
    },
    timeout: 60000
  })
  // 后端约定：code=0 成功；code=400 表示全部失败（data 仍有 results）
  if (res.data?.code === 0 || res.data?.code === 200) {
    return res.data.data as BatchUploadResponse
  }
  if (res.data?.code === 400 && res.data?.data) {
    return res.data.data as BatchUploadResponse
  }
  throw new Error(res.data?.message || '上传失败')
}
