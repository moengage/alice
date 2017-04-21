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
from alice.helper.file_utlis import write_to_file_from_top, clear_file
from enum import Enum
application = Flask(__name__)


class Actor(Base):
    
    def __init__(self, pr_payload):
        self.pr = pr_payload
        self.github = GithubHelper(self.pr.config.organisation, self.pr.repo, self.pr.config.githubToken, self.pr.link)
        self.slack = SlackHelper(self.pr.config.slackToken)
        self.change_requires_product_plus1 = False
        self.is_product_plus1 = False
        self.sensitive_file_touched = {}
        if self.pr.is_merged:
            self.parse_files_and_set_flags()

        self.base_branch = self.pr.base_branch
        self.head_branch = self.pr.head_branch


    def was_eligible_to_merge(self):
        if self.pr.is_merged: #and self.head_branch in PushPayload.PROTECTED_BRANCH_LIST:  TO ENABLE
            is_bad_pr = self.is_reviewed(self.pr.created_by_slack_nick)
            return "Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=is_bad_pr)


    def is_reviewed(self, created_by_slack_nick):
        reviews = self.github.get_reviews()
        if 200 != reviews.status_code:
            raise Exception(reviews.content)

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
            self.slack.postToSlack(self.pr.config.alertChannelName, msg)
        return bad_pr

    def parse_files_and_set_flags(self):
        files_contents = self.github.get_files()
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
        if self.pr.is_opened:
            if self.pr.base_branch == self.pr.config.mainBranch:
                guideline_comment = special_comment
            else:
                guideline_comment = general_comment
            self.github.comment_pr(self.pr.config.githubToken, self.pr.comments_section, guideline_comment)
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
        if self.pr.is_opened:
            desired_action = self.pr.config.actionToBeNotifiedFor
            if self.pr.action == desired_action:
                if self.pr.base_branch == self.pr.config.mainBranch:
                    for person in self.pr.config.techLeadsToBeNotified:
                        self.slack.postToSlack(person, msg + MSG_RELEASE_PREPARATION, parseFull=False)
                else:
                    self.slack.postToSlack('@' + self.pr.config.personToBeNotified, msg,
                                           parseFull=False)


    def slack_personally_for_release_guidelines(self):
        if self.pr.is_merged:
            if self.base_branch in self.pr.config.sensitiveBranches:
                msg = MSG_GUIDELINE_ON_MERGE.format(person=self.pr.by_slack, pr_link= self.pr.link,
                                                    base_branch=self.pr.base_branch)
                slack_helper.postToSlack('@'+ self.pr.created_by_slack_nick, msg)

    def close_dangerous_pr(self):
        if self.pr.is_opened:
            master_branch = self.pr.config.mainBranch
            qa_branch =  self.pr.config.testBranch
            if self.base_branch == master_branch and self.head_branch != qa_branch:
                msg = MSG_AUTO_CLOSE.format(tested_branch=qa_branch, main_branch=master_branch)
                self.github.modify_pr(msg, "closed")
                self.slack.postToSlack(self.pr.config.alertChannelName, "@" + self.pr.by_slack + ": " + msg)

    def notify_on_sensitive_files_touched(self):
        if self.pr.is_merged:
            if sensitive_file_touched.get("is_found"):
                self.slack.postToSlack(self.pr.config.alertChannelName, dev_ops_team + " " + sensitive_file_touched["file_name"]
                                       + " is modified in PR=" + pr_link + " by @" + pr_by_slack,
                                       parseFull=False)


    def personal_msgs_to_leads_on_release_freeze(self):
        if self.pr.is_opened:
            pass

    def notify_QA_signOff(self):
        msg = "<@{0}>  QA passed :+1: `master` is updated <{1}|Details here>  Awaiting your go ahead. \n cc: {2} {3} ".\
            format(self.pr.config.personToBeNotified, data["pull_request"][
                "html_url"], self.pr.config.devOpsTeam, self.pr.config.techLeadsToBeNotified)

        self.slack.postToSlack(self.pr.config.alertChannelName, msg,
                               data=self.slack.getBot(channel_name, merged_by_slack), parseFull=False)
        """ for bot """
        write_to_file_from_top(release_freeze_details_path, ":clubs:" +
                               str(datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
                                   '%B %d,%Y at %I.%M %p')) + " with <" + pr_link + "|master> code")  # on:" + str(datetime.datetime.now().strftime('%B %d, %Y @ %I.%M%p'))
        clear_file(code_freeze_details_path)


    def notify_to_add_release_notes_for_next_release(self):
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
    steps = pull_request.pr.config.checks
    merge_correctness = {}
    #import pdb; pdb.set_trace()
    if len(steps) == 0:
            pull_request.close_dangerous_pr()
            pull_request.add_comment()
            pull_request.slack_direct_on_open()
            pull_request.personal_msgs_to_leads_on_release_freeze()

            merge_correctness = pull_request.was_eligible_to_merge()
            pull_request.slack_merged_to_channel()
            pull_request.slack_personally_for_release_guidelines()
            pull_request.notify_on_sensitive_files_touched()
    else:
        for item in steps:
            if item == Action.TECH_REVIEW.value:
                merge_correctness = pull_request.was_eligible_to_merge()
            elif item == Action.PRODUCT_REVIEW.value:
                pass
            elif item == Action.GUIDELINES.value:
                pull_request.add_comment()
            elif item == Action.DIRECT_ON_OPEN.value:
                pull_request.slack_direct_on_open()


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


class Action(Enum):

    TECH_REVIEW = "tech_review"
    PRODUCT_REVIEW = "product_review"
    GUIDELINES = "comment_guidelines"
    DIRECT_ON_OPEN = "slack_direct_on_pr_open"




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

