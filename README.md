# trellaction-workflow
Trellaction is a Github Action workflow used to automatically create Github issues for Github security alerts. Those issues are then copied as Trello cards onto a designated Trello board in a designated column.

# Getting started
In order to use this workflow, you will require a few things:
- A GitHub repo with Dependabot alerts, CodeQL code security scanning, and secrets scanning enabled
- A GitHub personal access token with full repo and workflow access
- A Trello board to accept the Trello cards
- A Trello integration to allow access to your Trello board including API keys and tokens

This readme will walk you through setting up those requirements.

## Trello Settings
### Get Trello board ID
Your board ID is an alphanumeric set of characters in the URL of your board listed after "https://trello.com/b/" and before the board name.  For example, in the URL "https://trello.com/b/5OsOTUuY/api-testing", the board ID would be "5OsOTUuY". 

#### Create a Trello integration with API secrets and tokens
1. Go to https://trello.com/power-ups/admin in your web browser
2. Click the "New" button at the top right
3. Fill in the appropriate details with the desired workspace then click "Create" at the bottom right
4. Click "Generate a new API key" button in the ceneter of the screen
5. Click "Generate API key" after reviewing the information on the resulting popup
6. Copy the API key and secret from this page
7. On your local machine, ensure Python is installed
8. Open a terminal and install the "py-trello" pip package 
9. Run `export TRELLO_API_KEY=<your api key> && export TRELLO_API_SECRET=<your api secret> && python3 -m trello oauth`
10. Follow the link provided by the command in your web browser and click "Allow"
11. Copy the PIN you receive
12. Back in your terminal, type `y` in response to "Have you authorized me?"
13. Paste the PIN you copied from your web browser
14. Copy the oauth_token and oauth_token_secret provided in your terminal

## Github Repo Settings
For each of your GitHub repos, your will need to do the following:

### Add workflow scripts
Copy both the workflows scripts from https://github.com/niaid/trellaction-workflow/tree/main/sample-workflows into the .github/workflows folder of your repo.  Make sure to set which column your cards will be created in using the "trello_list_index" value.  The columns are indexed starting with 1 (first column = 1, second column = 2, etc.).

### Enable Security Alerts
1. In your Github repo, go to the "Settings" tab
2. Under the Security section of the menu on the left, select "Code security and analysis"
3. Click "Enable" on "Dependabot alerts"
4. If CodeQL code security scanning or secret scanning is desired, click "Enable" on GitHub Advanced Security
5. Click "Enable" for Secret scanning
6. Click "Set up" for CodeQL analysis
7. Select "Default" or "Advanced" for the desired level of configuration
8. Click "Enable CodeQL" to set up code scanning

### Set up Personal Access Token
1. Click on your profile picture at the top right
2. Click on "Settings" on the dropdown
3. Click on "Developer Settings" at the bottom on the menu on the left
4. Click the "Personal access token" menu to drop down the options
5. Click on "Tokens (classic)"
6. Click "Generate new token" then "Generate new token (classic)"
7. Follow MFA steps if required
8. Give the token a name under the "Note" field
9. Set an appropriate expiration for this token
10. Click the checkboxes for "repo" and "workflow"
11. Copy the token

### Add secrets to GitHub Repo
1. In your Github repo, go to the "Settings" tab
2. Click "Secrets and varibles" on the menu on the left 
3. Click "Actions" from the resulting dropdown options
4. Click "New repository secret" for each of the values from this table:
| Secret Name | Description | 
| --- | --- |
| REPO_TOKEN | Your Github personal access token |
| TRELLO_API_KEY | Your API key for your Trello integration |
| TRELLO_API_SECRET | Your API secret for your Trello integration |
| TRELLO_BOARD_ID | Your trello board ID |
| TRELLO_TOKEN | Your oauth token for your Trello integration | 
| TRELLO_TOKEN_SECRET | Your oauth token secret for your Trello integration |