import requests
from bs4 import BeautifulSoup
from html import unescape
import re
import json
from jparty.game import Question, Board, FinalBoard, GameData
import logging
import csv
import os
from jparty.constants import MONIES, SAVED_GAMES, QUESTION_MEDIA


def list_to_game(s):
    # Template link: https://docs.google.com/spreadsheets/d/1_vBBsWn-EVc7npamLnOKHs34Mc2iAmd9hOGSzxHQX0Y/edit?usp=sharing
    alpha = "BCDEFG"  # columns
    boards = []
    # gets single and double jeopardy rounds
    for n1 in [1, 14]:
        categories = s[n1 - 1][1:7]
        questions = []
        for row in range(5):
            for col, cat in enumerate(categories):
                address = alpha[col] + str(row + n1 + 1)
                index = (col, row)
                text = s[row + n1][col + 1]
                answer = s[row + n1 + 6][col + 1]
                value = int(s[row + n1][0])
                dd = address in s[n1 - 1][-1]
                questions.append(Question(index, text, answer, cat, value, dd))

        boards.append(Board(categories, questions, dj=(n1 == 14)))

    # gets final jeopardy round
    fj = s[-1]
    index = (0, 0)
    text = fj[2]
    answer = fj[3]
    category = fj[1]
    question = Question(index, text, answer, category)
    boards.append(FinalBoard(category, question))
    date = fj[5]
    comments = fj[7]
    return GameData(boards, date, comments)


def get_Gsheet_game(file_id):
    csv_url = f"https://docs.google.com/spreadsheet/ccc?key={file_id}&output=csv"
    with requests.get(csv_url, stream=True) as r:
        lines = (line.decode("utf-8") for line in r.iter_lines())
        r3 = csv.reader(lines)
        return list_to_game(list(r3))


def get_game_html(game_id):
    saved_game_path = SAVED_GAMES / f"{game_id}.html"
    if saved_game_path.exists():
        print("game is saved, using saved game")
        with saved_game_path.open("r") as f:
            game_html = f.read()
            return game_html
    try:
        print("using wayback machine")
        game_html = get_wayback_game_html(game_id)
    except Exception as e:
        print("using j-archive")
        logging.error(e)
        game_html = get_jarchive_game_html(game_id)
    return game_html

def get_game(game_id):
    os.environ["JPARTY_GAME_ID"] = str(game_id)
    if len(str(game_id)) < 7:
        game_html = get_game_html(game_id)
        return process_game_board_from_html(game_html, game_id)
    else:
        return get_Gsheet_game(str(game_id))


def findanswer(clue):
    return re.findall(r'correct_response">(.*?)</em', unescape(str(clue)))[0]

def get_jarchive_game_html(game_id):
    game_url = f"http://www.j-archive.com/showgame.php?game_id={game_id}"
    r = requests.get(game_url)
    return r.text

def find_question_media(game_id: int, round: int, index: tuple) -> str:
    """Return path to question media or False if none exist
    
    Args:
        game_id: game id
        round: round number, 1-jeopardy, 2-double jeopardy
        index: (category, question) index, from top left 0-indexed
    """
    game_media_path = QUESTION_MEDIA / str(game_id)
    if game_media_path.exists():
        potential_filename = f"{round}-{index[0]}-{index[1]}"
        for media_file in game_media_path.iterdir():
            if media_file.stem == potential_filename:
                return str(media_file)
    return False

def get_actual_player_results(clue: BeautifulSoup, value: int):
    """Get the results from the actual jeopardy contestants"""
    dd_value = clue.find(class_="clue_value_daily_double")
    if dd_value is not None:
        value = int(dd_value.text[5:].replace(",", ""))
    wrong_answers = clue.find_all("td", {"class": "wrong"})
    answers = [
        [wrong_answer.text, -value] 
        for wrong_answer in wrong_answers 
        if wrong_answer.text != "Triple Stumper"
    ]
    right_answer = clue.find("td", {"class": "right"})
    if right_answer:
        answers.append([right_answer.text, value])
    return answers

