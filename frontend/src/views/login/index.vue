<template>
  <div class="login-container">
    <!-- ========== 左侧 深色品牌区 ========== -->
    <aside class="login-brand-area" aria-label="品牌区">
      <!-- 元素 1 · 静态 SVG 网格背景 -->
      <svg
        class="brand-grid"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <pattern
            id="hr-grid"
            x="0"
            y="0"
            width="64"
            height="64"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 64 0 L 0 0 0 64"
              fill="none"
              stroke="#6E97A1"
              stroke-width="1"
              opacity="0.18"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#hr-grid)" />
      </svg>

      <!-- 元素 2 · 同心圆环 (直径 600px · 3 圈) -->
      <svg
        class="brand-rings"
        viewBox="0 0 600 600"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <circle
          cx="300"
          cy="300"
          r="280"
          fill="none"
          stroke="#6E97A1"
          stroke-width="0.6"
          opacity="0.55"
        />
        <circle
          cx="300"
          cy="300"
          r="190"
          fill="none"
          stroke="#6E97A1"
          stroke-width="0.6"
          opacity="0.45"
        />
        <circle
          cx="300"
          cy="300"
          r="100"
          fill="none"
          stroke="#6E97A1"
          stroke-width="0.6"
          opacity="0.35"
        />
      </svg>

      <!-- 元素 3 · 品牌徽章 (浅色描边六边形 + 衬线 H) -->
      <div class="brand-badge" aria-label="HR-SaaS 品牌徽章">
        <svg
          width="64"
          height="64"
          viewBox="0 0 64 64"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M32 4L56 18V46L32 60L8 46V18L32 4Z"
            fill="none"
            stroke="#C2D4D9"
            stroke-width="1.5"
          />
          <text
            x="32"
            y="42"
            text-anchor="middle"
            font-family="var(--font-display)"
            font-weight="700"
            font-size="28"
            fill="#C2D4D9"
          >H</text>
        </svg>
      </div>

      <!-- 文本区 · 标语 + 副标 -->
      <div class="brand-text">
        <h1 class="brand-title">让每一次招聘决策都有据可依</h1>
        <p class="brand-subtitle">自 2025 年起为 127 家企业服务 · 覆盖 23 个城市</p>
      </div>

      <!-- 顶部 · 版本徽章 -->
      <div class="brand-meta">
        <span class="meta-version">V1.1 · 2026 春季版</span>
        <span class="meta-divider">·</span>
        <span class="meta-locale">简体中文</span>
      </div>

      <!-- 底部 · 版权与备案 -->
      <footer class="brand-footer">
        <span class="footer-line">© 2026 HR-SaaS</span>
        <span class="footer-divider">/</span>
        <span class="footer-line">京 ICP 备 2025 0000 号</span>
      </footer>
    </aside>

    <!-- ========== 右侧 登录表单区 ========== -->
    <main class="login-form-area" aria-label="登录表单">
      <div class="login-card" ref="cardRef">
        <!-- 错误条 · slideDown 240ms -->
        <transition name="slide-down">
          <div v-if="errorMsg" class="error-banner" role="alert">
            <el-icon class="error-icon"><WarningFilled /></el-icon>
            <span class="error-text">{{ errorMsg }}</span>
          </div>
        </transition>

        <!-- 卡片标题 -->
        <header class="card-header">
          <h2 class="card-title">欢迎回来</h2>
          <p class="card-subtitle">HR-SaaS · 招聘驾驶舱管理系统</p>
        </header>

        <!-- 表单 -->
        <form class="login-form" @submit.prevent="handleLogin" novalidate>
          <!-- 用户名 -->
          <div class="form-field" :class="{ 'is-focused': focusedField === 'username' }">
            <el-icon class="field-icon"><User /></el-icon>
            <input
              v-model="loginForm.username"
              type="text"
              class="field-input"
              placeholder="用户名"
              autocomplete="username"
              aria-label="用户名"
              required
              @focus="focusedField = 'username'"
              @blur="focusedField = ''"
            />
          </div>

          <!-- 密码 -->
          <div class="form-field" :class="{ 'is-focused': focusedField === 'password' }">
            <el-icon class="field-icon"><Lock /></el-icon>
            <input
              v-model="loginForm.password"
              type="password"
              class="field-input"
              placeholder="密码"
              autocomplete="current-password"
              aria-label="密码"
              required
              @focus="focusedField = 'password'"
              @blur="focusedField = ''"
            />
          </div>

          <!-- 记住我 · 忘记密码 -->
          <div class="form-actions">
            <label class="remember-me">
              <input type="checkbox" v-model="rememberMe" />
              <span class="checkmark" aria-hidden="true"></span>
              <span class="remember-text">记住我</span>
            </label>
            <a href="#" class="forgot-pwd" @click.prevent="onForgotPwd">忘记密码？</a>
          </div>

          <!-- 主 CTA -->
          <button
            type="submit"
            class="login-btn"
            :disabled="loading"
            ref="btnRef"
            aria-label="登录"
          >
            <span v-if="!loading" class="btn-label">登&nbsp;录</span>
            <span v-else class="btn-loading">
              <span class="spinner" aria-hidden="true"></span>
              <span>验证中…</span>
            </span>
          </button>
        </form>

        <!-- 测试账号提示 · 带复制按钮 -->
        <div class="login-tips">
          <span class="tips-label">测试账号</span>
          <code class="tips-chip">admin / admin123</code>
          <button
            type="button"
            class="tips-copy"
            :class="{ 'is-copied': copied }"
            @click="copyAccount"
            :aria-label="copied ? '已复制' : '复制测试账号'"
          >
            <el-icon v-if="!copied" :size="14"><DocumentCopy /></el-icon>
            <el-icon v-else :size="14"><Check /></el-icon>
            <span>{{ copied ? '已复制' : '复制' }}</span>
          </button>
        </div>
      </div>

      <!-- 表单区右上 · 联系管理员 -->
      <div class="form-area-top">
        <a href="#" class="contact-link" @click.prevent="onContact">
          <el-icon :size="14"><Service /></el-icon>
          <span>联系管理员</span>
        </a>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  User,
  Lock,
  WarningFilled,
  DocumentCopy,
  Check,
  Service
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { loginApi, getUserInfoApi } from '@/api/auth'

