"""
图片提取模块 — 按题目在页面中的大致位置裁切，留足边距确保题号完整
"""

import cv2
import numpy as np
from typing import List
from pathlib import Path


class ImageExtractor:
    """裁切每道题的页面截图"""

    def __init__(self, padding: int = 15):
        self.padding = padding

    def crop_by_count(self, page_image: np.ndarray,
                       n_questions: int) -> List[np.ndarray]:
        """
        A3 页面：先左右分栏，再在每栏内均分。留足重叠防止截断。

        Args:
            page_image: 页面图片
            n_questions: 本页题目数

        Returns:
            [crop, ...] 每题一张
        """
        h, w = page_image.shape[:2]
        if n_questions <= 0:
            return []

        # A3 宽页面分左右栏
        if w > h * 1.3:
            mid = w // 2
            n_left = max(1, round(n_questions * 0.55))
            n_left = min(n_left, n_questions - 1)
            n_right = n_questions - n_left

            left = self._crop_column(page_image[:, :mid, :], n_left)
            right = self._crop_column(page_image[:, mid:, :], n_right)
            return left + right
        else:
            return self._crop_column(page_image, n_questions)

    def _crop_column(self, col_image: np.ndarray, n: int) -> List[np.ndarray]:
        """在一栏内裁 n 张截图，相邻截图间有 30% 重叠防截断"""
        h, w = col_image.shape[:2]
        if n <= 0:
            return []

        # 每道题占区域 = 页面高度 / n，额外扩展 40% 防截断
        crop_h = int(h / n * 1.4)

        crops = []
        for i in range(n):
            center_y = int(h * (i + 0.5) / n)
            y1 = max(0, center_y - crop_h // 2)
            y2 = min(h, y1 + crop_h)

            # 第一题向上多留空间
            if i == 0:
                y1 = 0
            # 最后一题向下到页面底部
            if i == n - 1:
                y2 = h

            crop = col_image[y1:y2, :, :].copy()
            crop = self._trim_whitespace(crop)
            crops.append(crop)

        return crops

    def _trim_whitespace(self, crop: np.ndarray) -> np.ndarray:
        """裁掉上下边缘大片空白（但至少保留5px边距）"""
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
        if y2 - y1 < 30:
            return crop  # 太小就别裁了
        return crop[y1:y2+1, :, :]

    def save(self, crops: List[np.ndarray], output_dir: str,
             page_num: int) -> List[str]:
        save_dir = Path(output_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for i, crop in enumerate(crops):
            filename = f"p{page_num:02d}_q{i+1:02d}.png"
            filepath = save_dir / filename
            cv2.imwrite(str(filepath), crop)
            paths.append(str(Path(output_dir) / filename))
        return paths
