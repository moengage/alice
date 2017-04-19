from flask import Flask, request, jsonify, abort
from logging.handlers import RotatingFileHandler
from alice.helper.constants  import *
import requests
#from flask import app as application
import simplejson as json
from alice.config.message_template import *
from alice.commons.base import Base, PushPayloadParser
from alice.helper.github_helper import GithubHelper, PRFilesNotFoundException
from alice.helper.slack_helper import SlackHelper
application = Flask(__name__)


class Actor(Base):
    
    def __init__(self, pr_payload):
        self.pr = pr_payload
        self.github = GithubHelper(self.pr.config.githubToken)
        self.slack = SlackHelper(self.pr.config.slackToken)
        self.change_requires_product_plus1 = False
        self.is_product_plus1 = False
        self.sensitive_file_touched = {}
        if self.pr.is_merged:
            self.parse_files_and_set_flags()


    def was_eligible_to_merge(self):
        if self.pr.is_merged: #and self.head_branch in PushPayload.PROTECTED_BRANCH_LIST:  TO ENABLE
            is_bad_pr = self.is_reviewed(self.pr.created_by_slack_nick)
            return "Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=is_bad_pr)


    def is_reviewed(self, created_by_slack_nick):
        reviews = self.github.get_reviews(self.pr.link)
        if 200 != reviews.status_code:
            return reviews.content

        print "************ My REVIEWS ***********", reviews.content
        bad_pr = True
        for item in json.loads(reviews.content):
            review_comment = item["body"]
            logger.debug("review body= %s", review_comment)
            thumbsUpIcon = THUMBS_UP_ICON in json.dumps(review_comment)
            print "thumbsUpIcon present=", thumbsUpIcon

            if self.pr.pr_by in VALID_CONTRIBUTORS:  # FEW FOLKS TO ALLOW TO HAVE SUPER POWER
                logger.debug("pr_by is super user of repo %s, so NO alert'", self.pr.repo)
                bad_pr = False
                break

            if item["user"]["login"] != self.pr.pr_by and (review_comment.find("+1") != -1 or thumbsUpIcon):
                logger.debug(" No Alert because +1 found from commenter=%s breaking further comments checks", item["user"]["login"] )
                bad_pr = False
                break

        bad_name_str = MSG_BAD_START + "@" + created_by_slack_nick
        if bad_pr:
            msg = MSG_NO_TECH_REVIEW.format(name=bad_name_str, pr=self.pr.link_pretty, branch= self.pr.base_branch,
                                            team=self.pr.config.alertChannelName)
            print msg
            self.slack.postToSlack(channel_name, msg, data={"username": bot_name})
        return bad_pr

    def parse_files_and_set_flags(self):
        try:
            self.github.get_reviews(self.pr.link)
            files_contents = self.github.get_files(self.pr.link)
        except PRFilesNotFoundException, e:
            files_contents = e.pr_response

        if "message" in files_contents:
            return files_contents  # STOP as files not found

        self.change_requires_product_plus1 = False
        self.is_product_plus1 = False
        print "changed files-"
        for item in files_contents:
            file_path = item["filename"]
            print file_path
            if any(x in str(file_path) for x in self.pr.config.sensitiveFiles):
                self.sensitive_file_touched["is_found"] = True
                self.sensitive_file_touched["file_name"] = str(file_path)
            if item["filename"].find(self.pr.config.productPlusRequiredDirPattern) != -1:
                print "dashboard change found marking ui_change to True"
                self.change_requires_product_plus1 = True
                # break

    def add_comment(self):
        if self.pr.base_branch == self.pr.config.mainBranch:
            guideline_comment = special_comment
        else:
            guideline_comment = general_comment

        github_helper.comment_pr(self.pr.config.githubToken, self.pr.comments_section, guideline_comment)
        print "**** Added Comment of dev guidelines ***"


    def slack_merged_to_channel(self):
        if self.pr.is_merged and self.pr.is_sensitive_branch:
            #print "**** Repo=" + repo + ", new merge came to " + base_branch + " set trace to " + code_merge_channel + " channel"
            msg = MSG_CODE_CHANNEL.format(title=title_pr, desc=body_pr, pr=self.pr.link,
                                          head_branch=self.pr.head_branch, base_branch=self.pr.base_branch,
                                          pr_by=self.pr.by_slack, merge_by=self.pr.merged_by_slack_nick)
            return msg
            #slack_helper.postToSlack(code_merge_channel, msg, data={"username": bot_name})  # code-merged


    def slack_direct_on_open(self):
        desired_action = self.pr.config.actionToBeNotifiedFor
        if self.pr.action == desired_action:
            if self.pr.base_branch == self.pr.config.mainBranch:
                for person in self.pr.config.techLeadsToBeNotified:
                    self.slack.postToSlack(person, msg + MSG_RELEASE_PREPARATION, data={"username": bot_name}, parseFull=False)
            else:
                self.slack.postToSlack('@' + self.pr.config.personToBeNotified, msg, data={"username": bot_name},
                                       parseFull=False)


    def slack_personally_for_release_guidelines(self):
        msg = MSG_GUIDELINE_ON_MERGE.format(person=self.pr.by_slack, pr_link= self.pr.link,
                                            base_branch=self.pr.base_branch)
        slack_helper.postToSlack('@'+ self.pr.created_by_slack_nick, msg)


    def close_dangerous_pr(self):
        msg = MSG_AUTO_CLOSE.format(tested_branch=self.pr.config.testBranch, main_branch=self.pr.config.mainBranch)
        self.github.modify_pr(msg, "closed")
        self.slack.postToSlack(self.pr.config.alertChannelName, "@" + self.pr.by_slack + ": " + msg)

    def notify_on_sensitive_files_touched(self):
        if sensitive_file_touched.get("is_found"):
            self.slack.postToSlack(channel_name, dev_ops_team + " " + sensitive_file_touched["file_name"]
                                   + " is modified in PR=" + pr_link + " by @" + pr_by_slack, data={"username": bot_name},
                                   parseFull=False)


    def personal_msgs_to_leads_on_release_freeze(self):
        pass

    def announce_code_freeze(self):
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

