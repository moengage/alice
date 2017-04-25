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
from alice.helper.log_utils import logger
from logging import Formatter, FileHandler

app = Flask(__name__)


class Actor(Base):
    
    def __init__(self, pr_payload):
        self.pr = pr_payload
        self.github = GithubHelper(self.pr.config.organisation, self.pr.repo, self.pr.config.githubToken, self.pr.link)
        self.slack = SlackHelper(self.pr.config)
        self.change_requires_product_plus1 = False
        self.is_product_plus1 = False
        self.sensitive_file_touched = {}
        if self.pr.is_merged:
            self.parse_files_and_set_flags()

        self.base_branch = self.pr.base_branch
        self.head_branch = self.pr.head_branch
        self.created_by = self.pr.config.getSlackName(self.pr.opened_by)
        self.merged_by = self.pr.config.getSlackName(self.pr.merged_by)
        logger.debug("I'm Here")


    def was_eligible_to_merge(self):
        """
        checks for +1 in review approved
        :return:
        """
        if self.pr.is_merged: #and self.head_branch in PushPayload.PROTECTED_BRANCH_LIST:  TO ENABLE
            is_bad_pr = self.is_reviewed(self.created_by)
            logger.info("Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=is_bad_pr))
            return {"msg":"Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=is_bad_pr)}
        return {"msg":"Skipped review because its not PR merge event"}


    def add_comment(self):
        """
        add comment on opened PR
        :return:
        """
        if self.pr.is_opened:
            if not self.pr.config.is_debug:
                if self.pr.base_branch == self.pr.config.mainBranch:
                    guideline_comment = special_comment
                else:
                    guideline_comment = general_comment
                self.github.comment_pr(self.pr.comments_section, guideline_comment)
                logger.info("**** Added Comment of dev guidelines ***")
                return {"msg": "Added Comment of dev guidelines"}
            return {"msg": "Skipped commenting because DEBUG is on "}
        return {"msg": "Skipped commenting because its not PR opened"}


    def slack_merged_to_channel(self):
        """
        store merged PR data to respective channel
        :return:
        """
        if self.pr.is_merged and self.pr.is_sensitive_branch:
            #print "**** Repo=" + repo + ", new merge came to " + base_branch + " set trace to " + code_merge_channel + " channel"
            msg = MSG_CODE_CHANNEL.format(title=self.pr.title, desc=self.pr.description, pr=self.pr.link,
                                          head_branch=self.pr.head_branch, base_branch=self.pr.base_branch,
                                          pr_by=self.created_by, merge_by=self.merged_by)
            return msg
            # TO DO: slack.postToSlack(code_merge_channel, msg, data={"username": bot_name})  # code-merged

    def slack_lead_on_specific_action(self):
        """
        keep lead posted on particular action on sensitive branch
        :return:
        """
        #if self.pr.is_opened:
        desired_action = self.pr.config.actionToBeNotifiedFor
        if self.pr.action == desired_action:
            if self.pr.base_branch == self.pr.config.mainBranch:
                msg = MSG_OPENED_TO_MAIN_BRANCH.format(repo=self.pr.repo, pr_by=self.created_by,
                                                       main_branch=self.pr.config.mainBranch, title=self.pr.title,
                                                       pr=self.pr.link_pretty, action=self.pr.action)
                for person in self.pr.config.techLeadsToBeNotified:
                    self.slack.postToSlack(person, msg + MSG_RELEASE_PREPARATION)
                logger.info("Notified to %s on action %s" % (self.pr.config.techLeadsToBeNotified, self.pr.action))
                return {"msg": "Notified to %s on action %s" % (self.pr.config.techLeadsToBeNotified, self.pr.action)}
            else:
                msg = MSG_OPENED_TO_PREVENTED_BRANCH.format(repo=self.pr.repo, pr_by=self.created_by,
                                                            base_branch=self.pr.base_branch, title=self.pr.title,
                                                            pr=self.pr.link_pretty, action=self.pr.action)
                self.slack.postToSlack('@' + self.pr.config.personToBeNotified, msg)
                logger.info("Notified to %s on action %s" % (self.pr.config.personToBeNotified, self.pr.action))
                return {"msg": "Notified to %s on action %s" %(self.pr.config.personToBeNotified,self.pr.action)}
        return {"msg": "Skipped notify because its not desired event %s" % self.pr.action}


    def slack_creator_for_release_guidelines(self):
        if self.pr.is_merged:
            if self.base_branch in self.pr.config.sensitiveBranches:
                msg = MSG_GUIDELINE_ON_MERGE.format(person=self.created_by, pr= self.pr.link_pretty,
                                                    base_branch=self.pr.base_branch, title=self.pr.title)
                self.slack.directSlack('@' + self.created_by, msg)
                logger.info("slacked personally to %s" %self.created_by)
                return {"msg":"slacked personally to %s" %self.created_by}
            return {"msg": "skipped slack personally because not sensitive branch"}
        return {"msg": "skipped slack personally because its not merge event" % self.created_by}


    def close_dangerous_pr(self):
        if self.pr.is_opened or self.pr.is_reopened:
            master_branch = self.pr.config.mainBranch
            qa_branch =  self.pr.config.testBranch
            if self.base_branch == master_branch and self.head_branch != qa_branch:
                msg = MSG_AUTO_CLOSE.format(tested_branch=qa_branch, main_branch=master_branch)
                self.github.modify_pr(msg, "closed")
                self.slack.postToSlack(self.pr.config.alertChannelName, "@" + self.created_by + ": " + msg)
                logger.info("closed dangerous PR %s" % self.pr.link_pretty)
                return {"msg":"closed dangerous PR %s"%self.pr.link_pretty}
            return {"msg": "skipped closing PR because not raised to mainBranch %s" % self.pr.link_pretty}
        return {"msg": "skipped closing PR because not a opened PR"}


    def notify_on_sensitive_files_touched(self):
        if self.pr.is_merged:
            if self.sensitive_file_touched.get("is_found"):
                msg = MSG_SENSITIVE_FILE_TOUCHED.format(
                    notify_folks = self.pr.config.devOpsTeam, file=self.sensitive_file_touched["file_name"],
                    pr=self.pr.link_pretty, pr_by=self.created_by, pr_number=self.pr.number)
                self.slack.postToSlack(self.pr.config.alertChannelName, msg)
                logger.info("informed %s because sensitive files are touched" % self.pr.config.devOpsTeam)
                return {"msg":"informed %s because sensitive files are touched" % self.pr.config.devOpsTeam}
            return {"msg": "Skipped sensitive files alerts because no sensitive file being touched"}
        return {"msg": "Skipped sensitive files alerts because its not PR merge event" % self.pr.config.devOpsTeam}



    def notify_QA_signOff(self):
        if self.pr.is_merged and self.pr.base_branch == self.pr.config.mainBranch\
                and self.pr.head_branch == self.pr.config.testBranch:
            msg = MSG_QA_SIGN_OFF.format(person=self.pr.config.personToBeNotified, pr=self.pr.link_pretty,
                                         dev_ops_team=self.pr.config.devOpsTeam,
                                         tech_team=self.pr.config.techLeadsToBeNotified)

            self.slack.postToSlack(self.pr.config.alertChannelName, msg,
                                   data=self.slack.getBot(channel_name, self.merged_by))
            """ for bot """
            write_to_file_from_top(release_freeze_details_path, ":clubs:" +
                                   str(datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
                                       '%B %d,%Y at %I.%M %p')) + " with <" + self.pr.link_pretty + "|master> code")  # on:" + str(datetime.datetime.now().strftime('%B %d, %Y @ %I.%M%p'))
            clear_file(code_freeze_details_path)


    def notify_to_add_release_notes_for_next_release(self):
        pass

    def announce_code_freeze(self):
        pass

    def ci_lint_checker(self):
        pass

    def ci_unit_tests(self):
        pass

    def is_reviewed(self, created_by_slack_nick):
        reviews = self.github.get_reviews()
        if 200 != reviews.status_code:
            raise Exception(reviews.content)

        #logger.debug("##### reviews= %s #####" + reviews.content)
        bad_pr = True
        logger.info("***** Reading Reviews *****")
        for item in json.loads(reviews.content):
            if "APPROVED" == item["state"]:
                review_comment = item["body"]
                logger.debug("review body= %s" + review_comment)
                thumbsUpIcon = THUMBS_UP_ICON in json.dumps(review_comment)
                logger.debug("unicode thumbsUp icon present=%s" % (thumbsUpIcon))
                if self.created_by in self.pr.config.superMembers:  # FEW FOLKS TO ALLOW TO HAVE SUPER POWER
                    logger.debug("PR is opened by %s who is the super user of repo %s, so NO alert'"
                                 % (self.pr.opened_by_slack, self.pr.repo))
                    bad_pr = False
                    break
                print "***** review_comment", review_comment
                if item["user"]["login"] != self.created_by and (review_comment.find("+1") != -1 or thumbsUpIcon):
                    logger.debug("+1 found from reviewer=%s marking No Alert" + item["user"]["login"])
                    bad_pr = False
                    break

        bad_name_str = MSG_BAD_START + "@" + created_by_slack_nick
        if bad_pr:
            msg = MSG_NO_TECH_REVIEW.format(name=bad_name_str, pr=self.pr.link_pretty, title=self.pr.title,
                                            branch=self.pr.base_branch, team=self.pr.config.alertChannelName)
            logger.debug(msg)
            self.slack.postToSlack(self.pr.config.alertChannelName, msg)
        return bad_pr

    def parse_files_and_set_flags(self):
        files_contents = self.github.get_files()
        self.change_requires_product_plus1 = False
        self.is_product_plus1 = False
        logger.info("**** Reading files ****")
        for item in files_contents:
            file_path = item["filename"]
            if any(x in str(file_path) for x in self.pr.config.sensitiveFiles):
                self.sensitive_file_touched["is_found"] = True
                self.sensitive_file_touched["file_name"] = str(file_path)
            if item["filename"].find(self.pr.config.productPlusRequiredDirPattern) != -1:
                logger.info("product change found marking ui_change to True")
                self.change_requires_product_plus1 = True
                # break


@app.route("/merge", methods=['POST'])
def merge():
    if request.method != 'POST':
        abort(501)
    payload = request.get_data()
    data = json.loads(unicode(payload, errors='replace'), strict=False)
    pull_request = Actor(PushPayloadParser(request, payload=data))

    steps = pull_request.pr.config.checks
    merge_correctness = run_checks(pull_request, steps)
    return jsonify(merge_correctness)


def run_checks(actor, steps):
    merge_correctness = {}
    if actor.is_sensitive_branch:
        if len(steps) == 0:
            actor.close_dangerous_pr()
            actor.add_comment()
            actor.slack_lead_on_specific_action()
            merge_correctness = actor.was_eligible_to_merge()
            actor.slack_merged_to_channel()
            actor.slack_creator_for_release_guidelines()
            actor.notify_on_sensitive_files_touched()
            actor.notify_QA_signOff()
        else:
            for item in steps:
                check_type = item.lower()
                if check_type == Action.CLOSE_DANGEROUS_PR.value:
                    actor.close_dangerous_pr()
                elif check_type == Action.GUIDELINES.value:
                    actor.add_comment()
                elif check_type == Action.SLACK_DIRECT_ON_GIVEN_ACTION.value:
                    actor.slack_lead_on_specific_action()
                if check_type == Action.TECH_REVIEW.value:
                    merge_correctness = actor.was_eligible_to_merge()
                elif check_type == Action.PRODUCT_REVIEW.value:
                    pass
                elif check_type == Action.SLACK_CHANNEL_ON_MERGE.value:
                    actor.slack_merged_to_channel()
                elif check_type == Action.SLACK_REMIND_FOR_RELEASE_GUIDELINE.value:
                    actor.slack_creator_for_release_guidelines()
                elif check_type == Action.NOTIFY_SENSITIVE_FILES_TOUCHED.value:
                    actor.notify_on_sensitive_files_touched()
                elif check_type == Action.NOTIFY_QA_SIGN_OFF.value:
                    actor.notify_QA_signOff()
        return merge_correctness
    logger.info("skipped because '%s' is not sensitive branch" %actor.base_branch)
    return {"msg":"skipped because '%s' is not sensitive branch" %actor.base_branch}



@app.route("/", methods=['GET', 'POST'])
def hello():
    return "Welcome to the world of Alice "


@app.before_first_request
def setup_logging():
    if not app.debug:
        # In production mode, add log handler to sys.stderr.
        # file_handler = FileHandler('output.log')
        # handler = logging.StreamHandler()
        # file_handler.setLevel(logging.DEBUG)
        # handler.setLevel(logging.DEBUG)
        # file_handler.setFormatter(Formatter(
        #     '%(asctime)s %(levelname)s: %(message)s '
        #     '[in %(pathname)s:%(lineno)d]'
        # ))
        # handler.setFormatter(Formatter(
        #     '%(asctime)s %(levelname)s: %(message)s '
        #     '[in %(pathname)s:%(lineno)d]'
        # ))
        # app.logger.addHandler(handler)
        # app.logger.addHandler(file_handler)
        #
        # app.logger.info('****** flask logger ...')
        logger.debug('************ log from setup_config *********')


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


class Action(Enum):

    TECH_REVIEW = "tech_review"
    PRODUCT_REVIEW = "product_review"
    GUIDELINES = "comment_guidelines"
    SLACK_DIRECT_ON_GIVEN_ACTION = "notify_direct_on_given_action"
    SLACK_CHANNEL_ON_MERGE = "notify_channel_on_merge"
    NOTIFY_QA_SIGN_OFF = "notify_qa_sign_off"
    NOTIFY_SENSITIVE_FILES_TOUCHED = "notify_on_sensitive_files_touched"
    CLOSE_DANGEROUS_PR = "close_dangerous_pr"
    SLACK_REMIND_FOR_RELEASE_GUIDELINE = "remind_direct_for_release_guideline_on_merge"





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