def process_game_board_from_html(html, game_id) -> GameData:
    """Given j-archive html, produce a game data object"""
    soup = BeautifulSoup(html, "html.parser")
    datesearch = re.search(
        r"- \w+, (.*?)$", soup.select("#game_title > h1")[0].text
    )
    if datesearch is None:
        return None
    date = datesearch.groups()[0]
    comments = soup.select("#game_comments")[0].contents
    comments = comments[0] if len(comments) > 0 else ""

    # Normal Rounds
    boards = []
    rounds = soup.find_all(class_="round")
    # Use only Double and Triple Jeopardy for Celebrity Jeopardy
    if len(rounds) == 3:
        rounds = rounds[1:]
    for i, ro in enumerate(rounds):
        categories_objs = ro.find_all(class_="category")
        categories = [c.find(class_="category_name").text for c in categories_objs]
        questions = []
        for clue in ro.find_all(class_="clue"):
            text_obj = clue.find(class_="clue_text")
            if text_obj is None:
                logging.info("this game is incomplete")
                return None
            image_likely = text_obj.find('a')
            image_url = None
            text = text_obj.text
            # get actual player results
            index_key = text_obj["id"]
            index = (
                int(index_key[-3]) - 1,
                int(index_key[-1]) - 1,
            )  # get index from id string
            dd = clue.find(class_="clue_value_daily_double") is not None
            value = MONIES[i][index[1]]
            actual_results = get_actual_player_results(clue, value)
            answer = findanswer(clue)
            potential_media_file = find_question_media(game_id, i, index)
            if potential_media_file:
                image_likely = True
                image_url = potential_media_file
            questions.append(
                Question(
                    index,
                    text,
                    answer,
                    categories[index[0]],
                    value,
                    dd,
                    image=image_likely,
                    image_url=image_url,
                    actual_results=actual_results
                )
            )
        boards.append(Board(categories, questions, dj=(i == 1)))

    # Final Jeopardy
    final_round_obj = soup.find_all(class_="final_round")[0]
    category_obj = final_round_obj.find_all(class_="category")[0]
    category = category_obj.find(class_="category_name").text
    clue = final_round_obj.find_all(class_="clue")[0]
    text_obj = clue.find(class_="clue_text")
    if text_obj is None:
        logging.info("this game is incomplete")
        return None

    text = text_obj.text
    answer = findanswer(final_round_obj)
    question = Question((0, 0), text, answer, category)

    boards.append(FinalBoard(category, question))

    return GameData(boards, date, comments)

def get_wayback_game_html(game_id):
    # kudos to Abhi Kumbar: https://medium.com/analytics-vidhya/the-wayback-machine-scraper-63238f6abb66
    # this query's the wayback cdx api for possible instances of the saved jarchive page with the specified game id & returns the latest one
    JArchive_url = f"j-archive.com/showgame.php?game_id={str(game_id)}"  # use the url w/o the http:// or https:// to include both in query
    url = f'http://web.archive.org/cdx/search/cdx?url={JArchive_url}&collapse=digest&limit=-2&fastLatest=true&output=json'  # for some reason, using limit=-1 does not work
    urls = requests.get(url).text
    parse_url = json.loads(urls)  # parses the JSON from urls.
    if len(parse_url) == 0:  # if no results, return None
        logging.info("no games found in wayback")
        # alternative: use fallback to get game from scraping j-archive directly
        raise Exception("no games found in wayback")

    ## Extracts timestamp and original columns from urls and compiles a url list.
    url_list = []
    for i in range(1, len(parse_url)): # gets the wayback url
        orig_url = parse_url[i][2]
        tstamp = parse_url[i][1]
        waylink = tstamp + '/' + orig_url
        final_url = f'http://web.archive.org/web/{waylink}'
        url_list.append(final_url)
    latest_url = url_list[-1]
    r = requests.get(latest_url)
    return r.text


def get_game_sum(soup):
    date = re.search(
        r"- \w+, (.*?)$", soup.select("#game_title > h1")[0].contents[0]
    ).groups()[0]
    comments = soup.select("#game_comments")[0].contents

    return date, comments


def get_random_game():
    """Use j-archive's random game feature to get a random game id"""
    r = requests.get("http://j-archive.com/")
    soup = BeautifulSoup(r.text, "html.parser")

    link = soup.find_all(class_="splash_clue_footer")[1].find("a")["href"]
    return int(link[21:])
