"""
PDF → 图片转换模块
使用 PyMuPDF (fitz) 将扫描版 PDF 的每一页渲染为图片供后续处理
"""

import fitz
import numpy as np
from typing import List


class PDFProcessor:
    """将 PDF 文件逐页渲染为 numpy 图片数组"""

    def __init__(self, dpi: int = 200):
        """
        Args:
            dpi: 渲染分辨率，200dpi 可兼顾速度与清晰度
        """
        self.dpi = dpi

    def render(self, pdf_path: str) -> List[dict]:
        """
        渲染 PDF 所有页面为图片

        Args:
            pdf_path: PDF 文件路径

        Returns:
            [{page, image: np.ndarray(BGR), width, height}, ...]
        """
        pages = []
        doc = fitz.open(pdf_path)

        for page_num in range(doc.page_count):
            page_data = self._render_page(doc, page_num)
            pages.append(page_data)

        doc.close()
        return pages

    def render_page(self, pdf_path: str, page_num: int) -> dict:
        """
        只渲染 PDF 的指定页

        Args:
            pdf_path: PDF 文件路径
            page_num: 页码（从 0 开始）

        Returns:
            {page, image: np.ndarray(BGR), width, height}
        """
        doc = fitz.open(pdf_path)

        if page_num < 0 or page_num >= doc.page_count:
            doc.close()
            raise ValueError(f"页码 {page_num + 1} 超出范围 (共 {doc.page_count} 页)")

        page_data = self._render_page(doc, page_num)
        doc.close()
        return page_data

    def get_page_count(self, pdf_path: str) -> int:
        """获取 PDF 总页数"""
        doc = fitz.open(pdf_path)
        count = doc.page_count
        doc.close()
        return count

    def _render_page(self, doc: fitz.Document, page_num: int) -> dict:
        """渲染单个页面"""
        page = doc[page_num]

        # 计算缩放矩阵以达到目标 DPI（fitz 默认 72dpi）
        zoom = self.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # 转为 numpy 数组
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )

        # 统一为 BGR 格式（OpenCV 默认）
        if img.shape[2] == 4:
            import cv2
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif img.shape[2] == 3:
            # RGB → BGR
            img = img[:, :, ::-1].copy()
        elif img.shape[2] == 1:
            # 灰度图转 BGR
            import cv2
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        return {
            "page": page_num + 1,
            "image": img,
            "width": pix.width,
            "height": pix.height,
        }

# PDF → 图片转换模块结束
