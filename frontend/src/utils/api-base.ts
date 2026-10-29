// API base 运行时自适应
// - HTTPS 页面（经 nginx 反代）: 走同源 /api/v1，避免混合内容被浏览器拦截
// - HTTP 页面（原有 :8080 直链、本地开发）: 保持原绝对地址，行为与历史完全一致
export const API_BASE: string =
  typeof window !== 'undefined' && window.location.protocol === 'https:'
    ? '/api/v1'
    : (import.meta.env.VITE_APP_BASE_API as string)
