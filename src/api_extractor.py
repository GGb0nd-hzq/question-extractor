"""
Qwen-VL API 题目提取器 (阿里百炼 DashScope)
发送试卷图片给 Qwen-VL，返回结构化 JSON
"""

import json
import base64
import io
import re
from typing import List
import numpy as np
from PIL import Image
from openai import OpenAI


SYSTEM_PROMPT = """你是化学试卷数字化工具。从图片中提取所有题目，返回JSON数组。

每道题格式:
{
  "number_raw": "题号",
  "type": "single_choice|multiple_choice|fill_blank|true_false|essay|sub_question",
  "section": "大题标题",
  "content": "题干原文",
  "options": ["A. xx", "B. xx"],
  "answer": "答案或null",
  "has_image": true/false
}

规则:
1. 照录原文，包括化学式
2. 选择题必须列出全部选项
3. 单选=只有1个正确, 不定向=有1~2个正确
4. 大题的子题(如(1)(2)①)不要单独输出，放到父题的sub_questions数组里
   sub_questions格式: [{"content": "子题内容", "answer": null}]
5. 题目含图片/图表时has_image填true
6. 题目总数严格按题号(1. 2. 3.)计数，子题号不算
7. 跳过以下内容:
   - 试卷标题、"注意事项""答卷前"等考试说明、页眉页脚
8. 只输出JSON数组"""


class APIExtractor:
    """VLM API 提取器 — 支持所有 OpenAI 兼容接口"""

    def __init__(self, api_key: str, base_url: str = "",
                 model: str = "qwen-vl-max", max_tokens: int = 8192):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_tokens = max_tokens

    def extract(self, image: np.ndarray, page_num: int = 1) -> List[dict]:
        """提取一页中的所有题目（A3自动切左右栏）"""
        h, w = image.shape[:2]
        all_questions = []

        # A3宽页面(宽>高*1.3)切左右两半分别提取
        if w > h * 1.3:
            mid = w // 2
            all_questions.extend(self._extract_half(
                image[:, :mid, :], f"第{page_num}页左栏"
            ))
            all_questions.extend(self._extract_half(
                image[:, mid:, :], f"第{page_num}页右栏"
            ))
        else:
            all_questions.extend(self._extract_half(
                image, f"第{page_num}页"
            ))

        return all_questions

    def _extract_half(self, image: np.ndarray, label: str) -> List[dict]:
        """提取半页/A4页的题目"""
        if image.shape[-1] == 3:
            pil = Image.fromarray(image[:, :, ::-1])
        else:
            pil = Image.fromarray(image)

        w, h = pil.size
        if max(w, h) > 2000:
            ratio = 2000 / max(w, h)
            pil = pil.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        resp = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{
                "role": "system", "content": SYSTEM_PROMPT,
            }, {
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": f"提取{label}的所有题目。"},
                ],
            }],
        )

        text = resp.choices[0].message.content
        cost = (
            resp.usage.prompt_tokens * 0.003 / 1000
            + resp.usage.completion_tokens * 0.012 / 1000
        )
        print(f"    tokens: {resp.usage.prompt_tokens}+{resp.usage.completion_tokens} ¥{cost:.4f}")

        return self._parse_json(text)

    def _parse_json(self, text: str) -> List[dict]:
        """解析 JSON 数组"""
        text = re.sub(r'^```(?:json)?\s*\n?', '', text.strip())
        text = re.sub(r'\n?```\s*$', '', text)

        start = text.find('[')
        end = text.rfind(']')
        if start == -1 or end == -1:
            return []

        try:
            questions = json.loads(text[start:end + 1])
            if isinstance(questions, list):
                return [self._normalize(q) for q in questions]
        except json.JSONDecodeError:
            pass

        return []

    def _normalize(self, q: dict) -> dict:
        item = {
            "number_raw": str(q.get("number_raw", "")),
            "type": q.get("type", "unknown"),
            "section": q.get("section"),
            "content": q.get("content", ""),
            "options": q.get("options", []),
            "answer": q.get("answer"),
            "has_image": q.get("has_image", False),
            "images": [],
            "sub_questions": [],
        }
        # 嵌套子题
        subs = q.get("sub_questions", [])
        if subs and isinstance(subs, list):
            item["sub_questions"] = [
                {"content": s.get("content", ""), "answer": s.get("answer")}
                for s in subs if isinstance(s, dict)
            ]
        return item
