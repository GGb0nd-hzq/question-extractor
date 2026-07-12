"""
图片提取模块 — 为每道题裁切其在页面中的完整区域截图
"""

import cv2
import numpy as np
from typing import List
from pathlib import Path


class ImageExtractor:
    """按题目在页面中的位置，裁切每道题的完整截图"""

    def __init__(self, padding: int = 20):
        self.padding = padding

    def crop_all_questions(self, page_image: np.ndarray,
                            n_questions: int) -> List[np.ndarray]:
        """
        将页面均分为 n 个区域，每道题一个截图

        Args:
            page_image: 页面图片 (BGR)
            n_questions: 该页题目数量

        Returns:
            [crop_image, ...] 按题目顺序排列
        """
        h, w = page_image.shape[:2]
        if n_questions <= 0:
            return []

        crops = []
        for i in range(n_questions):
            # 每道题占页面的 1/n，相邻题之间重叠 15% 防止截断
            overlap = 0.15
            zone_h = int(h / n_questions * (1 + overlap))
            center_y = int(h * (i + 0.5) / n_questions)
            y1 = max(0, center_y - zone_h // 2)
            y2 = min(h, y1 + zone_h)

            crop = page_image[y1:y2, :, :].copy()
            crop = self._trim_whitespace(crop)
            crops.append(crop)

        return crops

    def _trim_whitespace(self, crop: np.ndarray) -> np.ndarray:
        """裁掉图片上下边缘的大片空白"""
        if crop.size == 0:
            return crop

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)

        # 找上下边界
        rows = np.any(binary > 0, axis=1)
        if not rows.any():
            return crop

        y1, y2 = np.where(rows)[0][[0, -1]]
        y1 = max(0, y1 - self.padding)
        y2 = min(crop.shape[0], y2 + self.padding)

        return crop[y1:y2+1, :, :]

    def save(self, crops: List[np.ndarray], output_dir: str,
             page_num: int) -> List[str]:
        """保存裁切图片"""
        save_dir = Path(output_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        paths = []
        for i, crop in enumerate(crops):
            filename = f"p{page_num:02d}_q{i+1:02d}.png"
            filepath = save_dir / filename
            cv2.imwrite(str(filepath), crop)
            paths.append(str(Path(output_dir) / filename))

        return paths
