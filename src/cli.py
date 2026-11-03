"""命令行入口。"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

from . import __version__
from .agent import MODE_LABELS, GameOpsAgent
from .config import PROJECT_ROOT, Settings
from .data_loader import load_dataset
from .llm import LLMError
from .utils import save_report

DEFAULT_INPUT = PROJECT_ROOT / "data" / "sample_comments.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "analysis_report.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="game-ops-agent",
        description="基于长文本证据与可选联网检索的游戏经营分析智能体",
    )
    parser.add_argument(
        "-i",
        "--input",
        default=str(DEFAULT_INPUT),
        help=f"评论数据文件（.csv/.txt/.md/.log），默认 {DEFAULT_INPUT}",
    )
    parser.add_argument("--game", default="冒险大作战", help="游戏名称")
    parser.add_argument(
        "--level",
        default="5",
        help="问题关卡或模块，如 5、第5关、新手引导",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"报告输出路径，默认 {DEFAULT_OUTPUT}",
    )
    parser.add_argument("--competitor", action="append", default=[], help="竞品名称，可重复传入")
    parser.add_argument("--offline", action="store_true", help="不调用大模型，仅输出规则基线报告")
    parser.add_argument("--no-search", action="store_true", help="关闭联网检索")
    parser.add_argument(
        "--full-context",
        action="store_true",
        help="LLM 模式下附带评论原文（受 MAX_CONTEXT_CHARS 限制），默认只传统计证据",
    )
    parser.add_argument("--strict-llm", action="store_true", help="LLM 不可用时直接失败，不降级")
    parser.add_argument("--model", help="覆盖 LLM_MODEL")
    parser.add_argument("--max-comments", type=int, help="覆盖 MAX_COMMENTS")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    args = build_parser().parse_args(argv)
    _setup_logging(args.verbose)
    logger = logging.getLogger("game_ops_agent")

    settings = Settings.from_env()
    overrides = {}
    if args.model:
        overrides["model"] = args.model
    if args.max_comments is not None:
        overrides["max_comments"] = args.max_comments
    if overrides:
        settings = replace(settings, **overrides)

    try:
        dataset = load_dataset(Path(args.input), max_comments=settings.max_comments)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 2

    for warning in dataset.warnings:
        logger.warning(warning)

    agent = GameOpsAgent(settings, logger)
    try:
        result = agent.run(
            dataset=dataset,
            game=args.game,
            level=args.level,
            competitors=args.competitor,
            offline=args.offline,
            use_search=not args.no_search,
            full_context=args.full_context,
            strict_llm=args.strict_llm,
        )
    except LLMError as exc:
        logger.error("%s", exc)
        return 3

    try:
        output = save_report(result.report, Path(args.output))
    except OSError as exc:
        logger.error("报告保存失败：%s", exc)
        return 4
    print(f"分析模式：{MODE_LABELS.get(result.mode, result.mode)}")
    print(
        f"样本量：{len(dataset)} 条 | 负面占比：{result.profile.negative_share:.0%} "
        f"| 风险等级：{result.profile.risk_level}"
    )
    if result.search is not None:
        print(f"联网检索：{len(result.search.results)} 条结果")
    print(f"报告已保存：{output}")
    return 0


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stderr,
    )
    if not verbose:
        for noisy in ("httpx", "httpcore", "openai", "primp"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
