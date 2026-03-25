import pandas as pd
import os


def load_comments_from_csv(file_path: str) -> str:
    """加载 CSV 评论数据并转换为文本字符串"""
    if not os.path.exists(file_path):
        return "未找到数据文件，使用默认模拟数据。"

    df = pd.read_csv(file_path)
    # 假设 CSV 有 'content' 列
    comments = df['content'].tolist() if 'content' in df.columns else df.iloc[:, 0].tolist()
    return "\n".join(comments)


def save_report(content: str, filename: str = "report.md"):
    """保存报告到 output 目录"""
    os.makedirs("output", exist_ok=True)
    path = os.path.join("output", filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path