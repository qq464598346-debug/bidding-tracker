# 运营商招投标信息跟踪平台

<div align="center">

![版本](https://img.shields.io/badge/版本-v3.0-blue)
![协议](https://img.shields.io/badge/协议-MIT-green)
![部署](https://img.shields.io/badge/部署-GitHub_Pages-orange)
![状态](https://img.shields.io/badge/状态-可用-success)

**📡 覆盖三大运营商 · 基础软件 / 行业解决方案 / 服务器 / 服务**

[在线预览](#) · [功能介绍](#-核心功能) · [一键部署](#-一键部署) · [数据说明](#-数据说明)

</div>

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 📊 **数据概览面板** | 总数 / 即将截止 / 本周新增 / 涉及金额 |
| 📈 **运营商分布统计** | 移动 / 联通 / 电信分别展示，带品牌色 |
| 🔍 **多维度搜索筛选** | 关键词 × 运营商 × 状态 × 类别 × 排序方式 |
| ▦ **双视图切换** | 卡片视图 / 列表视图，一键切换 |
| 📄 **详情弹窗** | 完整项目信息、中标结果、标签等 |
| 🔄 **自动刷新** | 30秒 / 1分钟 / 3分钟 / 5分钟可选 |
| 📤 **导出功能** | Excel（含品牌色）+ PDF报告 + CSV |
| 🎯 **智能状态更新** | 自动判断即将截止（≤7天）和已过期项目 |

## 🚀 一键部署到 GitHub Pages

### 方法一：最简单（推荐）

1. Fork 本仓库
2. 进入 Settings → Pages → Source 选择 `main` 分支
3. 访问 `https://你的用户名.github.io/仓库名/` 即可

### 方法二：GitHub Actions 自动部署

本仓库已配置 Actions 工作流，推送代码后自动构建和部署：

```bash
git clone https://github.com/你的用户名/bidding-tracker.git
cd bidding-tracker
git push origin main
# 自动触发部署
```

### 方法三：本地运行

```bash
# 直接用浏览器打开即可
open index.html

# 或使用任意HTTP服务
npx serve .
python -m http.server 8080
```

## 📋 数据说明

### 数据来源

内置 **60+ 条高质量招标信息**，覆盖：

- ✅ 中国移动 (CMCC) — 20条
- ✅ 中国联通 (CUCC) — 20条  
- ✅ 中国电信 (CTCC) — 20条

### 覆盖类别

| 类别 | 示例项目 |
|------|---------|
| 💻 **基础软件** | 云计算平台、操作系统、数据库、AIOps、大模型平台 |
| 💡 **行业解决方案** | 智慧城市、5G专网、数字政府、算力网络、车联网 |
| 🖧 **服务器** | AI算力集群、通用服务器、全闪存存储、FTTR网关 |
| 🛠️ **服务** | 网络安全运维、IDC运维、系统集成、容灾备份 |

### 项目状态

- 🔵 **招标中** — 正在投标期
- ⚡ **即将截止** — ≤7天截止（自动标记）
- 🔵 **已公示** — 已出中标结果
- ⚪ **已结束** — 已过截止日期

## 🛠️ 技术栈

- **纯前端**：HTML + CSS + JavaScript（零依赖）
- **无需后端**：所有数据内置，开箱即用
- **响应式设计**：适配桌面端 / 平板 / 手机

## 📂 文件结构

```
├── index.html          # 完整应用（单文件）
├── README.md           # 项目文档
└── .github/
    └── workflows/
        └── deploy.yml   # GitHub Pages 自动部署
```

## 📝 更新日志

### v3.0 (2026-04-15)
- 🔄 全面重构为纯前端自包含应用
- 📊 内置60+条高质量招标数据
- 🤖 一键支持 GitHub Pages 部署
- 📤 新增 Excel/PDF/CSV 三种格式导出
- ⏱️ 新增定时自动刷新机制

---

<div align="center">

Made with ❤️ for tracking China telecom operator bidding info

</div>
