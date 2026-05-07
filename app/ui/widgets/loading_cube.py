from __future__ import annotations

from math import cos, radians, sin

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class LoadingCubeWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = 0.0
        self._pulse = 0.0
        self._progress = 0

        self._timer = QTimer(self)
        self._timer.setInterval(24)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_progress(self, progress: int) -> None:
        self._progress = max(0, min(progress, 100))
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 2.4) % 360
        self._pulse += 0.12
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, on=True)

        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) * 0.34

        self._draw_orbit(painter=painter, center=center, radius=radius)
        self._draw_cube(painter=painter, center=center, radius=radius * 0.75)

    def _draw_orbit(self, painter: QPainter, center: QPointF, radius: float) -> None:
        base_pen = QPen(QColor(255, 66, 132, 80), 2)
        painter.setPen(base_pen)
        painter.drawEllipse(center, radius + 20, radius + 20)

        arc_pen = QPen(QColor(255, 90, 168, 240), 4)
        painter.setPen(arc_pen)
        rect_x = center.x() - radius - 20
        rect_y = center.y() - radius - 20
        size = (radius + 20) * 2

        span = int((max(self._progress, 5) / 100) * 5760)
        painter.drawArc(int(rect_x), int(rect_y), int(size), int(size), 90 * 16, -span)

    def _draw_cube(self, painter: QPainter, center: QPointF, radius: float) -> None:
        pulse_scale = 1.0 + (0.05 * sin(self._pulse))
        r = radius * pulse_scale

        points_front = self._regular_polygon(center=center, radius=r, sides=6, rotation=self._angle)
        points_back = self._regular_polygon(
            center=QPointF(center.x() + 16, center.y() - 14),
            radius=r,
            sides=6,
            rotation=self._angle + 22,
        )

        front_pen = QPen(QColor(255, 116, 186, 200), 2)
        back_pen = QPen(QColor(255, 74, 146, 120), 2)
        link_pen = QPen(QColor(255, 136, 200, 95), 1)

        painter.setPen(back_pen)
        painter.drawPolygon(points_back)

        painter.setPen(front_pen)
        painter.drawPolygon(points_front)

        painter.setPen(link_pen)
        for front_point, back_point in zip(points_front, points_back):
            painter.drawLine(front_point, back_point)

        glow_pen = QPen(QColor(255, 187, 222, 130), 3)
        painter.setPen(glow_pen)
        path = QPainterPath(points_front[0])
        for index in range(2, len(points_front), 2):
            path.lineTo(points_front[index])
        painter.drawPath(path)

    def _regular_polygon(
        self,
        center: QPointF,
        radius: float,
        sides: int,
        rotation: float,
    ) -> list[QPointF]:
        result = []
        for index in range(sides):
            angle = radians((360 / sides) * index + rotation)
            x = center.x() + radius * cos(angle)
            y = center.y() + radius * sin(angle)
            result.append(QPointF(x, y))
        return result
