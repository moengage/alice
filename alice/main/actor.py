import simplejson as json

from alice.commons.base import Base
from alice.config.message_template import MSG_BAD_START, MSG_NO_TECH_REVIEW, MSG_AUTO_CLOSE, MSG_OPENED_TO_MAIN_BRANCH, \
    MSG_OPENED_TO_PREVENTED_BRANCH, SPECIAL_COMMENT, GENERAL_COMMENT, MSG_RELEASE_PREPARATION, \
    MSG_SENSITIVE_FILE_TOUCHED, MSG_QA_SIGN_OFF, MSG_CODE_CHANNEL, MSG_GUIDELINE_ON_MERGE
from alice.config.message_template import MSG_NO_PRODUCT_REVIEW
from alice.helper.constants import THUMBS_UP_ICON
from alice.helper.github_helper import GithubHelper
from alice.helper.github_helper import PRFilesNotFoundException
from alice.helper.log_utils import LOG
from alice.helper.slack_helper import SlackHelper


#app = Flask(__name__)


class Actor(Base):
    
    def __init__(self, pr):
        self.pr = pr
        self.github = GithubHelper(self.pr)
        self.slack = SlackHelper(self.pr.config)
        self.change_requires_product_plus1 = False
        self.is_product_plus1 = False
        self.sensitive_file_touched = {}
        self.base_branch = self.pr.base_branch
        self.head_branch = self.pr.head_branch
        self.created_by = self.pr.config.getSlackName(self.pr.opened_by)
        self.merged_by = self.pr.config.getSlackName(self.pr.merged_by)
        self.sensitive_file_touched, self.change_requires_product_plus1 = self.parse_files_and_set_flags()


    def parse_files_and_set_flags(self):
        """
        Parse payload and keep important flags ready to be used in checks
        :return: sensitive_file_touched (dict of file name with boolean value)
        :return: change_requires_product_plus1 (boolean)
        """
        change_requires_product_plus1 = False
        sensitive_file_touched = {}
        try:
            files_contents = self.github.get_files()
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
        except PRFilesNotFoundException, e:
            LOG.exception(e)
        return sensitive_file_touched, change_requires_product_plus1

    def is_bad_pr(self):
        """
        parse approval's content to identify if PR is actually approved or just random approval click
        :return: bad_pr (boolean)
        """
        reviews = self.github.get_reviews()
        if 200 != reviews.status_code:
            raise Exception(reviews.content)

        bad_pr = True
        LOG.info("***** Reading Reviews *****")
        for item in json.loads(reviews.content):
            if "APPROVED" == item["state"]:
                review_comment = item["body"]
                LOG.debug("review body= %s" + review_comment)
                thumbsUpIcon = THUMBS_UP_ICON in json.dumps(review_comment)
                LOG.debug("unicode thumbsUp icon present=%s" % (thumbsUpIcon))
                if self.pr.opened_by in self.pr.config.superMembers:  # FEW FOLKS TO ALLOW TO HAVE SUPER POWER
                    LOG.debug("PR is opened by %s who is the super user of repo %s, so NO alert'"
                              % (self.pr.opened_by_slack, self.pr.repo))
                    bad_pr = False
                    break
                print "***** review_comment", review_comment
                created_by = self.pr.config.getSlackName(self.pr.opened_by)
                if item["user"]["login"] != created_by and (review_comment.find("+1") != -1 or thumbsUpIcon):
                    LOG.debug("+1 is found from reviewer=%s marking No Alert " % item["user"]["login"])
                    bad_pr = False
                    break
        return bad_pr

    def validate_tech_approval(self):
        """
        notify in channel if not tech approved
        :return: relevant response dict
        """
        if self.pr.is_merged:  # and self.head_branch in PushPayload.PROTECTED_BRANCH_LIST:  TO ENABLE
            is_bad_pr = self.is_bad_pr()
            bad_name_str = MSG_BAD_START + "@" + self.created_by
            if is_bad_pr:
                msg = MSG_NO_TECH_REVIEW.format(name=bad_name_str, pr=self.pr.link_pretty, title=self.pr.title,
                                                branch=self.pr.base_branch, team=self.pr.config.cc_tech_team)
                LOG.debug(msg)
                self.slack.postToSlack(self.pr.config.alertChannelName, msg)
                LOG.info("Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=is_bad_pr))
                return {"msg": "Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=is_bad_pr)}
            return {"msg": "PR is approved so No Alerts"}
        return {"msg": "Skipped review because its not PR merge event"}

    def validate_product_approval(self):
        """
        notify in channel if not product approved (applicable only to files/dir which require product approval)
        :return: relevant response dict
        """
        if self.pr.is_merged:
            if self.pr.opened_by in self.pr.config.superMembers:
                LOG.debug('pr_opened_by is super user of {repo} so NO alert, super_members={super_members}'
                          .format(repo=self.pr.repo, super_members=self.pr.config.superMembers))
                return {"msg": "Skipped product review because the PR=%s is by a Super User" % self.pr.link_pretty}

            if self.change_requires_product_plus1:
                comments = self.github.get_comments()
                is_product_plus1 = self.is_plus_1_in_comments(comments, self.pr.config.productTeamGithub)
                if not is_product_plus1:
                    bad_name_str = MSG_BAD_START + "@" + self.created_by
                    msg = MSG_NO_PRODUCT_REVIEW.format(name=bad_name_str, pr=self.pr.link_pretty, title=self.pr.title,
                                                    branch=self.pr.base_branch, team="".join(self.pr.config.productTeamToBeNotified))
                    LOG.debug(msg)
                    self.slack.postToSlack(self.pr.config.alertChannelName, msg)
                    LOG.info("Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=self.is_bad_pr))
                    return {"msg": "Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=self.is_bad_pr)}
                return {"msg":"Product approved so no alert, pr=%s" %self.pr.link_pretty}
            return {"msg":"Skipped product review because no changes found which requires product +1 as well, PR=%s"
                          %self.pr.link_pretty}
        return {"msg": "Skipped product review because the PR=%s is not merged" %self.pr.link_pretty}

    def is_plus_1_in_comments(self, comments, team):
        """
        parse comments and check if :+1: exists (symbol for approval)
        :param comments:
        :return: relevant response dict
        """
        is_plus_1 = False
        if self.change_requires_product_plus1:
            for comment in json.loads(comments["content"]):
                thumbsUpIcon = "\ud83d\udc4d" in json.dumps(comment["body"])
                if self.change_requires_product_plus1 and (comment["user"]["login"] in team) \
                        and (comment["body"].find("+1") != -1 or thumbsUpIcon):
                    is_plus_1 = True
                    break
        return is_plus_1

    def comment_on_pr(self):
        """
        comment on pr
        :return: relevant response dict
        """
        if self.pr.is_opened:
            if not self.pr.config.is_debug:
                if self.pr.base_branch == self.pr.config.mainBranch:
                    guideline_comment = SPECIAL_COMMENT
                    self.slack.postToSlack(self.pr.opened_by)
                else:
                    guideline_comment = GENERAL_COMMENT
                self.github.comment_pr(self.pr.comments_section, guideline_comment)
                LOG.info("**** Added Comment of dev guidelines ***")
                return {"msg": "Added Comment of dev guidelines"}
            return {"msg": "Skipped commenting because DEBUG is on "}
        return {"msg": "Skipped commenting because its not PR opened"}


    def notify_on_action(self):
        """
        notify respective folk(s) on particular action. Ex. on open notify to lead (or on merged, can configure that)
        :return: relevant response dict
        """
        desired_action = self.pr.config.actionToBeNotifiedFor
        if self.pr.action == desired_action:
            if self.pr.base_branch == self.pr.config.mainBranch:
                msg = MSG_OPENED_TO_MAIN_BRANCH.format(repo=self.pr.repo, pr_by=self.created_by,
                                                       main_branch=self.pr.config.mainBranch, title=self.pr.title,
                                                       pr=self.pr.link_pretty, action=self.pr.action)
                for person in self.pr.config.techLeadsToBeNotified:
                    self.slack.postToSlack(person, msg + MSG_RELEASE_PREPARATION)
                LOG.info("Notified to %s on action %s" % (self.pr.config.techLeadsToBeNotified, self.pr.action))
                return {"msg": "Notified to %s on action %s" % (self.pr.config.techLeadsToBeNotified, self.pr.action)}
            else:
                msg = MSG_OPENED_TO_PREVENTED_BRANCH.format(repo=self.pr.repo, pr_by=self.created_by,
                                                            base_branch=self.pr.base_branch, title=self.pr.title,
                                                            pr=self.pr.link_pretty, action=self.pr.action)
                self.slack.postToSlack(self.pr.config.personToBeNotified, msg)
                LOG.info("Notified to %s on action %s" % (self.pr.config.personToBeNotified, self.pr.action))
                return {"msg": "Notified to %s on action %s" % (self.pr.config.personToBeNotified, self.pr.action)}
        return {"msg": "Skipped notify because its (%s) not desired event '%s'" %(self.pr.action, desired_action)}


    def remind_direct_release_guideline_on_merge(self):
        """
        remind individually to follow guidelines for QA process
        :return: relevant response dict
        """
        if self.pr.is_merged:
            if self.base_branch in self.pr.config.sensitiveBranches:
                msg = MSG_GUIDELINE_ON_MERGE.format(person=self.created_by, pr=self.pr.link_pretty,
                                                    base_branch=self.pr.base_branch, title=self.pr.title,
                                                    release_notes_link=self.pr.config.release_notes_link)
                self.slack.directSlack('@' + self.created_by, msg)
                LOG.info("slacked personally to %s" % self.created_by)
                return {"msg": "slacked personally to %s" % self.created_by}
            return {"msg": "skipped slack personally because not sensitive branch"}
        return {"msg": "skipped slack personally because its not merge event" % self.created_by}


    def close_dangerous_pr(self):
        """
        close a Pull Request which is not supposed to be opened Ex. base=master head=feature
        :return: relevant response dict
        """
        if self.pr.is_opened or self.pr.is_reopened:
            master_branch = self.pr.config.mainBranch
            qa_branch = self.pr.config.testBranch
            if self.base_branch == master_branch and self.head_branch != qa_branch:
                msg = MSG_AUTO_CLOSE.format(tested_branch=qa_branch, main_branch=master_branch)
                self.github.modify_pr(msg, "closed")
                self.slack.postToSlack(self.pr.config.alertChannelName, "@" + self.created_by + ": " + msg)
                LOG.info("closed dangerous PR %s" % self.pr.link_pretty)
                return {"msg": "closed dangerous PR %s" % self.pr.link_pretty}
            return {"msg": "skipped closing PR because not raised to mainBranch %s" % self.pr.link_pretty}
        return {"msg": "skipped closing PR because not a opened PR"}

    def notify_if_sensitive_modified(self):
        """
        check & notify devOps team if any sensitive files are touched
        :return: relevant response dict
        """
        if self.pr.is_merged:
            if self.sensitive_file_touched.get("is_found"):
                msg = MSG_SENSITIVE_FILE_TOUCHED.format(
                    notify_folks=self.pr.config.devOpsTeamToBeNotified, file=self.sensitive_file_touched["file_name"],
                    pr=self.pr.link_pretty, pr_by=self.created_by, pr_number=self.pr.number)
                self.slack.postToSlack(self.pr.config.alertChannelName, msg)
                LOG.info("informed %s because sensitive files are touched in pr=%s" %
                         (self.pr.config.devOpsTeamToBeNotified, self.pr.link_pretty))
                return {"msg": "informed %s because sensitive files are touched" % self.pr.config.devOpsTeamToBeNotified}
            return {"msg": "Skipped sensitive files alerts because no sensitive file being touched"}
        return {
            "msg": "Skipped sensitive files alerts because its not PR merge event %s" % self.pr.config.devOpsTeamToBeNotified}


    def notify_qa_sign(self):
        if self.pr.is_merged and self.pr.base_branch == self.pr.config.mainBranch \
                and self.pr.head_branch == self.pr.config.testBranch:
            msg = MSG_QA_SIGN_OFF.format(person=self.pr.config.personToBeNotified, pr=self.pr.link_pretty,
                                         dev_ops_team=self.pr.config.devOpsTeamToBeNotified,
                                         tech_team=self.pr.config.techLeadsToBeNotified)

            self.slack.postToSlack(self.pr.config.alertChannelName, msg,
                               data=self.slack.getBot(self.pr.config.alertChannelName, self.merged_by))
        """ for bot """
        # write_to_file_from_top(release_freeze_details_path, ":clubs:" +
        #                        str(datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
        #                            '%B %d,%Y at %I.%M %p')) + " with <" + self.pr.link_pretty + "|master> code")  # on:" + str(datetime.datetime.now().strftime('%B %d, %Y @ %I.%M%p'))
        # clear_file(code_freeze_details_path)

    def notify_channel_on_merge(self):
        """
        pass entry in fixed channel for all code merge details (merged to any of sensitive branch)
        :return: relevant response dict
        """
        if self.pr.is_merged:
            # print "**** Repo=" + repo + ", new merge came to " + base_branch + " set trace to " + code_merge_channel + " channel"
            msg = MSG_CODE_CHANNEL.format(title=self.pr.title, desc=self.pr.description, pr=self.pr.link,
                                          head_branch=self.pr.head_branch, base_branch=self.pr.base_branch,
                                          pr_by=self.created_by, merge_by=self.merged_by)
            self.slack.postToSlack(self.pr.config.alertChannelName, msg)
            LOG.info("informed %s because pr=%s is merged into sensitive branch=%s" %
                     (self.pr.config.alertChannelName, self.pr.link_pretty, self.pr.base_branch))
            return {"msg":"informed %s because pr=%s is merged into sensitive branch=%s" %
                     (self.pr.config.alertChannelName, self.pr.link_pretty, self.pr.base_branch)}
        return {"msg", "Skipped posting to code channel because '%s' is not merge event" %self.pr.action}



