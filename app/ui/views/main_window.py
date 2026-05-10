from __future__ import annotations

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для возможности прямого запуска файла
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

import json
from datetime import datetime, timezone
from typing import Any

from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QRadioButton,
    QButtonGroup,
)

from app.core.exceptions import WalletAnalyzerError
from app.domain.models.network import Network
from app.domain.models.results import WalletFetchResult
from app.services.wallet_data_service import WalletDataService
from app.ui.theme import APP_STYLESHEET
from app.ui.widgets.glitch_icon import GlitchXWidget
from app.ui.widgets.loading_cube import LoadingCubeWidget


class InfoIcon(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__("?", parent)
        self.setToolTip(text)
        self.setFixedSize(18, 18)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "InfoIcon {"
            "  background-color: rgba(255, 81, 130, 40);"
            "  border: 1px solid rgba(255, 81, 130, 120);"
            "  border-radius: 9px;"
            "  color: #ff5182;"
            "  font-weight: bold;"
            "  font-size: 11px;"
            "}"
            "InfoIcon:hover {"
            "  background-color: rgba(255, 81, 130, 80);"
            "  border: 1px solid #ff5182;"
            "}"
        )


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget, current_ai_state: bool) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки анализа")
        self.setFixedWidth(400)
        self.setStyleSheet(APP_STYLESHEET)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("МЕТОД АНАЛИЗА")
        title.setObjectName("Title")
        title.setStyleSheet("font-size: 18px;")
        layout.addWidget(title)
        
        self.template_radio = QRadioButton("Использовать шаблоны (быстро)")
        self.ai_radio = QRadioButton("Использовать ИИ-ассистент (анализ)")
        
        self.group = QButtonGroup(self)
        self.group.addButton(self.template_radio)
        self.group.addButton(self.ai_radio)
        
        if current_ai_state:
            self.ai_radio.setChecked(True)
        else:
            self.template_radio.setChecked(True)
            
        layout.addWidget(self.template_radio)
        layout.addWidget(self.ai_radio)
        
        save_btn = QPushButton("СОХРАНИТЬ")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self.accept)
        layout.addWidget(save_btn)
        
    def is_ai_enabled(self) -> bool:
        return self.ai_radio.isChecked()


class FetchWorker(QObject):
    progress = Signal(str, int)
    success = Signal(object)
    failure = Signal(str)

    CANCELLED_ERROR = "__CANCELLED__"

    def __init__(
        self,
        data_service: WalletDataService,
        address: str,
    ) -> None:
        super().__init__()
        self._data_service = data_service
        self._address = address
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True

    def _is_cancelled(self) -> bool:
        return self._cancel_requested or QThread.currentThread().isInterruptionRequested()

    @Slot()
    def run(self) -> None:
        try:
            if self._is_cancelled():
                self.failure.emit(self.CANCELLED_ERROR)
                return

            self.progress.emit("Определение сети (1/4)...", 18)
            network = self._data_service.detect_network(address=self._address)

            if self._is_cancelled():
                self.failure.emit(self.CANCELLED_ERROR)
                return

            self.progress.emit(f"Загрузка транзакций из {network.ui_label} (2/4)...", 46)
            transactions = self._data_service.fetch_transactions(
                address=self._address,
                network=network,
            )

            if self._is_cancelled():
                self.failure.emit(self.CANCELLED_ERROR)
                return

            self.progress.emit("Сохранение сырых данных (3/4)...", 72)
            saved_paths = self._data_service.save_raw_transactions(
                address=self._address,
                network=network,
                transactions=transactions,
            )

            if self._is_cancelled():
                self.failure.emit(self.CANCELLED_ERROR)
                return

            self.progress.emit("Формирование сводки (4/4)...", 92)
            result = self._data_service.build_result(
                address=self._address,
                network=network,
                transactions=transactions,
                saved_paths=saved_paths,
            )

            if self._is_cancelled():
                self.failure.emit(self.CANCELLED_ERROR)
                return

            self.progress.emit("Готово", 100)
            self.success.emit(result)
        except WalletAnalyzerError as exc:
            self.failure.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failure.emit(f"Непредвиденная ошибка: {exc}")


