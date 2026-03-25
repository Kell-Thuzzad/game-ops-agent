import os
from dotenv import load_dotenv
from langchain_community.chat_models import MoonshotChat  # 假设使用社区集成，或用 ChatOpenAI 兼容模式
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools import DuckDuckGoSearchRun  # 使用免费的搜索工具
from langchain.agents import initialize_agent, AgentType, Tool
from .prompts import SYSTEM_PROMPT, ANALYSIS_TASK_PROMPT

load_dotenv()


class GameOpsAgent:
    def __init__(self, api_key: str):
        # 初始化大模型 (使用 Kimi moonshot-v1-128k 或更高版本)
        self.llm = MoonshotChat(
            model="moonshot-v1-128k",
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1"
        )

        # 初始化工具：联网搜索
        self.search_tool = DuckDuckGoSearchRun()

        # 定义工具列表
        tools = [
            Tool(
                name="Web Search",
                func=self.search_tool.run,
                description="用于搜索最新的游戏行业资讯、竞品动态和社交媒体热点。"
            )
        ]

        # 初始化 Agent
        self.agent_executor = initialize_agent(
            tools,
            self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True
        )

    def analyze(self, game_name: str, level: int, context_text: str):
        """
        执行分析任务
        :param game_name: 游戏名称
        :param level: 问题关卡/模块
        :param context_text: 输入的长文本（评论+工单）
        """
        # 构建完整的提示词
        # 注意：对于超长文本，直接传入 context，利用 Kimi 的长窗口特性
        full_prompt = f"""
        {SYSTEM_PROMPT}

        {ANALYSIS_TASK_PROMPT.format(
            game_name=game_name,
            level=level,
            comment_count=len(context_text.split('\n'))
        )}

        --- 参考数据开始 ---
        {context_text}
        --- 参考数据结束 ---

        请根据上述数据和你的搜索能力，生成一份完整的经营分析报告。
        """

        try:
            # 执行 Agent 推理
            response = self.agent_executor.invoke({"input": full_prompt})
            return response['output']
        except Exception as e:
            return f"分析过程中出现错误：{str(e)}"


# 使用示例
if __name__ == "__main__":
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中配置 MOONSHOT_API_KEY")

    agent = GameOpsAgent(api_key)

    # 模拟输入数据 (实际使用时可读取 CSV)
    mock_comments = """
    玩家A: 第5关太难了，根本过不去，劝退！
    玩家B: 新手引导没讲清楚技能怎么用，卡在这里半小时了。
    玩家C: 感觉数值策划疯了，小怪血量比BOSS还厚。
    玩家D: 隔壁《XX传说》昨天更新了送复活币的活动，我们这啥都没有？
    ... (此处省略 496 条模拟数据)
    """

    print("正在启动智能体进行分析...")
    report = agent.analyze(game_name="冒险大作战", level=5, context_text=mock_comments)

    # 保存报告
    with open("../output/analysis_report.md", "w", encoding="utf-8") as f:
        f.write(report)

    print("分析报告已生成至 output/analysis_report.md")