# 文件传输助手 - 项目上下文

## 项目概述

个人文件传输助手，类似微信文件传输助手的开源自建版本。专为个人设备间文件传输设计，支持图片、文档、二进制文件等多种类型文件的上传、存储和分享。

**设计理念：极简、稳定、快速**
- 专注核心功能，避免过度设计
- 优先实现MVP版本，后续渐进增强
- 保持代码简洁，易于维护

**界面设计：类微信聊天模式**
- 所有消息（文本、文件）在聊天框内按时间顺序显示
- 模拟微信文件传输助手的交互体验
- 支持文本消息和文件混合展示

## 技术栈

- **后端**: FastAPI + SQLite + WebSocket
- **前端**: Vue.js 3 (独立仓库)
- **存储**: 本地文件系统
- **部署**: Docker + Docker Compose

## 功能规划

### MVP 核心功能
- **聊天式界面**: 类微信聊天框，消息和文件按时间顺序显示
- **文本消息**: 支持发送和接收文本消息
- **文件传输**: 多类型文件上传（图片、文档、二进制）
- **拖拽上传**: 文件拖拽上传支持
- **实时通信**: WebSocket 实时消息推送
- **设备状态**: 设备在线状态显示
- **基础安全**: 访问密码保护、文件大小限制、路径遍历防护

### 后续优化功能（低优先级）
- **文件管理**: 独立的文件列表管理界面
- **文件预览**: 文本文件在线预览、图片缩略图
- **文件操作**: 文件分类存储、搜索和过滤
- **系统功能**: 自动清理过期文件、Docker 部署
- **性能优化**: 上传进度显示、静态文件缓存、数据库优化
- **高级功能**: 文件类型验证、多文件批量上传、操作通知推送

## 项目架构

### 仓库说明
**当前仓库：后端专用仓库**
- 本仓库专注于后端 API 开发
- 前端代码已迁移到独立仓库
- 项目结构已从 `backend/` 子目录提升到根目录

### 目录结构
```
talkeme/ (后端仓库)
├── app/                    # FastAPI 应用核心
│   ├── __init__.py
│   ├── main.py            # 应用入口
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库连接
│   ├── models/            # SQLAlchemy 数据模型
│   │   ├── __init__.py
│   │   ├── file.py        # 文件模型
│   │   ├── message.py     # 消息模型
│   │   └── hash_task.py   # 哈希任务模型
│   ├── api/               # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py        # 认证接口
│   │   ├── files.py       # 文件管理接口
│   │   ├── messages.py    # 消息管理接口
│   │   └── websocket.py   # WebSocket 处理
│   ├── services/          # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── file_service.py       # 文件服务
│   │   ├── message_service.py    # 消息服务
│   │   └── hash_service.py       # 哈希计算服务
│   └── utils/             # 工具函数
│       ├── __init__.py
│       ├── security.py    # 安全工具
│       └── file_utils.py  # 文件处理工具
├── uploads/               # 文件存储目录
│   ├── images/            # 图片文件
│   ├── documents/         # 文档文件
│   └── others/            # 其他文件
├── temp/                  # 临时文件目录
├── tests/                 # 测试文件
├── init_db.py            # 数据库初始化脚本
├── run.py                # 启动脚本
├── requirements.txt      # Python 依赖
├── .env.example          # 环境变量示例
├── .env                  # 环境变量配置（本地，不提交）
├── README.md             # 项目说明（后端专用）
├── README.old.md         # 旧版说明（归档）
└── CLAUDE.md             # 项目上下文（本文件）
```

## 数据模型

### 数据库设计和文件去重实现计划

#### 文件去重策略
- **哈希算法**: 使用 SHA256 完整文件哈希确保精确去重
- **计算方式**: 异步方式计算哈希值，避免阻塞上传流程
- **存储优化**: 相同文件只存储一份，通过引用计数管理
- **秒传支持**: 检查哈希值实现文件秒传功能

#### 实现计划
1. **数据库模型优化**:
   - File表增加file_hash和reference_count字段
   - Message表分离文件信息，只存储引用关系
   - 在file_hash字段建立索引优化查询性能

2. **文件去重服务**:
   - 实现异步SHA256哈希计算工具
   - 创建去重检查和引用计数管理逻辑
   - 支持文件上传时的秒传检测

3. **数据库迁移**:
   - 创建SQLAlchemy模型定义
   - 生成数据库迁移脚本
   - 配置数据库连接和索引

### 优化后的数据模型
```python
class File:
    id: int                    # 主键
    file_hash: str             # SHA256哈希值，用于去重（建立索引）
    stored_name: str           # 存储文件名（UUID）
    file_type: str             # 文件类型（image/document/other）
    mime_type: str             # MIME类型
    size: int                  # 文件大小（字节）
    first_upload_time: datetime # 首次上传时间
    reference_count: int       # 引用计数（有多少消息引用此文件）
    is_deleted: bool           # 软删除标记
    hash_status: str           # 哈希计算状态（pending/completed/failed）

class Message:
    id: int                    # 主键
    message_type: str          # 消息类型（text/file）
    content: str               # 文本内容或原始文件名
    file_id: int              # 关联的文件ID（文件消息时使用）
    timestamp: datetime        # 消息时间
    device_id: str            # 设备标识
    is_deleted: bool          # 软删除标记

# 异步任务表（用于哈希计算）
class HashTask:
    id: int                   # 主键
    file_id: int             # 关联文件ID
    status: str              # 任务状态（pending/processing/completed/failed）
    created_at: datetime     # 创建时间
    completed_at: datetime   # 完成时间
```

