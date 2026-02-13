# 客服邮件智能回复平台

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Node.js-18+-green?logo=node.js" alt="Node.js">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-orange?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-blue?logo=react" alt="React">
</p>

基于 AI 的客服邮件自动分类与回复系统，支持自动拉取邮件、智能分类、模板回复生成，适用于电商客服场景。

---

## 功能特性

### 核心功能
- **自动拉取邮件** - 通过 IMAP 协议自动收取未回复邮件
- **智能分类** - 关键词匹配 + AI 语义分析双重分类
- **AI 回复生成** - 基于 DeepSeek 大模型生成回复建议
- **模板管理** - 支持自定义回复模板和变量替换
- **自动翻译** - 百度翻译 API 支持多语言翻译
- **一键发送** - 编辑确认后通过 SMTP 发送回复

### 邮件场景支持
- 催发货咨询
- 退款申请
- 物流投诉/未收到快递
- 商品问题咨询
- 其他常见客服场景

---

## 项目架构

```
PythonProject/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── db/                # SQLite 数据库
│   │   │   └── db.py          # 数据库初始化和操作
│   │   ├── routes/            # API 路由
│   │   │   ├── emails.py      # 邮件处理 API
│   │   │   ├── settings.py    # 配置管理 API
│   │   │   ├── categories.py  # 分类管理 API
│   │   │   └── templates.py   # 模板管理 API
│   │   ├── services/          # 业务逻辑
│   │   │   ├── email_client.py      # IMAP/SMTP 邮件客户端
│   │   │   ├── ai_client.py         # DeepSeek AI 接口
│   │   │   ├── classifier.py        # 邮件分类器
│   │   │   ├── template_engine.py   # 模板渲染引擎
│   │   │   ├── translator.py        # 百度翻译接口
│   │   │   └── test_email_generator.py  # 测试邮件生成
│   │   ├── scheduler/         # 定时任务
│   │   │   └── poller.py      # 邮件拉取调度器
│   │   ├── main.py            # FastAPI 应用入口
│   │   └── utils.py           # 工具函数
│   ├── requirements.txt       # Python 依赖
│   └── run.py                 # 启动脚本
│
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── App.jsx           # 主应用组件
│   │   ├── components/       # UI 组件
│   │   │   └── Button.jsx
│   │   ├── styles.css        # 全局样式
│   │   └── main.jsx          # 前端入口
│   ├── index.html
│   ├── package.json
│   └── vite.config.js        # Vite 配置
│
├── scripts/                   # 构建脚本
│   ├── build_macos.sh
│   ├── build_linux.sh
│   └── build_windows.ps1
│
├── data/                     # 本地数据
│   └── app.db               # SQLite 数据库文件
│
└── .gitignore
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+, FastAPI, SQLite |
| 前端 | React 18, Vite |
| AI | DeepSeek API (大模型) |
| 翻译 | 百度翻译 API |
| 邮件 | IMAP/SMTP |

---

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- npm 或 yarn

### 2. 克隆项目

```bash
git clone https://github.com/Yoodo2/AI-reply-email.git
cd AI-reply-email
```

### 3. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 前端配置

```bash
cd frontend

# 安装依赖
npm install

# 开发模式运行
npm run dev
```

### 5. 启动服务

```bash
# 后端（在一个终端）
cd backend
python run.py

# 前端（另一个终端）
cd frontend
npm run dev
```

- 后端地址：http://127.0.0.1:8000
- 前端地址：http://localhost:5173

---

## 首次配置

启动后打开浏览器访问 `http://127.0.0.1:8000`，按照向导完成配置：

### 邮箱配置
| 配置项 | 说明 | 示例 |
|--------|------|------|
| 邮箱账号 | 你的邮箱地址 | yo17765767816@163.com |
| IMAP Host | IMAP 服务器地址 | imap.163.com |
| IMAP Port | IMAP 端口（SSL） | 993 |
| SMTP Host | SMTP 服务器地址 | smtp.163.com |
| SMTP Port | SMTP 端口（SSL） | 465 |
| 登录用户名 | 邮箱前缀或完整地址 | yo17765767816@163.com |
| 登录密码 | 授权码（非邮箱密码） | xxxxxxxx |

