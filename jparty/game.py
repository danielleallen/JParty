from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QApplication


import threading
import time
from dataclasses import dataclass
import os
import sys
import simpleaudio as sa
from collections.abc import Iterable
import logging
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

from jparty.utils import SongPlayer, resource_path, CompoundObject
from jparty.constants import FJTIME, QUESTIONTIME, REPO_ROOT


MAX_PLAYERS = 6
index_to_key = {
    0: Qt.Key.Key_Q,
    1: Qt.Key.Key_W,
    2: Qt.Key.Key_E,
    3: Qt.Key.Key_R,
    4: Qt.Key.Key_T,
    5: Qt.Key.Key_Y,
}

class QuestionTimer(object):
    def __init__(self, interval, f, *args, **kwargs):
        super().__init__()
        self.f = f
        self.args = args
        self.kwargs = kwargs
        self.interval = interval
        self.__thread = None
        self.__start_time = None
        self.__elapsed_time = 0

    def run(self, i):
        thread = self.__thread
        time.sleep(i)
        if thread == self.__thread:
            self.f(*self.args, **self.kwargs)

    def start(self):
        """wrapper for resume"""
        self.resume()

    def cancel(self):
        """wrapper for pause"""
        self.pause()

    def pause(self):
        self.__thread = None
        self.__elapsed_time += time.perf_counter_ns() - self.__start_time

    def resume(self):
        self.__thread = threading.Thread(
            target=self.run, args=(self.interval - self.__elapsed_time,)
        )
        self.__thread.start()
        self.__start_time = time.perf_counter_ns()


@dataclass
class KeystrokeEvent:
    key: int
    func: callable
    hint_setter: callable = None
    active: bool = False
    persistent: bool = False
    func_args: int = None


class KeystrokeManager(object):
    def __init__(self):
        super().__init__()
        self.__events = {}

    def addEvent(
        self, ident, key, func, hint_setter=None, active=False, persistent=False, func_args=None
    ):
        self.__events[ident] = KeystrokeEvent(
            key, func, hint_setter, active, persistent, func_args
        )

    def call(self, key):
        """this is split in to two for loops so one execution doesnt cause another event to trigger"""
        events_to_call = []
        for ident, event in self.__events.items():
            if event.active and event.key == key:
                logging.info(f"Calling {ident}")
                events_to_call.append(event)
                if not event.persistent:
                    self._deactivate(ident)

        for event in events_to_call:
            if event.func_args is not None:
                event.func(event.func_args)
            else:
                event.func()

    def _activate(self, ident):
        logging.info(f"Activating {ident}")
        e = self.__events[ident]
        e.active = True
        e.hint_setter(True)
        if e.hint_setter:
            e.hint_setter(True)

    def _deactivate(self, ident):
        e = self.__events[ident]
        e.active = False
        if e.hint_setter:
            e.hint_setter(False)

    def activate(self, *idents):
        if isinstance(idents, Iterable):
            for ident in idents:
                self._activate(ident)
        else:
            self._activate(idents)

    def deactivate(self, *idents):
        if isinstance(idents, Iterable):
            for ident in idents:
                self._deactivate(ident)
        else:
            self._deactivate(idents)


@dataclass
class Question:
    index: tuple
    text: str
    answer: str
    category: str
    value: int = -1
    dd: bool = False
    complete: bool = False
    image: bool = False
    image_url: str = None
    actual_results: str = None


class Board(object):
    size = (6, 5)

    def __init__(self, categories, questions, dj=False):
        self.categories = categories
        self.dj = dj
        if not questions is None:
            self.questions = questions
        else:
            self.questions = []

    def get_question(self, i, j):
        for q in self.questions:
            if q.index == (i, j):
                return q
        return None

    def complete(self):
        return len(self.questions) == 30


class FinalBoard(Board):
    size = (1, 1)

    def __init__(self, category, question):
        super().__init__([category], [question], dj=False)
        self.category = category
        self.question = question

    def complete(self):
        return len(self.questions) == 1


@dataclass
class GameData:
    rounds: list
    date: str
    comments: str


