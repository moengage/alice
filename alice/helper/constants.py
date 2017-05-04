"""" API ROUTES """
SLACK_USER_LIST = "https://slack.com/api/users.list?token="
API_GITHUB_USERS = "https://api.github.com/users/"
API_GITHUB_MEMBERS_LIST = "https://api.github.com/orgs/{org}/members?page="
API_GITHUB_MEMBERS = "https://api.github.com/orgs/{org}/members"
API_GITHUB_REPO_MEMBER = "https://api.github.com/repos/{org}/{repo}"
API_GITHUB_REVIEW_ACCEPT_KEY = "application/vnd.github.black-cat-preview+json"
API_GITHUB_ISSUES = "https://api.github.com/repos/{org}/{repo}/issues"

EP_REVIEWS = "reviews"
EP_COMMENTS = "comments"
STATE_OPEN = "open"
STATE_CLOSED = "closed"


""" docs link """
EXTEND_ALICE= "https://github.com/moengage/alice/blob/master/docs/extend_alice.md"
config_file="https://github.com/moengage/alice/blob/master/docs/setup_config.md"
ISSUE_LINK= "https://github.com/moengage/alice/issues/new"


""" other constants """
THUMBS_UP_ICON = "\ud83d\udc4d"
SLACK_ICON = "https://cloud.githubusercontent.com/assets/12966925/25132384/021095fc-2467-11e7-95c0-78917bf4d52a.png"
bot_name = "alice"
