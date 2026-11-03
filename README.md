# Game-Ops-Agent

把玩家评论与客服反馈转成**带证据、可执行**的游戏经营分析报告。项目面向长文本场景：先用确定性统计锁定问题分布，再让长上下文大模型做归因与策略推演，并可选联网补充竞品情报。

> 默认对接 Moonshot（Kimi）OpenAI 兼容接口，模型名与网关均可配置。没有 API Key 时也能运行——输出本地规则基线报告，便于演示与联调。

## 核心特性

- **证据优先**：负面率、评分分布、主题提及、代表评论全部由本地代码计算，LLM 只负责解释与推演，避免“拍脑袋”数字。
- **长上下文分析**：`--full-context` 可按字符预算附带评论原文，配合 128K/200K 级上下文模型处理海量文本。
- **可选联网检索**：自动生成竞品与行业查询，检索结果以 `[S1]` 形式进入报告；搜索失败不会中断主流程。
- **无 Key 可用**：离线模式输出结构完整、标注不确定性来源的规则基线报告。
- **自动降级**：LLM 鉴权失败、限流、模型名错误时自动回退到离线报告，并保留失败原因。
- **可审计**：LLM 报告自动附带统计证据、代表性评论与检索来源附录。
- **脏数据入口**：兼容 CR/CRLF 换行、UTF-8/GB18030 编码、不同列名、重复评论与超量样本。

## 工作原理

```text
CSV / TXT
   │
   ▼
数据清洗（编码回退、列名探测、去重、截断）
   │
   ▼
本地统计（负面率 / 评分分布 / 主题提及 / 代表评论）
   │
   ├──► 可选联网检索（竞品 / 行业情报，失败可忽略）
   │
   ▼
证据注入 Prompt ──► OpenAI 兼容 LLM ──► 分析报告 + 证据附录
   │
   └──► 无 Key / 调用失败 ──► 本地规则基线报告
```

## 快速开始

要求 Python 3.10+。

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

零配置先跑离线报告（不需要 API Key）：

```bash
python -m src --offline --no-search
```

接入大模型与联网检索：

```bash
cp .env.example .env        # Windows: copy .env.example .env
# 编辑 .env，填入 MOONSHOT_API_KEY

python -m src --input data/sample_comments.csv --game 冒险大作战 --level 5
```

报告默认写入 `output/analysis_report.md`，可参考已生成的示例 [output/analysis_report.md](output/analysis_report.md)。

## 常用命令

```bash
# 离线规则基线（无 Key 时也会自动使用）
python -m src --offline --no-search

# LLM 深度分析，关闭联网检索
python -m src --no-search --level 5

# 长上下文模式，额外附带评论原文（默认只传统计证据）
python -m src --full-context

# 指定竞品与输出位置
python -m src --game 冒险大作战 --level 5 \
  --competitor 天天冒险 --competitor XX传说 \
  --output output/adventure_report.md

# 严格模式：LLM 不可用时直接失败，不降级
python -m src --strict-llm
```

| 参数 | 说明 |
| :--- | :--- |
| `-i, --input` | 评论文件，支持 `.csv/.txt/.md/.log`，默认 `data/sample_comments.csv` |
| `--game` | 游戏名称 |
| `--level` | 问题关卡或模块，如 `5`、`第5关`、`新手引导` |
| `-o, --output` | 报告输出路径 |
| `--competitor` | 竞品名称，可重复传入 |
| `--offline` | 不调用大模型，仅输出规则基线报告 |
| `--no-search` | 关闭联网检索 |
| `--full-context` | LLM 模式下附带评论原文（受 `MAX_CONTEXT_CHARS` 限制） |
| `--strict-llm` | LLM 不可用时直接失败，不降级 |
| `--model` | 覆盖 `LLM_MODEL` |
| `--max-comments` | 覆盖 `MAX_COMMENTS` |
| `-v, --verbose` | 输出调试日志 |
| `--version` | 显示版本 |

## 输入数据

CSV 第一行是表头。推荐字段：

```csv
user_id,comment_content,date,rating
1001,"第5关太难了，小怪血量比BOSS还厚",2026-03-20,1
1002,"新手引导没讲清楚连携技能怎么用",2026-03-21,2
```

- 文本列：优先识别 `comment_content/content/comment/text/message/内容/评论`，找不到时自动选择平均内容最长的字符串列。
- 评分列：`rating/score/star/stars/评分`，解析为 1-5 星；缺失时改用负面词判断。
- 日期列：`date/time/created_at/created/日期`，支持 ISO 日期、`2026/03/20`、`2026年03月20日` 等格式。
- 用户列：`user_id/uid/user/player_id/用户`，仅用于回显代表评论。
- TXT/MD：每个非空行视为一条评论，`#` 开头视为注释。
- 完全重复的评论会自动去重；超过 `MAX_COMMENTS` 会截断并记录警告。

