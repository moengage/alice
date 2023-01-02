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
EXTEND_ALICE = "https://github.com/moengage/alice/blob/master/docs/extend_alice.md"
config_file = "https://github.com/moengage/alice/blob/master/docs/setup_config.md"
ISSUE_LINK = "https://github.com/moengage/alice/issues/new"

""" other constants """
THUMBS_UP_ICON = "\ud83d\udc4d"
SLACK_ICON = "https://cloud.githubusercontent.com/assets/12966925/25132384/021095fc-2467-11e7-95c0-78917bf4d52a.png"

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
context_api_test = "shield-api-test-python"

package_builder_branches_repo_wise = {
    "dashboard-ui": ["qa", "master"]
}
python_repo = ["MoEngage", "MoeDataScience", "mongoengine", "inapp-rest-service", "mongo", "segmentation",
               "commons", "idp-metadata", "datapoints", "oauth2", "saas", "dash", "user-profile", "key-metrics",
               "moengcache", "MoeAbTesting", "apns_client", "Bugsy_Backend", "product-management", "custom-segments",
               "product-recommendation", "s2s", "email-campaigns", "campaigns-core", "url_tracking",
               "dashboard-segmentation", "commons-core", "commons-frameworks", "commons-services",
               "segmentation-uis", "segmentation-client", "cards", "campaign-reports"]

file_path = "/opt/alice/release_items.txt"
file_mergedBy = "/opt/alice/release_mergedby.txt"
release_freeze_details_path = "/opt/alice/release_freeze_details.txt"
job_dir = "moe_repo_shield/"
job_name = job_dir + "CI_SyntaxValidator"
context_description = "Syntax Validation"
action_commit_to_investigate = ["opened", "open", "reopened", "synchronize"]

sensitive_branches_default = ["develop", "release", "master", "qa", "dev", "master_py2"]

bot_name = "Alice"
applaud_list = ["Awesome", "Great Efforts", "Good work", "Appreciate your efforts", "Perfect"]
post_checklist_msg = ["planned for VodQA? Click here to read more",
                      "here is your post release activities list", "had your vodQA? :thinking_face:",
                      "Click here for your checklist", "Scheduled Automation class?",
                      "Did you check *Let's Shine* here?",
                      "on your behalf, I have reminded PMs to update the release notes for next release. here is your checklist",
                      "6 points you may want to check now"]
code_freeze_details_path = "/opt/alice/code_freeze_details.txt"


merged_by_slack_name = ""

close_action = ["close", "closed", "merge", "merged"]
edited_action = ["edited"]
open_action = ["open", "opened"]

organization_repo = 'moengage'
master_branch = ['master', 'master_py2']
staging_branch = 'qa'
dev_branch = 'dev'
dev_branch_commons = 'develop'
staging_branch_commons = 'release'
ally_master_branch = 'ally/master'

moengage_repo = 'MoEngage'
dashboard = 'dashboard-ui'

repo_site_url = 'https://api.github.com/'
github_site_url = 'https://github.com/'

repos_slack = ['segmentation', 'commons']

ALICE_ERROR = "#shield-monitoring"

sensitive_files_master = "releasenotes"
sensitive_files_release = "changelog"

integration_test_file_path = "delight/viewhandlers/dashboard_handler.py"
integration_test_folder_path = ["delight/viewhandlers/saml/", "integration_tests/dashboard/"]


DRONE_URL = "https://drone.moengage.com/api/repos/{owner}/{repo}/builds/{build_no}"

DRONE_IGNORE_JOBS = ["clone", "Clone"]
DRONE_CONTEXT = "continuous-integration/drone/pr"

REPO_NOT_CLOSE = ["key-metrics",  "custom-segments", "value-suggestions", "dashboard-segmentation", "segmentation-uis",
                  "saas", "MoeDataScience", "user-profile", "cards"]

SKIP_SLACK_MESSAGE = ['dependabot[bot]']

JAVA_REPO = ['MoeDataScience']
syntax_java = "shield-java-compile"
unit_java = "shield-unit-test"

AMI_DEPENDENCY = "Block-PR"
AMI_LABEL = "ami_dependency"

RELEASE_CHECKLIST_REPOS = [moengage_repo, "email-campaigns"]
