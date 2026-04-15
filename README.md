# 运营商招投标信息跟踪平台

<div align="center">

![版本](https://img.shields.io/badge/版本-v5.0-blue)
![协议](https://img.shields.io/badge/协议-MIT-green)
![数据源](https://img.shields.io/badge/数据源-乙方宝_+_百度寻标宝-orange)
![状态](https://img.shields.io/badge/状态-可用-success)

**📡 三大运营商招标信息实时抓取 · 智能 · 数据展示**

[在线预览](https://qq464598346-debug.github.io/bidding-tracker/) · [快速开始](#-快速开始) · [功能介绍](#-核心功能) · [本地部署](#-本地部署爬虫模式)

</div>

---

## 🌟 亮点

- 🕷️ **实时爬虫** — 自动从乙方宝 + 百度寻标宝抓取最新招标公告
- 📊 **智能面板** — 运营商分布、品类统计、金额汇总一目了然
- 🔗 **原文直达** — 每条数据有可点击的公告详情链接
- 🔄 **定时更新** — 可配置30秒/1分钟/3分钟/5分钟自动刷新
- 📤 **一键导出** — Excel / PDF / CSV 三种格式
- 🖥️ **双模式运行** — 本地（爬虫+API）或 GitHub Pages（纯前端）

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🕷️ **实时数据采集** | 从乙方宝、百度寻标宝自动抓取，支持手动/定时触发 |
| 📊 **数据概览面板** | 总数 / 即将截止 / 本周新增 / 涉及金额 |
| 📈 **运营商分布统计** | 移动 / 联通 / 电信分别展示，带品牌色 |
| 🔍 **多维度搜索筛选** | 关键词 × 运营商 × 状态 × 类别 × 排序方式 |
| ▦ **双视图切换** | 卡片视图 / 列表视图，一键切换 |
| 📄 **详情弹窗** | 完整项目信息、中标结果、标签、原文链接 |
| 📤 **导出功能** | Excel（含品牌色）+ PDF报告 + CSV |
| 🔄 **自动刷新** | 30秒 / 1分钟 / 3分钟 / 5分钟可选 |
| 🎯 **智能状态** | 自动判断即将截止（≤7天）和已过期项目 |

---

## ⚡ 快速开始

### 方式一：直接浏览（无需安装）

访问 GitHub Pages 在线版本，使用内置静态数据：

👉 **https://qq464598346-debug.github.io/bidding-tracker/**

### 方式二：本地纯前端（零依赖）

```bash
git clone https://github.com/qq464598346-debug/bidding-tracker.git
cd bidding-tracker
# 双击 index.html 或：
python -m http.server 8080
```

---

## 🛠️ 本地部署（爬虫模式）

> 需要 Python 3.9+ 环境。此模式支持实时抓取最新数据。

### 一键启动

```bash
# 1. 克隆项目
git clone https://github.com/qq464598346-debug/bidding-tracker.git
cd bidding-tracker

# 2. 安装依赖
pip install -r spider/requirements.txt

# 3. 双击启动（Windows）
start.bat
# 或手动运行：
cd spider && python main.py
```

启动后会自动执行：
1. 🕷️ **首次全量采集** — 从乙方宝（移动/联通/电信）+ 寻标宝抓取数据
2. 🔄 **后台定时采集** — 每隔30分钟自动更新
3. 🌐 **API服务启动** — `http://localhost:8765`

然后浏览器打开 `index.html` 即可查看实时数据。

### 手动采集

```bash
# 仅运行一次数据采集
cd spider
python main.py --crawl

# 仅启动API服务（不采集）
python main.py --api

# 指定API端口
python main.py --port 8080
```

### Windows 快捷脚本

| 脚本 | 功能 |
|------|------|
| `start.bat` | 启动爬虫 + API服务（推荐） |
| `crawl.bat` | 仅运行一次数据采集 |

---

## 📋 数据说明

### 数据源

| 数据源 | 网址 | 覆盖内容 |
|--------|------|---------|
| 📱 乙方宝·移动 | `yfbzb.com/zbzt/40` | 中国移动招标公告 |
| 📞 乙方宝·联通 | `yfbzb.com/search?keyword=中国联通` | 中国联通招标公告 |
| ☎️ 乙方宝·电信 | `yfbzb.com/zbzt/84` | 中国电信招标公告 |
| 🔍 百度寻标宝 | `xunbiaobao.baidu.com` | 搜索三大运营商标讯 |

### 覆盖品类

| 类别 | 示例项目 |
|------|---------|
| 💻 **基础软件** | 云计算平台、操作系统、数据库、AI大模型平台 |
| 💡 **行业解决方案** | 智慧城市、5G专网、数字政府、算力网络、车联网 |
| 🖧 **服务器** | AI算力集群、通用服务器、全闪存存储、FTTR网关 |
| 🛠️ **服务** | 网络安全运维、IDC运维、系统集成、容灾备份 |

---

## 🏗️ 项目结构

```
bidding-tracker/
├── index.html              # 前端应用（单文件，含静态数据）
├── start.bat               # 一键启动脚本（Windows）
├── crawl.bat               # 单次采集脚本（Windows）
├── deploy.bat              # 一键部署脚本
├── README.md               # 项目文档
├── .gitignore
└── spider/                 # 爬虫 + API 后端
    ├── main.py             # 入口（启动爬虫+API）
    ├── requirements.txt    # Python 依赖
    ├── api/                # Flask API 服务
    │   └── server.py       # REST API + SSE 实时推送
    ├── core/               # 核心模块
    │   ├── db.py           # SQLite 数据库
    │   ├── config.py       # 配置管理
    │   └── scheduler.py    # 定时任务调度
    ├── crawlers/           # 爬虫模块
    │   ├── coordinator.py  # 采集协调器（6任务并发）
    │   ├── yifangbao_crawler.py  # 乙方宝爬虫
    │   ├── xunbiaobao_crawler.py # 百度寻标宝爬虫
    │   └── base.py         # 爬虫基类
    └── data/               # 数据存储目录
        └── bidding.db      # SQLite 数据库（自动生成）
```

---

## 🔌 API 接口

本地运行爬虫模式后，API 服务运行在 `http://localhost:8765`：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/bidding` | 获取所有招标数据 |
| GET | `/api/bidding/:id` | 获取单条详情 |
| GET | `/api/stats` | 获取统计数据 |
| POST | `/api/crawl` | 手动触发数据采集 |
| GET | `/api/events` | SSE 实时推送 |
| GET | `/api/export/excel` | 导出 Excel |
| GET | `/api/export/pdf` | 导出 PDF 报告 |
| GET | `/api/export/csv` | 导出 CSV |

---

## 📝 更新日志

### v5.0 (2026-04-15)
- 🕷️ 新增爬虫系统：乙方宝 + 百度寻标宝双数据源
- 🌐 Flask API 服务：REST 接口 + SSE 实时推送
- 💾 SQLite 数据库：自动存储和管理抓取数据
- 🔄 后台定时采集：每30分钟自动更新
- 📱 前端双模式：自动检测 API 连接，降级到静态数据

### v4.0 (2026-04-15)
- 📊 数据替换为乙方宝真实招标信息（60条）
- 🔗 每条数据有可点击的原文详情链接

### v3.0 (2026-04-15)
- 🔄 全面重构为纯前端自包含应用
- 📊 内置60+条高质量招标数据
- 📤 Excel/PDF/CSV 三种格式导出

---

## 📄 技术栈

**前端**：HTML + CSS + JavaScript（零依赖，单文件）
**后端**：Python + Flask + SQLite
**爬虫**：httpx + BeautifulSoup4 + Playwright（可选）
**部署**：GitHub Pages / 本地运行

---

## 📜 许可证

MIT License

<div align="center">

Made with ❤️ for tracking China telecom operator bidding info

</div>
