import os
from trello import TrelloClient
import json

client = TrelloClient(
    api_key=os.getenv("TRELLO_API_KEY"),
    api_secret=os.getenv("TRELLO_API_SECRET"),
    token=os.getenv("TRELLO_TOKEN"),
    token_secret=os.getenv("TRELLO_TOKEN_SECRET")
)

board_id = os.getenv('TRELLO_BOARD_ID')
list_index = int(os.getenv('TRELLO_LIST_INDEX')) - 1
github_event = os.getenv('GITHUB_EVENT_PATH')
with open(github_event, "r") as event_file:
    event = json.load(event_file)

issue = event["issue"]
if "security" in [label["name"] for label in issue["labels"]]:
    board = client.get_board(board_id)
    in_list = board.list_lists()[list_index]  # Get the list specified

    # Get all cards in the board, including those in the archive
    existing_cards = board.all_cards()

    # Check if card already exists
    if not any(card.name == issue["title"] for card in existing_cards):
        card = in_list.add_card(issue["title"], desc=issue["body"])
    else:
        print("Card with title '{}' already exists.".format(issue["title"]))