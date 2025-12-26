import logging
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .mainwindow import MainWindow
from .utils import run_all_checks

logging.basicConfig(
    filename="pymsort.log",
    encoding="utf-8",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
)

logger = logging.getLogger(__name__)


def main():
    app = QApplication(sys.argv)

    # Set application metadata and icon (must be done before creating widgets on macOS)
    app.setApplicationName("pymsort")
    app.setApplicationDisplayName("Python Media Sorter")
    icon_path = Path(__file__).parent.parent.parent / "ressources" / "appicon.png"
    app.setWindowIcon(QIcon(str(icon_path)))

    # Run startup checks
    logger.info("Running startup checks...")
    all_passed, messages = run_all_checks()

    # Display results
    check_message = "\n".join(messages)
    logger.info(f"Startup checks:\n{check_message}")

    if not all_passed:
        QMessageBox.critical(
            None,
            "Startup Check Failed",
            f"Some required tools are missing:\n\n{check_message}\n\n"
            "Please install the missing tools and place them in your system PATH or application directory.",
        )
        return 1

    # Show informational dialog with check results
    QMessageBox.information(
        None,
        "Startup Checks Passed",
        f"All required tools are available:\n\n{check_message}",
    )

    window = MainWindow()
    window.resize(1024, 384)
    window.show()
    app.exec()
    return 0


if __name__ == "__main__":
    logger.info("Starting pymsort")
    exit_code = main()
    logger.info(f"Exiting pymsort with code {exit_code}")
    sys.exit(exit_code)
