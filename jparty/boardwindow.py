from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QImage,
    QColor,
    QFont,
    QPalette,
    QPixmap,
    QTextDocument,
    QTextOption,
    QGuiApplication,
    QFontMetrics,
    QTransform
)
from PyQt6.QtWidgets import *  # QWidget, QApplication, QDesktopWidget, QPushButton
from PyQt6.QtCore import (
    Qt,
    QRectF,
    QRect,
    QPoint,
    QPointF,
    QTimer,
    QRect,
    QSize,
    QSizeF,
)
from PyQt6.sip import delete


from .game import game_params as gp
from .utils import resource_path
from .constants import DEBUG
import time
import threading
import re
import logging
from base64 import urlsafe_b64decode

margin = 50
n = 8  # even integer
FONTSIZE = 10

BLUE = QColor("#031591")
HINTBLUE = QColor("#041ec8")
YELLOW = QColor("#ffcc00")
RED = QColor("#ff0000")
BLACK = QColor("#000000")
GREY = QColor("#505050")
WHITE = QColor("#ffffff")
GREEN = QColor("#33cc33")


CARDPAL = QPalette()
CARDPAL.setColor(QPalette.ColorRole.Window, BLUE)
CARDPAL.setColor(QPalette.ColorRole.WindowText, WHITE)

BOARDSIZE = (6, 6)

CATFONT = QFont()
CATFONT.setBold(True)
CATFONT.setPointSize(24)
CATPEN = QPen(WHITE)

MONFONT = QFont(CATFONT)
MONFONT.setPointSize(50)
MONPEN = QPen(YELLOW)
TEXTPADDING = 20

QUFONT = QFont()
QUFONT.setPointSize(70)
QUMARGIN = 50

NAMEHEIGHT = 50
NAMEFONT = QFont()
NAMEFONT.setPointSize(20)
NAMEPEN = QPen(WHITE)
SCOREFONT = QFont()
SCOREFONT.setPointSize(50)
SCOREPEN = QPen(WHITE)
HOLEPEN = QPen(RED)
HIGHLIGHTPEN = QPen(BLUE)
HIGHLIGHTBRUSH = QBrush(WHITE)
HINTBRUSH = QBrush(HINTBLUE)

CORRECTBRUSH = QBrush(GREEN)
INCORRECTBRUSH = QBrush(RED)

LIGHTPEN = QPen(GREY)
LIGHTBRUSH = QBrush(RED)

BORDERWIDTH = 10
BORDERPEN = QPen(BLACK)
BORDERPEN.setWidth(BORDERWIDTH)
DIVIDERBRUSH = QBrush(WHITE)
DIVIDERWIDTH = 20

FILLBRUSH = QBrush(BLUE)
SCOREHEIGHT = 0.15
ANSWERHEIGHT = 0.15

ANSWERBARS = 30
ANSWERSECS = 5

FINALANSWERHEIGHT = 0.6


def updateUI(f):
    return f
    # def wrapper(self, *args):
    #     ret = f(self, *args)
    #     self.game.update()
    #     return ret

    # return wrapper


def autofitsize(text, font, rect, start=None, stepsize=2):
    if start:
        font.setPointSize(start)

    size = font.pointSize()
    flags = Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter

    def fullrect(font, text=text, flags=flags):
        fm = QFontMetrics(font)
        return fm.boundingRect(rect, flags, text)

    newrect = fullrect(font)
    if not rect.contains(newrect):
        while size > 0:
            size -= stepsize
            font.setPointSize(size)
            newrect = fullrect(font)
            if rect.contains(newrect):
                return font.pointSize()

        logging.warn(f"Nothing fit! (text='{text}')")
        print(f"Nothing fit! (text='{text}')")

    return size