class Game(QObject):
    buzz_trigger = pyqtSignal(int, float)
    new_player_trigger = pyqtSignal()
    wager_trigger = pyqtSignal(int, int)
    toolate_trigger = pyqtSignal()
    lectern_update_trigger = pyqtSignal(int, dict)

    def __init__(self):
        super().__init__()

        self.host_display = None
        self.main_display = None
        self.dc = None
        self.question_number = 1
        self.data = None

        self.current_round = None
        self.players = []
        self.original_players = {}

        self.active_question = None
        self.accepting_responses = False
        self.answering_player = None
        self.previous_answerer = None
        self.timer = None
        self.soliciting_player = False  # part of selecting who found a daily double
        self.early_buzzers = set()  # Track players who buzz before OPEN_RESPONSES
        self.open_responses_time = None  # Track when OPEN_RESPONSES was activated

        self.song_player = SongPlayer()
        self.__judgement_round = 0
        self.__sorted_players = None

        self.buzzer_controller = None

        self.keystroke_manager = KeystrokeManager()

        self.keystroke_manager.addEvent(
            "CORRECT_ANSWER", Qt.Key.Key_Left, self.correct_answer, self.arrowhints
        )
        self.keystroke_manager.addEvent(
            "INCORRECT_ANSWER", Qt.Key.Key_Right, self.incorrect_answer, self.arrowhints
        )
        self.keystroke_manager.addEvent(
            "BACK_TO_BOARD", Qt.Key.Key_Space, self.back_to_board, self.spacehints
        )
        self.keystroke_manager.addEvent(
            "OPEN_RESPONSES", Qt.Key.Key_Space, self.open_responses, self.spacehints
        )
        self.keystroke_manager.addEvent(
            "NEXT_ROUND", Qt.Key.Key_Space, self.next_round, self.spacehints
        )
        self.keystroke_manager.addEvent(
            "OPEN_FINAL", Qt.Key.Key_Space, self.open_final, self.spacehints
        )
        self.keystroke_manager.addEvent(
            "CLOSE_GAME", Qt.Key.Key_Space, self.close_game, self.spacehints
        )
        self.keystroke_manager.addEvent(
            "GENERATE_GRAPHS", Qt.Key.Key_Space, self.generate_final_score_graphs, self.spacehints
        )
        self.keystroke_manager.addEvent(
            "FINAL_OPEN_RESPONSES",
            Qt.Key.Key_Space,
            self.final_open_responses,
            self.spacehints,
        )
        self.keystroke_manager.addEvent(
            "FINAL_NEXT_PLAYER",
            Qt.Key.Key_Space,
            self.final_next_player,
            self.spacehints,
        )
        self.keystroke_manager.addEvent(
            "FINAL_SHOW_ANSWER",
            Qt.Key.Key_Space,
            self.final_show_answer,
            self.spacehints,
        )
        self.keystroke_manager.addEvent(
            "FINAL_CORRECT_ANSWER",
            Qt.Key.Key_Left,
            self.final_correct_answer,
            self.arrowhints,
        )
        self.keystroke_manager.addEvent(
            "FINAL_INCORRECT_ANSWER",
            Qt.Key.Key_Right,
            self.final_incorrect_answer,
            self.arrowhints,
        )
        for player_index in range(MAX_PLAYERS):
            self.keystroke_manager.addEvent(
                f"BUZZED_{player_index}",
                index_to_key[player_index],
                lambda i=player_index: self.buzz(i, time.perf_counter_ns()),
                lambda x: x, #nonsense
                active=True,
                persistent=True
            )
        self.wager_trigger.connect(self.wager)
        self.buzz_trigger.connect(self.buzz)
        self.new_player_trigger.connect(self.new_player)
        self.toolate_trigger.connect(self.__toolate)
        self.lectern_update_trigger.connect(self.__broadcast_lectern_update)

    def startable(self):
        return self.valid_game() and len(self.buzzer_controller.connected_players) > 0

    def begin(self):
        self.song_player.play(repeat=True)

    def start_game(self):
        self.current_round = self.data.rounds[0]
        self.dc.hide_welcome_widgets()
        self.dc.board_widget.load_round(self.current_round)
        self.buzzer_controller.accepting_players = False
        self.song_player.stop()

    def setDisplays(self, host_display, main_display):
        self.host_display = host_display
        self.main_display = main_display
        self.dc = CompoundObject(host_display, main_display)

    def setBuzzerController(self, controller):
        self.buzzer_controller = controller

    def arrowhints(self, val):
        self.host_display.borders.arrowhints(val)

    def spacehints(self, val):
        self.host_display.borders.spacehints(val)

    def new_player(self):
        self.players = self.buzzer_controller.connected_players
        self.dc.scoreboard.refresh_players()
        self.host_display.welcome_widget.check_start()
        for player in self.players:
            self._update_lectern_for_player(player)

    def remove_player(self, player):
        self.players.remove(player)
        player.waiter.close()
        self.dc.scoreboard.refresh_players()
        self.host_display.welcome_widget.check_start()

    def valid_game(self):
        return self.data is not None and all(b.complete() for b in self.data.rounds)

    def open_responses(self):
        self.dc.borders.lights(True)
        self.accepting_responses = True
        self.open_responses_time = time.perf_counter_ns()  # Record when responses are opened
        logging.info(f"Responses opened at {self.open_responses_time}. Early buzzers: {self.early_buzzers}")

        if not self.timer:
            self.timer = QuestionTimer(QUESTIONTIME, self.stumped)

        self.timer.start()

    def close_responses(self):
        self.timer.pause()
        self.accepting_responses = False
        self.early_buzzers.clear()  # Clear early buzzers for new question
        self.dc.borders.lights(True)

    def keyboard_buzz(self):
        """Is this ever used???"""
        buzz_time = time.perf_counter_ns()
        logging.info(f"Keyboard buzz at {buzz_time}")
        self.buzz(0, buzz_time)

    def buzz(self, i_player, buzz_time=None):
        if buzz_time is None:
            buzz_time = time.perf_counter_ns()
            logging.warning("Buzz called without timestamp, using current time")
            
        player = self.players[i_player]
        
        # If not accepting responses yet, mark as early buzzer
        if not self.accepting_responses:
            self.early_buzzers.add(player)
            self.dc.player_widget(player).buzz_hint()
            return
            
        # If accepting responses, check if player is locked out
        if player in self.early_buzzers:
            # Check if 250ms lockout period has passed (convert to ns)
            if buzz_time - self.open_responses_time < 250_000_000:
                # self.dc.player_widget(player).buzz_hint()
                return
            else:
                self.early_buzzers.remove(player)  # Remove from lockout after period
            
        # Only process buzz if player is not the previous answerer
        if player is not self.previous_answerer:
            logging.info(f"Valid buzz registered at {buzz_time}")
            self.accepting_responses = False
            self.timer.pause()
            self.previous_answerer = player
            self.dc.player_widget(player).run_lights()

            self.answering_player = player
            self.keystroke_manager.activate("CORRECT_ANSWER", "INCORRECT_ANSWER")
            self.dc.borders.lights(False)
            self._update_lectern_for_player(player, buzzed=True)
        elif self.active_question is None:
            self.dc.player_widget(player).buzz_hint()
        else:
            pass

    def answer_given(self):
        self.keystroke_manager.deactivate("CORRECT_ANSWER", "INCORRECT_ANSWER")
        self.dc.player_widget(self.answering_player).stop_lights()
        answering_player = self.answering_player
        self.answering_player = None
        if answering_player:
            self._update_lectern_for_player(answering_player, buzzed=False)

    def update_original_player_scores(self):
        buzzed_players = []
        for player, score in self.active_question.actual_results:
            if player not in self.original_players:
                self.original_players[player] = [0 for _ in range(self.question_number)]
            buzzed_players.append(player)
            self.original_players[player].append(score + self.original_players[player][-1])
        for player in self.original_players:
            if player not in buzzed_players:
                self.original_players[player].append(self.original_players[player][-1])

    def back_to_board(self):
        logging.info("back_to_board")
        self.question_number += 1
        self.dc.hide_question()
        self.timer = None
        self.active_question.complete = True
        self.update_original_player_scores()
        self.active_question = None
        self.previous_answerer = None
        # Clear active state for all players on lecterns
        if self.answering_player:
            self._update_lectern_for_player(self.answering_player, buzzed=False)
        self.answering_player = None
        # Update all players to ensure lecterns show correct state
        for player in self.players:
            self._update_lectern_for_player(player, buzzed=False)
        if all(q.complete for q in self.current_round.questions):
            logging.info("NEXT ROUND")
            self.keystroke_manager.activate("NEXT_ROUND")

    def accept_image(self):
        logging.info("Proposed question image accepted")
        self.load_question(self.active_question)

    def no_image_needed(self):
        logging.info("No image needed for question")
        self.active_question.image = False
        self.active_question.image_url = None
        self.load_question(self.active_question)

    def next_round(self):
        logging.info("next round")
        i = self.data.rounds.index(self.current_round)
        logging.info(f"ROUND {i}")
        self.current_round = self.data.rounds[i + 1]

        if isinstance(self.current_round, FinalBoard):
            self.dc.load_final(self.current_round.question)
            self.active_question = self.current_round.question
            self.update_original_player_scores()
            self.start_final()
        else:
            self.dc.board_widget.load_round(self.current_round)

    def start_final(self):
        logging.info("start final")
        for player in self.players:
            self.dc.player_widget(player).set_lights(True)

        self.buzzer_controller.open_wagers()

    def wager(self, i_player, amount):
        player = self.players[i_player]
        player.wager = amount
        self.dc.player_widget(player).set_lights(False)
        logging.info(f"{player} wagered {amount}")
        if all(p.wager is not None for p in self.players):
            self.host_display.question_widget.hint_label.setText(
                "Press space to show clue!"
            )
            self.keystroke_manager.activate("OPEN_FINAL")

    def answer(self, player, guess):
        player.finalanswer = guess
        logging.info(f"{player} guessed {guess}")

    def final_open_responses(self):
        self.dc.borders.lights(True)
        self.buzzer_controller.prompt_answers()

        self.song_player.final()

        self.timer = QuestionTimer(FJTIME, self.final_finished_song)
        self.timer.start()

    def final_next_player(self):
        for p in self.players:
            self.dc.player_widget(p).set_lights(False)

        if self.__judgement_round == 0:
            self.dc.load_final_judgement()
            self.__sorted_players = sorted(self.players, key=lambda x: x.score)

        elif self.__judgement_round == len(self.players):
            self.end_game()
            return

        self.answering_player = self.__sorted_players[self.__judgement_round]

        self.dc.player_widget(self.answering_player).set_lights(True)

        self.dc.final_window.guess_label.setText("")
        self.dc.final_window.wager_label.setText("")
        
        # Update lectern to show player name (answer will be shown in final_show_answer)
        self._update_lectern_for_player(self.answering_player, show_final_answer=False)

        self.keystroke_manager.activate("FINAL_SHOW_ANSWER")

    def final_show_answer(self):
        answer = self.answering_player.finalanswer
        if answer == "":
            answer = "________"

        self.dc.final_window.guess_label.setText(answer)
        # Update lectern to show final answer
        self._update_lectern_for_player(self.answering_player, show_final_answer=True)
        self.keystroke_manager.activate(
            "FINAL_CORRECT_ANSWER", "FINAL_INCORRECT_ANSWER"
        )

    def final_correct_answer(self):
        ap = self.answering_player
        new_score = ap.score + ap.wager
        ap.update_scores(self.question_number, new_score)
        self.set_score(ap, ap.score + ap.wager)
        self.final_judgement_given()

    def final_incorrect_answer(self):
        ap = self.answering_player
        new_score = ap.score - ap.wager
        ap.update_scores(self.question_number, new_score)
        self.set_score(ap, new_score)
        self.final_judgement_given()

    def final_judgement_given(self):
        self.keystroke_manager.deactivate(
            "FINAL_CORRECT_ANSWER", "FINAL_INCORRECT_ANSWER"
        )
        self.dc.final_window.wager_label.setText(str(self.answering_player.wager))
        self.keystroke_manager.activate("FINAL_NEXT_PLAYER")
        self.__judgement_round += 1

    def final_finished_song(self):
        logging.info("Final song ended")
        self.toolate_trigger.emit()
        self.accepting_responses = False
        self.dc.borders.flash()
        self.keystroke_manager.activate("FINAL_NEXT_PLAYER")

    def end_game(self):
        top_score = max([p.score for p in self.players])
        winners = [p for p in self.players if p.score == top_score]
        for w in winners:
            self.dc.player_widget(w).set_lights(True)

        if len(winners) == 1:
            self.dc.final_window.show_winner(winners[0])
        else:
            self.dc.final_window.show_tie()

        # self.generate_final_score_graph()
        logging.info("Game over!")
        self.keystroke_manager.activate("GENERATE_GRAPHS")

    def generate_final_score_graphs(self):
        self.keystroke_manager.deactivate("GENERATE_GRAPHS")
        
        for player_set in ["original", "current", "all"]:
            self.generate_final_score_graph(player_set)
        
        # Ensure PyQt6 GUI is fully updated after all matplotlib operations
        QApplication.processEvents()
        
        self.dc.load_final_graphs()
        self.keystroke_manager.activate("CLOSE_GAME")

    def generate_final_score_graph(self, players):
        """create an image of score by question number"""
        current_player_data = {player.player_number : player.score_by_question for player in self.players}
        if players == "original":
            data = self.original_players
        elif players == "current":
            data = current_player_data
        elif players == "all":
            data = current_player_data | self.original_players
        
        game_id = os.environ["JPARTY_GAME_ID"]
        
        # Isolate matplotlib operations to prevent interference with PyQt6
        fig = None
        try:
            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot each player's scores
            for player, scores in data.items():
                x_values = list(range(1, len(scores)+1))
                ax.plot(x_values, scores, marker='o', label=str(player), linewidth=2, markersize=6)
            
            ax.set_xlabel('Question Number', fontsize=12)
            ax.set_ylabel('Score', fontsize=12)
            ax.set_title(f'Game {game_id}:Player Scores', fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            
            # Save the figure
            games_scores_dir = REPO_ROOT / "jparty" / "data" / "game_scores"
            games_scores_dir.mkdir(exist_ok=True)
            image_path = games_scores_dir / f"{game_id}-{players}.jpg"
            
            plt.tight_layout()
            fig.savefig(str(image_path), dpi=150, bbox_inches='tight')
        finally:
            # Always clean up matplotlib state
            if fig is not None:
                plt.close(fig)  # Close figure to free memory
            plt.close('all')  # Close all figures to ensure clean state
            # Ensure matplotlib doesn't interfere with PyQt6
            plt.ioff()  # Turn off interactive mode
        
        # Process PyQt6 events to ensure GUI stays responsive
        QApplication.processEvents()

    def close_game(self):
        self.buzzer_controller.restart()
        # Notify all lecterns that players are cleared
        if self.buzzer_controller:
            for player_number in list(self.buzzer_controller.lectern_connections.keys()):
                if player_number in self.buzzer_controller.lectern_connections:
                    try:
                        self.buzzer_controller.lectern_connections[player_number].send("NO_PLAYER", "")
                    except:
                        pass
        self.players = []
        self.original_players = {}
        self.question_number = 1
        self.active_question = None
        self.current_round = None
        self.answering_player = None
        self.timer = None
        self.data = None
        self.__judgement_round = 0
        self.dc.restart()
        self.begin()

    def get_dd_wager(self, player):
        self.answering_player = player
        self.soliciting_player = False
        try:
            logging.info(f"Current round is: {self.current_round}")
            logging.info(f"Rounds are {self.data.rounds}")
            round_index = self.data.rounds.index(self.current_round)
        except:
            round_index = 1

        max_wager = max(
            self.answering_player.score,
            1000 if round_index == 0 else 2000)
        wager_res = QInputDialog.getInt(
            self.host_display,
            "Wager",
            f"How much do they wager? (min: 5, max: ${max_wager})",
            min=5,
            max=max_wager,
        )
        if not wager_res[1]:
            self.soliciting_player = True
            return False

        wager = wager_res[0]
        self.active_question.value = wager

        self.keystroke_manager.activate("CORRECT_ANSWER", "INCORRECT_ANSWER")
        self.dc.question_widget.show_question()

    def load_image_review_screen(self, q):
        self.active_question = q
        self.host_display.load_image_review_screen(q)


    def load_question(self, q):
        self.active_question = q
        if q.dd:
            logging.info("Daily double!")
            wo = sa.WaveObject.from_wave_file(resource_path("dd.wav"))
            wo.play()
            self.soliciting_player = True
        else:
            self.keystroke_manager.activate("OPEN_RESPONSES")
        self.dc.load_question(q)
        self.dc.remove_card(q)

    def open_final(self):
        self.dc.question_widget.show_question()
        self.keystroke_manager.activate("FINAL_OPEN_RESPONSES")

    def correct_answer(self):
        new_score = self.answering_player.score + self.active_question.value
        self.answering_player.update_scores(self.question_number, new_score) 
        if self.timer:
            self.timer.cancel()

        self.set_score(
            self.answering_player,
            new_score,
        )
        self.dc.borders.lights(False)
        self.answer_given()
        self.back_to_board()

    def incorrect_answer(self):
        new_score = self.answering_player.score - self.active_question.value
        self.answering_player.update_scores(self.question_number, new_score) 
        self.set_score(
            self.answering_player,
            new_score,
        )
        self.answer_given()
        if self.active_question.dd:
            self.back_to_board()
        else:
            self.open_responses()
            self.timer.resume()

    def stumped(self):
        self.accepting_responses = False
        sa.WaveObject.from_wave_file(resource_path("stumped.wav")).play()
        self.dc.borders.flash()
        self.keystroke_manager.activate("BACK_TO_BOARD")

    def __toolate(self):
        self.buzzer_controller.toolate()

    def __broadcast_lectern_update(self, player_number, state_dict):
        if self.buzzer_controller:
            self.buzzer_controller.broadcast_to_lecterns(player_number, state_dict)

    def _update_lectern_for_player(self, player, buzzed=False, show_final_answer=False):
        if self.buzzer_controller:
            state_dict = self.buzzer_controller.get_player_state_dict(player)
            state_dict["buzzed"] = buzzed
            state_dict["active"] = (self.answering_player is player) if self.answering_player else False
            # Only include finalanswer if we're showing it
            if not show_final_answer:
                state_dict["finalanswer"] = None
            self.lectern_update_trigger.emit(player.player_number, state_dict)

    def set_score(self, player, score):
        player.score = score
        self.dc.player_widget(player).update_score()
        self._update_lectern_for_player(player)

    def adjust_score(self, player):
        new_score, answered = QInputDialog.getInt(
            self.host_display,
            "Adjust Score",
            "Enter a new score:",
            value=player.score,
        )
        if answered:
            self.set_score(player, new_score)
        player.score_by_question[-1] = new_score

    def close(self):
        self.song_player.stop()
        QApplication.quit()


class Player(object):
    def __init__(self, name, waiter, player_number):
        self.name = name
        self.token = os.urandom(15)
        # score at index 0 is start of game, 1 after first question
        self.score_by_question = [0]
        self.score = 0
        self.waiter = waiter
        self.wager = None
        self.finalanswer = ""
        self.page = "buzz"
        self.player_number = player_number
        self.key = index_to_key[player_number]

    def __hash__(self):
        return int.from_bytes(self.token, sys.byteorder)

    def state(self):
        return {"page": self.page, "score": self.score}
    
    def update_scores(self, question_number, new_score):
        """update players score"""
        if (len(self.score_by_question)) == question_number:
            self.score_by_question.append(new_score)
        else:
            for _ in range(question_number - len(self.score_by_question)):
                self.score_by_question.append(self.score_by_question[-1])
            self.score_by_question.append(new_score)

