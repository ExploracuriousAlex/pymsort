import logging

from PySide6 import QtWidgets

from .mediafiles_tablemodel import MediaFilesTableModel
from .services import ExifToolService, MediaInfoService

logger = logging.getLogger(__name__)


class MediaFilesTableView(QtWidgets.QTableView):
    def __init__(self, exiftool_service=None, media_info_service=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use provided services or create new ones
        if exiftool_service is None:
            exiftool_service = ExifToolService()
        if media_info_service is None:
            media_info_service = MediaInfoService()

        self.setModel(MediaFilesTableModel(exiftool_service, media_info_service))
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        self.model().dropEvent(event.mimeData().urls())
