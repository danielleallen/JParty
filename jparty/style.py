from PyQt6.QtWidgets import QStyle, QCommonStyle
from PyQt6.QtGui import QPalette, QColor, QPixmap
from PyQt6.QtCore import QRect, Qt

from jparty.utils import DynamicLabel, add_shadow
from jparty.constants import REPO_ROOT


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


class MyLabel(DynamicLabel):
    def __init__(self, text, initialSize, parent=None, image=False):
        super().__init__(text, initialSize, parent)
        if not image:
            self.font().setBold(True)
            self.setWordWrap(True)
        else:
            print("image is ", image)
            self.question_image = QPixmap(str(REPO_ROOT / "jparty" / "data" / "up-dixie.jpg"))
            # self.setGeometry(QRect(0, 0, 841, 511))
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
