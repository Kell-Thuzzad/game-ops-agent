\# 🎮 Game-Ops-Agent: 基于长文本大模型的游戏经营分析智能体



\[!\[License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

\[!\[Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

\[!\[Model: Kimi K2.5](https://img.shields.io/badge/Model-Kimi%20K2.5%20(200K%20Context)-green.svg)](https://platform.moonshot.cn/)



> \*\*项目简介\*\*：这是一个基于 \*\*Kimi K2.5 (200K+ Context)\*\* 和 \*\*LangChain\*\* 构建的自动化游戏经营分析原型系统。它旨在解决传统运营分析中“海量非结构化文本难以处理”和“市场情报获取滞后”的痛点，通过 \*\*自主联网搜索\*\* 与 \*\*长文本深度推理\*\*，自动生成包含归因分析与策略建议的专业研报。



\## 🌟 核心特性



\- \*\*📄 超长上下文无损理解\*\*：利用 Kimi K2.5 的 200K+ 窗口，一次性处理数万条玩家评论与长篇客服记录，无需切片，保留完整语义逻辑。

\- \*\*🌐 原生联网情报搜集\*\*：集成实时搜索工具，自动抓取竞品动态、行业公告及社媒热点，实现内外数据交叉验证。

\- \*\*🧠 思维链（CoT）归因\*\*：模拟资深分析师思维，从情绪宣泄中提炼实质问题，精准定位流失率波动、付费下降等异常的根本原因。

\- \*\*📝 自动化报告生成\*\*：一键输出结构化经营分析报告（现状 - 归因 - 对标 - 建议），支持 Markdown 格式导出。



\## 🛠️ 技术栈



\- \*\*LLM Base\*\*: Moonshot AI (Kimi K2.5) - \*Long Context \& Native Search\*

\- \*\*Framework\*\*: LangChain (Agent Orchestration)

\- \*\*Tools\*\*: DuckDuckGo Search (Web Retrieval), Pandas (Data Processing)

\- \*\*Language\*\*: Python 3.9+



\## 🚀 快速开始



\### 1. 环境准备

确保已安装 Python 3.9 或以上版本。



```bash

\# 克隆项目

git clone https://github.com/your-username/game-ops-agent.git

cd game-ops-agent



\# 安装依赖

pip install -r requirements.txt

