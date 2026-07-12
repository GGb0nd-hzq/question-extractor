"""
图片提取模块 — 为每道题裁切其在页面中的完整截图（A3自动分左右栏）
"""

import cv2
import numpy as np
from typing import List
from pathlib import Path


class ImageExtractor:
    """按题目在页面中的位置裁切截图，A3 试卷自动分左右两栏"""

    def __init__(self, padding: int = 15):
        self.padding = padding

    def crop_all_questions(self, page_image: np.ndarray,
                            n_questions: int) -> List[np.ndarray]:
        """
        为每道题裁切截图。A3 宽页面先左右分栏，再在每栏内均分。

        Args:
            page_image: 页面图片 (BGR)
            n_questions: 该页题目数量

        Returns:
            [crop_image, ...] 按题目顺序排列
        """
        h, w = page_image.shape[:2]
        if n_questions <= 0:
            return []

        # A3 宽页面 → 先左右分栏
        is_a3 = w > h * 1.3
        if is_a3:
            mid = w // 2
            # 按高度比例分配题目到左右栏
            n_left = max(1, round(n_questions * 0.55))  # 左栏略多（通常从左上开始）
            n_left = min(n_left, n_questions - 1)
            n_right = n_questions - n_left

            left_crops = self._crop_column(page_image[:, :mid, :], n_left)
            right_crops = self._crop_column(page_image[:, mid:, :], n_right)

            # 交错排列：左1, 右1, 左2, 右2... 还是 左全, 右全？
            # 中文试卷阅读顺序：左栏从上到下 → 右栏从上到下
            return left_crops + right_crops
        else:
            return self._crop_column(page_image, n_questions)

    def _crop_column(self, col_image: np.ndarray, n: int) -> List[np.ndarray]:
        """在一栏内均分为 n 个区域"""
        h, w = col_image.shape[:2]
        if n <= 0:
            return []

        crops = []
        for i in range(n):
            y1 = int(h * i / n)
            y2 = int(h * (i + 1) / n)

            # 上下各扩展一点，防截断
            y1 = max(0, y1 - self.padding)
            y2 = min(h, y2 + self.padding)

            crop = col_image[y1:y2, :, :].copy()
            crop = self._trim_whitespace(crop)
            crops.append(crop)

        return crops

    def _trim_whitespace(self, crop: np.ndarray) -> np.ndarray:
        """裁掉上下边缘的大片空白"""
        if crop.size == 0:
            return crop

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)

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
