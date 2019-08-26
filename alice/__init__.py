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

from celery import Celery

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


@app.route("/alice", methods=['POST'])
def alice():
    payload = request.get_data()
    data = json.loads(unicode(payload, errors='replace'), strict=False)
    run.delay(data)
    # merge_correctness = RunChecks().run_checks(data)
    # return jsonify(merge_correctness)


@celery.task
def run(data):
    with app.app_context():
        merge_correctness = RunChecks().run_checks(data)
        return jsonify(merge_correctness)


@app.route("/", methods=['GET', 'POST'])
def home():
    return "************ Welcome to the wonderful world of Alice ***********"


# view to handle data coming from jira webhook
# @app.route("/alice/jira", methods=['GET', 'POST'])
# def jira_integration():
#     if request.method == 'GET':
#         return "************ listening from jira webhook ***********"
#     if request.method == 'POST':
#         payload = request.get_data()
#         print("************* payload ***************", payload)
#         data = json.loads(payload)
#
#         # if not verify_request(payload, request.headers['X-Hub-Signature']):
#         #     return {"401": "Not Authorized"}
#
#         print("************* data ***************", data)
#         parsed_data = JiraPayloadParser(request, data)
#         actor_obj = JiraActor(parsed_data)
#         if parsed_data.webhook_event == "jira:issue_updated":
#             actor_obj.get_slack_users()
#             actor_obj.handle_issue_update()
#         elif parsed_data.webhook_event == "jira:issue_created":
#             actor_obj.get_slack_users()
#             actor_obj.handle_issue_create()
#         else:
#             actor_obj.fetch_users()  # fetch users mentioned in jira comment which are jira user key
#             actor_obj.fetch_email()  # fetch respective email of users mentioned in jira comment using jira user keys
#             actor_obj.get_slack_users()  # fetch current slack user
#             response = actor_obj.slack_jira_map()  # create jira slack map {<jira_user_key> : <slack_user_id>}
#             if response == False:
#                 return "Email not found"
#             actor_obj.send_to_slack()
#         return "******** jira post request ************"


@app.before_first_request
def setup_logging():
    if not app.debug:
        LOG.debug('************ log from setup_config *********')
