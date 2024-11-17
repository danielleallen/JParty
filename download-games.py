"""Script to download games"""

from jparty.retrieve import get_game_html
from jparty.constants import SAVED_GAMES
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "game_ids", nargs="*", help="List of all game ids you'd like to download", default=None
)
args = parser.parse_args()

for game_id in args.game_ids:
    with (SAVED_GAMES / f"{game_id}.html").open("w+") as f:
        f.write(get_game_html(game_id))