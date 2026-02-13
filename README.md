# 本地部署客服邮件智能回复平台

## 功能概述
- IMAP 自动拉取未回复邮件，SMTP 发送回复
- 自动语言检测 + 百度翻译（默认中文）
- 分类规则：关键词匹配 > AI 语义匹配 > 默认分类
- AI 生成回复建议（DeepSeek）
- 模板管理 + 变量替换
- 客服可编辑后发送
- SQLite 本地存储，免登录

## 运行环境
- Python 3.10+
- Node.js 18+

## 后端启动
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```
启动后会自动打开浏览器 `http://127.0.0.1:8000`。

## 前端开发
```bash
cd frontend
npm install
npm run dev
```
开发时访问 `http://localhost:5173`。

## 前端构建
```bash
cd frontend
npm run build
```
构建后由 FastAPI 静态托管（自动读取 `frontend/dist`）。

## 配置说明
在“配置中心”填写以下内容：
- 邮箱配置（网易企业邮箱 IMAP/SMTP）
- 百度翻译 AppID/Secret
- DeepSeek API Key
- 拉取间隔（秒）

配置将存储在本地 SQLite：`data/app.db`。

## 打包部署
构建前先生成前端静态文件：
```bash
cd frontend
npm run build
```

执行对应脚本：
```bash
bash scripts/build_macos.sh
bash scripts/build_linux.sh
powershell scripts/build_windows.ps1
```
产物在 `dist/` 目录。

## 重要说明
- 邮件拉取以未读（UNSEEN）为准，如有差异可在后端自行扩展筛选规则。
- AI 分类/回复为辅助建议，请人工确认后发送。