class DynamicLabel(QLabel):
    def __init__(self, text, initialSize, parent=None):
        super().__init__( text, parent )
        self.__initialSize = initialSize


        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    ### These three re-override QLabel's versions
    def sizeHint(self):
        return QSize()

    def initialSize(self):
        if callable(self.__initialSize):
            return self.__initialSize()
        else:
            return self.__initialSize


    def minimizeSizeHint(self):
        return QSize()

    def heightForWidth(self, w):
        return -1

    def resizeEvent(self, event):
        if self.size().height() == 0 or self.text() == "":
            return None

        fontsize = autofitsize(self.text(), self.font(), self.rect(), start=self.initialSize())
        font = self.font()
        font.setPointSize(fontsize)
        self.setFont(font)

class MyLabel(DynamicLabel):
    def __init__(self, text, initialSize, parent=None):
        super().__init__(text, initialSize, parent)
        self.setFont( QFont( "Helvetica" ) )
        self.font().setBold(True)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor("black"))
        shadow.setOffset(3)
        self.setGraphicsEffect(shadow)
        self.show()

class PlayerWidget(QWidget):
    aspect_ratio = 0.4
    def __init__(self, player):
        super().__init__()
        self.player = player

        if player.name[:21] == 'data:image/png;base64':
            i = QImage()
            i.loadFromData(urlsafe_b64decode(self.player.name[22:]), "PNG")
            self.signature = QPixmap.fromImage(i)
            self.name_label = DynamicLabel("", 0, self)
        else:
            self.name_label = MyLabel(player.name, self.startNameFontSize, self)
            self.signature = None

        self.score_label = MyLabel("$0", self.startScoreFontSize, self)

        self.resizeEvent(None)
        self.update_score()

        self.highlighted = False

        layout = QVBoxLayout()
        layout.addStretch(4)
        layout.addWidget(self.score_label, 11)
        layout.addStretch(9)
        layout.addWidget(self.name_label, 22)
        layout.addStretch(20)
        layout.setContentsMargins( 0, 0, 0, 0)

        # palette = QPalette()
        # palette.setColor(QPalette.ColorRole.WindowText, WHITE)
        # self.setPalette(palette)

        self.setSizePolicy( QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self.setLayout(layout)

        self.show()

    def sizeHint(self):
        h = self.height()
        return QSize(h * PlayerWidget.aspect_ratio, h)

    def minimumSizeHint(self):
        return self.sizeHint()

    def startNameFontSize(self):
        return self.height() * 0.2

    def startScoreFontSize(self):
        return self.height() * 0.2

    def resizeEvent(self, event):
        if self.size().height() == 0:
            return None

        print(self.minimumSize)
        ## Add signture
        size = self.sizeHint()
        if self.signature is not None:
            self.name_label.setPixmap(
                self.signature.scaled(
                    size.width(), size.height(),
                    transformMode=Qt.TransformationMode.SmoothTransformation,
                )
            )

        self.setContentsMargins( self.width() * 0.1, 0, self.width() * 0.1, 0)

    def __buzz_hint(self, p):
        self.__buzz_hint_players.append(p)
        self.update()
        time.sleep(0.25)
        self.__buzz_hint_players.remove(p)
        self.update()

    def buzz_hint(self, p):
        self.__buzz_hint_thread = threading.Thread(
            target=self.__buzz_hint, args=(p,), name="buzz_hint"
        )
        self.__buzz_hint_thread.start()

    def update_score(self):
        score = self.player.score
        palette = self.score_label.palette()
        if score < 0:
            palette.setColor(QPalette.ColorRole.WindowText, RED)
        else:
            palette.setColor(QPalette.ColorRole.WindowText, WHITE)
        self.score_label.setPalette(palette)

        self.score_label.setText( f"{score:,}" )

    def mousePressEvent(self, event):
        self.adjust_score(self.player)
        self.update_score()

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        # qp.drawPixmap( self.rect(), QPixmap( resource_path("player_background.png") ))
        print(self.rect().width() / self.rect().height())
        qp.setBrush(FILLBRUSH)
        qp.drawRect(self.rect())

        # qp.drawRect(self.name_label.geometry())
        # qp.drawRect(self.score_label.geometry())





class QuestionLabel(QLabel):
    def __init__(self, text, rect, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("color: white;")
        self.setGeometry(QRect(rect))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.font = QFont("Helvetica")
        fontsize = autofitsize(text, self.font, rect, start=72)
        self.font.setPointSize(fontsize)
        self.setFont(self.font)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor("black"))
        shadow.setOffset(3)
        self.setGraphicsEffect(shadow)


class QuestionWidget(QWidget):
    def __init__(self, question, parent=None):
        super().__init__(parent)
        self.question = question

        self.responses_open = False

        # pheight = parent.geometry().height()
        # height = pheight * (1 - SCOREHEIGHT)
        # width = height / CELLRATIO
        self.resize(parent.size())
        # self.move(
        # self.parent().geometry().width() / 2 - self.parent().boardwidget.geometry().width() / 2, 0
        # )
        alex = self.parent().alex

        if alex:
            anheight = ANSWERHEIGHT * self.size().height()
            self.qurect = self.rect().adjusted(
                QUMARGIN, QUMARGIN, -2 * QUMARGIN, -ANSWERHEIGHT * self.size().height(),
            )
            self.anrect = QRect(
                QUMARGIN,
                self.size().height() * (1 - ANSWERHEIGHT),
                self.size().width() - 2 * QUMARGIN,
                ANSWERHEIGHT * self.size().height(),
            )
            self.answer_label = QuestionLabel(question.answer, self.anrect, self)
            text = question.text

        else:
            self.qurect = self.rect().adjusted(
                QUMARGIN, QUMARGIN, -2 * QUMARGIN, -2 * QUMARGIN
            )
            self.anrect = None
            self.answer_label = None

            text = question.text.upper()

        self.question_label = QuestionLabel(text, self.qurect, self)

        self.show()

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)

        qp.setBrush(FILLBRUSH)
        qp.drawRect(self.rect())
        # Show question
        if self.parent().alex:
            anheight = ANSWERHEIGHT * self.size().height()
            qp.drawLine(
                0,
                (1 - ANSWERHEIGHT) * self.size().height(),
                self.size().width(),
                (1 - ANSWERHEIGHT) * self.size().height(),
            )