const router = useRouter()
const userStore = useUserStore()

const cardRef = ref<HTMLElement>()
const btnRef = ref<HTMLElement>()
const loading = ref(false)
const rememberMe = ref(false)
const errorMsg = ref('')
const focusedField = ref<'username' | 'password' | ''>('')
const copied = ref(false)

const loginForm = ref({
  username: '',
  password: ''
})

let errorTimer: number | null = null
let copyTimer: number | null = null

function showError(msg: string) {
  errorMsg.value = msg
  if (errorTimer) clearTimeout(errorTimer)
  errorTimer = window.setTimeout(() => {
    errorMsg.value = ''
  }, 6000)
}

function onForgotPwd() {
  showError('请联系系统管理员重置密码')
}

function onContact() {
  showError('管理员邮箱：admin@hr-saas.local')
}

async function copyAccount() {
  const text = 'admin / admin123'
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      // Fallback: execCommand
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    copied.value = true
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = window.setTimeout(() => {
      copied.value = false
    }, 1800)
  } catch (err) {
    // 静默失败：复制不可用时不打扰用户
    console.warn('[Login] clipboard not available:', err)
  }
}

async function handleLogin() {
  if (!loginForm.value.username || !loginForm.value.password) {
    showError('请输入用户名和密码')
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    const response = await loginApi(loginForm.value)
    const token = response.data.access_token

    await userStore.setToken(token)
    const userInfoResponse = await getUserInfoApi()
    await userStore.setUserInfo(userInfoResponse.data)

    setTimeout(() => {
      const redirect = router.currentRoute.value.query.redirect as string
      router.push(redirect || '/dashboard')
    }, 200)
  } catch (error: any) {
    console.error('[Login] failed:', error)
    showError('用户名或密码错误')
  } finally {
    setTimeout(() => {
      loading.value = false
    }, 200)
  }
}