class MainWindow(QMainWindow):
    def __init__(self, data_service: WalletDataService) -> None:
        super().__init__()
        self._data_service = data_service
        self._thread: QThread | None = None
        self._worker: FetchWorker | None = None
        self._orphan_threads: list[QThread] = []
        self._displayed_transactions: list[dict] = []
        self._current_result: WalletFetchResult | None = None

        self._pulse_state = False
        self._cancel_requested = False
        self._analyze_button_timer = QTimer(self)
        self._analyze_button_timer.setInterval(600)
        self._analyze_button_timer.timeout.connect(self._animate_analyze_button)

        self._setup_window()
        self._build_ui()
        self._analyze_button_timer.start()

    def _setup_window(self) -> None:
        self.setWindowTitle("Классификация и анализ криптокошелька")
        self.setMinimumSize(1220, 760)
        self.setStyleSheet(APP_STYLESHEET)

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("RootContainer")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 20, 20, 20)

        self._stack = QStackedWidget(root)
        self._page_init = self._create_init_page()
        self._page_loading = self._create_loading_page()
        self._page_results = self._create_results_page()
        self._page_error = self._create_error_page()

        self._stack.addWidget(self._page_init)
        self._stack.addWidget(self._page_loading)
        self._stack.addWidget(self._page_results)
        self._stack.addWidget(self._page_error)

        root_layout.addWidget(self._stack)
        self.setCentralWidget(root)

    def _create_init_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Кнопка настроек сверху справа
        top_bar = QHBoxLayout()
        top_bar.addStretch(1)
        settings_btn = QPushButton("⚙ Настройки")
        settings_btn.clicked.connect(self._show_settings)
        top_bar.addWidget(settings_btn)
        layout.addLayout(top_bar)

        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        title = QLabel("КЛАССИФИКАЦИЯ И АНАЛИЗ\nКРИПТОКОШЕЛЬКА")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("PanelCard")
        card.setFixedWidth(700)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(14)

        self._address_input = QLineEdit()
        self._address_input.setPlaceholderText(
            "Введите адрес кошелька (например, 0x... или EQ...)"
        )
        card_layout.addWidget(self._address_input)

        auto_network_hint = QLabel("Сеть определяется автоматически по введенному адресу.")
        auto_network_hint.setObjectName("SubTitle")
        card_layout.addWidget(auto_network_hint)

        self._analyze_button = QPushButton("АНАЛИЗИРОВАТЬ")
        self._analyze_button.setObjectName("Primary")
        self._analyze_button.setMinimumHeight(48)
        self._analyze_button.clicked.connect(self._start_fetch)
        card_layout.addWidget(self._analyze_button)

        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

        info = QLabel(
            "Прототип системы для автоматического анализа истории транзакций\n"
            "и риск-профиля."
        )
        info.setObjectName("SubTitle")
        info.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(info)

        return page

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self, self._data_service._use_ai_analysis)
        if dialog.exec():
            self._data_service.set_use_ai_analysis(dialog.is_ai_enabled())

    def _get_export_dir(self) -> Path:
        if not getattr(self, '_current_result', None):
            return self._data_service._repository._output_dir / "raw"
        net_name = self._current_result.network.value.lower()
        out_dir = self._data_service._repository._output_dir / "raw" / net_name
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def _export_markdown(self) -> None:
        if hasattr(self, '_current_result') and self._current_result:
            out_dir = self._get_export_dir()
            path = out_dir / f'report_{self._current_result.address[:10]}.md'
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f'# Wallet Analysis Report\n\n**Address:** {self._current_result.address}\n')
                if self._current_result.category_stats:
                    f.write('\n## Stats\n')
                    for k, v in self._current_result.category_stats.items():
                        f.write(f'- {k}: {v}\n')
            QMessageBox.information(self, 'Export', f'Saved to {path}')

    def _export_html(self) -> None:
        if hasattr(self, '_current_result') and self._current_result:
            out_dir = self._get_export_dir()
            path = out_dir / f'report_{self._current_result.address[:10]}.html'
            with open(path, 'w', encoding='utf-8') as f:
                f.write('<html><body><h1>Wallet Report</h1><p><b>Address:</b> '+self._current_result.address+'</p>')
                if self._current_result.category_stats:
                    f.write('<ul>')
                    for k, v in self._current_result.category_stats.items():
                        f.write(f'<li>{k}: {v}</li>')
                    f.write('</ul>')
                f.write('</body></html>')
            QMessageBox.information(self, 'Export', f'Saved to {path}')

    def _export_json(self) -> None:
        if not getattr(self, '_current_result', None):
            self._show_error("Нет данных для экспорта")
            return
        try:
            out_dir = self._get_export_dir()
            path = out_dir / f"report_{self._current_result.address[:10]}.json"
            data = {
                "address": self._current_result.address,
                "network": self._current_result.network.ui_label,
                "transaction_count": self._current_result.transaction_count,
                "total_native_volume": str(self._current_result.total_native_volume),
                "risk_level": self._current_result.risk_level,
                "risk_score": self._current_result.risk_score,
                "wallet_type": self._current_result.wallet_type,
                "category_stats": self._current_result.category_stats,
                "portrait": {
                    "behavior_type": self._current_result.portrait.behavior_type if self._current_result.portrait else None,
                    "asset_preferences": self._current_result.portrait.asset_preferences if self._current_result.portrait else [],
                    "summary": self._current_result.portrait.summary if self._current_result.portrait else ""
                },
                "transactions": self._current_result.transactions
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Экспорт", f"JSON сохранен: {path}")
        except Exception as e:
            self._show_error(f"Ошибка экспорта JSON: {e}")


    def _export_graph_png(self) -> None:
        if not getattr(self, '_current_result', None) or not self._current_result.transactions:
            self._show_error("Нет данных для графика")
            return
        try:
            from matplotlib import cm
            from matplotlib.figure import Figure
            cat_stats = self._current_result.category_stats
            if not cat_stats:
                self._show_error("Нет данных по категориям")
                return
            fig = Figure(figsize=(10, 7), facecolor='#1E1E2E')
            ax = fig.add_subplot(111)
            colors = cm.Set3.colors[:len(cat_stats)]
            wedges, texts, autotexts = ax.pie(
                list(cat_stats.values()),
                labels=list(cat_stats.keys()),
                autopct='%1.1f%%',
                textprops=dict(color="white", fontsize=11),
                colors=colors,
                pctdistance=0.85,
                wedgeprops=dict(width=0.4, edgecolor='#1E1E2E')
            )
            for autotext in autotexts:
                autotext.set_fontsize(10)
                autotext.set_color('white')
            ax.axis('equal')
            ax.set_title("Распределение по категориям", color="white", fontsize=14, pad=20)
            fig.tight_layout()
            out_dir = self._get_export_dir()
            path = out_dir / f"pie_chart_{self._current_result.address[:10]}.png"
            fig.savefig(path, facecolor=fig.get_facecolor(), dpi=200)
            QMessageBox.information(self, "Экспорт", f"График сохранен: {path}")
        except Exception as e:
            self._show_error(f"Ошибка PNG графика: {e}")

    def _export_network_png(self) -> None:
        if not getattr(self, '_current_result', None) or not self._current_result.transactions:
            self._show_error("Нет данных для графа")
            return
        try:
            import networkx as nx
            from collections import Counter, defaultdict
            from matplotlib.figure import Figure
            from matplotlib import cm
            from matplotlib import colors as mcolors
            from matplotlib.patches import Patch
            G = nx.DiGraph()
            main_addr = self._current_result.address.lower()

            analysis_service = self._data_service._analysis_service
            counterparty_category_counts: dict[str, Counter[str]] = defaultdict(Counter)
            for tx in self._current_result.transactions:
                if "in_msg" in tx or "out_msgs" in tx:
                    in_msg = tx.get("in_msg")
                    if isinstance(in_msg, dict):
                        f_adr = in_msg.get("source", "") or main_addr
                        t_adr = in_msg.get("destination", "") or main_addr
                        if f_adr and t_adr and f_adr != "-" and t_adr != "-":
                            G.add_edge(f_adr.lower(), t_adr.lower())
                    out_msgs = tx.get("out_msgs", [])
                    if isinstance(out_msgs, list):
                        for om in out_msgs:
                            if isinstance(om, dict):
                                f_adr = om.get("source", "") or main_addr
                                t_adr = om.get("destination", "") or main_addr
                                if f_adr and t_adr and f_adr != "-" and t_adr != "-":
                                    G.add_edge(f_adr.lower(), t_adr.lower())
                else:
                    f_adr = str(tx.get("from", "")).lower()
                    t_adr = str(tx.get("to", "")).lower()
                    if f_adr and t_adr and f_adr != "-" and t_adr != "-":
                        G.add_edge(f_adr, t_adr)

                # Сбор категории для контрагентов (для раскраски узлов)
                try:
                    category_label = analysis_service.classify_transaction(tx, main_addr).value
                except Exception:  # noqa: BLE001
                    category_label = "Прочее"

                # Приводим участников к одному формату (EVM/TON)
                tx_from = ""
                tx_to = ""
                if isinstance(tx, dict) and ("in_msg" in tx or "out_msgs" in tx):
                    in_msg = tx.get("in_msg") if isinstance(tx.get("in_msg"), dict) else {}
                    tx_from = str(in_msg.get("source") or in_msg.get("src") or "").lower()
                    tx_to = str(in_msg.get("destination") or in_msg.get("dest") or "").lower()
                else:
                    tx_from = str(tx.get("from", "")).lower()
                    tx_to = str(tx.get("to", "")).lower()

                if tx_from and tx_to and tx_from != "-" and tx_to != "-":
                    if tx_from == main_addr and tx_to != main_addr:
                        counterparty_category_counts[tx_to][category_label] += 1
                    elif tx_to == main_addr and tx_from != main_addr:
                        counterparty_category_counts[tx_from][category_label] += 1

            if G.number_of_nodes() == 0:
                self._show_error("Недостаточно данных для построения графа связей")
                return
            fig = Figure(figsize=(12, 10), facecolor='#1E1E2E')
            ax = fig.add_subplot(111)
            node_count = G.number_of_nodes()
            if node_count > 200:
                pos = nx.spring_layout(G, k=0.5, iterations=30, seed=42)
            else:
                pos = nx.spring_layout(G, k=0.3, iterations=50, seed=42)
            # Назначаем каждой вершине "доминирующую" категорию (по частоте)
            node_to_category: dict[str, str] = {}
            for node, counts in counterparty_category_counts.items():
                if counts:
                    node_to_category[node] = counts.most_common(1)[0][0]

            categories_in_graph = sorted({cat for cat in node_to_category.values() if cat})
            cmap = cm.get_cmap("tab20", max(1, len(categories_in_graph)))
            category_color_map: dict[str, str] = {}
            for idx, cat in enumerate(categories_in_graph):
                category_color_map[cat] = mcolors.to_hex(cmap(idx))

            node_colors: list[str] = []
            node_sizes: list[int] = []
            for n in G.nodes():
                if str(n).lower() == main_addr:
                    node_colors.append('#ff0055')
                    node_sizes.append(120)
                else:
                    cat = node_to_category.get(str(n).lower())
                    node_colors.append(category_color_map.get(cat, '#00aabb'))
                    node_sizes.append(40)
            nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes, node_color=node_colors, alpha=0.9)
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color='#ffffff', alpha=0.15, arrows=True, arrowsize=8, width=0.5)
            if node_count <= 50:
                labels = {n: (n[:6] + "..." + n[-4:] if len(str(n)) > 12 else str(n)) for n in G.nodes()}
                nx.draw_networkx_labels(G, pos, labels, font_size=7, font_color='#ffffff', ax=ax)
            ax.set_facecolor('#1E1E2E')
            ax.axis('off')

            # Легенда: кошелек + основные категории контрагентов
            legend_items: list[Patch] = [Patch(color="#ff0055", label="Кошелек")]
            if categories_in_graph:
                # Ограничим легенду, чтобы не занимала пол-экрана
                top_cats = [
                    cat for cat, _ in Counter(node_to_category.values()).most_common(8)
                    if cat in category_color_map
                ]
                for cat in top_cats:
                    legend_items.append(Patch(color=category_color_map[cat], label=cat))

            if len(legend_items) > 1:
                legend = ax.legend(
                    handles=legend_items,
                    loc="lower left",
                    fontsize=8,
                    frameon=False,
                )
                for text in legend.get_texts():
                    text.set_color("white")

            fig.tight_layout()
            out_dir = self._get_export_dir()
            path = out_dir / f"network_graph_{self._current_result.address[:10]}.png"
            fig.savefig(path, facecolor=fig.get_facecolor(), dpi=200)
            QMessageBox.information(self, "Экспорт", f"Граф сохранен: {path}")
        except Exception as e:
            self._show_error(f"Ошибка сохранения графа: {e}")

    def _create_loading_page(self) -> QWidget:

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        self._loading_cube = LoadingCubeWidget()
        self._loading_cube.setFixedSize(290, 290)
        layout.addWidget(self._loading_cube, alignment=Qt.AlignmentFlag.AlignCenter)

        loading_title = QLabel("ЗАГРУЗКА ДАННЫХ...")
        loading_title.setObjectName("Title")
        loading_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(loading_title)

        self._loading_status = QLabel("Подготовка...")
        self._loading_status.setObjectName("SubTitle")
        self._loading_status.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._loading_status)

        self._loading_progress = QProgressBar()
        self._loading_progress.setFixedWidth(420)
        self._loading_progress.setRange(0, 100)
        self._loading_progress.setValue(0)
        layout.addWidget(self._loading_progress, alignment=Qt.AlignmentFlag.AlignCenter)

        self._cancel_button = QPushButton("ОТМЕНА")
        self._cancel_button.setMinimumHeight(40)
        self._cancel_button.clicked.connect(self._cancel_fetch)
        layout.addWidget(self._cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    def _create_results_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self._results_title = QLabel("АНАЛИЗ КОШЕЛЬКА: -")
        self._results_title.setObjectName("Title")
        header.addWidget(self._results_title)

        header.addStretch(1)
        for label, action in [
            ("Markdown (MD)", self._export_markdown),
            ("Отчет (HTML)", self._export_html),
            ("JSON", self._export_json),
            ("График категорий (PNG)", self._export_graph_png),
            ("Граф связей (PNG)", self._export_network_png)
        ]:
            button = QPushButton(label)
            button.clicked.connect(action)
            header.addWidget(button)

        layout.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        self._summary_card = self._build_summary_card()
        self._portrait_card = self._build_portrait_card()
        self._stats_card = self._build_stats_card()
        self._table_card = self._build_table_card()

        grid.addWidget(self._summary_card, 0, 0)
        grid.addWidget(self._portrait_card, 0, 1)
        grid.addWidget(self._stats_card, 1, 0)
        grid.addWidget(self._table_card, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        layout.addLayout(grid)

        actions_row = QHBoxLayout()
        back_button = QPushButton("Новый анализ")
        back_button.clicked.connect(self._go_to_init)
        actions_row.addStretch(1)
        actions_row.addWidget(back_button)
        layout.addLayout(actions_row)

        return page

    def _build_summary_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("PanelCard")
        card_layout = QVBoxLayout(card)

        title_row = QHBoxLayout()
        title = QLabel("СВОДКА И РИСК")
        title.setObjectName("SubTitle")
        title_row.addWidget(title)
        title_row.addWidget(InfoIcon("Общая информация о кошельке и расчетный уровень риска на основе эвристик."))
        title_row.addStretch()
        card_layout.addLayout(title_row)

        self._risk_value = QLabel("РИСК: -")
        self._risk_value.setStyleSheet(
            "font-size: 28px; color: #ffb36b; font-family: 'Bahnschrift SemiBold';"
        )
        card_layout.addWidget(self._risk_value)

        self._tx_count_label = QLabel("Всего транзакций: 0")
        self._volume_label = QLabel("Общий объем (native): 0")
        self._source_label = QLabel("Сеть: -")
        self._wallet_type_label = QLabel("Тип кошелька: -")
        self._wallet_type_label.setStyleSheet("font-size: 16px; color: #ff6cae; font-family: 'Bahnschrift SemiBold';")

        card_layout.addWidget(self._tx_count_label)
        card_layout.addWidget(self._volume_label)
        card_layout.addWidget(self._source_label)
        
        type_row = QHBoxLayout()
        type_row.addWidget(self._wallet_type_label)
        type_row.addWidget(InfoIcon("Классификация владельца: Биржа, Майнер, Миксер или Индивидуальный пользователь."))
        type_row.addStretch()
        card_layout.addLayout(type_row)

        turnover_hint = QLabel(
            "Общий оборот (native) - сумма всех входящих и исходящих переводов "
            "в нативной монете сети (например ETH/BNB/MATIC/TON). "
            "Это не баланс и не прибыль."
        )
        turnover_hint.setWordWrap(True)
        turnover_hint.setObjectName("SubTitle")
        card_layout.addWidget(turnover_hint)

        note = QLabel(
            "Риск рассчитывается эвристически по структуре и истории транзакций."
        )
        note.setWordWrap(True)
        note.setObjectName("SubTitle")
        card_layout.addWidget(note)

        return card

    def _build_portrait_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("PanelCard")
        card_layout = QVBoxLayout(card)

        title_row = QHBoxLayout()
        title = QLabel("ПОРТРЕТ ВЛАДЕЛЬЦА")
        title.setObjectName("SubTitle")
        title_row.addWidget(title)
        title_row.addWidget(InfoIcon("Автоматически сгенерированный портрет на основе истории транзакций и типов активности."))
        title_row.addStretch()
        card_layout.addLayout(title_row)

        self._portrait_behavior = QLabel("Поведение: -")
        self._portrait_behavior.setStyleSheet("font-size: 16px; color: #ffdbe8;")
        card_layout.addWidget(self._portrait_behavior)

        self._portrait_assets = QLabel("Предпочтения: -")
        card_layout.addWidget(self._portrait_assets)

        self._portrait_summary = QPlainTextEdit()
        self._portrait_summary.setReadOnly(True)
        self._portrait_summary.setStyleSheet("background: transparent; border: none; color: #f6f3ff;")
        card_layout.addWidget(self._portrait_summary)

        return card

    def _build_stats_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("PanelCard")
        card_layout = QVBoxLayout(card)

        title_row = QHBoxLayout()
        title = QLabel("СТАТИСТИКА ОПЕРАЦИЙ")
        title.setObjectName("SubTitle")
        title_row.addWidget(title)
        title_row.addWidget(InfoIcon("Распределение транзакций по категориям: DEX, Мосты, NFT, DeFi и др."))
        title_row.addStretch()
        card_layout.addLayout(title_row)

        self._stats_list = QVBoxLayout()
        card_layout.addLayout(self._stats_list)
        
        self._btn_build_graph = QPushButton("Построить график категорий")
        self._btn_build_graph.clicked.connect(self._build_graph)
        self._btn_build_graph.hide()
        card_layout.addWidget(self._btn_build_graph)

        self._btn_build_network = QPushButton("Построить граф связей")
        self._btn_build_network.clicked.connect(self._build_network_graph)
        self._btn_build_network.hide()
        card_layout.addWidget(self._btn_build_network)

        card_layout.addStretch(1)

        return card

    def _build_table_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("PanelCard")
        card_layout = QVBoxLayout(card)

        title = QLabel("ВСЕ ТРАНЗАКЦИИ")
        title.setObjectName("SubTitle")
        card_layout.addWidget(title)

        tip = QLabel("Двойной клик по строке открывает полные данные транзакции (JSON).")
        tip.setObjectName("SubTitle")
        tip.setWordWrap(True)
        card_layout.addWidget(tip)
        
        self._btn_clear_filter = QPushButton("Сбросить фильтр")
        self._btn_clear_filter.hide()
        self._btn_clear_filter.clicked.connect(self._clear_filter)
        card_layout.addWidget(self._btn_clear_filter)

        self._tx_table = QTableWidget(0, 9)
        self._tx_table.setHorizontalHeaderLabels(
            [
                "Hash",
                "Time (UTC)",
                "Category",
                "From",
                "To",
                "Value (native)",
                "Fee (native)",
                "Status",
                "Ref",
            ]
        )
        # Убираем дефолтные стили сетки, которые могут мешать
        self._tx_table.setShowGrid(False)
        self._tx_table.setAlternatingRowColors(True)
        self._tx_table.setStyleSheet("QTableWidget { background-color: transparent; }")
        self._tx_table.horizontalHeader().setStretchLastSection(False)
        self._tx_table.verticalHeader().setVisible(False)
        self._tx_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tx_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tx_table.cellDoubleClicked.connect(self._show_transaction_details)
        self._tx_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        card_layout.addWidget(self._tx_table)

        return card

    def _create_error_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("PanelCard")
        card.setFixedWidth(640)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)

        glitch = GlitchXWidget()
        glitch.setFixedSize(160, 160)
        card_layout.addWidget(glitch, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel("ОЙ! ЧТО-ТО ПОШЛО НЕ ТАК.")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        card_layout.addWidget(title)

        self._error_label = QLabel("Не удалось проанализировать кошелек.")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._error_label.setWordWrap(True)
        card_layout.addWidget(self._error_label)

        retry_button = QPushButton("ПОПРОБОВАТЬ СНОВА")
        retry_button.setObjectName("Primary")
        retry_button.clicked.connect(self._go_to_init)
        card_layout.addWidget(retry_button, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(card)
        return page

    def _start_fetch(self) -> None:
        if self._thread is not None:
            return

        address = self._address_input.text().strip()
        if not address:
            QMessageBox.warning(self, "Пустой адрес", "Введите адрес кошелька.")
            return

        self._stack.setCurrentWidget(self._page_loading)
        self._loading_progress.setValue(0)
        self._loading_status.setText("Подготовка...")
        self._cancel_requested = False
        if hasattr(self, "_cancel_button"):
            self._cancel_button.setEnabled(True)

        self._thread = QThread(self)
        self._worker = FetchWorker(
            data_service=self._data_service,
            address=address,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.success.connect(self._on_worker_success)
        self._worker.failure.connect(self._on_worker_failure)

        # Корректная очистка объектов после завершения потока
        self._thread.finished.connect(self._worker.deleteLater)

        self._worker.success.connect(self._cleanup_worker)
        self._worker.failure.connect(self._cleanup_worker)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _track_orphan_thread(self, thread: QThread) -> None:
        if thread in self._orphan_threads:
            return
        self._orphan_threads.append(thread)

        def _release() -> None:
            try:
                self._orphan_threads.remove(thread)
            except ValueError:
                pass

        thread.finished.connect(_release)

    def _stop_worker_thread(self, *, soft_wait_ms: int = 600, hard_wait_ms: int = 2000) -> bool:
        thread = self._thread
        if thread is None:
            return True

        if self._worker is not None:
            try:
                self._worker.cancel()
            except Exception:  # noqa: BLE001
                pass

        try:
            thread.requestInterruption()
        except Exception:  # noqa: BLE001
            pass

        try:
            thread.quit()
        except Exception:  # noqa: BLE001
            pass

        if thread.wait(soft_wait_ms):
            return True

        # Фоллбек: принудительное завершение (прототип)
        try:
            thread.terminate()
        except Exception:  # noqa: BLE001
            pass

        thread.wait(hard_wait_ms)
        return not thread.isRunning()

    @Slot(str, int)
    def _on_worker_progress(self, status_text: str, progress: int) -> None:
        if self.sender() is not self._worker:
            return
        if self._cancel_requested:
            return
        self._loading_status.setText(status_text)
        self._loading_progress.setValue(progress)
        self._loading_cube.set_progress(progress)

    @Slot(object)
    def _on_worker_success(self, payload: Any) -> None:
        if self.sender() is not self._worker:
            return
        if self._cancel_requested:
            return
        if not isinstance(payload, WalletFetchResult):
            self._show_error("Получен неожиданный формат данных результата.")
            return

        short_addr = f"{payload.address[:6]}...{payload.address[-4:]}"
        self._results_title.setText(f"АНАЛИЗ КОШЕЛЬКА: {short_addr}")

        self._tx_count_label.setText(f"Всего транзакций: {payload.transaction_count}")
        self._volume_label.setText(self._build_volume_text(payload=payload))
        self._source_label.setText(f"Сеть: {payload.network.ui_label}")
        self._wallet_type_label.setText(f"Тип кошелька: {payload.wallet_type}")
        self._set_risk_display(level=payload.risk_level, score=payload.risk_score)

        # Заполнение портрета
        if payload.portrait:
            self._portrait_behavior.setText(f"Поведение: {payload.portrait.behavior_type}")
            self._portrait_assets.setText(f"Предпочтения: {', '.join(payload.portrait.asset_preferences)}")
            self._portrait_summary.setPlainText(payload.portrait.summary)

        self._current_result = payload

        # Заполнение статистики
        self._update_stats_display(payload.category_stats)

        self._btn_build_graph.show()
        self._btn_build_network.show()

        self._fill_transactions_table(
            transactions=payload.transactions,
            network=payload.network,
            wallet_address=payload.address,
        )
        self._stack.setCurrentWidget(self._page_results)

    @Slot(str)
    def _on_worker_failure(self, error_message: str) -> None:
        if self.sender() is not self._worker:
            return
        if error_message == FetchWorker.CANCELLED_ERROR:
            return
        if self._cancel_requested:
            return
        self._show_error(error_message)

    def _cancel_fetch(self) -> None:
        # UI должен вернуться сразу. Остановить сетевой запрос мгновенно нельзя,
        # поэтому делаем отмену "best-effort": просим воркер завершиться и
        # даём потоку спокойно догнаться в фоне.
        if self._thread is None:
            self._go_to_init()
            return

        self._cancel_requested = True
        if hasattr(self, "_cancel_button"):
            self._cancel_button.setEnabled(False)

        thread = self._thread
        worker = self._worker

        self._loading_status.setText("Отмена...")
        self._loading_progress.setValue(0)
        self._loading_cube.set_progress(0)

        if worker is not None:
            try:
                worker.cancel()
            except Exception:  # noqa: BLE001
                pass

        try:
            thread.requestInterruption()
        except Exception:  # noqa: BLE001
            pass

        # Останавливаем event-loop QThread (как только воркер выйдет из run()).
        try:
            thread.quit()
        except Exception:  # noqa: BLE001
            pass

        # Чтобы можно было сразу запускать новый анализ, отвязываем активный воркер/поток,
        # но держим ссылку на поток, чтобы Qt не уничтожил его раньше завершения.
        self._track_orphan_thread(thread)
        self._thread = None
        self._worker = None

        self._go_to_init()

    @Slot()
    def _cleanup_worker(self) -> None:
        if self.sender() is not self._worker:
            return
        if self._thread is None:
            return

        # На обычном завершении/ошибке поток должен закрыться быстро.
        self._stop_worker_thread(soft_wait_ms=1500, hard_wait_ms=2000)

        if self._thread is not None:
            try:
                self._thread.deleteLater()
            except Exception:  # noqa: BLE001
                pass

        self._thread = None
        self._worker = None

    def _stop_thread(self, thread: QThread, *, soft_wait_ms: int = 600, hard_wait_ms: int = 2000) -> None:
        try:
            thread.requestInterruption()
        except Exception:  # noqa: BLE001
            pass
        try:
            thread.quit()
        except Exception:  # noqa: BLE001
            pass
        if thread.wait(soft_wait_ms):
            return
        try:
            thread.terminate()
        except Exception:  # noqa: BLE001
            pass
        thread.wait(hard_wait_ms)

    def closeEvent(self, event) -> None:  # noqa: N802
        # Если пользователь закрывает окно во время загрузки — останавливаем поток,
        # иначе Qt выдаст: "QThread: Destroyed while thread is still running".
        self._cancel_requested = True

        if self._thread is not None and self._thread.isRunning():
            self._stop_thread(self._thread, soft_wait_ms=800, hard_wait_ms=2500)
            self._thread = None
            self._worker = None

        # Также добиваем все "осиротевшие" потоки, если отмена была во время запроса.
        for thread in list(self._orphan_threads):
            if thread.isRunning():
                self._stop_thread(thread, soft_wait_ms=800, hard_wait_ms=2500)

        try:
            event.accept()
        except Exception:  # noqa: BLE001
            pass

    def _update_stats_display(self, category_stats: dict[str, int] | None) -> None:
        # Очистка старой статистики
        while self._stats_list.count():
            item = self._stats_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not category_stats:
            self._stats_list.addWidget(QLabel("Нет данных для статистики"))
            return
            
        total = sum(category_stats.values())
        for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            percent = (count / total) * 100
            
            row = QHBoxLayout()
            btn_cat = QPushButton(cat)
            btn_cat.setFixedWidth(150)
            btn_cat.setStyleSheet("text-align: left; background: transparent; border: none; text-decoration: underline;")
            btn_cat.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cat.clicked.connect(lambda _, c=cat: self._filter_by_category(c))
            row.addWidget(btn_cat)
            
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(int(percent))
            progress.setFormat(f"{count} ({percent:.1f}%)")
            row.addWidget(progress)
            
            container = QWidget()
            container.setLayout(row)
            self._stats_list.addWidget(container)

    def _fill_transactions_table(
        self,
        transactions: list[dict],
        network: Network,
        wallet_address: str,
    ) -> None:
        def _extract_address(value: Any) -> str:
            if isinstance(value, dict):
                raw = value.get("address")
                return str(raw) if raw is not None else "-"
            if value is None:
                return "-"
            return str(value)

        def _safe_int(value: Any) -> int | None:
            try:
                return int(str(value))
            except (TypeError, ValueError):
                return None

        def _format_timestamp(tx: dict) -> str:
            raw_timestamp = tx.get("utime") if network is Network.TON else tx.get("timeStamp")
            timestamp_value = _safe_int(raw_timestamp)
            if timestamp_value is None or timestamp_value <= 0:
                return "-"
            try:
                return datetime.fromtimestamp(
                    timestamp_value,
                    tz=timezone.utc,
                ).strftime("%Y-%m-%d %H:%M:%S UTC")
            except (OverflowError, OSError, ValueError):
                return str(raw_timestamp)

        def _format_fee_native(tx: dict) -> str:
            if network is Network.TON:
                fee_raw = tx.get("total_fees")
                if fee_raw is None:
                    fee_raw = tx.get("fee")
                fee_base = _safe_int(fee_raw)
                if fee_base is None:
                    return "-"
                rendered = f"{fee_base / 10**9:.9f}".rstrip("0").rstrip(".")
                return rendered if rendered else "0"

            gas_price = _safe_int(tx.get("gasPrice"))
            gas_used = _safe_int(tx.get("gasUsed"))
            if gas_used is None:
                gas_used = _safe_int(tx.get("gas"))

            if gas_price is None or gas_used is None:
                return "-"

            rendered = f"{(gas_used * gas_price) / 10**18:.8f}".rstrip("0").rstrip(".")
            return rendered if rendered else "0"

        def _extract_reference(tx: dict) -> str:
            if network is Network.TON:
                lt = tx.get("lt") or (tx.get("transaction_id") or {}).get("lt")
                return f"lt: {lt}" if lt is not None else "-"

            block = tx.get("blockNumber")
            return f"block: {block}" if block is not None else "-"

        def _extract_ton_participants(tx: dict) -> tuple[str, str]:
            source_msg = tx.get("in_msg") if isinstance(tx.get("in_msg"), dict) else {}
            account = tx.get("account") if isinstance(tx.get("account"), dict) else {}
            owner_address = _extract_address(account).strip()

            from_addr = _extract_address(source_msg.get("source") or source_msg.get("src"))
            if from_addr == "-":
                from_addr = owner_address if owner_address else "-"

            to_addr = _extract_address(source_msg.get("destination") or source_msg.get("dest"))

            owner_norm = owner_address.lower()
            to_norm = to_addr.lower() if to_addr != "-" else ""
            if to_addr == "-" or (owner_norm and to_norm == owner_norm):
                out_msgs = tx.get("out_msgs") if isinstance(tx.get("out_msgs"), list) else []
                for out_msg in out_msgs:
                    if not isinstance(out_msg, dict):
                        continue
                    out_dest = _extract_address(out_msg.get("destination") or out_msg.get("dest"))
                    if out_dest != "-":
                        to_addr = out_dest
                        break

            if to_addr == "-" and owner_address:
                to_addr = owner_address

            return from_addr, to_addr

        def _format_native_value(tx: dict) -> str:
            base_units = self._data_service.extract_transaction_value_base_units(
                tx=tx,
                network=network,
            )
            divider = 10**9 if network is Network.TON else 10**18
            value_native = base_units / divider

            if network is Network.TON:
                rendered = f"{value_native:.9f}".rstrip("0").rstrip(".")
                return rendered if rendered else "0"

            return f"{value_native:.6f}"

        wallet_address_norm = wallet_address.strip().lower()

        rows = transactions
        self._displayed_transactions = rows
        self._tx_table.setRowCount(len(rows))

        for row_index, tx in enumerate(rows):
            tx_hash = str(
                tx.get("hash")
                or (tx.get("transaction_id") or {}).get("hash")
                or "-"
            )

            if network is Network.TON:
                from_address, to_address = _extract_ton_participants(tx)
            else:
                from_address = _extract_address(tx.get("from"))
                to_address = _extract_address(tx.get("to"))

            if not from_address or from_address == "-":
                from_address = wallet_address
            if not to_address or to_address == "-":
                to_address = wallet_address

            from_norm = from_address.lower()
            to_norm = to_address.lower()
            if wallet_address_norm and from_norm == wallet_address_norm and to_norm != wallet_address_norm:
                direction = "OUT"
            elif wallet_address_norm and to_norm == wallet_address_norm and from_norm != wallet_address_norm:
                direction = "IN"
            elif wallet_address_norm and from_norm == wallet_address_norm and to_norm == wallet_address_norm:
                direction = "SELF"
            else:
                direction = "UNKNOWN"

            if wallet_address_norm and from_norm == wallet_address_norm:
                from_address = f"{from_address} (you)"
            if wallet_address_norm and to_norm == wallet_address_norm:
                to_address = f"{to_address} (you)"

            if "isError" in tx:
                status = "OK" if str(tx.get("isError", "0")) == "0" else "ERROR"
            elif isinstance(tx.get("success"), bool):
                status = "OK" if bool(tx.get("success")) else "ERROR"
            elif isinstance(tx.get("aborted"), bool):
                status = "ERROR" if bool(tx.get("aborted")) else "OK"
            else:
                status = "OK"

            value_display = _format_native_value(tx)
            fee_display = _format_fee_native(tx)
            timestamp_display = _format_timestamp(tx)
            reference_display = _extract_reference(tx)
            
            # Определяем категорию через сервис
            analysis_service = self._data_service._analysis_service
            category = analysis_service.classify_transaction(tx, wallet_address).value

            values = [
                tx_hash,
                timestamp_display,
                category,
                from_address,
                to_address,
                value_display,
                fee_display,
                status,
                reference_display,
            ]

            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._tx_table.setItem(row_index, col_index, item)

    @Slot(int, int)
    def _show_transaction_details(self, row: int, _column: int) -> None:
        if row < 0 or row >= len(self._displayed_transactions):
            return

        tx = self._displayed_transactions[row]

        dialog = QDialog(self)
        dialog.setWindowTitle("Полные данные транзакции")
        dialog.resize(980, 640)

        layout = QVBoxLayout(dialog)
        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(json.dumps(tx, indent=4, ensure_ascii=False))
        layout.addWidget(viewer)
        dialog.exec()

    def _build_volume_text(self, payload: WalletFetchResult) -> str:
        symbol = "TON" if payload.network is Network.TON else "native"
        return f"Общий объем ({symbol}): {payload.total_native_volume:.6f}"

    def _set_risk_display(self, level: str, score: int) -> None:
        safe_score = max(0, min(100, int(score)))
        self._risk_value.setText(f"{level} ({safe_score}/100)")

        if "НИЗКИЙ" in level:
            color = "#42d392"
        elif "СРЕДНИЙ" in level:
            color = "#ffb36b"
        else:
            color = "#ff4f9c"

        self._risk_value.setStyleSheet(
            f"font-size: 28px; color: {color}; font-family: 'Bahnschrift SemiBold';"
        )


    def _filter_by_category(self, category: str) -> None:
        for row in range(self._tx_table.rowCount()):
            item = self._tx_table.item(row, 2)
            if item:
                self._tx_table.setRowHidden(row, item.text() != category)
        self._btn_clear_filter.show()

    def _clear_filter(self) -> None:
        for row in range(self._tx_table.rowCount()):
            self._tx_table.setRowHidden(row, False)
        self._btn_clear_filter.hide()

    def _build_graph(self) -> None:
        if not self._current_result or not self._current_result.transactions:
            self._show_error("Нет данных для графика")
            return

        try:
            from matplotlib import cm
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

            cat_stats = self._current_result.category_stats
            if not cat_stats:
                self._show_error("Нет данных по категориям")
                return

            categories = list(cat_stats.keys())
            counts = list(cat_stats.values())

            dialog = QDialog(self)
            dialog.setWindowTitle("График категорий")
            dialog.resize(800, 700)
            layout = QVBoxLayout(dialog)

            fig = Figure(figsize=(8, 7), facecolor='#1E1E2E')
            ax = fig.add_subplot(111)
            colors = cm.Set3.colors[:len(categories)]
            wedges, texts, autotexts = ax.pie(
                counts,
                labels=categories,
                autopct='%1.1f%%',
                textprops=dict(color="white", fontsize=12),
                colors=colors,
                pctdistance=0.85,
                wedgeprops=dict(width=0.4, edgecolor='#1E1E2E')
            )
            for autotext in autotexts:
                autotext.set_fontsize(11)
                autotext.set_color('white')
            ax.axis('equal')
            ax.set_title("Распределение по категориям", color="white", fontsize=16, pad=20)
            fig.tight_layout()

            canvas = FigureCanvasQTAgg(fig)
            canvas.setStyleSheet("background-color: transparent;")
            layout.addWidget(canvas)
            dialog.exec()

        except Exception as e:
            self._show_error(f"Ошибка графика: {e}")

    def _build_network_graph(self) -> None:
        if not self._current_result or not self._current_result.transactions:
            self._show_error("Нет данных для графа связей")
            return

        try:
            import networkx as nx
            from collections import Counter, defaultdict
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib import cm
            from matplotlib import colors as mcolors
            from matplotlib.patches import Patch

            G = nx.DiGraph()
            main_addr = self._current_result.address.lower()
            analysis_service = self._data_service._analysis_service
            counterparty_category_counts: dict[str, Counter[str]] = defaultdict(Counter)
            for tx in self._current_result.transactions:
                if "in_msg" in tx or "out_msgs" in tx:
                    in_msg = tx.get("in_msg")
                    if isinstance(in_msg, dict):
                        f_adr = in_msg.get("source", "") or main_addr
                        t_adr = in_msg.get("destination", "") or main_addr
                        if f_adr and t_adr and f_adr != "-" and t_adr != "-":
                            G.add_edge(f_adr.lower(), t_adr.lower())
                    out_msgs = tx.get("out_msgs", [])
                    if isinstance(out_msgs, list):
                        for om in out_msgs:
                            if isinstance(om, dict):
                                f_adr = om.get("source", "") or main_addr
                                t_adr = om.get("destination", "") or main_addr
                                if f_adr and t_adr and f_adr != "-" and t_adr != "-":
                                    G.add_edge(f_adr.lower(), t_adr.lower())
                else:
                    f_adr = str(tx.get("from", "")).lower()
                    t_adr = str(tx.get("to", "")).lower()
                    if f_adr and t_adr and f_adr != "-" and t_adr != "-":
                        G.add_edge(f_adr, t_adr)

                # Сбор категории для контрагентов (для раскраски узлов)
                try:
                    category_label = analysis_service.classify_transaction(tx, main_addr).value
                except Exception:  # noqa: BLE001
                    category_label = "Прочее"

                tx_from = ""
                tx_to = ""
                if isinstance(tx, dict) and ("in_msg" in tx or "out_msgs" in tx):
                    in_msg = tx.get("in_msg") if isinstance(tx.get("in_msg"), dict) else {}
                    tx_from = str(in_msg.get("source") or in_msg.get("src") or "").lower()
                    tx_to = str(in_msg.get("destination") or in_msg.get("dest") or "").lower()
                else:
                    tx_from = str(tx.get("from", "")).lower()
                    tx_to = str(tx.get("to", "")).lower()

                if tx_from and tx_to and tx_from != "-" and tx_to != "-":
                    if tx_from == main_addr and tx_to != main_addr:
                        counterparty_category_counts[tx_to][category_label] += 1
                    elif tx_to == main_addr and tx_from != main_addr:
                        counterparty_category_counts[tx_from][category_label] += 1

            if G.number_of_nodes() == 0:
                self._show_error("Недостаточно данных для построения графа связей")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("Граф связей")
            dialog.resize(900, 800)
            layout = QVBoxLayout(dialog)

            fig = Figure(figsize=(10, 9), facecolor='#1E1E2E')
            ax = fig.add_subplot(111)
            node_count = G.number_of_nodes()
            if node_count > 200:
                pos = nx.spring_layout(G, k=0.5, iterations=30, seed=42)
            else:
                pos = nx.spring_layout(G, k=0.3, iterations=50, seed=42)

            node_to_category: dict[str, str] = {}
            for node, counts in counterparty_category_counts.items():
                if counts:
                    node_to_category[node] = counts.most_common(1)[0][0]

            categories_in_graph = sorted({cat for cat in node_to_category.values() if cat})
            cmap = cm.get_cmap("tab20", max(1, len(categories_in_graph)))
            category_color_map: dict[str, str] = {}
            for idx, cat in enumerate(categories_in_graph):
                category_color_map[cat] = mcolors.to_hex(cmap(idx))

            node_colors: list[str] = []
            node_sizes: list[int] = []
            for n in G.nodes():
                if str(n).lower() == main_addr:
                    node_colors.append('#ff0055')
                    node_sizes.append(150)
                else:
                    cat = node_to_category.get(str(n).lower())
                    node_colors.append(category_color_map.get(cat, '#00aabb'))
                    node_sizes.append(50)

            nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes, node_color=node_colors, alpha=0.9)
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color='#ffffff', alpha=0.15, arrows=True, arrowsize=8, width=0.5)
            if node_count <= 50:
                labels = {n: (n[:6] + "..." + n[-4:] if len(str(n)) > 12 else str(n)) for n in G.nodes()}
                nx.draw_networkx_labels(G, pos, labels, font_size=7, font_color='#ffffff', ax=ax)

            ax.set_facecolor('#1E1E2E')
            ax.axis('off')

            legend_items: list[Patch] = [Patch(color="#ff0055", label="Кошелек")]
            if categories_in_graph:
                top_cats = [
                    cat for cat, _ in Counter(node_to_category.values()).most_common(8)
                    if cat in category_color_map
                ]
                for cat in top_cats:
                    legend_items.append(Patch(color=category_color_map[cat], label=cat))

            if len(legend_items) > 1:
                legend = ax.legend(
                    handles=legend_items,
                    loc="lower left",
                    fontsize=8,
                    frameon=False,
                )
                for text in legend.get_texts():
                    text.set_color("white")

            fig.tight_layout()

            canvas = FigureCanvasQTAgg(fig)
            canvas.setStyleSheet("background-color: transparent;")
            layout.addWidget(canvas)
            dialog.exec()

        except Exception as e:
            self._show_error(f"Ошибка графа связей: {e}")

    def _show_error(self, error_message: str) -> None:
        self._error_label.setText(
            "Не удалось проанализировать кошелек.\n"
            "Проверьте адрес или API.\n"
            f"Детали: {error_message}"
        )
        self._stack.setCurrentWidget(self._page_error)

    def _go_to_init(self) -> None:
        self._stack.setCurrentWidget(self._page_init)

    def _not_implemented_action(self) -> None:
        QMessageBox.information(
            self,
            "Модуль в разработке",
            "Эта функция пока не реализована.",
        )

    def _animate_analyze_button(self) -> None:
        self._pulse_state = not self._pulse_state
        if self._pulse_state:
            self._analyze_button.setStyleSheet(
                "QPushButton#Primary {"
                "background-color: rgba(240, 56, 114, 255);"
                "border: 1px solid rgba(255, 193, 217, 255);"
                "font-size: 15px; padding: 11px 18px; }"
            )
        else:
            self._analyze_button.setStyleSheet(
                "QPushButton#Primary {"
                "background-color: rgba(211, 35, 79, 230);"
                "border: 1px solid rgba(255, 145, 180, 230);"
                "font-size: 15px; padding: 11px 18px; }"
            )

if __name__ == "__main__":
    from app.config.settings import load_settings
    from app.data.api.explorer_client import ExplorerApiClient
    from app.data.repositories.transaction_repository import TransactionRepository
    from app.services.wallet_analysis_service import WalletAnalysisService
    from PySide6.QtWidgets import QApplication

    settings = load_settings()
    qt_app = QApplication(sys.argv)
    
    api_client = ExplorerApiClient(settings=settings)
    repository = TransactionRepository(output_dir=settings.output_dir)
    analysis_service = WalletAnalysisService()
    wallet_data_service = WalletDataService(
        api_client=api_client, 
        repository=repository,
        analysis_service=analysis_service
    )

    main_window = MainWindow(data_service=wallet_data_service)
    main_window.show()
    sys.exit(qt_app.exec())