class DailyDoubleWidget(QuestionWidget):
    def __init__(self, game, parent=None):
        super().__init__(game, parent)
        self.question_label.setVisible(False)
        if self.parent().alex:
            self.answer_label.setVisible(False)

        self.dd_label = QuestionLabel("DAILY<br/>DOUBLE!", self.qurect, self)
        self.dd_label.setFont(QFont("Helvetica", 140))
        self.dd_label.setVisible(True)
        self.update()

    def show_question(self):
        self.question_label.setVisible(True)
        if self.parent().alex:
            self.answer_label.setVisible(True)
        self.dd_label.setVisible(False)


class CardLabel(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)

        self.__margin = 0.1


        self.label = MyLabel(text, self.startFontSize, parent=self)

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, BLUE)
        palette.setColor(QPalette.ColorRole.WindowText, WHITE)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def startFontSize(self):
        return self.height() * 0.3

    def labelRect(self):
        wmargin = int(self.__margin * self.width())
        hmargin = int(self.__margin * self.height())
        return self.rect().adjusted(wmargin, hmargin, -wmargin, -hmargin)

    @property
    def text(self):
        return self.label.text()

    def resizeEvent(self, event):
        if self.height() == 0:
            return None

        self.label.setGeometry(self.labelRect())

# class CardLabel(QLabel):
#     def __init__(self, text, parent=None):
#         super().__init__(text, parent)

#         self.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self.setWordWrap(True)
#         self.__font = QFont("Helvetica")
#         self.__font.setBold(True)
#         self.setFont( self.__font )
#         # self.setAutoFillBackground(True)

#         # font = self.font()
#         # fontsize = autofitsize(self.text, font, self.geometry(), start=self.geometry().height() / 10 )
#         # font.setPointSize(fontsize)
#         # self.label.setFont(font)

#         palette = QPalette()
#         palette.setColor(QPalette.ColorRole.Window, BLUE)
#         palette.setColor(QPalette.ColorRole.WindowText, WHITE)
#         self.setPalette(palette)

