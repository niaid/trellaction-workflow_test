import os
from trello import TrelloClient
from github import Github
import json

client = TrelloClient(
    api_key=os.getenv("TRELLO_API_KEY"),
    api_secret=os.getenv("TRELLO_API_SECRET"),
    token=os.getenv("TRELLO_TOKEN"),
    token_secret=os.getenv("TRELLO_TOKEN_SECRET")
)

github_client = Github(os.getenv('REPO_TOKEN'))

board_id = os.getenv('TRELLO_BOARD_ID')
list_index = int(os.getenv('TRELLO_LIST_INDEX')) - 1
github_event = os.getenv('GITHUB_EVENT_PATH')

with open(github_event, "r") as event_file:
    event = json.load(event_file)

issue_data = event["issue"]
repo = github_client.get_repo(event["repository"]["full_name"])
issue = repo.get_issue(number=issue_data["number"])

if "security" in [label["name"] for label in issue_data["labels"]]:
    board = client.get_board(board_id)
    in_list = board.list_lists()[list_index]  # Get the list specified

    # Get all cards in the board, including those in the archive
    existing_cards = board.all_cards()
    archived_cards = board.closed_cards()

    # Get all labels in the board
    existing_labels = board.get_labels(limit=None)

    # Prepare labels for the card
    card_labels = []
    for issue_label in issue_data["labels"]:
        for trello_label in existing_labels:
            # Check if a label with the same name exists in Trello
            if trello_label.name == issue_label["name"]:
                card_labels.append(trello_label)

    issue_link = issue_data["html_url"]
    desc = f'{issue_data["body"]}\n\n[Link to GitHub Issue]({issue_link})'

    # Including the repo name in the card's title
    card_title = f'{event["repository"]["full_name"]}: {issue_data["title"]}'

    # Check if a card with the same title exists
    for card in existing_cards:
        if card.name == card_title:
            # If the card is closed (archived), do nothing
            if card in archived_cards:
                print("Card already closed.")
                break

            print("Card already open. Updating description...")
            # Update the existing card
            card.set_description(desc)
            # Add labels to the card
            for label in card_labels:
                card.add_label(label)
            trello_card_link = card.url
            break
    else:
        print("No card exists for this issue.  Creating new card...")
        # If no existing card is found, add a new card
        list = board.list_lists()[list_index]  # Put the card in the specified list
        card = list.add_card(card_title, desc=desc)
        # Add labels to the card
        for label in card_labels:
            card.add_label(label)
        trello_card_link = card.url

    # Add a comment to the GitHub issue with a link to the Trello card
    repo_full_name = issue_data["repository_url"].split("https://api.github.com/repos/")[1]
    repo = github_client.get_repo(repo_full_name)
    issue = repo.get_issue(number=issue_data["number"])
    comments = issue.get_comments()

    # Check if a comment with a link to the Trello card already exists
    for comment in comments:
        if trello_card_link in comment.body:
            break
    else:
        issue.create_comment(f"Related Trello card: {trello_card_link}")