from alice.config.message_template import MSG_BAD_START, MSG_NO_TECH_REVIEW, MSG_AUTO_CLOSE, MSG_OPENED_TO_MAIN_BRANCH, \
    MSG_OPENED_TO_PREVENTED_BRANCH, SPECIAL_COMMENT, GENERAL_COMMENT, MSG_RELEASE_PREPARATION, MSG_CODE_CHANNEL, \
    MSG_GUIDELINE_ON_MERGE, MSG_SENSITIVE_FILE_TOUCHED, MSG_QA_SIGN_OFF
from alice.helper.file_utils import write_to_file_from_top, clear_file
from alice.helper.github_helper import GithubHelper
from alice.helper.log_utils import LOG
from alice.helper.slack_helper import SlackHelper


class Checks(object):
    def __init__(self, pr_payload):
        from alice.main.actor import Actor
        self.pr = pr_payload
        self.github = GithubHelper(self.pr.config.organisation, self.pr.repo, self.pr.config.githubToken, self.pr.link)
        self.slack = SlackHelper(self.pr.config)
        self.change_requires_product_plus1 = False
        self.is_product_plus1 = False
        self.sensitive_file_touched = {}
        self.base_branch = self.pr.base_branch
        self.head_branch = self.pr.head_branch
        self.created_by = self.pr.config.getSlackName(self.pr.opened_by)
        self.merged_by = self.pr.config.getSlackName(self.pr.merged_by)
        if self.pr.is_merged:
            self.actor = Actor(github=self.github, pr=self.pr)
            self.sensitive_file_touched, self.change_requires_product_plus1 = self.actor.parse_files_and_set_flags()


    def tech_review(self):
        """
        checks for +1 in review approved
        :return:
        """
        if self.pr.is_merged:  # and self.head_branch in PushPayload.PROTECTED_BRANCH_LIST:  TO ENABLE
            is_bad_pr = self.actor.is_bad_pr()
            bad_name_str = MSG_BAD_START + "@" + self.created_by
            if is_bad_pr:
                msg = MSG_NO_TECH_REVIEW.format(name=bad_name_str, pr=self.pr.link_pretty, title=self.pr.title,
                                                branch=self.pr.base_branch, team=self.pr.config.alertChannelName)
                LOG.debug(msg)
                self.slack.postToSlack(self.pr.config.alertChannelName, msg)
            LOG.info("Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=is_bad_pr))
            return {"msg": "Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=is_bad_pr)}
        return {"msg": "Skipped review because its not PR merge event"}

    def comment_guidelines(self):
        """
        add comment on opened PR
        :return:
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

    def notify_channel_on_merge(self):
        """
        store merged PR data to respective channel
        :return:
        """
        if self.pr.is_merged:
            # print "**** Repo=" + repo + ", new merge came to " + base_branch + " set trace to " + code_merge_channel + " channel"
            msg = MSG_CODE_CHANNEL.format(title=self.pr.title, desc=self.pr.description, pr=self.pr.link,
                                          head_branch=self.pr.head_branch, base_branch=self.pr.base_branch,
                                          pr_by=self.created_by, merge_by=self.merged_by)
            return msg
            # TO DO: slack.postToSlack(code_merge_channel, msg, data={"username": bot_name})  # code-merged

    def notify_lead_on_given_action(self):
        """
        keep lead posted on particular action on sensitive branch
        :return:
        """
        # if self.pr.is_opened:
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
                self.slack.postToSlack('@' + self.pr.config.personToBeNotified, msg)
                LOG.info("Notified to %s on action %s" % (self.pr.config.personToBeNotified, self.pr.action))
                return {"msg": "Notified to %s on action %s" % (self.pr.config.personToBeNotified, self.pr.action)}
        return {"msg": "Skipped notify because its not desired event %s" % self.pr.action}

    def remind_direct_release_guideline_on_merge(self):
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

    def notify_on_sensitive_files_touched(self):
        if self.pr.is_merged:
            if self.sensitive_file_touched.get("is_found"):
                msg = MSG_SENSITIVE_FILE_TOUCHED.format(
                    notify_folks=self.pr.config.devOpsTeam, file=self.sensitive_file_touched["file_name"],
                    pr=self.pr.link_pretty, pr_by=self.created_by, pr_number=self.pr.number)
                self.slack.postToSlack(self.pr.config.alertChannelName, msg)
                LOG.info("informed %s because sensitive files are touched" % self.pr.config.devOpsTeam)
                return {"msg": "informed %s because sensitive files are touched" % self.pr.config.devOpsTeam}
            return {"msg": "Skipped sensitive files alerts because no sensitive file being touched"}
        return {"msg": "Skipped sensitive files alerts because its not PR merge event" % self.pr.config.devOpsTeam}

    def notify_qa_sign_off(self):
        if self.pr.is_merged and self.pr.base_branch == self.pr.config.mainBranch \
                and self.pr.head_branch == self.pr.config.testBranch:
            msg = MSG_QA_SIGN_OFF.format(person=self.pr.config.personToBeNotified, pr=self.pr.link_pretty,
                                         dev_ops_team=self.pr.config.devOpsTeam,
                                         tech_team=self.pr.config.techLeadsToBeNotified)

            self.slack.postToSlack(self.pr.config.alertChannelName, msg,
                                   data=self.slack.getBot(self.pr.config.alertChannelName, self.merged_by))
            """ for bot """
            # write_to_file_from_top(release_freeze_details_path, ":clubs:" +
            #                        str(datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
            #                            '%B %d,%Y at %I.%M %p')) + " with <" + self.pr.link_pretty + "|master> code")  # on:" + str(datetime.datetime.now().strftime('%B %d, %Y @ %I.%M%p'))
            # clear_file(code_freeze_details_path)

    def notify_to_add_release_notes_for_next_release(self):
        pass

    def announce_code_freeze(self):
        pass

    def ci_lint_checker(self):
        pass

    def ci_unit_tests(self):
        pass

    def product_review(self):
        pass