#         shadow = QGraphicsDropShadowEffect(self)
#         shadow.setBlurRadius(40)
#         shadow.setColor(QColor("black"))
#         shadow.setOffset(3)
#         self.setGraphicsEffect(shadow)

        # self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)


    # def minimumSizeHint(self):
    #     # parent_height = self.parent().geometry().height()
    #     # height = parent_height * (1-SCOREHEIGHT)
    #     # width = height / CELLRATIO
    #     return QSize(50, 30)

    # def resizeEvent(self, event):
    #     if self.size().height() > 0:
    #         margin = 100 #int(self.width() * 0.1) + 1
    #         smallerrect = self.rect().adjusted(margin, 0, -margin, 0)

    #         fontsize = autofitsize(self.text(), self.__font, smallerrect, start=self.geometry().height()*0.3 )
    #         self.__font.setPointSize(fontsize)
    #         self.setFont(self.__font)


class QuestionCard(CardLabel):
    def __init__(self, game, question):
        self.game = game
        self.question = question
        if not question.complete:
            moneytext = "$" + str(question.value)
        else:
            moneytext = ""
        super().__init__(moneytext)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.WindowText, YELLOW)
        self.setPalette(palette)

    def startFontSize(self):
        return self.height()*0.5

    def mousePressEvent(self, event):
        if not self.question.complete:
            self.game.load_question(self.question)
            self.label.setText("")



