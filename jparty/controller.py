import logging
import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.options import define, options

import os
from threading import Thread
import socket

from jparty.environ import root
from jparty.game import Player
from jparty.constants import MAXPLAYERS, PORT


define("port", default=PORT, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self, controller):
        handlers = [
            (r"/", WelcomeHandler),
            (r"/play", BuzzerHandler),
            (r"/buzzersocket", BuzzerSocketHandler),
            (r"/lectern", LecternHandler),
            (r"/lecternsocket", LecternSocketHandler),
        ]
        settings = dict(
            cookie_secret="",
            template_path=os.path.join(os.path.join(root, "buzzer", "templates")),
            static_path=os.path.join(root, "buzzer", "static"),
            xsrf_cookies=False,
            websocket_ping_interval=0.19,
        )
        super(Application, self).__init__(handlers, **settings)
        self.controller = controller


class WelcomeHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", messages=BuzzerSocketHandler.cache)


class BuzzerHandler(tornado.web.RequestHandler):
    def post(self):
        if not self.get_cookie("test"):
            self.set_cookie("test", "test_val")
            logging.info("set cookie")
        else:
            logging.info(f"cookie: {self.get_cookie('test')}")
        self.render("play.html", messages=BuzzerSocketHandler.cache)


class BuzzerSocketHandler(tornado.websocket.WebSocketHandler):
    cache = []
    cache_size = 400

    def initialize(self):
        # self.name = None
        self.controller = self.application.controller
        self.player = None

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    def open(self):
        self.set_nodelay(True)

    def send(self, msg, text=""):
        data = {"message": msg, "text": text}
        try:
            self.write_message(data)
            logging.info(f"Sent {data}")
        except:
            logging.error(f"Error sending message {msg}", exc_info=True)

    def check_if_exists(self, token):

        p = self.controller.player_with_token(token)
        if p is None:
            logging.info("NEW")
            self.send("NEW")
        else:
            logging.info(f"Reconnected {p}")
            self.player = p
            p.connected = True
            p.waiter = self
            self.send("EXISTS", tornado.escape.json_encode(p.state()))

    def on_message(self, message):
        # do this first to kill latency
        if "BUZZ" in message:
            self.buzz()
            return
        parsed = tornado.escape.json_decode(message)
        msg = parsed["message"]
        text = parsed["text"]
        if msg == "NAME":
            self.init_player(text)
        elif msg == "CHECK_IF_EXISTS":
            logging.info(f"Checking if {text} exists")
            self.check_if_exists(text)
        elif msg == "WAGER":
            self.wager(text)
        elif msg == "ANSWER":
            self.application.controller.answer(self.player, text)

        else:
            raise Exception("Unknown message")

    def init_player(self, name):

        if not self.controller.accepting_players:
            logging.info("Game started!")
            self.send("GAMESTARTED")
            return

        if len(self.controller.connected_players) >= MAXPLAYERS:
            self.send("FULL")
            return
        player_index = len(self.controller.connected_players)
        self.player = Player(name, self, player_index)
        self.application.controller.new_player(self.player)
        logging.info(
            f"New Player: {self.player} {self.request.remote_ip} {self.player.token.hex()}"
        )
        self.send("TOKEN", self.player.token.hex())

    def buzz(self):
        self.application.controller.buzz(self.player)

    def wager(self, text):
        self.application.controller.wager(self.player, int(text))
        self.player.page = "null"

    def toolate(self):
        self.send("TOOLATE")

    def on_close(self):
        pass


class LecternHandler(tornado.web.RequestHandler):
    def get(self):
        player_number = self.get_argument("player", "0")
        self.render("lectern.html", player_number=player_number)


