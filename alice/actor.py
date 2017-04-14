from flask import Flask, request, jsonify, abort
from logging.handlers import RotatingFileHandler
from alice.helper.constants  import *
import requests
#from flask import app as application
import simplejson as json
from alice.helper.message_template import *
from alice.commons.base import Base, PushPayloadParser
application = Flask(__name__)


class Actor(Base):
    
    def __init__(self, pr_payload):
        self.pr = pr_payload

    def was_eligible_to_merge(self):
        if self.pr.is_merged: #and self.head_branch in PushPayload.PROTECTED_BRANCH_LIST:  TO ENABLE
            is_bad_pr = self.is_reviewed(self.pr.created_by_slack_nick)
            return "Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=is_bad_pr)

    def is_reviewed(self, created_by_slack_nick):
        reviews = requests.get(self.pr.link + "/" + PushPayloadParser.EP_REVIEWS, headers={
            "Authorization": "token "+self.pr.config.getGithubToken(), "Accept":GITHUB_REVIEW_ACCEPT_KEY})
        if 200 != reviews.status_code:
            return reviews.content

        print "************ My REVIEWS ***********", reviews.content
        bad_pr = True
        for item in json.loads(reviews.content):
            print item
            comment = item["body"]
            logger.debug("review body= %s", item['body'])
            print item["state"]
            thumbsUpIcon = THUMBS_UP_ICON in json.dumps(comment)
            print "thumbsUpIcon present=", thumbsUpIcon

            if self.pr.pr_by in VALID_CONTRIBUTORS:  # FEW FOLKS TO ALLOW TO HAVE SUPER POWER
                logger.debug("pr_by is super user of repo %s, so NO alert'", self.pr.repo)
                bad_pr = False
                break

            if item["user"]["login"] != self.pr.pr_by and (comment.find("+1") != -1 or thumbsUpIcon):
                logger.debug(" No Alert because +1 found from commenter=%s breaking further comments checks", item["user"]["login"] )
                bad_pr = False
                break

        bad_name_str = "Very Bad @" + created_by_slack_nick
        if bad_pr:
            msg = MSG_NO_TECH_REVIEW.format(name=bad_name_str, pr=self.pr.link_pretty, branch= self.pr.base_branch,
                                            team=self.pr.config.getAlertChannelName())
            print msg
            #postToSlack(channel_name, msg, data={"username": bot_name})
        return bad_pr

    def add_comment(self):
        if self.pr.base_branch == self.pr.config.getSpecialBranchNameToAddComment():
            guideline_comment = special_comment
        else:
            guideline_comment = general_comment
        res = requests.post(self.pr.comments_section, headers={"Authorization": "token " + self.pr.config.getGithubToken()}
                            , data=json.dumps(guideline_comment))
        print "**** Added Comment of dev guidelines ***"


    def record_merged_to_channel(self):
        if self.pr.is_merged and self.pr.is_sensitive_branch:
            #print "**** Repo=" + repo + ", new merge came to " + base_branch + " set trace to " + code_merge_channel + " channel"
            msg = "Title=\"{0}\",  Description=\"{1}\" \nPR: {2}\n from {3} into `{4}` By: *{5}*, mergedBy: {6}\n".format(
                title_pr, body_pr, link_pr, head_branch, base_branch, by_slack, self.pr.merged_by_slack_nick)
            return msg
            #postToSlack(code_merge_channel, msg, data={"username": bot_name})  # code-merged

    def notify_direct_on_open(self):
        pass


    def personal_msg_for_release_guidlines(self):
        pass


    def close_dangerous_pr(self):
        pass

    def notify_on_sensitive_files_touched(self):
        pass

    def personal_msgs_on_release_freeze(self):
        pass

    def announce_code_freez(self):
        pass


    def ci_lint_checker(self):
        pass

    def ci_unit_tests(self):
        pass



@application.route("/merge", methods=['POST'])
def merge():
    if request.method != 'POST':
        abort(501)
    payload = request.get_data()
    data = json.loads(unicode(payload, errors='replace'), strict=False)
    pull_request = Actor(PushPayloadParser(request, payload=data))
    merge_correctness = pull_request.was_eligible_to_merge()

    return jsonify(merge_correctness)


@application.route("/", methods=['GET','POST'])
def hello():
    return "Welcome to the world of Alice"


if __name__ == "__main__":
    #application.run()
    handler = RotatingFileHandler('app.log', maxBytes=100000, backupCount=3)
    logger = logging.getLogger('tdm')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    application.run(debug=True,
        host="0.0.0.0",
        port=int("5005")
    )


# @application.after_request
# def after_request(response):
#     timestamp = strftime('[%Y-%b-%d %H:%M]')
#     application.logger.error('%s %s %s %s %s %s', timestamp, request.remote_addr, request.method, request.scheme, request.full_path, response.status)
#     return response

# @application.errorhandler(Exception)
# def exceptions(e):
#     tb = traceback.format_exc()
#     timestamp = strftime('[%Y-%b-%d %H:%M]')
#     application.logger.error('%s %s %s %s %s 5xx INTERNAL SERVER ERROR\n%s', timestamp, request.remote_addr, request.method, request.scheme, request.full_path, tb)
#     return e.status_code

