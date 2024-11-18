from PyQt6.QtWidgets import QStyle, QCommonStyle
from PyQt6.QtGui import QPalette, QColor, QPixmap
from PyQt6.QtCore import Qt, QRect, QByteArray

import requests

from jparty.utils import DynamicLabel, add_shadow


class JPartyStyle(QCommonStyle):
    PM_dict = {
        QStyle.PixelMetric.PM_LayoutBottomMargin: 0,
        QStyle.PixelMetric.PM_LayoutLeftMargin: 0,
        QStyle.PixelMetric.PM_LayoutRightMargin: 0,
        QStyle.PixelMetric.PM_LayoutTopMargin: 0,
        QStyle.PixelMetric.PM_LayoutHorizontalSpacing: 0,
        QStyle.PixelMetric.PM_LayoutVerticalSpacing: 0,
    }
    SH_dict = {
        QStyle.StyleHint.SH_Button_FocusPolicy: 0,
    }

    def pixelMetric(self, key, *args, **kwargs):
        return JPartyStyle.PM_dict.get(key, super().pixelMetric(key, *args, **kwargs))

    def styleHint(self, key, *args, **kwargs):
        return JPartyStyle.SH_dict.get(key, super().styleHint(key, *args, **kwargs))

def fetch_image_from_url(url: str) -> QPixmap:
    """
    Fetches an image from the given URL and converts it to a QPixmap.
    """
    try:
        # Fetch image data from the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for failed requests
        
        # Convert image data to QPixmap
        image_data = QByteArray(response.content)
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        
        return pixmap
    except Exception as e:
        print(f"Failed to fetch or load the image: {e}")
        return QPixmap()  # Return an empty pixmap on failure

class MyLabel(DynamicLabel):
    def __init__(self, text, initialSize, parent=None, image=False):
        super().__init__(text, initialSize, parent)
        if not image:
            self.font().setBold(True)
            self.setWordWrap(True)
        else:
            question_image = text
            self.question_image = fetch_image_from_url(str(question_image))
            self.setText("")
            self.setPixmap(self.question_image)
            self.setScaledContents(True)
            self.setObjectName("photo")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        add_shadow(self)

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor("white"))
        self.setPalette(palette)

        self.show()


WINDOWPAL = QPalette()
WINDOWPAL.setColor(QPalette.ColorRole.Base, QColor("white"))
WINDOWPAL.setColor(QPalette.ColorRole.WindowText, QColor("black"))
WINDOWPAL.setColor(QPalette.ColorRole.Text, QColor("black"))
WINDOWPAL.setColor(QPalette.ColorRole.Window, QColor("#fefefe"))
WINDOWPAL.setColor(QPalette.ColorRole.Button, QColor("#e6e6e6"))
WINDOWPAL.setColor(QPalette.ColorRole.Button, QColor("#e6e6e6"))
WINDOWPAL.setColor(QPalette.ColorRole.ButtonText, QColor("black"))
WINDOWPAL.setColor(
    QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#d0d0d0")
)

JBLUE = QColor("#1010a1")
DARKBLUE = QColor("#0b0b74")
CARDPAL = QPalette()
CARDPAL.setColor(QPalette.ColorRole.Window, JBLUE)
CARDPAL.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