onMounted(async () => {
  await nextTick()
  // 动效 #1 · 表单卡 opacity 0→1 + translateY(12px→0) / 320ms / 首挂载
  if (cardRef.value) {
    cardRef.value.animate(
      [
        { opacity: 0, transform: 'translateY(12px)' },
        { opacity: 1, transform: 'translateY(0)' }
      ],
      {
        duration: 320,
        easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
        fill: 'forwards'
      }
    )
  }
})
</script>

<style scoped>
/* ========== 容器 ========== */
.login-container {
  display: flex;
  width: 100%;
  min-height: 100vh;
  overflow: hidden;
  background: var(--paper);
}

/* ========== 左侧品牌区 ========== */
.login-brand-area {
  position: relative;
  flex: 1 1 50%;
  min-height: 100vh;
  background: #0F4C5C;
  color: var(--paper);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 56px 64px;
  overflow: hidden;
  isolation: isolate;
}

/* 元素 1 · SVG 网格背景 — absolute inset:0 */
.brand-grid {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

/* 元素 2 · 同心圆环 — 直径 600 / 3 圈 / 不旋转不呼吸 */
.brand-rings {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 600px;
  height: 600px;
  transform: translate(-50%, -50%);
  z-index: 0;
  pointer-events: none;
}

/* 元素 3 · 品牌徽章 — 居中偏上 80px */
.brand-badge {
  position: absolute;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-badge svg {
  width: 48px;
  height: 48px;
  display: block;
}

/* 文本区 */
.brand-text {
  position: relative;
  z-index: 2;
  margin-top: 80px;
  margin-bottom: auto;
  max-width: 520px;
}

.brand-text .brand-title,
.brand-text .brand-subtitle {
  margin-left: auto;
  margin-right: auto;
  text-align: left;
}

.brand-title {
  font-family: var(--font-display);
  font-size: 48px;
  font-weight: 600;
  line-height: 1.2;
  color: var(--paper);
  letter-spacing: 0.01em;
  margin: 0 0 18px 0;
}

.brand-subtitle {
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 400;
  line-height: 1.6;
  color: rgba(226, 232, 240, 0.75);
  letter-spacing: 0.02em;
  margin: 0;
}

/* 顶部 · 版本徽章 */
.brand-meta {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 400;
  color: rgba(226, 232, 240, 0.65);
  letter-spacing: 0.04em;
}

.meta-version {
  font-family: var(--font-number);
  letter-spacing: 0.06em;
}

.meta-divider {
  opacity: 0.4;
}

/* 底部 · 版权 */
.brand-footer {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 400;
  color: rgba(226, 232, 240, 0.55);
  letter-spacing: 0.02em;
}

.footer-divider {
  opacity: 0.5;
}

/* ========== 右侧表单区 ========== */
.login-form-area {
  position: relative;
  flex: 1 1 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--paper);
  padding: 40px 24px;
}

/* 表单区右上 · 联系管理员 */
.form-area-top {
  position: absolute;
  top: 32px;
  right: 40px;
  z-index: 2;
}

.contact-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-500);
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: color 200ms var(--ease-smooth);
}

.contact-link:hover {
  color: var(--brand-primary-500);
}

/* ========== 登录卡 ========== */
.login-card {
  position: relative;
  width: 100%;
  max-width: 420px;
  background: var(--paper);
  border: 1px solid var(--ink-100);
  border-radius: 4px;
  padding: 40px 36px 32px 36px;
  opacity: 0;
}

/* ========== 错误条 · slideDown 240ms ========== */
.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 20px;
  background: var(--danger-50);
  border-left: 3px solid var(--danger-500);
  border-radius: 2px;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--danger-500);
  letter-spacing: 0.01em;
}

.error-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: opacity 240ms var(--ease-smooth),
              transform 240ms var(--ease-smooth);
  overflow: hidden;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ========== 卡片标题 ========== */
.card-header {
  margin-bottom: 32px;
}

.card-title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 600;
  line-height: 1.25;
  color: var(--ink-900);
  letter-spacing: 0.01em;
  margin: 0 0 8px 0;
}

.card-subtitle {
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
  color: var(--ink-500);
  letter-spacing: 0.02em;
  margin: 0;
}

/* ========== 表单 ========== */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  position: relative;
  display: flex;
  align-items: center;
  height: 52px;
  background: var(--paper);
  border: 1px solid var(--ink-100);
  border-radius: 2px;
  padding: 0 16px;
  transition: border-color 200ms var(--ease-smooth);
}

