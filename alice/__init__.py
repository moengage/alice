from flask import Flask, request, jsonify, abort
import simplejson as json
import hmac
import hashlib
import os
import base64

from alice.helper.file_utils import get_dict_from_config_file
from alice.main.runner import RunChecks
from alice.helper.log_utils import LOG
from alice.commons.base_jira import JiraPayloadParser
from alice.main.jira_actor import JiraActor
from alice.main.actor import Infra
from alice.helper.constants import DRONE_URL, DRONE_IGNORE_JOBS, DRONE_CONTEXT
from alice.helper.api_manager import ApiManager
from alice.helper.slack_helper import SlackHelper
from alice.config.config_provider import ConfigProvider

app = Flask(__name__)


def verify_request_drone(header):
    # Setting for testing alice through postman
    config_file = os.environ.get("config")
    config = get_dict_from_config_file(config_file)
    debug = config.get('debug', False)
    if debug:
        return True

    key_str = ConfigProvider().drone_secret
    key = bytes(key_str, 'utf-8')
    date = header["Date"]
    digest = header["Digest"]
    string_formed_from_header = 'date: {date}\ndigest: {digest}'.format(date=date, digest=digest)

    signature = base64.b64encode(hmac.new(key, msg=string_formed_from_header, digestmod=hashlib.sha256).digest()).decode("utf-8")
    signature_to_match = str(header["Signature"].split(',')[-2].split('signature=')[1])
    print(signature, signature_to_match)

    if hmac.compare_digest(signature, signature_to_match):
        return True
    else:
        return False


def verify_request(payload, token):
    #Setting for testing alice through postman
    config_file = os.environ.get("config")
    config = get_dict_from_config_file(config_file)
    debug = config.get('debug', False)
    if debug:
        return True

    key = bytes('fHA3ogLICKad4JLU7jY9juYqZHQjBIXa608NLtFd', 'utf-8')
    # payload = bytes(payload, 'utf-8')
    digest = hmac.new(key, msg=payload, digestmod=hashlib.sha1)
    signature = "sha1=" + digest.hexdigest()
    if hmac.compare_digest(signature, token):
        return True
    else:
        return False


@app.route("/alice/issue", methods=['POST'])
def infra_request():
    payload = request.get_data()
    if 'X-Hub-Signature' not in request.headers:
        return jsonify("X-Hub-Signature Header missing")

    if not verify_request(payload, request.headers['X-Hub-Signature']):
        return jsonify("Not Authorized")

    payload = json.loads(payload)

    if "pull_request" not in payload and "repository" in payload:

        if payload["repository"]["name"] == "InfraRequests":
            Infra().infra_requests(payload)
            return jsonify("Notified for Infra requests")
        else:
            return jsonify("Not allowed for This Repo")

    else:
        return jsonify("No Matching Url")


@app.route("/alice/task", methods=['POST'])
def alice():
    payload = request.get_data()
    if 'X-Hub-Signature' not in request.headers:
        return jsonify("X-Hub-Signature Header missing")

    if not verify_request(payload, request.headers['X-Hub-Signature']):
        return jsonify("Not Authorized")

    payload = json.loads(payload)
    if "pull_request" not in payload:
        return jsonify("Not a Pull request")

    try:
        merge_correctness = RunChecks().run_checks(payload)
        return jsonify(merge_correctness)
    except:
        config = ConfigProvider()
        channel_name = '#shield-monitoring'
        msg = "<@UL91SP77H> Post Request failed in Alice for Pull request {}".format(payload["pull_request"]["html_url"])
        SlackHelper(config).postToSlack(channel_name, msg)
        print("Posted message to channel for fast lookup of why Alice Failed")


@app.route("/alice/drone", methods=['POST'])
def drone_build():
    if 'Digest' not in request.headers:
        return jsonify("Digest Header missing")

    if not verify_request_drone(request.headers):
        print("match nhi hua")
        return jsonify("Not Authorized")

    print("match ho gya")
    return ""

    payload = request.get_data()
    payload = json.loads(payload)
    context = payload["context"]
    sha = payload["sha"]
    if payload["state"] and context == DRONE_CONTEXT:
        target_url = payload["target_url"]
        build_no = target_url.split('/')[-1]
        repo_name = target_url.split('/')[-2]
        owner_repo = target_url.split('/')[-3]
        token_github = ConfigProvider().githubToken
        url_github = "https://api.github.com/repos/{owner_repo}/{repo}/statuses/{sha}".format(sha=sha, repo=repo_name, owner_repo=owner_repo)
        header_github = "token {token}".format(token=token_github)
        drone_url = DRONE_URL.format(owner=owner_repo, repo=repo_name, build_no=build_no)
        token = ConfigProvider().drone_token
        header = "Bearer {drone_token}".format(drone_token=token)
        resp = ApiManager.get(url=drone_url, headers={"Authorization": header})
        if resp["status_code"] == 200:
            data = json.loads(resp["content"])
            stages = data["stages"]
            for stage in stages:
                jobs = stage["steps"]
                for job in jobs:
                    if job["name"] not in DRONE_IGNORE_JOBS:
                        data = {
                            "state": payload["state"],
                            "target_url": target_url,
                            "description": "",
                            "context": job["name"],
                        }
                        resp = ApiManager.post(url=url_github, headers={"Authorization": header_github},
                                               data=json.dumps(data))

                        print(job["name"])

    return jsonify("Drone Build Recieved")


@app.route("/", methods=['GET'])
def home():
    return "************ Welcome to the wonderful world of Alice ***********"


# view to handle data coming from jira webhook
@app.route("/alice/jira", methods=['GET', 'POST'])
def jira_integration():
    if request.method == 'GET':
        return "************ listening from jira webhook ***********"
    if request.method == 'POST':
        payload = request.get_data()
        print("************* payload ***************", payload)
        data = json.loads(payload)

        # if not verify_request(payload, request.headers['X-Hub-Signature']):
        #     return {"401": "Not Authorized"}

        print("************* data ***************", data)
        parsed_data = JiraPayloadParser(request, data)
        actor_obj = JiraActor(parsed_data)
        if parsed_data.webhook_event == "jira:issue_updated":
            actor_obj.get_slack_users()
            actor_obj.handle_issue_update()
        elif parsed_data.webhook_event == "jira:issue_created":
            actor_obj.get_slack_users()
            actor_obj.handle_issue_create()
        else:
            actor_obj.fetch_users()  # fetch users mentioned in jira comment which are jira user key
            actor_obj.fetch_email()  # fetch respective email of users mentioned in jira comment using jira user keys
            actor_obj.get_slack_users()  # fetch current slack user
            actor_obj.slack_jira_map()  # create jira slack map {<jira_user_key> : <slack_user_id>}
            actor_obj.send_to_slack() 
        return "******** jira post request ************"


@app.before_first_request
def setup_logging():
    if not app.debug:
        LOG.debug('************ log from setup_config *********')