class BoardWidget(QWidget):
    cell_ratio = 3/5
    def __init__(self, game, alex, parent=None):
        super().__init__(parent)
        self.game = game
        self.alex = alex

        self.responses_open = False

        self.questionwidget = None
        self.__completed_questions = []

        self.grid_layout = QGridLayout()


        for x in range(self.board.size[0]):
            self.grid_layout.setRowStretch(x, 1.)
        for y in range(self.board.size[1]+1):
            self.grid_layout.setColumnStretch(y, 1.)

        for x in range(self.board.size[0]):
            for y in range(self.board.size[1]+1):

                if y == 0:
                    # Categories
                    label = CardLabel(self.board.categories[x])
                    self.grid_layout.addWidget(label, 0, x)

                else:
                    # Questions
                    q = self.board.get_question(x,y-1)

                    label = QuestionCard(game, q)
                    self.grid_layout.addWidget(label, y, x)

        self.resizeEvent(None)
        self.setLayout(self.grid_layout)

        self.show()

    def resizeEvent(self, event):
        self.grid_layout.setSpacing(self.width() // 150)

    # def paintEvent(self, event):
    #     h = self.geometry().height()
    #     w = self.geometry().width()
    #     qp = QPainter()
    #     qp.begin(self)
    #     qp.setBrush(QBrush(YELLOW))
    #     qp.drawRect(self.rect())

    # def minimumSizeHint(self):
    #     return QSize(self.geometry().width(), 900)

    # @updateUI
    # def resizeEvent(self, event):
    #     print(self.geometry().height())
    #     print(self.parent().geometry().height())
    #     parent = self.parent()
    #     pheight = parent.geometry().height()
    #     height = pheight * (1 - SCOREHEIGHT)
    #     width = height / CELLRATIO
    #     self.resize(width + BORDERWIDTH, height)
    #     print("RESIZE!")


    @property
    def board(self):
        return self.game.current_round

    # def paintEvent(self, event):
    #     return None
    #     qp = QPainter()
    #     qp.begin(self)
    #     qp.setBrush(FILLBRUSH)
    #     parent = self.parent()
    #     pheight = parent.geometry().height()
    #     height = pheight * (1 - SCOREHEIGHT)
    #     width = height / CELLRATIO
    #     if not self.board.final:
    #         # Normal board
    #         for x in range(self.board.size[0]):
    #             for y in range(-1, self.board.size[1]):
    #                 rel_pos = (
    #                     x * self.cellsize[0] + BORDERWIDTH / 2,
    #                     (y + 1) * self.cellsize[1],
    #                 )
    #                 cell = (x, y)
    #                 qp.setPen(BORDERPEN)
    #                 qp.setBrush(FILLBRUSH)
    #                 cell_rect = QRectF(*rel_pos, *self.cellsize)
    #                 text_rect = QRectF(cell_rect)
    #                 text_rect.setX(cell_rect.x() + TEXTPADDING)
    #                 text_rect.setWidth(cell_rect.width() - 2 * TEXTPADDING)
    #                 qp.drawRect(cell_rect)
    #                 if y == -1:
    #                     # Categories
    #                     qp.setPen(CATPEN)
    #                     qp.setFont(CATFONT)
    #                     qp.drawText(
    #                         text_rect,
    #                         Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter,
    #                         self.board.categories[x],
    #                     )
    #                 else:
    #                     # Questions
    #                     q = self.board.get_question(*cell)
    #                     if not q in self.game.completed_questions:
    #                         qp.setPen(MONPEN)
    #                         qp.setFont(MONFONT)
    #                         if not self.board.dj:
    #                             monies = gp.money1
    #                         else:
    #                             monies = gp.money2
    #                         qp.drawText(
    #                             text_rect,
    #                             Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter,
    #                             "$" + str(q.value),
    #                         )
    #     else:
    #         # Final jeopardy
    #         qp.setBrush(FILLBRUSH)
    #         qp.drawRect(self.rect())
    #         qp.setPen(CATPEN)
    #         qp.setFont(QUFONT)

    #         qurect = self.rect().adjusted(
    #             QUMARGIN, QUMARGIN, -2 * QUMARGIN, -2 * QUMARGIN
    #         )

    #         qp.drawText(
    #             qurect,
    #             Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter,
    #             self.board.categories[0],
    #         )

    @updateUI
    def load_question(self, q):
        if q.dd:
            self.questionwidget = DailyDoubleWidget(q, self)
        else:
            logging.info("Question widget!")
            self.questionwidget = QuestionWidget(q, self)

    @updateUI
    def hide_question(self):
        delete(self.questionwidget)

    # def _identify_question(self, event):
    #     dc = self.game.dc

    #     coord = (
    #         event.position().x() // self.cellsize[0],
    #         event.position().y() // self.cellsize[1] - 1,
    #     )
    #     q = self.board.get_question(*coord)
    #     if not q in self.game.completed_questions:
    #         dc.load_question(q)
    #         self.game.load_question(q)

    # def mousePressEvent(self, event):
    #     if not any(
    #         [
    #             self.game.paused,
    #             self.game.active_question,
    #             not self.alex,
    #             self.board.final,
    #         ]
    #     ):
    #         self._identify_question(event)


class LightsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.__light_level = 0
        self.__light_thread = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, WHITE)
        self.setPalette(palette)

    # def sizeHint(self):
    #     return QSize(self.geometry().width(), DIVIDERWIDTH)

    def paintEvent(self, event):
        w = self.geometry().width()
        qp = QPainter()
        qp.begin(self)

        # Light dividers
        num_lights = 9
        light_width = w // num_lights
        light_padding = 3
        ungrouped_rects = [
            QRect(
                light_width * i + light_padding,
                light_padding,
                light_width - 2 * light_padding,
                DIVIDERWIDTH - 2 * light_padding,
            )
            for i in range(num_lights)
        ]
        grouped_rects = [
            [
                rect
                for j, rect in enumerate(ungrouped_rects)
                if abs(num_lights // 2 - j) == i
            ]
            for i in range(5)
        ]
        qp.setBrush(LIGHTBRUSH)
        qp.setPen(LIGHTPEN)
        for i, rects in enumerate(grouped_rects):
            if i < self.__light_level:
                for rect in rects:
                    qp.drawRect(rect)

    def __lights(self):
        self.__light_level = ANSWERSECS + 1
        while (
            self.__light_level > 0 and threading.current_thread() is self.__light_thread
        ):
            self.__light_level -= 1
            self.update()
            time.sleep(1.0)

    def run_lights(self):
        self.__light_thread = threading.Thread(target=self.__lights, name="lights")
        self.__light_thread.start()

    def stop_lights(self):
        self.__light_level = 0


class ScoreBoard(QWidget):
    def __init__(self, display):
        super().__init__(display)

        self.display = display

        self.__buzz_hint_players = []
        self.__buzz_hint_thread = []


        # self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.show()



    def game(self):
        return self.display.game

    # def resizeEvent(self, event):
    #     spacing  = int( self.width() / (len(self.game.players) + 1) * 0.3 )
    #     self.player_layout.setContentsMargins( spacing, 0, spacing, 0)
    #     self.player_layout.setSpacing( spacing )

    def minimumHeight(self):
        return 0.2 * self.width()

    def refreshPlayers(self):
        game = self.game()
        if game is None:
            return None

        player_layout = QHBoxLayout()
        player_layout.addStretch()
        for p in game.players:
            player_layout.addWidget( PlayerWidget(p) )
            player_layout.addStretch()

        player_layout.setContentsMargins( 0, 0, 0, 0)

        self.setLayout(player_layout)

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        qp.drawPixmap( self.rect(), QPixmap( resource_path("pedestal.png") ))


    # def maximumSizeHint(self):
    #     return QSize(self.geometry().width(), 100)

    # def paintEvent(self, event):
    #     return None
    #     h = self.geometry().height()
    #     w = self.geometry().width()
    #     qp = QPainter()
    #     qp.begin(self)

    #     qp.setBrush(DIVIDERBRUSH)
    #     dividerrect = QRectF(0, 0, w, DIVIDERWIDTH)
    #     qp.drawRect(dividerrect)

    #     # Light dividers
    #     num_lights = 9
    #     light_width = w // num_lights
    #     light_padding = 3
    #     ungrouped_rects = [
    #         QRect(
    #             light_width * i + light_padding,
    #             light_padding,
    #             light_width - 2 * light_padding,
    #             DIVIDERWIDTH - 2 * light_padding,
    #         )
    #         for i in range(num_lights)
    #     ]
    #     grouped_rects = [
    #         [
    #             rect
    #             for j, rect in enumerate(ungrouped_rects)
    #             if abs(num_lights // 2 - j) == i
    #         ]
    #         for i in range(5)
    #     ]
    #     qp.setBrush(LIGHTBRUSH)
    #     qp.setPen(LIGHTPEN)
    #     for i, rects in enumerate(grouped_rects):
    #         if i < self.__light_level:
    #             for rect in rects:
    #                 qp.drawRect(rect)

    #     margin = 50
    #     players = self.game.players
    #     sw = w // len(players)

    #     if self.game.current_round.final:
    #         highlighted_players = [p for p in players if p not in self.game.wagered]
    #     else:
    #         highlighted_players = []
    #     ap = self.game.answering_player
    #     if ap:
    #         highlighted_players.append(ap)

    #     for i, p in enumerate(players):
    #         if p.score < 0:
    #             qp.setPen(HOLEPEN)
    #         else:
    #             qp.setPen(SCOREPEN)

    #         qp.setFont(SCOREFONT)
    #         qp.drawText(
    #             self.__scorerect(i),
    #             Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter,
    #             f"{p.score:,}",
    #         )

    #         namerect = QRectF(sw * i, h - NAMEHEIGHT, sw, NAMEHEIGHT)
    #         qp.setFont(NAMEFONT)
    #         qp.setPen(NAMEPEN)
    #         if p in highlighted_players:
    #             qp.setBrush(HIGHLIGHTBRUSH)
    #             qp.drawRect(namerect)
    #             qp.setPen(HIGHLIGHTPEN)
    #         elif p in self.__buzz_hint_players:
    #             qp.setBrush(HINTBRUSH)
    #             qp.drawRect(namerect)

    #         qp.drawText(
    #             namerect,
    #             Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter,
    #             p.name,
    #         )

    # def __scorerect(self, i):
    #     w = self.geometry().width()
    #     h = self.geometry().height()
    #     sw = w // len(self.game.players)
    #     return QRectF(sw * i, DIVIDERWIDTH, sw, h - NAMEHEIGHT - DIVIDERWIDTH)



class FinalAnswerWidget(QWidget):
    def __init__(self, game, parent=None):
        super().__init__()
        self.game = game
        self.__margin = 50
        self.winner = None

        if parent.alex:
            self.setGeometry(
                parent.boardwidget.x(),
                self.__margin,
                parent.boardwidget.width(),
                parent.height() * FINALANSWERHEIGHT,
            )

        else:
            self.setGeometry(
                0, self.__margin, parent.width(), parent.height() * FINALANSWERHEIGHT,
            )
        self.info_level = 0

        self.__light_level = 0
        self.__light_thread = None

        self.show()

    def paintEvent(self, event):
        h = self.geometry().height()
        w = self.geometry().width()
        qp = QPainter()
        qp.begin(self)
        qp.setBrush(FILLBRUSH)
        qp.drawRect(self.rect())

        p = self.game.answering_player
        margin = self.__margin

        qp.setPen(SCOREPEN)
        qp.setFont(SCOREFONT)

        if self.winner:
            winnerrect = QRectF(0, NAMEHEIGHT + 2 * margin, w, 2 * NAMEHEIGHT)
            qp.drawText(
                winnerrect,
                Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter,
                f"{self.winner.name} is the winner!",
            )
            return

        namerect = QRectF(0, margin, w, NAMEHEIGHT)
        qp.drawText(
            namerect, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter, p.name
        )

        if self.info_level > 0:
            answerrect = QRectF(0, NAMEHEIGHT + 2 * margin, w, 2 * NAMEHEIGHT)
            finalanswer = (
                p.finalanswer
                if len(p.finalanswer.replace(" ", "")) > 0
                else "_________"
            )
            qp.drawText(
                answerrect,
                Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter,
                finalanswer,
            )

        if self.info_level > 1:
            wagerrect = QRectF(0, h - NAMEHEIGHT - margin, w, NAMEHEIGHT)
            qp.drawText(
                wagerrect,
                Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter,
                f"{p.wager:,}",
            )



class Borders(object):
    def __init__(self, parent):
        super().__init__()
        self.left  = BorderWidget(parent, -1)
        self.right = BorderWidget(parent,  1)

    def __iter__(self):
        return iter([self.left, self.right])


    def lights(self, val):
        for b in self:
            b.lights(val)

    def arrowhints(self, val):
        for b in self:
            b.arrowhints(val)

    def spacehints(self, val):
        for b in self:
            b.spacehints(val)


class BorderWidget(QWidget):
    def __init__(self, parent=None, d=1):
        super().__init__(parent)
        self.d = d

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.hint_label = QLabel(self)

        # icon_size = 64
        # self.icon_label.setPixmap(
        #     QPixmap(resource_path("space.png")).scaled(
        #         icon_size,
        #         icon_size,
        #         transformMode=Qt.TransformationMode.SmoothTransformation,
        #     )
        # )
        #
        self.space_image = QPixmap(resource_path("space.png"))

        self.layout.addWidget(self.hint_label)
        self.setLayout(self.layout)

        self.show()

    def lights(self, val):
        color = val if WHITE else BLACK
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, color)
        self.setPalette(palette)

    def arrowhints(self, val):
        pass

    def spacehints(self, val):
        if val:
            self.hint_label.setPixmap(
                self.space_image.scaled( self.size(),
                                         Qt.AspectRatioMode.KeepAspectRatio,
                                         transformMode=Qt.TransformationMode.SmoothTransformation
                )
            )
        else:
            self.hint_label.setPixmap(QPixmap())

    def sizeHint(self):
        return QSize()


    # def paintEvent(self, event):
    #     qp = QPainter()
    #     qp.begin(self)
    #     qp.drawRect(self.rect())

        # qp.drawRect(self.name_label.geometry())
        # qp.drawRect(self.score_label.geometry())
    #     self.boardrect = boardrect
    #     margin_size = self.boardrect.x()
    #     self.__answerbarrect = boardrect.adjusted(-ANSWERBARS, 0, ANSWERBARS, 0)

    #     self.__correctrect = QRect(0, 0, margin_size, self.boardrect.height())
    #     self.__incorrectrect = QRect(
    #         self.boardrect.right(), 0, margin_size, self.boardrect.height()
    #     )
    #     arrow_size = QSize(int(margin_size * 0.7), int(margin_size * 0.7))
    #     self.__leftarrowrect = QRect(QPoint(0, 0), arrow_size)
    #     self.__leftarrowrect.moveCenter(self.__correctrect.center())
    #     self.__rightarrowrect = QRect(QPoint(0, 0), arrow_size)
    #     self.__rightarrowrect.moveCenter(self.__incorrectrect.center())

    #     self.__leftarrowimage = QPixmap(resource_path("left-arrow.png"))
    #     self.__rightarrowimage = QPixmap(resource_path("right-arrow.png"))
    #     self.__spaceimage = QPixmap(resource_path("space.png"))

    #     self.show()
    #     self.__lit = False
    #     self.arrowhints = False
    #     self.spacehints = False


    # def paintEvent(self, event):
    #     qp = QPainter()
    #     qp.begin(self)
    #     if self.lit:
    #         qp.setBrush(HIGHLIGHTBRUSH)
    #         qp.drawRect(self.__answerbarrect)
    #     if self.arrowhints and self.parent().alex:
    #         qp.setBrush(CORRECTBRUSH)
    #         qp.drawRect(self.__correctrect)
    #         qp.setBrush(INCORRECTBRUSH)
    #         qp.drawRect(self.__incorrectrect)
    #         qp.setBrush(HIGHLIGHTBRUSH)
    #         qp.drawPixmap(self.__leftarrowrect, self.__leftarrowimage)
    #         qp.drawPixmap(self.__rightarrowrect, self.__rightarrowimage)

    #     if self.spacehints and self.parent().alex:
    #         qp.setBrush(HIGHLIGHTBRUSH)
    #         qp.drawPixmap(self.__leftarrowrect, self.__spaceimage)
    #         qp.drawPixmap(self.__rightarrowrect, self.__spaceimage)

