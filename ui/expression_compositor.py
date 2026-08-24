from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QRect
from PyQt5.QtGui import QImage, QPainter


class ExpressionCompositor:
    """从角色图集的下方网格取表情，并覆盖到上方身体底图。"""

    BASE_HEIGHT = 768
    GRID_COLUMNS = 4
    GRID_ROWS = 4
    EXPRESSION_ORIGIN_Y = 768
    HEAD_DEST_X = 416
    HEAD_DEST_Y = 156
    EMOTIONS = {
        "neutral": (1, 1), "happy": (0, 0), "开心": (0, 0), "smile": (0, 0),
        "surprised": (1, 0), "惊讶": (1, 0), "sad": (3, 0), "难过": (3, 0),
        "angry": (2, 3), "生气": (2, 3), "blush": (2, 0), "脸红": (2, 0),
        "confused": (3, 1), "困惑": (3, 1), "evil": (2, 2), "恶作剧": (2, 2),
        "cry": (1, 3), "哭": (1, 3), "excited": (3, 2), "兴奋": (3, 2),
        "shy": (1, 2), "害羞": (1, 2), "tired": (0, 2), "疲惫": (0, 2),
    }

    def __init__(self, image_path: str):
        self.image_path = Path(image_path)
        self.atlas = QImage(str(self.image_path)).convertToFormat(QImage.Format_ARGB32)

    def compose(self, emotion: str = "neutral") -> QImage:
        base = self.atlas.copy(0, 0, self.atlas.width(), self.BASE_HEIGHT)
        cell_width = self.atlas.width() / self.GRID_COLUMNS
        cell_height = (self.atlas.height() - self.EXPRESSION_ORIGIN_Y) / self.GRID_ROWS
        column, row = self.EMOTIONS.get((emotion or "neutral").strip().lower(), (0, 0))
        source = QRect(
            round(column * cell_width),
            round(self.EXPRESSION_ORIGIN_Y + row * cell_height),
            round((column + 1) * cell_width) - round(column * cell_width),
            round(self.EXPRESSION_ORIGIN_Y + (row + 1) * cell_height)
            - round(self.EXPRESSION_ORIGIN_Y + row * cell_height),
        )
        expression = self.atlas.copy(source)
        painter = QPainter(base)
        painter.drawImage(self.HEAD_DEST_X, self.HEAD_DEST_Y, expression)
        painter.end()
        return base
