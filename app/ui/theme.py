APP_STYLESHEET = """
/* Общие настройки */
* {
    font-family: "Segoe UI", "Roboto", "Bahnschrift";
    color: #ffffff;
}

QMainWindow {
    background-color: #05010a;
}

QWidget#RootContainer {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #0d0221,
        stop: 0.5 #05010a,
        stop: 1 #1a021d
    );
}

/* Карточки с эффектом стекла */
QFrame#PanelCard {
    background-color: rgba(25, 10, 45, 160);
    border: 1px solid rgba(255, 45, 140, 60);
    border-radius: 20px;
}

/* Заголовки */
QLabel#Title {
    font-size: 32px;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: 1px;
    background: transparent;
}

QLabel#SubTitle {
    font-size: 13px;
    font-weight: 600;
    color: #ff7eb9;
    text-transform: uppercase;
}

/* Таблицы */
QTableWidget {
    background-color: rgba(10, 5, 25, 180);
    border: 1px solid rgba(255, 255, 255, 20);
    border-radius: 12px;
    gridline-color: rgba(255, 255, 255, 10);
    color: #ffffff;
    selection-background-color: rgba(255, 45, 140, 80);
    alternate-background-color: rgba(255, 255, 255, 10);
}

QTableWidget::item {
    padding: 10px;
    color: #ffffff;
}

QHeaderView::section {
    background-color: rgba(30, 10, 50, 255);
    color: #ff7eb9;
    padding: 12px;
    border: none;
    border-bottom: 2px solid #ff2d8c;
    font-weight: bold;
}

/* Поля ввода */
QLineEdit {
    background-color: rgba(15, 5, 25, 200);
    border: 2px solid rgba(255, 45, 140, 80);
    border-radius: 12px;
    padding: 12px;
    color: #ffffff;
}

/* Кнопки */
QPushButton {
    background-color: rgba(255, 45, 140, 30);
    border: 1px solid rgba(255, 45, 140, 100);
    border-radius: 10px;
    color: #ffffff;
    padding: 8px 16px;
}

QPushButton#Primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff2d8c, stop:1 #ff7eb9);
    border: none;
    font-weight: bold;
}

/* Прогресс-бары */
QProgressBar {
    border: 1px solid rgba(255, 255, 255, 20);
    border-radius: 10px;
    background-color: rgba(0, 0, 0, 80);
    text-align: center;
    color: white;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff2d8c, stop:1 #6a00ff);
    border-radius: 9px;
}

/* ИСПРАВЛЕНИЕ ТУЛТИПОВ */
QToolTip {
    background-color: #1a0a2e;
    color: #ffffff;
    border: 2px solid #ff2d8c;
    border-radius: 8px;
    padding: 10px;
    font-size: 13px;
    opacity: 255;
}

/* ИСПРАВЛЕНИЕ ДИАЛОГА НАСТРОЕК */
QDialog {
    background-color: #120524;
    border: 2px solid #ff2d8c;
    border-radius: 15px;
}

QRadioButton {
    color: #ffffff;
    background: transparent;
    padding: 10px;
    font-size: 14px;
}

QRadioButton::indicator {
    width: 20px;
    height: 20px;
    border: 2px solid #ff2d8c;
    border-radius: 10px;
    background: #0d0221;
}

QRadioButton::indicator:checked {
    background-color: #ff2d8c;
    border: 4px solid #0d0221;
}

QRadioButton:hover {
    background-color: rgba(255, 45, 140, 20);
    border-radius: 8px;
}
"""
