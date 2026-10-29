#!/bin/bash
# ============================================
# HR-SaaS 一键启动脚本
# 启动后端 + 前端服务，外网可访问
# ============================================

echo "============================================="
echo "  HR-SaaS 一键启动脚本"
echo "============================================="
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend/dist"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# 清理旧进程
# ============================================
echo -e "${YELLOW}🔧 清理旧进程...${NC}"
pkill -f "uvicorn.*hr-saas" 2>/dev/null || true
pkill -f "app.main" 2>/dev/null || true
pkill -f "http.server.*8080" 2>/dev/null || true
sleep 1
echo -e "${GREEN}✅ 旧进程已清理${NC}"
echo ""

# ============================================
# 启动后端服务
# ============================================
echo -e "${YELLOW}🚀 启动后端服务...${NC}"
cd $BACKEND_DIR

# 确保依赖已安装
pip install fastapi uvicorn sqlalchemy pydantic-settings python-jose passlib python-multipart pypdf -q 2>/dev/null

# 启动后端
nohup python -m app.main > backend.log 2>&1 &
sleep 2

# 检查后端是否启动成功
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 后端服务启动成功${NC}"
    echo -e "${GREEN}   API 地址: http://localhost:8000${NC}"
    echo -e "${GREEN}   接口文档: http://localhost:8000/docs${NC}"
else
    echo -e "${RED}❌ 后端启动失败，请检查日志: $BACKEND_DIR/backend.log${NC}"
fi
echo ""

# ============================================
# 启动前端服务
# ============================================
echo -e "${YELLOW}🚀 启动前端服务...${NC}"

# 如果 dist 目录不存在，创建一个简单的前端
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${YELLOW}   前端未打包，创建简易演示页面...${NC}"
    mkdir -p $FRONTEND_DIR
    
    cat > $FRONTEND_DIR/index.html << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HR-SaaS 人力资源管理平台</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
    <div class="container mx-auto px-4 py-16">
        <div class="max-w-3xl mx-auto text-center">
            <div class="mb-8">
                <div class="w-24 h-24 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                    <svg class="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                    </svg>
                </div>
                <h1 class="text-4xl font-bold text-gray-800 mb-4">HR-SaaS 人力资源管理平台</h1>
                <p class="text-xl text-gray-600 mb-8">AI 驱动的智能招聘管理系统</p>
            </div>
            
            <div class="grid md:grid-cols-3 gap-6 mb-12">
                <div class="bg-white rounded-xl shadow-lg p-6">
                    <div class="text-blue-500 text-3xl mb-3">📋</div>
                    <h3 class="font-semibold text-lg mb-2">项目管理</h3>
                    <p class="text-gray-600 text-sm">多项目并行管理，灵活分配权限</p>
                </div>
                <div class="bg-white rounded-xl shadow-lg p-6">
                    <div class="text-green-500 text-3xl mb-3">📄</div>
                    <h3 class="font-semibold text-lg mb-2">简历管理</h3>
                    <p class="text-gray-600 text-sm">AI 自动解析简历，智能匹配</p>
                </div>
                <div class="bg-white rounded-xl shadow-lg p-6">
                    <div class="text-purple-500 text-3xl mb-3">📊</div>
                    <h3 class="font-semibold text-lg mb-2">数据看板</h3>
                    <p class="text-gray-600 text-sm">实时数据统计，可视化展示</p>
                </div>
            </div>
            
            <div class="bg-white rounded-2xl shadow-xl p-8 text-left max-w-md mx-auto">
                <h2 class="text-xl font-semibold mb-6 text-center">系统登录</h2>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
                        <input type="text" value="admin" class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50" readonly>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
                        <input type="text" value="admin123" class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50" readonly>
                    </div>
                </div>
                <div class="mt-6 pt-6 border-t border-gray-200">
                    <h3 class="font-medium mb-3">后端 API 状态</h3>
                    <div id="api-status" class="flex items-center">
                        <div class="w-3 h-3 rounded-full bg-yellow-500 mr-2 animate-pulse"></div>
                        <span class="text-gray-600">检查中...</span>
                    </div>
                    <a href="http://localhost:8000/docs" target="_blank" class="mt-3 inline-block text-blue-600 hover:text-blue-800 text-sm">
                        查看 API 文档 →
                    </a>
                </div>
            </div>
            
            <div class="mt-8 text-gray-500 text-sm">
                <p>完整 Vue 前端可通过 npm run build 打包后部署</p>
                <p class="mt-1">当前为简化演示页面，后端 API 已就绪</p>
            </div>
        </div>
    </div>
    
    <script>
        // 检查 API 状态
        fetch('http://localhost:8000/health')
            .then(res => res.json())
            .then(data => {
                document.getElementById('api-status').innerHTML = `
                    <div class="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
                    <span class="text-green-600 font-medium">后端 API 运行正常</span>
                `;
            })
            .catch(err => {
                document.getElementById('api-status').innerHTML = `
                    <div class="w-3 h-3 rounded-full bg-red-500 mr-2"></div>
                    <span class="text-red-600">后端连接失败</span>
                `;
            });
    </script>
</body>
</html>
EOF
fi

# 启动前端静态服务
cd $FRONTEND_DIR
nohup python -m http.server 8080 --bind 0.0.0.0 > frontend.log 2>&1 &
sleep 1

# 检查前端是否启动成功
if curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 前端服务启动成功${NC}"
    echo -e "${GREEN}   访问地址: http://localhost:8080${NC}"
else
    echo -e "${RED}❌ 前端启动失败，请检查日志: $FRONTEND_DIR/frontend.log${NC}"
fi
echo ""

# ============================================
# 服务信息汇总
# ============================================
echo "============================================="
echo "  🌐 服务部署完成"
echo "============================================="
echo ""
echo -e "${GREEN}🎨 前端地址:${NC}  http://localhost:8080"
echo -e "${GREEN}🔧 后端地址:${NC}  http://localhost:8000"
echo -e "${GREEN}📄 API 文档:${NC}  http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}👤 默认管理员账号:${NC}"
echo "   用户名: admin"
echo "   密码:   admin123"
echo ""
echo "============================================="
echo "  📝 日志文件位置"
echo "============================================="
echo "  后端日志: $BACKEND_DIR/backend.log"
echo "  前端日志: $FRONTEND_DIR/frontend.log"
echo ""
echo "  停止服务命令:"
echo "    pkill -f 'app.main'"
echo "    pkill -f 'http.server.*8080'"
echo "============================================="
