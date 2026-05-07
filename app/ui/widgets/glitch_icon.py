from __future__ import annotations

import random

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class GlitchXWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._jitter = 0
        self._flash_alpha = 180

        self._timer = QTimer(self)
        self._timer.setInterval(85)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._jitter = random.randint(-3, 3)
        self._flash_alpha = random.randint(140, 250)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, on=True)

        center = QPointF((self.width() / 2) + self._jitter, self.height() / 2)
        radius = min(self.width(), self.height()) * 0.34
        outer_rect = QRectF(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2,
        )

        ring_pen = QPen(QColor(255, 72, 126, self._flash_alpha), 4)
        painter.setPen(ring_pen)
        painter.drawEllipse(outer_rect)

        x_pen = QPen(QColor(255, 128, 162, 245), 6)
        painter.setPen(x_pen)
        pad = radius * 0.44
        painter.drawLine(
            QPointF(center.x() - pad, center.y() - pad),
            QPointF(center.x() + pad, center.y() + pad),
        )
        painter.drawLine(
            QPointF(center.x() + pad, center.y() - pad),
            QPointF(center.x() - pad, center.y() + pad),
        )

        noise_pen = QPen(QColor(255, 95, 141, 80), 1)
        painter.setPen(noise_pen)
        for _ in range(9):
            offset_y = random.randint(-30, 30)
            width = random.randint(16, 48)
            painter.drawLine(
                QPointF(center.x() - width, center.y() + offset_y),
                QPointF(center.x() + width, center.y() + offset_y),
            )
