"""" API ROUTES """
SLACK_USER_LIST = "https://slack.com/api/users.list?token="
API_GITHUB_USERS = "https://api.github.com/users/"
API_GITHUB_MEMBERS_LIST = "https://api.github.com/orgs/{org}/members?page="
API_GITHUB_MEMBERS = "https://api.github.com/orgs/{org}/members"
API_GITHUB_REPO_MEMBER = "https://api.github.com/repos/{org}/{repo}"
API_GITHUB_REVIEW_ACCEPT_KEY = "application/vnd.github.black-cat-preview+json"
API_GITHUB_ISSUES = "https://api.github.com/repos/{org}/{repo}/issues"
API_JIRA_USERS = "{jira_domain}/rest/api/3/user?key={user_key}"
API_JIRA_USERS_ACCOUNTID = "{jira_domain}/rest/api/3/user?accountId={account_id}"

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



"""
alice 3.0 constants
"""

auto_revert = False
ui_change = False
base_api_cmd = "https://api.github.com/repos/moengage/"
ui_repo = ["dashboard-ui"]

context = "shield-syntax-validator-python"
context_react = "shield-linter-react"
context_angular = "shield-linter-angular"

package_builder_branches_repo_wise = {
    "dashboard-ui": ["qa", "master"]
}
python_repo = ["MoEngage", "MoeDataScience", "mongoengine", "inapp-rest-service", "mongo", "segmentation",
              "commons",
              "moengcache", "MoeAbTesting", "apns_client", "Bugsy_Backend", "product-management",
              "product-recommendation", "s2s", "email-campaigns", "campaigns-core", "url_tracking"]

file_path = "/opt/alice/release_items.txt"
file_mergedBy = "/opt/alice/release_mergedby.txt"
code_freeze_details_path = "/opt/alice/code_freeze_details.txt"
release_freeze_details_path = "/opt/alice/release_freeze_details.txt"
job_dir = "moe_repo_shield/"
job_name = job_dir + "CI_SyntaxValidator"
context_description = "Syntax Validation"
action_commit_to_investigate = ["opened", "open", "reopened", "synchronize"]
jenkins_instance = jenkins.Jenkins(JENKINS_BASE, username=username, password=token)
JENKINS_BASE = "http://ci.moengage.com:8080"
username = "mojenkins"
token = "f08036fd9280e68561746179a7baf48f"

sensitive_branches_repo_wise = {"moengage": ["dev", "qa", "master"],
                                "dashboard-ui": ["dev", "qa", "master"],
                                "segmentation": ["develop", "release", "master", "qa"],
                                "commons": ["develop", "release", "master", "qa"],
                                "product-management": ["develop", "release", "master", "qa"]
                                }
sensitive_branches_default = ["develop", "release", "master", "qa", "dev"]
