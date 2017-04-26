from flask import Flask, request, jsonify, abort
# from logging.handlers import RotatingFileHandler
from alice.helper.constants  import *
import requests
#from flask import app as application
import simplejson as json
from alice.config.message_template import *
from alice.commons.base import Base, PushPayloadParser
from alice.helper.github_helper import GithubHelper, PRFilesNotFoundException
from alice.helper.slack_helper import SlackHelper
from alice.helper.file_utlis import write_to_file_from_top, clear_file
from enum import Enum
import logging
from alice.helper.log_utils import LOG
from logging import Formatter, FileHandler
from alice.main.runner import RunChecks

app = Flask(__name__)


class Actor(Base):
    
    def __init__(self, github, pr):
        self.github = github
        self.pr = pr
        super(Actor, self).__init__()

    def parse_files_and_set_flags(self):
        files_contents = self.github.get_files()
        change_requires_product_plus1 = False
        sensitive_file_touched = {}
        LOG.info("**** Reading files ****")
        for item in files_contents:
            file_path = item["filename"]
            if any(x in str(file_path) for x in self.pr.config.sensitiveFiles):
                sensitive_file_touched["is_found"] = True
                sensitive_file_touched["file_name"] = str(file_path)
            if item["filename"].find(self.pr.config.productPlusRequiredDirPattern) != -1:
                LOG.info("product change found marking ui_change to True")
                change_requires_product_plus1 = True
                # break
        return (sensitive_file_touched, change_requires_product_plus1)

    def is_bad_pr(self):
        reviews = self.github.get_reviews()
        if 200 != reviews.status_code:
            raise Exception(reviews.content)

        # logger.debug("##### reviews= %s #####" + reviews.content)
        bad_pr = True
        LOG.info("***** Reading Reviews *****")
        for item in json.loads(reviews.content):
            if "APPROVED" == item["state"]:
                review_comment = item["body"]
                LOG.debug("review body= %s" + review_comment)
                thumbsUpIcon = THUMBS_UP_ICON in json.dumps(review_comment)
                LOG.debug("unicode thumbsUp icon present=%s" % (thumbsUpIcon))
                if self.created_by in self.pr.config.superMembers:  # FEW FOLKS TO ALLOW TO HAVE SUPER POWER
                    LOG.debug("PR is opened by %s who is the super user of repo %s, so NO alert'"
                              % (self.pr.opened_by_slack, self.pr.repo))
                    bad_pr = False
                    break
                print "***** review_comment", review_comment
                created_by = self.pr.config.getSlackName(self.pr.opened_by)
                if item["user"]["login"] != created_by and (review_comment.find("+1") != -1 or thumbsUpIcon):
                    LOG.debug("+1 found from reviewer=%s marking No Alert" + item["user"]["login"])
                    bad_pr = False
                    break
        return bad_pr


@app.route("/merge", methods=['POST'])
def merge():
    if request.method != 'POST':
        abort(501)
    payload = request.get_data()
    data = json.loads(unicode(payload, errors='replace'), strict=False)
    merge_correctness = RunChecks().run_checks(request, data)
    return jsonify(merge_correctness)


@app.route("/", methods=['GET', 'POST'])
def hello():
    return "Welcome to the world of Alice "


@app.before_first_request
def setup_logging():
    if not app.debug:
        LOG.debug('************ log from setup_config *********')

# if __name__ == "__main__":
#     #application.run()
#     handler = RotatingFileHandler('app.log', maxBytes=100000, backupCount=3)
#     logger = logging.getLogger('tdm')
#     logger.setLevel(logging.DEBUG)
#     logger.addHandler(handler)
#
#     application.run(debug=True,
#         host="0.0.0.0",
#         port=int("5006")
#     )

