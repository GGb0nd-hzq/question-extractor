#!/usr/bin/env python3
"""
题目提取工具 — 从试卷 PDF 中提取题目，生成结构化 JSON
使用视觉语言模型 API (Qwen-VL / GPT-4o / Claude 等)

用法:
    # 设置 API Key (二选一)
    export API_KEY="sk-xxx"
    export API_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"  # 可选

    # 运行
    python main.py exam.pdf                          # 默认用 qwen-vl-max
    python main.py exam.pdf --model qwen-vl-plus      # 便宜模型
    python main.py exam.pdf -s 物理                    # 指定科目
    python main.py exam.pdf -o output/result.json     # 指定输出

支持的 API 厂商:
    阿里百炼:  API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
    OpenAI:    API_BASE_URL=https://api.openai.com/v1
    智谱:      API_BASE_URL=https://open.bigmodel.cn/api/paas/v4
    任意 OpenAI 兼容接口
"""

import argparse
import sys
import os
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_processor import PDFProcessor
from src.api_extractor import APIExtractor
from src.output_formatter import format_output, save_json, export_bot_db


def load_config(path: str) -> dict:
    p = Path(path)
    return yaml.safe_load(open(p, encoding="utf-8")) if p.exists() else {}


def main():
    parser = argparse.ArgumentParser(
        description="题目提取工具 — 使用 VLM API 从试卷 PDF 提取题目",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  export API_KEY="sk-xxx"
  python main.py exam.pdf
  python main.py exam.pdf -s 物理 --model qwen-vl-plus
  python main.py exam.pdf --api-base https://api.openai.com/v1 --model gpt-4o
        """,
    )
    parser.add_argument("input", help="PDF 文件路径")
    parser.add_argument("-o", "--output", default="output/questions.json", help="输出 JSON 路径")
    parser.add_argument("--bot-db", default=None, help="Bot 数据库输出路径")
    parser.add_argument("-s", "--subject", default="", help="科目名称（如: 化学、物理）")
    parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--dpi", type=int, default=None, help="PDF 渲染 DPI (默认 200)")
    parser.add_argument("--model", default=None, help="模型名称 (如: qwen-vl-max, gpt-4o)")
    parser.add_argument("--api-key", default=None, help="API Key (优先用环境变量 API_KEY)")
    parser.add_argument("--api-base", default=None, help="API Base URL (优先用环境变量 API_BASE_URL)")
    parser.add_argument("--max-tokens", type=int, default=None, help="单次最大输出 token")

    args = parser.parse_args()

    # 检查输入
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 文件不存在 - {args.input}")
        sys.exit(1)

    # 加载配置
    base_dir = Path(__file__).parent
    config = load_config(str(base_dir / args.config))
    api_cfg = config.get("api", {})

    # API Key: 命令行 > 环境变量 > 配置文件
    api_key = args.api_key or os.environ.get("API_KEY") or api_cfg.get("api_key")
    if not api_key:
        print("错误: 请设置 API Key")
        print("  export API_KEY='sk-xxx'")
        print("  或 python main.py exam.pdf --api-key 'sk-xxx'")
        sys.exit(1)

    # API Base URL: 命令行 > 环境变量 > 配置文件
    api_base = (args.api_base or os.environ.get("API_BASE_URL")
                or api_cfg.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"))

    model = args.model or api_cfg.get("model", "qwen-vl-max")
    dpi = args.dpi or config.get("pdf", {}).get("dpi", 200)
    max_tokens = args.max_tokens or api_cfg.get("max_tokens", 8192)

    # ================================================================
    # 步骤1: PDF → 图片
    # ================================================================
    print(f"[1/3] 渲染 PDF (DPI={dpi}): {args.input}")
    pages = PDFProcessor(dpi=dpi).render(str(input_path))
    print(f"  共 {len(pages)} 页")

    # ================================================================
    # 步骤2: VLM API 逐页提取
    # ================================================================
    print(f"[2/3] VLM 提取")
    print(f"  接口: {api_base}")
    print(f"  模型: {model}")

    api = APIExtractor(api_key=api_key, base_url=api_base,
                       model=model, max_tokens=max_tokens)

    all_questions = []
    for page_data in pages:
        page_num = page_data["page"]
        print(f"  第 {page_num}/{len(pages)} 页...", end=" ", flush=True)
        questions = api.extract(page_data["image"], page_num)
        print(f"→ {len(questions)} 题")
        all_questions.extend(questions)

    if not all_questions:
        print("\n未识别到任何题目，请检查:")
        print("  1. PDF 是否清晰可读")
        print("  2. API Key 是否有效")
        print("  3. 模型是否支持图片输入")
        sys.exit(0)

    # 重新编号
    for i, q in enumerate(all_questions):
        q["id"] = i + 1

    # ================================================================
    # 步骤3: 输出
    # ================================================================
    print(f"\n[3/3] 生成输出...")

    type_cn = {
        "single_choice": "单选", "multiple_choice": "不定向",
        "true_false": "判断", "fill_blank": "填空",
        "essay": "大题", "sub_question": "小题", "unknown": "未知",
    }

    type_stats = {}
    for q in all_questions:
        t = q["type"]; type_stats[t] = type_stats.get(t, 0) + 1

    print(f"  共 {len(all_questions)} 道题")
    for t, c in sorted(type_stats.items()):
        print(f"    {type_cn.get(t, t)}: {c}")

    # 保存 JSON
    data = format_output(all_questions, source_file=args.input, subject=args.subject)
    save_json(data, args.output)
    print(f"  JSON → {args.output}")

    # Bot 数据库
    bot_db_path = args.bot_db or str(Path(args.output).parent / "bot_db.json")
    export_bot_db(all_questions, bot_db_path)
    print(f"  Bot DB → {bot_db_path}")

    # 预览前 5 题
    print(f"\n{'='*50}")
    print("预览:")
    print(f"{'='*50}")
    for q in all_questions[:5]:
        name = type_cn.get(q["type"], q["type"])
        preview = q["content"][:80].replace("\n", " ")
        print(f"  [{name}] Q{q['id']}: {preview}...")
        for opt in q.get("options", [])[:4]:
            if isinstance(opt, str):
                print(f"         {opt[:80]}")
        if q.get("answer"):
            print(f"         答案: {q['answer']}")
        print()


if __name__ == "__main__":
    main()