.form-field.is-focused {
  border-color: var(--accent-amber);
}

.field-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  font-size: 18px;
  color: var(--ink-500);
  transition: color 200ms var(--ease-smooth);
}

.form-field.is-focused .field-icon {
  color: var(--accent-amber);
}

.field-input {
  flex: 1;
  height: 100%;
  background: transparent;
  border: none;
  outline: none;
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 400;
  color: var(--ink-900);
  letter-spacing: 0.01em;
}

.field-input::placeholder {
  color: var(--ink-500);
  font-weight: 400;
}

/* ========== 表单操作行 ========== */
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 4px 0 8px 0;
  font-family: var(--font-body);
  font-size: 13px;
}

.remember-me {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--ink-700);
  user-select: none;
}

.remember-me input[type='checkbox'] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.checkmark {
  position: relative;
  width: 16px;
  height: 16px;
  border: 1.5px solid var(--ink-300);
  border-radius: 2px;
  background: var(--paper);
  transition: border-color 200ms var(--ease-smooth),
              background-color 200ms var(--ease-smooth);
  flex-shrink: 0;
}

.remember-me input[type='checkbox']:checked ~ .checkmark {
  background: var(--brand-primary-500);
  border-color: var(--brand-primary-500);
}

.remember-me input[type='checkbox']:checked ~ .checkmark::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 0;
  width: 4px;
  height: 9px;
  border: solid var(--paper);
  border-width: 0 1.5px 1.5px 0;
  transform: rotate(45deg);
}

.remember-text {
  font-weight: 500;
  letter-spacing: 0.01em;
}

.forgot-pwd {
  position: relative;
  font-weight: 500;
  color: var(--brand-primary-500);
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: color 200ms var(--ease-smooth);
}

.forgot-pwd:hover {
  color: var(--brand-primary-700);
}

/* ========== 主 CTA ========== */
.login-btn {
  position: relative;
  width: 100%;
  height: 52px;
  border: none;
  border-radius: 2px;
  background: var(--brand-primary-500);
  color: var(--paper);
  font-family: var(--font-body);
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: background-color 200ms var(--ease-smooth);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-btn:hover:not(:disabled) {
  background: var(--brand-primary-700);
}

.login-btn:active:not(:disabled) {
  background: var(--brand-primary-900);
}

.login-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.btn-label {
  display: inline-block;
}

.btn-loading {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  border-top-color: var(--paper);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ========== 测试账号提示 · 带复制按钮 ========== */
.login-tips {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 24px;
  padding: 10px 14px;
  background: var(--ink-50);
  border: 1px solid var(--ink-100);
  border-radius: 2px;
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--ink-500);
}

.tips-label {
  font-weight: 500;
  color: var(--ink-700);
  letter-spacing: 0.02em;
}

.tips-chip {
  font-family: var(--font-number);
  font-size: 12px;
  font-weight: 500;
  color: var(--ink-900);
  letter-spacing: 0.04em;
  background: transparent;
  padding: 0;
}

.tips-copy {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border: 1px solid var(--ink-100);
  border-radius: 2px;
  background: var(--paper);
  color: var(--ink-700);
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: border-color 200ms var(--ease-smooth),
              color 200ms var(--ease-smooth);
}

.tips-copy:hover {
  border-color: var(--brand-primary-500);
  color: var(--brand-primary-500);
}

.tips-copy.is-copied {
  border-color: var(--accent-jade);
  color: var(--accent-jade);
}

/* ========== 响应式 ========== */
@media (max-width: 1024px) {
  .login-brand-area {
    padding: 48px 40px;
  }
  .brand-title {
    font-size: 40px;
  }
}

@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
  }
  .login-brand-area {
    display: none;
  }
  .login-form-area {
    width: 100%;
    flex: 1 1 100%;
    min-height: 100vh;
    padding: 32px 24px;
  }
  .form-area-top {
    top: 24px;
    right: 24px;
  }
  .login-card {
    padding: 32px 24px 24px 24px;
    max-width: 100%;
  }
  .card-title {
    font-size: 26px;
  }
}
</style>
