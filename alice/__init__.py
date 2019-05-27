from flask import Flask, request, jsonify, abort
import simplejson as json
from alice.main.runner import RunChecks
from alice.helper.log_utils import LOG
from alice.commons.base_jira import JiraPayloadParser
from alice.main.jira_actor import JiraActor

app = Flask(__name__)

@app.route("/alice", methods=['POST'])
def alice():
    if request.method != 'POST':
        abort(501)
    payload = request.get_data()
    data = json.loads(unicode(payload, errors='replace'), strict=False)
    merge_correctness = RunChecks().run_checks(request, data)
    return jsonify(merge_correctness)

@app.route("/", methods=['GET', 'POST'])
def home():
    return "************ Welcome to the wonderful world of Alice ***********"


# view to handel data coming from jira webhook
@app.route("/alice/jira", methods=['GET', 'POST'])
def jira():
    if request.method == 'GET':
        return "************ listening from jira webhook ***********"
    if request.method == 'POST':
        payload = request.get_data()
        data = json.loads(unicode(payload, errors='replace'), strict=False)
        if data.get("webhookEvent") ==  "jira:issue_created":
            LOG.info("************ issue created data ************* %s" % data)
        if data.get("webhookEvent") ==  "jira:issue_updated":
            LOG.info("************ issue update data ************* %s" % data)
        if data.get("webhookEvent") ==  "comment_created":
            LOG.info("************ comment created data ************* %s" % data)
        parsed_data = JiraPayloadParser(request, data)
        LOG.info("*********** data ********** %s" % parsed_data.comment)
        LOG.info("*********** data ********** %s" % parsed_data.change_log)
        actor_obj = JiraActor(parsed_data)
        if parsed_data.webhook_event == "jira:issue_updated":
            actor_obj.get_slack_users()
            actor_obj.issue_update_handler()
        elif parsed_data.webhook_event == "jira:issue_created":
            actor_obj.get_slack_users()
            actor_obj.issue_create_handler()
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