### 文件去重实现流程
1. **文件上传时**:
   - 先保存文件到临时目录
   - 创建File记录，hash_status设为pending
   - 创建异步哈希计算任务
   - 立即返回上传成功响应

2. **异步哈希计算**:
   - 后台任务计算SHA256哈希值
   - 检查数据库中是否存在相同哈希的文件
   - 如果存在，删除新文件，更新引用计数
   - 如果不存在，移动文件到正式目录

3. **消息删除时**:
   - 减少文件引用计数
   - 当引用计数为0时，标记文件为删除状态
   - 定期清理任务删除物理文件

## API 接口设计

### REST API - MVP版本
- `POST /api/auth/login` - 密码验证
- `GET /api/messages` - 获取消息列表（按时间顺序）
- `POST /api/messages/text` - 发送文本消息
- `POST /api/messages/file` - 发送文件消息（上传文件）
- `GET /api/files/{file_id}/download` - 下载文件
- `DELETE /api/messages/{message_id}` - 删除消息

### WebSocket - MVP版本
- `/ws` - WebSocket 连接端点
- 消息类型：
  - `new_message` - 新消息通知
  - `message_deleted` - 消息删除通知
  - `device_status` - 设备在线状态
  - `typing` - 正在输入状态（可选）

### 后续优化接口（低优先级）
- `GET /api/files` - 独立的文件列表管理
- `GET /api/files/{file_id}/thumbnail` - 获取缩略图
- WebSocket消息：`upload_progress` - 上传进度

## 配置参数

### 环境变量
```bash
# MVP 基础配置
APP_HOST=0.0.0.0          # 服务监听地址
APP_PORT=8000             # 服务端口
APP_SECRET=changeme       # 访问密码
DEBUG=false               # 调试模式

# 文件存储配置
UPLOAD_DIR=./uploads      # 文件存储目录
TEMP_DIR=./temp          # 临时目录
MAX_FILE_SIZE=104857600   # 最大文件大小（100MB）

# 数据库配置
DATABASE_URL=sqlite:///./files.db

# 安全配置
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# 后续优化配置（低优先级）
# THUMBNAIL_DIR=./thumbnails # 缩略图目录
# ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,pdf,txt,doc,docx,zip,rar
# FILE_EXPIRE_DAYS=7        # 文件过期天数
# MAX_FILES_PER_USER=1000   # 最大文件数量
# AUTO_CLEANUP=true         # 自动清理过期文件
```

## 开发约定

### MVP 开发原则
- 优先实现核心功能，避免过度设计
- 保持代码简洁，易于理解和维护
- 快速迭代，及时验证功能可用性

### 代码规范
- 后端使用 Black 格式化，遵循 PEP 8
- 前端使用 Prettier 格式化，遵循 Vue.js 风格指南
- 关键函数添加必要注释
- API 接口提供基础文档

### 测试策略（MVP版本）
- 手动测试覆盖主要功能
- 后续增加自动化测试

## 部署说明

### MVP 手动部署（优先）
1. 安装 Python 3.8+ 和 Node.js 16+
2. 安装后端依赖：`pip install -r backend/requirements.txt`
3. 安装前端依赖：`cd frontend && npm install`
4. 构建前端：`npm run build`
5. 启动后端：`uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`

### Docker 部署（后续优化）
1. 复制 `.env.example` 到 `.env` 并配置参数
2. 运行 `docker-compose up -d`
3. 访问 `http://localhost:8080`

## MVP 安全措施

- 访问密码验证
- 文件大小限制
- 路径遍历攻击防护
- 基础错误处理

## 后续优化（低优先级）

### 性能优化
- 图片自动压缩和缩略图生成
- 静态文件缓存策略
- 数据库查询优化
- WebSocket 连接池管理
- 文件上传分片处理

### 安全增强
- 文件类型白名单验证
- XSS 和 CSRF 防护
- 文件内容安全扫描

### 监控和日志
- 应用性能监控
- 文件操作日志记录
- 错误日志和异常追踪
- 存储空间使用监控

## MVP 版本限制

- 单用户模式，不支持多用户管理
- 文件存储在本地，不支持分布式存储
- 没有文件版本控制功能
- 依赖单机性能，不支持集群部署
- 简化的安全模型，仅基础防护
- 无文件类型过滤和预览优化
- 手动部署，暂无容器化支持

## 开发优先级

1. **第一阶段（MVP）**: 聊天式界面 + 文本消息 + 文件消息 + WebSocket 实时通信
2. **第二阶段**: 用户体验优化（文件预览、进度显示等）
3. **第三阶段**: 文件管理功能（独立文件列表、搜索、分类）
4. **第四阶段**: 部署和运维优化（Docker、监控、性能优化等）

## 界面交互设计

### 聊天窗口结构
```
┌─────────────────────────────────┐
│ 文件传输助手                      │ ← 顶部标题栏
├─────────────────────────────────┤
│ 今天 10:30                      │ ← 时间分隔线
│                                 │
│ [设备A] 这是一条文本消息          │ ← 文本消息
│ 10:31                          │
│                                 │
│ [设备A] 📄 document.pdf (2.5MB) │ ← 文件消息
│ 10:32                          │
│                                 │
│ [设备B] 收到文件                 │ ← 回复消息
│ 10:33                          │
│                                 │
├─────────────────────────────────┤
│ [输入框] [📎] [发送]             │ ← 输入区域
└─────────────────────────────────┘
```

### 消息类型设计
- **文本消息**: 普通文字内容
- **文件消息**: 显示文件名、大小、图标，可点击下载
- **系统消息**: 设备上线/离线通知（可选）