# 文件传输助手

类似微信文件传输助手的开源自建版本，专为个人设备间文件传输设计。

**设计理念：极简、稳定、快速**

## 界面设计

🗨️ **类微信聊天界面**: 所有消息（文本、文件）在聊天框内按时间顺序显示，类似微信文件传输助手的交互体验。

## 核心功能

- 📁 **多类型文件支持**: 图片、文档、二进制文件等
- 💬 **聊天式界面**: 文件和消息在聊天框中按时间顺序展示
- 🚀 **实时传输**: WebSocket 实时通信
- 🖱️ **拖拽上传**: 支持文件拖拽上传，操作便捷
- 📱 **移动适配**: 响应式设计，支持手机浏览器访问
- 🔐 **简单安全**: 访问密码保护，本地存储安全可控

## 技术架构

### 后端
- **FastAPI**: 高性能异步 Web 框架
- **SQLite**: 轻量级数据库，存储文件元数据
- **WebSocket**: 实时通信支持
- **本地存储**: 文件直接存储在服务器本地

### 前端
- **Vue.js 3**: 现代响应式前端框架
- **SPA**: 单页应用，流畅的用户体验
- **WebSocket 客户端**: 实时状态更新

## 项目结构

```
transfer/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   └── websocket/      # WebSocket 处理
│   ├── uploads/            # 文件存储目录
│   │   ├── images/         # 图片文件
│   │   ├── documents/      # 文档文件
│   │   └── others/         # 其他文件
│   └── temp/              # 临时文件
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/     # Vue 组件
│   │   ├── views/          # 页面视图
│   │   ├── stores/         # 状态管理
│   │   └── utils/          # 工具函数
│   └── public/
├── docker-compose.yml      # Docker 部署配置
└── README.md
```

## 快速开始

### 使用 Docker (推荐)

```bash
# 克隆项目
git clone [项目地址]
cd transfer

# 启动服务
docker-compose up -d

# 访问应用
http://localhost:8080
```

### 本地开发

#### 后端
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

## 配置说明

### 环境变量

```bash
# 应用配置
APP_PORT=8000              # 后端端口
APP_SECRET=your-secret     # 访问密码
UPLOAD_MAX_SIZE=100        # 最大文件大小(MB)
FILE_EXPIRE_DAYS=7         # 文件过期天数

# 存储配置
UPLOAD_DIR=./uploads       # 文件存储目录
```

## 核心功能

### 聊天式交互
- 类微信聊天界面设计
- 消息和文件按时间顺序显示
- 支持文本消息发送

### 文件传输
- 支持拖拽上传文件
- 文件在聊天框中显示
- 点击文件可下载

### 实时通信
- WebSocket 实时消息推送
- 设备在线状态显示

### 基础安全
- 访问密码保护
- 文件大小限制
- 路径遍历防护

## 开发计划

### MVP 版本
- [x] 基础架构设计
- [ ] 后端 API 开发 (消息、文件上传下载)
- [ ] 前端聊天界面开发
- [ ] WebSocket 实时消息集成
- [ ] 功能测试

### 后续优化 (低优先级)
- [ ] 文件列表管理界面
- [ ] Docker 部署
- [ ] 多文件批量上传
- [ ] 实时进度显示
- [ ] 文件类型验证
- [ ] 按类型分类显示
- [ ] 文件搜索功能
- [ ] 过期文件自动清理
- [ ] 上传进度实时更新
- [ ] 文件操作通知推送
- [ ] 图片缩略图生成
- [ ] 文件类型白名单
- [ ] XSS 防护
- [ ] 图片自动压缩
- [ ] 缩略图缓存
- [ ] 静态文件缓存
- [ ] 数据库查询优化
- [ ] 文本文件在线预览

## 贡献指南

欢迎提交 Issue 和 Pull Request 来改进项目。

## 许可证

MIT License