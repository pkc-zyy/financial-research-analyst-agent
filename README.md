# 💰 金融理财顾问系统 · Financial Research Analyst Agent

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-FF4B4B?style=for-the-badge&logo=langchain&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F00?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

**由 11 个专项智能体协作的自动化投研系统：从数据采集、多维分析到报告生成全流程闭环，融合 RAG 文档智能、量化分析工具链与 LLM Wiki 知识库。**

[功能一览](#-功能一览) • [多智能体协作](#-多智能体协作) • [量化工具链](#-量化分析工具链) • [LLM Wiki](#-llm-wiki-知识库) • [快速开始](#-快速开始)

</div>

---

> ✅ **零成本即可运行**：YFinance 免费行情 + Ollama 本地大模型，无需任何付费 API Key
> 🔑 也可配置 FMP / Alpha Vantage / FRED / Groq 等 Key，自动升级为更强的数据与推理能力

---

## ✨ 功能一览

| 能力 | 说明 |
| --- | --- |
| 🤖 多智能体分析 | 编排器调度 11 个专项 Agent，自动完成「数据采集 → 多维分析 → 交叉验证 → 报告生成」全流程 |
| 📊 实时多维分析 | 技术面（RSI/MACD/布林带）、基本面（估值/财报）、情绪面（新闻/社交）、风险面（VaR/回撤）四维交叉验证 |
| 🧠 RAG 文档智能 | SEC 财报（10-K/10-Q/8-K）与业绩电话会纪要自动摄取，语义分块 + 向量检索 + 交叉编码器重排 |
| 📐 量化工具链 | DCF 估值、蒙特卡洛模拟、组合优化、因子分解、事件驱动回测、遗传算法策略调优 |
| 📚 LLM Wiki | LLM 生成个股研究页与概念解释页，全库语义检索，投顾对话一键沉淀为分析报告 |
| 📈 ML 价格预测 | GradientBoosting 多周期预测（30/60/90 天）+ 置信区间，Z-score 异常与市场状态检测 |
| 📰 情绪引擎 | FinBERT 金融域情感分析 + VADER 金融词典增强，Reddit 社区情绪与新闻量价联动 |
| 🔔 实时告警 | 价格/成交量/RSI/52 周等 9 类告警，WebSocket 实时推送；定时报告邮件送达 |
| 📑 报告生成 | PDF / Excel / Markdown 多格式投研报告，含执行摘要与多 Agent 结论聚合 |
| 🌓 明暗主题 | Bloomberg 暗色 / 亮色双主题，18 页交互式看板，移动端自适应 |

## 🤖 多智能体协作

```
用户输入（股票代码 / 组合 / 主题）
        │
        ▼
🧠 编排器 Orchestrator —— 任务分解 · Agent 调度 · 冲突检测 · 置信度聚合
        │
        ├── 📡 数据采集 Agent    YFinance / FMP / Alpha Vantage 多源自动降级
        │
        │      asyncio 并行分析 ▼
        ├── 📈 技术面分析师      RSI / MACD / 形态识别 + ML 价格预测
        ├── 📋 基本面分析师      估值 / 财报质量 + SEC 文件 RAG 检索
        ├── 📰 情绪面分析师      FinBERT/VADER + 电话会语气分析
        ├── ⚠️ 风险分析师        VaR/CVaR · 蒙特卡洛 · 回撤分析
        ├── 🎯 主题投资分析师    AI / 新能源 / EV 等主题动量与健康度评分
        ├── 🚀 颠覆分析师        研发强度 / 增长加速度 → 颠覆者 vs 被颠覆者
        ├── 📅 财报分析师        EPS 超预期模式 · 财报质量评分
        │
        └── 📑 报告生成 Agent    多 Agent 结论聚合 → PDF / Excel 投研报告
```

| # | Agent | 核心能力 |
|---|-------|---------|
| 1 | 数据采集 | 多 Provider 采集 + 自动降级 + 数据质量校验与异常值检测 |
| 2 | 技术面分析 | RSI / MACD / 布林带 / 支撑阻力 + GradientBoosting 价格预测 |
| 3 | 基本面分析 | P/E · EPS · ROE · DCF 三情景估值 + 同业对标 + 宏观语境（FRED） |
| 4 | 情绪面分析 | 新闻 + Reddit 社交情绪 + 分析师评级 + 电话会语气 |
| 5 | 风险分析 | VaR/CVaR（1 万条路径蒙特卡洛）· Beta · 最大回撤 · 利率环境 |
| 6 | 主题投资 | 主题-标的映射、动量评分（0-100）、主题健康度、行业内重叠度 |
| 7 | 颠覆分析 | 研发强度（35%）+ 营收增长（40%）+ 毛利趋势（25%）→ 颠覆评分 |
| 8 | 财报分析 | EPS 实际 vs 预期、Beat/Miss 模式识别、财报质量评分（1-10） |
| 9 | 分红分析 | 股息率与安全性评分、派息可持续性、股息王/股息贵族识别 |
| 10 | 期权分析 | Put/Call 比、隐含波动率偏斜、Max Pain、异常成交识别 |
| 11 | 报告生成 | PDF/Excel 导出、执行摘要、跨 Agent 洞察聚合与矛盾检测 |

## 🧠 RAG 文档智能

```
SEC EDGAR（10-K / 10-Q / 8-K）+ 业绩电话会纪要
        │
        ├── 语义分块 → Sentence Transformers 向量化 → ChromaDB 持久化
        │
        查询：相似检索 + 交叉编码器重排（cross-encoder re-ranking）
        │
        ▼
注入 Agent 上下文 —— 让每个分析结论「有据可查」
```

- 分析 Agent 可选挂载 RAG Mixin，回答基本面问题时自动引用财报原文
- 与 LLM Wiki 共用向量化基础设施，页面内容全部可语义检索

## 📐 量化分析工具链

| 模块 | 能力 |
| --- | --- |
| DCF 估值 | WACC/CAPM 建模、三情景（乐观/中性/悲观）、5×5 敏感性矩阵、安全边际 |
| 蒙特卡洛 | 1 万条 GBM 路径模拟 → VaR / CVaR、目标价概率、组合风险 |
| 组合优化 | Markowitz 均值方差、有效前沿、风险平价配置 |
| 因子模型 | Fama-French 风格分解（市场/规模/价值/动量/质量） |
| 业绩归因 | Brinson-Fachler 归因（配置/选股/交互效应）、Alpha/Beta/跟踪误差 |
| 回测引擎 | 9 种内置策略 + Walk-Forward 滚动验证 + 遗传算法参数调优（防过拟合） |
| 税务优化 | Tax-Loss Harvesting 识别 + Wash Sale 预警 |

## 📚 LLM Wiki 知识库

- **📈 个股研究页** —— LLM 实时拉取行情、公司画像、财务报表、技术指标与已摄取的 SEC 文件，自动撰写结构化研究页（中/英文）
- **💡 概念解释页** —— 定义、公式、数值算例、常见误区，并自动交叉关联相关页面
- **🧾 对话一键成文** —— 投顾对话结束后一键转化为正式分析文档（客户背景/关键数据/结论/风险）
- **🔍 语义检索** —— 每页分块嵌入独立 ChromaDB 集合（`wiki_pages`），按含义而非关键词检索
- **✏️ 完全可编辑** —— 生成页面落在常规 Markdown 编辑器中，支持手工增删改

```python
from src.wiki import WikiStore, WikiGenerator

# 生成有实盘数据支撑的个股研究页
draft = WikiGenerator().generate_stock_page("AAPL", language="zh")
page = WikiStore().create_page(source="llm", **{k: v for k, v in draft.items() if k != "meta"})

# 全库语义检索
WikiStore().semantic_search("风险调整后收益指标", top_k=5)
```

## 🏗️ 技术栈

| 层 | 技术 |
| --- | --- |
| Agent 框架 | LangChain · LangGraph（ReAct 多步推理 + 置信度评分） |
| 大模型 | Ollama（Llama / Mistral 本地推理）/ Groq / LM Studio / 任意 OpenAI 兼容网关 |
| RAG | ChromaDB · Sentence Transformers · 交叉编码器重排 |
| 数据源 | YFinance · FMP · Alpha Vantage · FRED · Reddit（多源自动降级） |
| 量化/ML | Pandas · NumPy · SciPy · scikit-learn（GradientBoosting） |
| 后端 | FastAPI + WebSocket · SQLAlchemy ORM（PostgreSQL / SQLite）· Redis 缓存 |
| 前端 | Streamlit 18 页交互看板 · Plotly · TradingView Lightweight Charts |
| 报告 | reportlab（PDF）· openpyxl（Excel） |
| 安全 | API Key 鉴权 · 速率限制 · 输入净化（SQL/XSS/注入） |

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/pkc-zyy/financial-research-analyst-agent.git
cd financial-research-analyst-agent

# 2. 创建虚拟环境（Python 3.12+）
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量（可选：不配置也能用 YFinance + 本地模型运行）
copy .env.example .env           # 按需填入 OLLAMA_BASE_URL / FMP_API_KEY 等

# 5. 启动
python -m src.main               # REST API + WebSocket（http://localhost:8000/docs）
streamlit run frontend/app.py    # 18 页交互看板
```

命令行方式：

```bash
python -m src.cli analyze AAPL                        # 单只股票快速分析
python -m src.cli portfolio AAPL GOOGL MSFT --output report.pdf   # 组合分析出报告
```

## 📊 Streamlit 看板（18 页）

行情总览 · 个股分析 · 主题投资 · 同业对比 · 颠覆分析 · 季度财报 · 组合分析 · 报告中心 · 财经新闻 · 历史绩效 · AI 情绪 · ETF 筛选 · 宏观经济 · 空头持仓 · 分红分析 · 分析师共识 · 实时告警 · **LLM Wiki**

## 🔌 REST API 速览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/analyze` | 综合分析一只股票（技术+基本面+情绪+风险） |
| GET | `/api/v1/technical/{symbol}` | 技术面分析 |
| GET | `/api/v1/sentiment/{symbol}` | 情绪面分析 |
| POST | `/api/v1/portfolio` | 组合分析 |
| GET | `/api/v1/themes` | 主题投资列表 |
| GET | `/api/v1/peers/{symbol}` | 同业自动发现与对比 |
| POST | `/api/v1/backtest` | 策略回测 |
| GET | `/api/v1/performance/{symbol}` | 多周期绩效与基准对比 |
| GET | `/api/v1/wiki` | Wiki 页面列表（按分类/代码/标签过滤） |
| POST | `/api/v1/wiki/generate` | LLM 生成个股研究页 / 概念页 |
| POST | `/api/v1/wiki/search` | Wiki 语义检索 |
| POST | `/api/v1/wiki/generate-report` | 投顾对话一键转分析文档 |
| WebSocket | `/ws/alerts` | 实时告警推送 |

交互式文档：`http://localhost:8000/docs`（Swagger UI）· `/redoc`

## 📁 项目结构

```
financial-research-analyst-agent/
├── src/
│   ├── agents/          # 编排器 + 11 个专项 Agent（ReAct 推理 · RAG Mixin）
│   ├── tools/           # 30+ 分析工具（技术指标/估值/回测/情绪/组合优化…）
│   ├── rag/             # SEC 文件摄取 · 嵌入流水线 · 重排检索
│   ├── wiki/            # LLM Wiki 生成器 + 存储（向量索引同步）
│   ├── data/            # 多 Provider 数据层 + 质量校验
│   ├── api/             # REST 路由 · WebSocket 告警 · 鉴权与限流
│   ├── models/          # Pydantic 模型 · SQLAlchemy 持久化
│   └── cli.py           # 命令行入口
├── frontend/            # Streamlit 18 页看板（明暗主题 · 移动端自适应）
├── tests/               # 14 个测试套件（pytest）
├── config/              # agents.yaml · themes.yaml
├── docs/                # 架构设计 · 实施路线 · 差距分析
└── requirements.txt
```

## 🧪 测试

```bash
pytest tests/ -v                # 全量测试
pytest tests/test_wiki.py -v    # LLM Wiki 测试
pytest tests/ --cov=src         # 覆盖率报告
```

## 📄 许可

MIT — 仅供学习研究，不构成任何投资建议。

---

<div align="center">

**Author: Kecheng Peng (彭可程) · [@pkc-zyy](https://github.com/pkc-zyy)**

_AI Multi-Agent Systems · Wenzhou University of Technology · Artificial Intelligence_

[⬆ Back to Top](#-金融理财顾问系统--financial-research-analyst-agent)

</div>