class LecternSocketHandler(tornado.websocket.WebSocketHandler):
    def initialize(self):
        self.controller = self.application.controller
        self.player_number = None

    def get_compression_options(self):
        return {}

    def open(self):
        self.set_nodelay(True)
        try:
            # Get player number from query string
            player_arg = self.get_argument("player", "0")
            self.player_number = int(player_arg)
            if self.player_number < 0 or self.player_number >= MAXPLAYERS:
                raise ValueError(f"Player number {self.player_number} out of range")
            logging.info(f"Lectern connected for player {self.player_number}")
            self.controller.lectern_connections[self.player_number] = self
            self.send_initial_state()
        except (ValueError, TypeError) as e:
            logging.error(f"Invalid player number for lectern: {e}")
            self.close()

    def send(self, msg, text=""):
        data = {"message": msg, "text": text}
        try:
            self.write_message(data)
            logging.info(f"Sent to lectern {self.player_number}: {data}")
        except:
            logging.error(f"Error sending message to lectern {self.player_number}: {msg}", exc_info=True)

    def send_initial_state(self):
        if self.player_number is not None and self.controller.game:
            player = self.controller.get_player_by_number(self.player_number)
            if player:
                state = self.controller.get_player_state_dict(player)
                self.send("PLAYER_STATE", tornado.escape.json_encode(state))
            else:
                self.send("NO_PLAYER", "")

    def on_message(self, message):
        pass

    def on_close(self):
        if self.player_number is not None:
            if self.player_number in self.controller.lectern_connections:
                del self.controller.lectern_connections[self.player_number]
            logging.info(f"Lectern disconnected for player {self.player_number}")


class BuzzerController:
    def __init__(self, game):
        self.thread = None
        self.game = game
        tornado.options.parse_command_line()
        self.app = Application(
            self
        )  # this is to remove sleep mode on Macbook network card
        self.port = options.port
        self.connected_players = []
        self.accepting_players = True
        self.lectern_connections = {}

    def start(self, threaded=True, tries=0):
        try:
            self.app.listen(self.port)
        except OSError as e:
            if tries>10:
                raise Exception("Cannot find open port")
            self.port += 1
            self.start(threaded, tries+1)
            return

        if threaded:
            self.thread = Thread(target=tornado.ioloop.IOLoop.current().start)
            self.thread.setDaemon(True)
            self.thread.start()
        else:
            tornado.ioloop.IOLoop.current().start()

    def restart(self):
        for p in self.connected_players:
            p.waiter.close()
        self.connected_players = []
        self.accepting_players = True

    def buzz(self, player):
        if self.game:
            i_player = self.game.players.index(player)
            self.game.buzz_trigger.emit(i_player)
        else:
            i_player = self.connected_players.index(player)
            self.game.buzz_hint_trigger.emit(i_player)

    def wager(self, player, amount):
        i_player = self.game.players.index(player)
        self.game.wager_trigger.emit(i_player, amount)

    def answer(self, player, guess):
        if self.game:
            self.game.answer(player, guess)
            player.page = "null"

    def new_player(self, player):
        self.connected_players.append(player)
        self.game.new_player_trigger.emit()

    @classmethod
    def localip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", options.port))
        return s.getsockname()[0]

    def host(self):
        localip = BuzzerController.localip()
        if self.port == 80:
            return f"{localip}"
        else:
            return f"{localip}:{self.port}"

    def player_with_token(self, token):
        for p in self.connected_players:
            logging.info(f"{p.token}, {token}")
            if p.token.hex() == token:
                logging.info("MATCH")
                return p
        return None

    def open_wagers(self, players=None):
        if players is None:
            players = self.connected_players

        for p in players:
            p.waiter.send("PROMPTWAGER", str(max(p.score, 0)))
            p.page = "wager"

    def prompt_answers(self):
        for p in self.connected_players:
            p.waiter.send("PROMPTANSWER")
            p.page = "answer"

    def toolate(self):
        for p in self.connected_players:
            p.waiter.send("TOOLATE")

    def get_player_by_number(self, player_number):
        if self.game and player_number < len(self.game.players):
            return self.game.players[player_number]
        return None

    def get_player_state_dict(self, player):
        return {
            "name": player.name,
            "score": player.score,
            "player_number": player.player_number,
            "active": False,
            "buzzed": False,
            "finalanswer": getattr(player, 'finalanswer', None),
        }

    def broadcast_to_lecterns(self, player_number, state_dict):
        if player_number in self.lectern_connections:
            lectern = self.lectern_connections[player_number]
            try:
                lectern.send("PLAYER_STATE", tornado.escape.json_encode(state_dict))
            except:
                logging.error(f"Error broadcasting to lectern {player_number}", exc_info=True)
