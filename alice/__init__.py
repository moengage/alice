from flask import Flask, request, jsonify, abort
import simplejson as json
from alice.main.runner import RunChecks
from alice.helper.log_utils import LOG
from alice.commons.base_jira import JiraPayloadParser
from alice.main.jira_actor import JiraActor

app = Flask(__name__)


def verify_request(payload, token):
    import hmac, hashlib, os
    from alice.helper.file_utils import get_dict_from_config_file

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


@app.route("/alice", methods=['POST'])
def alice():
    payload = request.get_data()
    if 'X-Hub-Signature' not in request.headers:
        return jsonify("X-Hub-Signature Header missing")

    if not verify_request(payload, request.headers['X-Hub-Signature']):
        return jsonify("Not Authorized")

    payload = json.loads(payload)

    if "pull_request" not in payload:
        return jsonify("Not a Pull request")

    merge_correctness = RunChecks().run_checks(payload)
    return jsonify(merge_correctness)


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

        if not verify_request(payload, request.headers['X-Hub-Signature']):
            return {"401": "Not Authorized"}

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
