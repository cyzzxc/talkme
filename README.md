# 文件传输助手 - 后端API

个人文件传输助手的后端服务，基于 FastAPI 构建，支持文件上传、去重、消息管理和 WebSocket 实时通信。

## 功能特性

- ✅ **文件上传与下载**：支持多种文件类型
- ✅ **文件去重**：基于 SHA256 哈希值的智能去重，节省存储空间
- ✅ **消息管理**：统一管理文本和文件消息
- ✅ **实时通信**：WebSocket 支持实时消息推送
- ✅ **设备管理**：多设备在线状态跟踪
- ✅ **引用计数**：智能管理文件生命周期
- ✅ **简单认证**：密码保护访问

## 技术栈

- **FastAPI**: 高性能异步Web框架
- **SQLAlchemy**: ORM 和数据库管理
- **SQLite**: 轻量级数据库
- **WebSocket**: 实时双向通信
- **Pydantic**: 数据验证

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，至少修改 APP_SECRET
```

### 3. 初始化数据库

```bash
python init_db.py
```

### 4. 启动服务

```bash
python run.py
```

或使用 uvicorn：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 认证 (`/api/auth`)

- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/verify` - 验证令牌
- `GET /api/auth/status` - 认证状态

### 文件管理 (`/api/files`)

- `POST /api/files/upload` - 上传文件
- `GET /api/files/{file_id}/download` - 下载文件
- `GET /api/files/{file_id}/info` - 获取文件信息
- `GET /api/files/` - 获取文件列表（分页）
- `DELETE /api/files/{file_id}` - 删除文件
- `GET /api/files/stats` - 文件统计信息

### 消息管理 (`/api/messages`)

- `POST /api/messages/text` - 发送文本消息
- `POST /api/messages/file` - 发送文件消息
- `POST /api/messages/upload-and-send` - 上传并发送文件
- `GET /api/messages/` - 获取消息列表（分页）
- `GET /api/messages/{message_id}` - 获取单条消息
- `DELETE /api/messages/{message_id}` - 删除消息
- `PUT /api/messages/{message_id}/status` - 更新消息状态
- `GET /api/messages/stats/summary` - 消息统计

### WebSocket (`/ws`)

- `WS /ws?device_id=xxx` - WebSocket 连接
- `GET /ws/stats` - WebSocket 统计信息

## WebSocket 消息格式

### 客户端发送

```json
// 心跳
{"type": "ping"}

// 正在输入
{"type": "typing", "is_typing": true}

// 获取在线设备
{"type": "get_online_devices"}
```

### 服务端推送

```json
// 连接成功
{"type": "connected", "device_id": "xxx", "online_devices": [...]}

// 新消息
{"type": "new_message", "data": {...}}

// 消息删除
{"type": "message_deleted", "message_id": 123}

// 设备状态
{"type": "device_status", "device_id": "xxx", "status": "online"}

// 正在输入
{"type": "typing", "device_id": "xxx", "is_typing": true}
```

## 文件去重机制

1. **上传时计算哈希**：文件上传时计算 SHA256 哈希值
2. **检查重复**：查询数据库是否存在相同哈希的文件
3. **秒传处理**：如果文件已存在，直接返回文件ID，增加引用计数
4. **存储优化**：相同文件只存储一份，通过引用计数管理

## 数据模型

### File（文件）

- `id`: 主键
- `file_hash`: SHA256 哈希值（用于去重）
- `stored_name`: 存储文件名（UUID）
- `file_type`: 文件类型（image/document/other）
- `mime_type`: MIME 类型
- `size`: 文件大小
- `reference_count`: 引用计数
- `hash_status`: 哈希计算状态

### Message（消息）

- `id`: 主键
- `message_type`: 消息类型（text/file）
- `content`: 文本内容或文件名
- `file_id`: 关联文件ID
- `timestamp`: 消息时间
- `device_id`: 设备标识
- `status`: 消息状态

## 环境变量配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_HOST` | 0.0.0.0 | 服务监听地址 |
| `APP_PORT` | 8000 | 服务端口 |
| `APP_SECRET` | changeme | 访问密码（必须修改） |
| `DEBUG` | false | 调试模式 |
| `MAX_FILE_SIZE` | 104857600 | 最大文件大小（100MB） |
| `ENABLE_FILE_DEDUP` | true | 启用文件去重 |
| `ALLOWED_EXTENSIONS` | jpg,jpeg,png,... | 允许的文件扩展名 |

## 开发指南

### 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # 主应用
│   ├── config.py         # 配置
│   ├── database.py       # 数据库连接
│   ├── models/           # 数据模型
│   │   ├── file.py
│   │   ├── message.py
│   │   └── hash_task.py
│   └── api/              # API 路由
│       ├── auth.py
│       ├── files.py
│       ├── messages.py
│       └── websocket.py
├── uploads/              # 文件存储
├── temp/                 # 临时文件
├── init_db.py            # 数据库初始化
├── run.py                # 启动脚本
└── requirements.txt      # 依赖
```

### 添加新的API端点

1. 在 `app/api/` 下创建新的路由文件
2. 定义路由和处理函数
3. 在 `app/api/__init__.py` 中导入路由
4. 在 `app/main.py` 中注册路由

### 数据库迁移

使用 `init_db.py` 脚本初始化或重置数据库：

```bash
python init_db.py
```

## 安全注意事项

- **修改默认密码**：部署前务必修改 `APP_SECRET`
- **CORS 配置**：根据实际情况配置 `CORS_ORIGINS`
- **文件大小限制**：根据服务器资源调整 `MAX_FILE_SIZE`
- **文件类型限制**：配置 `ALLOWED_EXTENSIONS` 限制上传文件类型
- **HTTPS**：生产环境建议使用 HTTPS

## 故障排除

### 数据库连接失败

```bash
# 检查数据库文件权限
ls -l files.db

# 重新初始化数据库
python init_db.py
```

### 文件上传失败

```bash
# 检查上传目录权限
ls -ld uploads/

# 创建必要目录
mkdir -p uploads/{images,documents,others} temp
```

### WebSocket 连接失败

- 检查防火墙设置
- 确认 CORS 配置正确
- 查看浏览器控制台错误信息

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！