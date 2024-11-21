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
from pathlib import Path
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
    """Widget to display and manage an image-based question for a game."""

    def __init__(self, game, parent=None):
        """
        Initialize the widget with game state and setup UI components.

        Args:
            game: The game instance containing the active question.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.game = game
        self.question = game.active_question
        self.current_pixmap = None
        self.image_url = self.get_initial_image_url()

        self.setup_ui()
        self.fetch_image(self.image_url)

    def setup_ui(self):
        """Set up the UI components and layout."""
        self.setup_main_layout()
        self.setup_left_layout()
        self.setup_right_layout()

    def setup_main_layout(self):
        """Create the main layout dividing the screen into two sections."""
        self.main_horizontal_layout = QHBoxLayout(self)
        self.setLayout(self.main_horizontal_layout)

    def setup_left_layout(self):
        """Create the left section with the question and answer display."""
        self.left_layout = QVBoxLayout()
        self.setup_question_label()
        self.setup_answer_label()
        self.left_layout.addStretch()
        self.main_horizontal_layout.addLayout(self.left_layout, 1)

    def setup_question_label(self):
        """Create and configure the question label."""
        self.question_label = QLabel(self.question.text.upper(), self)
        self.question_label.setFont(QFont("ITC Korinna", 16))
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_layout.addWidget(self.question_label)

    def setup_answer_label(self):
        """Create and configure the answer label."""
        self.answer_label = QLabel(self.question.answer, self)
        self.answer_label.setFont(QFont("ITC Korinna", 14))
        self.answer_label.setWordWrap(True)
        self.answer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_layout.addWidget(self.answer_label)

    def setup_right_layout(self):
        """Create the right section with image display, input, and buttons."""
        self.right_layout = QVBoxLayout()
        self.setup_image_label()
        self.add_image_search_box()
        self.add_buttons()
        self.right_layout.addStretch()
        self.main_horizontal_layout.addLayout(self.right_layout, 2)

    def setup_image_label(self):
        """Create and configure the image display label."""
        self.image_label = QLabel("Loading image...", self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid black;")
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        self.right_layout.addWidget(self.image_label)

    def add_image_search_box(self):
        """Add the image search input box with debouncing."""
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.debounced_input_changed)

        self.textbox = QLineEdit(self)
        self.textbox.setPlaceholderText("Enter image URL or search query...")
        self.textbox.textChanged.connect(self.start_debounce_timer)
        self.right_layout.addWidget(self.textbox)

    def add_buttons(self):
        """Add buttons to accept or reject the image."""
        self.buttons_layout = QHBoxLayout()

        self.start_button = QPushButton("Accept Image", self)
        self.start_button.clicked.connect(self.on_accept_image_clicked)
        self.buttons_layout.addWidget(self.start_button)

        self.reject_button = QPushButton("No Image Necessary", self)
        self.reject_button.clicked.connect(self.on_no_image_needed_clicked)
        self.buttons_layout.addWidget(self.reject_button)

        self.right_layout.addLayout(self.buttons_layout)

    def get_initial_image_url(self):
        """Retrieve the initial image URL for the question."""
        return self.question.image_url or search_wikimedia_image(self.question.answer)

    def fetch_image(self, path_or_url):
        """Fetch the image from a local path or URL."""
        if Path(path_or_url).exists():
            self.load_image_from_file(path_or_url)
        else:
            self.load_image_from_url(path_or_url)

    def load_image_from_file(self, file_path):
        """Load an image from a local file and display it."""
        pixmap = QPixmap(file_path)
        self.handle_pixmap_load(pixmap)

    def load_image_from_url(self, url):
        """Download and load an image from a URL."""
        self.network_manager = QNetworkAccessManager(self.image_label)
        self.network_manager.finished.connect(self.on_image_downloaded)
        request = QNetworkRequest(QUrl(url))
        self.network_manager.get(request)

    def on_image_downloaded(self, reply):
        """Handle the downloaded image and display it."""
        if reply.error() == reply.NetworkError.NoError:
            pixmap = QPixmap()
            pixmap.loadFromData(reply.readAll())
            self.handle_pixmap_load(pixmap)
        else:
            self.image_label.setText("Failed to load image.")

    def handle_pixmap_load(self, pixmap):
        """Update the image display with the given pixmap."""
        if not pixmap.isNull():
            self.current_pixmap = pixmap
            self.update_image_display()
        else:
            self.image_label.setText("Failed to load image.")

    def start_debounce_timer(self, _):
        """Restart the debounce timer for text input."""
        self.debounce_timer.start(1000)

    def debounced_input_changed(self):
        """Update the image URL or query after debounce."""
        input_text = self.textbox.text()
        self.image_url = (
            input_text if input_text.startswith("https://")
            else search_wikimedia_image(input_text)
        )
        self.fetch_image(self.image_url)
        self.update_accept_button(input_text)

    def update_accept_button(self, input_text):
        """Enable or disable the accept button based on input."""
        self.start_button.setEnabled(bool(input_text.strip()))

    def resizeEvent(self, event):
        """Handle resize events to update the image display."""
        super().resizeEvent(event)
        self.update_image_display()

    def update_image_display(self):
        """Resize and display the current image."""
        if self.current_pixmap:
            scaled_pixmap = self.current_pixmap.scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled_pixmap)

    def on_accept_image_clicked(self):
        """Handle accept image button click."""
        self.question.image = True
        self.question.image_url = self.image_url
        self.game.accept_image()

    def on_no_image_needed_clicked(self):
        """Handle reject image button click."""
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