> 注意：QQ/163 等邮箱需要在设置中开启 IMAP/SMTP 并获取授权码

### AI 配置
| 配置项 | 说明 |
|--------|------|
| DeepSeek API Key | 从 https://platform.deepseek.com 获取 |
| 百度翻译 AppID | 从 https://fanyi-api.baidu.com 获取 |
| 百度翻译 Secret | 百度翻译 API 密钥 |

---

## 使用指南

### 1. 邮件处理流程

```
拉取邮件 → 自动分类 → 生成回复 → 人工确认 → 发送
```

1. **拉取邮件**：点击「手动拉取」或等待自动拉取
2. **自动分类**：系统自动识别邮件类型（如催发货、退款等）
3. **生成回复**：点击「生成建议」获取 AI 回复或选择模板
4. **人工确认**：编辑修改回复内容
5. **一键发送**：确认后发送邮件

### 2. 模板管理

在「模板库」页面可以：

- **创建模板**：选择关联分类，编写回复内容
- **使用变量**：支持 `{客户姓名}`、`{订单号}`、`{产品名称}` 等变量
- **变量映射**：自动从邮件中提取信息填充模板

### 3. 分类管理

在「配置中心」的「邮件分类管理」可以：

- **添加分类**：设置名称、描述、关键词
- **关键词配置**：用逗号分隔多个关键词
- **优先级设置**：数字越大优先级越高

---

## 邮件类型支持

系统内置支持以下常见客服场景：

| 场景 | 关键词示例 | 说明 |
|------|-----------|------|
| 催发货 | shipping,发货,物流 | 询问订单发货状态 |
| 退款 | refund,退款,cancel | 申请退款或取消订单 |
| 未收到快递 | not received,未收到 | 物流延误或包裹丢失 |
| 商品问题 | damaged,broken,质量问题 | 商品损坏或质量问题 |
| 其他 | 默认分类 | 无法识别时使用 |

---

## 测试功能

### 生成测试邮件

系统提供测试邮件生成功能，可以模拟真实客户邮件：

```python
from backend.app.services.test_email_generator import generateTestEmails

# 发送3封测试邮件
result = generateTestEmails(
    target_email="yo17765767816@163.com",
    count=3,
    email_types=["shipping", "refund", "delivery"]
)
```

支持的邮件类型：
- `shipping` - 催发货
- `refund` - 退款申请
- `delivery` - 未收到快递

---

## 生产部署

### 构建前端

```bash
cd frontend
npm run build
```

### 运行生产版本

```bash
cd backend
python run.py
# 前端静态文件会由 FastAPI 自动托管
```

### 打包脚本

```bash
# macOS
bash scripts/build_macos.sh

# Linux
bash scripts/build_linux.sh

# Windows
powershell scripts/build_windows.ps1
```

---

## 注意事项

1. **安全提示**
   - API Key 等敏感信息存储在本地数据库，不会上传
   - 生产环境建议使用企业邮箱和专属域名
   - 定期备份 `data/app.db` 数据库文件

2. **使用限制**
   - DeepSeek API 有调用频率限制，请合理使用
   - 百度翻译 API 每月有免费额度，超出需付费
   - 邮件拉取以未读状态为准

3. **AI 辅助**
   - AI 分类和回复为辅助建议，请人工确认后发送
   - 建议根据业务场景调整模板内容

---

## 常见问题

### Q: 邮件拉取失败？
A: 检查 IMAP 配置是否正确，确保已开启 IMAP 服务和授权码

### Q: AI 分类不准确？
A: 在「配置中心」调整分类关键词，或手动触发 AI 重新分类

### Q: 翻译失败？
A: 检查百度翻译 AppID 和 Secret 是否正确

### Q: 如何查看日志？
A: 后端日志会输出到终端，生产环境可配置日志文件

---

## License

MIT License - 你可以自由使用和修改本项目
