from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QFont,
    QPixmap,
    QKeyEvent
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QSplitter,
    QSizePolicy,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QObject, QEvent
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
import requests

from jparty.style import MyLabel, CARDPAL


class QuestionWidget(QWidget):
    def __init__(self, question, parent=None):
        super().__init__(parent)
        self.question = question
        self.setAutoFillBackground(True)
        text_only_question = self.isQuestionTypeTextOnly()

        self.main_layout = QVBoxLayout()
        self.question_label = MyLabel(
            question.text.upper() if text_only_question else self.question.image_url,
            self.startFontSize,
            self,
            not text_only_question
        )

        self.question_label.setFont(QFont("ITC_ Korinna"))
        self.main_layout.addWidget(self.question_label)
        self.setLayout(self.main_layout)

        self.setPalette(CARDPAL)
        self.show()

    def startFontSize(self):
        return self.width() * 0.05
    
    def isQuestionTypeTextOnly(self):
        """Check if visual clues have been saved for the question"""
        if self.question.image and self.question.image_url is not None:
            return False
        else:
            return True

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

    def isQuestionTypeTextOnly(self):
        """Host always see only text"""
        return True 


class HostImageQuestionWidget(QWidget):
    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.question = game.active_question
        # Main horizontal layout to divide the screen
        self.main_horizontal_layout = QHBoxLayout(self)
        self.setLayout(self.main_horizontal_layout)

        # Left section: Question and Answer
        self.left_layout = QVBoxLayout()
        self.question_label = QLabel(self.question.text.upper(), self)
        self.question_label.setFont(QFont("ITC Korinna", 16))
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_layout.addWidget(self.question_label)

        self.answer_label = QLabel(self.question.answer, self)
        self.answer_label.setFont(QFont("ITC Korinna", 14))
        self.answer_label.setWordWrap(True)
        self.answer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_layout.addWidget(self.answer_label)

        self.left_layout.addStretch()  # Add stretch to center content vertically

        # Right section: Image, Text Input, and Buttons
        self.right_layout = QVBoxLayout()

        # Image Label
        self.image_label = QLabel(self)
        self.image_label.setText("Loading image...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid black;")  # For visibility
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        self.right_layout.addWidget(self.image_label)

        # Textbox for input with debounce functionality
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.debounced_input_changed)

        self.textbox = QLineEdit(self)
        self.textbox.setPlaceholderText("Enter image url or search query to wikimedia...")
        self.textbox.textChanged.connect(self.start_debounce_timer)
        self.right_layout.addWidget(self.textbox)

        # Buttons
        self.buttons_layout = QHBoxLayout()
        self.start_button = QPushButton("Accept Image", self)
        self.start_button.setEnabled(True)
        self.start_button.clicked.connect(self.on_start_clicked)

        self.reject_button = QPushButton("No Image Necessary", self)
        self.reject_button.clicked.connect(self.on_reject_clicked)

        self.buttons_layout.addWidget(self.start_button)
        self.buttons_layout.addWidget(self.reject_button)
        self.right_layout.addLayout(self.buttons_layout)

        self.right_layout.addStretch()  # Add stretch to center content vertically

        # Add the left and right sections to the main horizontal layout
        self.main_horizontal_layout.addLayout(self.left_layout, 2)  # Left gets more space
        self.main_horizontal_layout.addLayout(self.right_layout, 1)  # Right gets less space

        # First guess of image is wikimedia result for question answer
        self.image_url = search_wikimedia_image(self.question.answer)
        self.fetch_image(self.image_url)

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

    def start_debounce_timer(self, text):
        """Start or reset the debounce timer when the text changes."""
        self.debounce_timer.start(1000)  # 1-second debounce delay

    def debounced_input_changed(self):
        """Handle debounced text input."""
        input_text = self.textbox.text()
        if input_text.startswith("https://"):
            self.image_url = input_text
        else:
            self.image_url = search_wikimedia_image(input_text)
        self.question.image_url = self.image_url
        self.fetch_image(self.image_url)

        self.update_start_button(input_text)

    def update_start_button(self, input_text):
        """Enable or disable the Start button based on input."""
        if input_text.strip():  # Check if input is not empty
            self.start_button.setEnabled(True)
        else:
            self.start_button.setEnabled(False)

    def on_start_clicked(self):
        """Handle Start button click."""
        self.game.accept_image()

    def on_reject_clicked(self):
        """Handle Reject button click."""
        self.game.no_image_needed()

def search_wikimedia_image(query):
    url = "https://en.wikipedia.org/w/api.php"
    header = {
        "User-Agent": "J-NoChance/0.1 (trevorspreadbury@gmail.com)"
    }
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageimages",
        "titles": query,
        "pithumbsize": 500,
    }
    response = requests.get(url, params=params, headers=header)
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
