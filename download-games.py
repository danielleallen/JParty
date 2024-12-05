"""Script to download games"""

from jparty.retrieve import get_game_html, process_game_board_from_html
from jparty.constants import SAVED_GAMES
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument(
    "game_ids", nargs="*", help="List of all game ids you'd like to download", default=None
)
args = parser.parse_args()

for game_id in args.game_ids:
    game_html = get_game_html(game_id)
    game_obj = process_game_board_from_html(game_html, game_id)
    with (SAVED_GAMES / f"{game_id}.html").open("w+", encoding="utf-8") as f:
        f.write(game_html)
    time.sleep(5)