## 配置

所有配置均可通过 `.env` 或环境变量提供，参考 [.env.example](.env.example)。

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `MOONSHOT_API_KEY` | 空 | Moonshot API Key；为空时进入离线模式 |
| `OPENAI_API_KEY` | 空 | 通用 OpenAI 兼容网关的 Key，优先级低于 `MOONSHOT_API_KEY` |
| `LLM_BASE_URL` | `https://api.moonshot.cn/v1` | OpenAI 兼容接口地址 |
| `LLM_MODEL` | `kimi-k2.5` | 模型名，按所用网关的实际名称填写 |
| `LLM_TEMPERATURE` | `0.3` | 分析场景使用较低温度 |
| `LLM_MAX_TOKENS` | `4096` | 单次报告长度上限 |
| `LLM_TIMEOUT` | `120` | 请求超时（秒） |
| `MAX_COMMENTS` | `20000` | 最多加载的评论数 |
| `MAX_CONTEXT_CHARS` | `120000` | `--full-context` 的原文预算 |

## 输出结构

报告固定包含五个章节：

1. **现状摘要**：样本规模、负面信号、风险等级、主要问题。
2. **核心归因**：按主题提及占比展开，区分事实与推断。
3. **竞品对标**：仅使用检索结果；无检索时明确说明情报缺口。
4. **行动建议**：优先级、动作、依据、成本、验证指标。
5. **风险与不确定性**：样本偏差、数据缺口、待验证假设。

LLM 模式会在正文后自动附加“证据与来源”附录；离线模式则在正文内直接给出统计证据和代表评论。两种模式都会明确标注自己的分析口径，避免把规则匹配说成语义理解。

## 项目结构

```text
.
├── data/
│   └── sample_comments.csv     # 50 条示例评论（CR 换行）
├── output/
│   └── analysis_report.md      # 生成的示例报告
├── src/
│   ├── __main__.py             # python -m src 入口
│   ├── cli.py                  # 参数解析与流程输出
│   ├── config.py               # 环境变量与 .env
│   ├── data_loader.py          # CSV/TXT 加载、编码与列名适配
│   ├── analytics.py            # 确定性统计与主题归因
│   ├── search.py               # DuckDuckGo 检索（可选）
│   ├── prompts.py              # 系统提示与任务模板
│   ├── llm.py                  # OpenAI 兼容调用封装
│   ├── report.py               # 离线报告、证据附录
│   ├── agent.py                # 分析编排与降级策略
│   └── utils.py                # 文本与文件工具
├── tests/                      # unittest 测试
├── requirements.txt
├── .env.example
└── README.md
```

## 测试

```bash
python -m unittest discover -s tests -v
```

测试覆盖：CR-only 换行 CSV、列名回退、GB18030 编码、去重与截断、评分/负面词两种口径、风险分级、报告章节、检索结果过滤（非 HTTP 链接与重复 URL）、LLM 封装、Agent 离线/LLM 编排/失败降级、CLI 端到端流程。离线测试不需要 API Key，也不会访问网络。

## 设计取舍与局限

- **不使用 LangChain**：Agent 流程只有“统计 → 检索 → 单次生成”三步，直接用 OpenAI 兼容接口可以减少框架版本漂移带来的运行风险；核心离线路径只依赖标准库。
- **主题归因是词典匹配**：`src/analytics.py` 中的主题词表针对关卡、数值、引导、客服、竞品等游戏运营场景设计，换品类时需要扩展。它适合发现信号和做基线，不替代人工复盘。
- **规则基线不证明因果**：离线报告只陈述相关性与玩家感知；策略上线前应做灰度或 A/B 验证。
- **联网检索结果需核验**：DuckDuckGo 可能限流或返回过时内容，报告中的外部信息必须人工核对。
- **LLM 输出需审阅**：提示词已禁止编造留存、收入等指标，并要求标注“推断（待验证）”，但仍建议发布前人工抽检。
- **样本偏差**：评论与工单来自主动发声用户，负面占比不代表全量玩家；如需更可靠结论，应结合关卡通过率、留存与付费数据。

## 数据与隐私

评论数据可能包含用户标识。`.env` 已加入 `.gitignore`；如果评论或生成报告包含真实用户信息，请自行脱敏，并避免提交到公开仓库。
