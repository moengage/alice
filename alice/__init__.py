from flask import Flask, request, jsonify, abort
import simplejson as json
from alice.main.runner import RunChecks
from alice.helper.log_utils import LOG

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
    return "************ Welcome to the world of Alice ***********"


@app.before_first_request
def setup_logging():
    if not app.debug:
        LOG.debug('************ log from setup_config *********')