class DisplayWindow(QMainWindow):
    def __init__(self, alex=True, monitor=0):
        super().__init__()
        self.alex = alex
        self.setWindowTitle("Host" if alex else "Board")

        colorpal = QPalette()
        colorpal.setColor(QPalette.ColorRole.Window, BLACK)
        self.setPalette(colorpal)

        # monitor = QDesktopWidget().screenGeometry(monitor)
        if DEBUG:
            if len(QGuiApplication.screens()) == 1:
                monitor = 0

        monitor = QGuiApplication.screens()[monitor].geometry()
        self.game = None

        # self.lights_widget = LightsWidget(self)

        self.boardwidget = QWidget() #BoardWidget(alex, self)

        self.scoreboard = ScoreBoard(self)
        # self.finalanswerwindow = FinalAnswerWidget(game)
        # self.finalanswerwindow.setVisible(False)

        self.borders = Borders(self)

        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0.)
        self.main_layout.setContentsMargins(0., 0., 0., 0.)

        self.board_layout = QHBoxLayout()
        self.board_layout.setContentsMargins(0., 0., 0., 0.)
        self.board_layout.addWidget(self.borders.left, 1)
        self.board_layout.addWidget(self.boardwidget, 20)
        self.board_layout.addWidget(self.borders.right, 1)
        self.main_layout.addLayout( self.board_layout, 7 )
        # self.main_layout.addWidget( self.lights_widget, 1 )
        self.main_layout.addWidget( self.scoreboard, 2)

        self.newWidget = QWidget(self)
        self.newWidget.setLayout(self.main_layout)
        self.setCentralWidget(self.newWidget)

        self.move(monitor.left(), monitor.top())  # move to monitor 0
        self.showFullScreen()

        self.show()


    # def resizeEvent(self, event):
    #     main_layout = self.centralWidget().layout()
    #     main_layout.setStretchFactor( self.boardwidget,2 )
    #     self.centralWidget().setLayout(main_layout)

    def hide_question(self):
        self.boardwidget.hide_question()

    def keyPressEvent(self, event):
        if self.game is not None:
            self.game.keystroke_manager.call(event.key())

    def load_question(self, q):
        logging.info("DC load_question")
        self.boardwidget.load_question(q)
