from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QFont,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QSplitter,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
import requests

from jparty.style import MyLabel, CARDPAL


class QuestionWidget(QWidget):
    def __init__(self, question, parent=None):
        super().__init__(parent)
        self.question = question
        self.setAutoFillBackground(True)

        self.main_layout = QVBoxLayout()
        self.question_label = MyLabel(question.text.upper(), self.startFontSize, self)

        self.question_label.setFont(QFont("ITC_ Korinna"))
        self.main_layout.addWidget(self.question_label)
        self.setLayout(self.main_layout)

        self.setPalette(CARDPAL)
        self.show()

    def startFontSize(self):
        return self.width() * 0.05


class ImageWidget(QWidget):
    def __init__(self, image_url, parent=None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout()
        self.image_label = QLabel(self)

        # Placeholder while loading the image
        self.image_label.setText("Loading image...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Fetch and load the image
        self.fetch_image(image_url)

        # Buttons for "Accept" and "Reject"
        self.buttons_layout = QHBoxLayout()
        self.accept_button = QPushButton("Accept", self)
        self.reject_button = QPushButton("Reject", self)
        self.buttons_layout.addWidget(self.accept_button)
        self.buttons_layout.addWidget(self.reject_button)

        # Combine the image and buttons
        self.main_layout.addWidget(self.image_label, 1)
        self.main_layout.addLayout(self.buttons_layout)
        self.setLayout(self.main_layout)

    def fetch_image(self, url):
        """Fetch image from the URL using QNetworkAccessManager."""
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self.on_image_downloaded)
        request = QNetworkRequest(QUrl(url))
        self.network_manager.get(request)

    def on_image_downloaded(self, reply):
        """Load the downloaded image into the QLabel."""
        if reply.error() == reply.NetworkError.NoError:
            pixmap = QPixmap()
            pixmap.loadFromData(reply.readAll())
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.image_label.setText("Failed to load image.")

class HostQuestionWidget(QuestionWidget):
    def __init__(self, question, parent=None):
        super().__init__(question, parent)

        self.question_label.setText(question.text)
        self.main_layout.setStretchFactor(self.question_label, 6)
        self.main_layout.addSpacing(self.main_layout.contentsMargins().top())
        self.answer_label = MyLabel(question.answer, self.startFontSize, self)
        self.answer_label.setFont(QFont("ITC_ Korinna"))
        self.main_layout.addWidget(self.answer_label, 1)

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        qp.setPen(QPen(QColor("white")))
        line_y = self.main_layout.itemAt(1).geometry().top()
        qp.drawLine(0, line_y, self.width(), line_y)


class HostImageQuestionWidget(QWidget):
    def __init__(self, question, parent=None):
        super().__init__(parent)

        # Main horizontal layout to divide the screen
        self.main_horizontal_layout = QHBoxLayout(self)
        self.setLayout(self.main_horizontal_layout)

        # Left section: Question and Answer
        self.left_layout = QVBoxLayout()
        self.question_label = QLabel(question.text.upper(), self)
        self.question_label.setFont(QFont("ITC Korinna", 16))
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_layout.addWidget(self.question_label)

        self.answer_label = QLabel(question.answer, self)
        self.answer_label.setFont(QFont("ITC Korinna", 14))
        self.answer_label.setWordWrap(True)
        self.answer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_layout.addWidget(self.answer_label)

        self.left_layout.addStretch()  # Add stretch to center content vertically

        # Right section: Image and Buttons
        self.right_layout = QVBoxLayout()
        self.image_label = QLabel(self)
        self.image_label.setText("Loading image...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid black;")  # For visibility
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        self.right_layout.addWidget(self.image_label)

        # Buttons
        self.buttons_layout = QHBoxLayout()
        self.accept_button = QPushButton("Accept", self)
        self.reject_button = QPushButton("Reject", self)
        self.buttons_layout.addWidget(self.accept_button)
        self.buttons_layout.addWidget(self.reject_button)
        self.right_layout.addLayout(self.buttons_layout)

        self.right_layout.addStretch()  # Add stretch to center content vertically

        # Add the left and right sections to the main horizontal layout
        self.main_horizontal_layout.addLayout(self.left_layout, 2)  # Left gets more space
        self.main_horizontal_layout.addLayout(self.right_layout, 1)  # Right gets less space

        # Fetch and display the image asynchronously
        image_url = search_wikimedia_image(question.answer)
        self.fetch_image(image_url)

    def fetch_image(self, url):
        """Fetch and display the image from the given URL."""
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self.on_image_downloaded)
        request = QNetworkRequest(QUrl(url))
        self.network_manager.get(request)

    def on_image_downloaded(self, reply):
        """Load the downloaded image into the QLabel."""
        if reply.error() == reply.NetworkError.NoError:
            pixmap = QPixmap()
            pixmap.loadFromData(reply.readAll())
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.width(), self.image_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.image_label.setText("Failed to load image.")

