"""输出格式化 — JSON + Bot 数据库"""

import json
import re
from typing import List
from pathlib import Path
from datetime import datetime

TYPE_CN = {"single_choice": "单选题", "multiple_choice": "不定向选择题",
           "true_false": "判断题", "fill_blank": "填空题",
           "essay": "大题", "sub_question": "小题", "unknown": "未知"}


def format_output(questions: List[dict], source_file: str = "", subject: str = "") -> dict:
    type_stats = {}
    for q in questions:
        t = q["type"]; type_stats[t] = type_stats.get(t, 0) + 1

    formatted = []
    for q in questions:
        item = {"id": q["id"], "type": q["type"],
                "type_cn": TYPE_CN.get(q["type"], q["type"]),
                "subject": subject, "section": q.get("section"),
                "number_raw": q.get("number_raw", ""),
                "content": q["content"], "options": q.get("options", []),
                "images": q.get("images", []),
                "has_image": q.get("has_image", False),
                "answer": q.get("answer"), "explanation": q.get("explanation")}
        if q.get("sub_questions"):
            item["sub_questions"] = q["sub_questions"]
        formatted.append(item)

    return {"source": {"file": Path(source_file).name if source_file else "",
                       "subject": subject, "parsed_at": datetime.now().isoformat(),
                       "engine": "Claude API"},
            "metadata": {"total": len(questions), "type_stats": type_stats},
            "questions": formatted}


def save_json(data: dict, output_path: str):
    p = Path(output_path); p.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def export_bot_db(questions: List[dict], output_path: str = "output/bot_db.json"):
    entries = []
    for q in questions:
        e = {"id": f"Q{q['id']:04d}", "type": q["type"], "content": q["content"],
             "options": q.get("options", []), "images": q.get("images", []),
             "has_image": q.get("has_image", False),
             "answer": q.get("answer"), "explanation": q.get("explanation"),
             "keywords": _keywords(q["content"])}
        if q.get("sub_questions"):
            e["sub_questions"] = q["sub_questions"]
        entries.append(e)
    save_json({"version": "4.0", "updated_at": datetime.now().isoformat(),
               "total": len(questions), "entries": entries}, output_path)


def _keywords(text: str) -> List[str]:
    cleaned = re.sub(r'[^一-鿿\w↑↓→←⇌]', ' ', text)
    words, seen, result = cleaned.split(), set(), []
    for w in words:
        if len(w) >= 2 and w not in seen:
            seen.add(w); result.append(w)
    return result[:10]
