import sys
from pathlib import Path

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
except ModuleNotFoundError as exc:
    raise SystemExit(
        "PySide6 is not installed for this Python interpreter. "
        "Install dependencies with: python -m pip install -r requirements.txt"
    ) from exc

from app.config.settings import load_settings
from app.data.api.explorer_client import ExplorerApiClient
from app.data.repositories.transaction_repository import TransactionRepository
from app.services.wallet_data_service import WalletDataService
from app.services.wallet_analysis_service import WalletAnalysisService
from app.ui.views.main_window import MainWindow


def main() -> None:
    settings = load_settings()

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Crypto Wallet Analyzer")

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
    QTimer.singleShot(0, main_window.raise_)
    QTimer.singleShot(0, main_window.activateWindow)

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