def search_wikimedia_image(query):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageimages",
        "titles": query,
        "pithumbsize": 500,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if "thumbnail" in page_data:
                return page_data["thumbnail"]["source"]
        return "No image found."
    else:
        return f"Error: {response.status_code}"


class DailyDoubleWidget(QuestionWidget):
    def __init__(self, question, parent=None):
        super().__init__(question, parent)
        self.question_label.setVisible(False)

        self.dd_label = MyLabel("DAILY<br/>DOUBLE!", self.startDDFontSize, self)
        self.main_layout.replaceWidget(self.question_label, self.dd_label)

    def startDDFontSize(self):
        return self.width() * 0.2

    def show_question(self):
        self.main_layout.replaceWidget(self.dd_label, self.question_label)
        self.dd_label.deleteLater()
        self.dd_label = None
        self.question_label.setVisible(True)


class HostDailyDoubleWidget(HostQuestionWidget, DailyDoubleWidget):
    def __init__(self, question, parent=None):
        super().__init__(question, parent)
        self.answer_label.setVisible(False)

        self.main_layout.setStretchFactor(self.dd_label, 6)
        self.hint_label = MyLabel(
            "Click the player below who found the Daily Double",
            self.startFontSize,
            self,
        )
        self.main_layout.replaceWidget(self.answer_label, self.hint_label)
        self.main_layout.setStretchFactor(self.hint_label, 1)

    def show_question(self):
        super().show_question()
        self.main_layout.replaceWidget(self.hint_label, self.answer_label)
        self.hint_label.deleteLater()
        self.hint_label = None
        self.answer_label.setVisible(True)


class FinalJeopardyWidget(QuestionWidget):
    def __init__(self, question, parent=None):
        super().__init__(question, parent)
        self.question_label.setVisible(False)

        self.category_label = MyLabel(
            question.category, self.startCategoryFontSize, self
        )
        self.main_layout.replaceWidget(self.question_label, self.category_label)

    def startCategoryFontSize(self):
        return self.width() * 0.1

    def show_question(self):
        self.main_layout.replaceWidget(self.category_label, self.question_label)
        self.category_label.deleteLater()
        self.category_label = None
        self.question_label.setVisible(True)


class HostFinalJeopardyWidget(FinalJeopardyWidget, HostQuestionWidget):
    def __init__(self, question, parent):
        super().__init__(question, parent)
        self.answer_label.setVisible(False)

        self.main_layout.setStretchFactor(self.question_label, 6)
        self.hint_label = MyLabel(
            "Waiting for all players to wager...", self.startFontSize, self
        )
        self.main_layout.replaceWidget(self.answer_label, self.hint_label)
        self.main_layout.setStretchFactor(self.hint_label, 1)

    def hide_hint(self):
        self.hint_label.setVisible(True)

    def show_question(self):
        super().show_question()
        self.main_layout.replaceWidget(self.hint_label, self.answer_label)
        self.hint_label.deleteLater()
        self.hint_label = None
        self.answer_label.setVisible(True)
