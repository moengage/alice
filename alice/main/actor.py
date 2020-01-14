import simplejson as json
from alice.helper.file_utils import write_to_file_from_top, clear_file, read_from_file

from alice.commons.base import Base
from alice.config.message_template import MSG_BAD_START, MSG_NO_TECH_REVIEW, MSG_AUTO_CLOSE, MSG_OPENED_TO_MAIN_BRANCH, \
    MSG_OPENED_TO_PREVENTED_BRANCH, SPECIAL_COMMENT, GENERAL_COMMENT, MSG_RELEASE_PREPARATION, \
    MSG_SENSITIVE_FILE_TOUCHED, MSG_QA_SIGN_OFF, MSG_CODE_CHANNEL, MSG_GUIDELINE_ON_MERGE, CODE_FREEZE_TEXT, \
    RELEASE_NOTES_REMINDER, DATA_SAVE_MERGED
from alice.helper.constants import *
from alice.helper.common_utils import CommonUtils
from alice.config.message_template import MSG_NO_PRODUCT_REVIEW, ADDITIONAL_COMMENT
from alice.helper.constants import THUMBS_UP_ICON
from alice.helper.github_helper import GithubHelper
from alice.helper.github_helper import PRFilesNotFoundException
from alice.helper.slack_helper import SlackHelper
from alice.helper.jenkins_helper import JenkinsHelper
from alice.helper.log_utils import LOG
from datetime import datetime
from alice.helper.api_manager import ApiManager

import time
import pytz
import shutil
import datetime
import traceback
import random
import requests
import jenkins


class PRFilesNotFoundException(Exception):
    def __init__(self, pr_response):
        self.pr_response = pr_response
        super(PRFilesNotFoundException, self).__init__(str(self.pr_response))


class Actor(Base):
    
    def __init__(self, pr):
        self.pr = pr
        self.github = GithubHelper(self.pr)
        self.slack = SlackHelper(self.pr.config)
        self.jenkins = JenkinsHelper(self.pr)
        self.change_requires_product_plus1 = False
        self.is_product_plus1 = False
        self.sensitive_file_touched = {}
        self.base_branch = self.pr.base_branch
        self.head_branch = self.pr.head_branch
        self.created_by = self.pr.config.getSlackName(self.pr.opened_by)
        if self.pr.is_merged:
            self.merged_by = self.pr.config.getSlackName(self.pr.merged_by)
            self.save_data_for_later()
        self.sensitive_file_touched, self.change_requires_product_plus1 = self.parse_files_and_set_flags()


    def save_data_for_later(self):
        """
        saves merge event data on file to use for code freeze notification later on
        :return:
        """
        if self.pr.is_merged and self.pr.base_branch == self.pr.config.devBranch:
            msg = DATA_SAVE_MERGED.format(title=self.pr.title, desc=self.pr.description, pr=self.pr.link_pretty,
                                          by=self.pr.opened_by_slack)
            write_to_file_from_top(self.pr.config.releaseItemsFilePath, msg)
            with open(self.pr.config.releaseItemsFileMergedBy, "a+") as f:
                name = "<@{0}>".format(self.pr.opened_by_slack)
                existing_names = f.read()
                if name not in existing_names:
                    f.write(name + ", ")
                    LOG.debug(msg + ' added unique names to file ' + self.pr.config.releaseItemsFileMergedBy)
                f.close()

    def parse_files_and_set_flags(self):
        """
        Parse payload and keep important flags ready to be used in checks
        :return: sensitive_file_touched (dict of file name with boolean value)
        :return: change_requires_product_plus1 (boolean)
        """
        change_requires_product_plus1 = False
        sensitive_file_touched = {}
        if self.pr.config.sensitiveFiles is None:
            return sensitive_file_touched, change_requires_product_plus1
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
                LOG.info("***** review_comment %r" %review_comment)
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
        """`
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
                                                    branch=self.pr.base_branch, team=""
                                                       .join(self.pr.config.productTeamToBeNotified))
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
                    guideline_comment = self.add_extra_comment(SPECIAL_COMMENT)
                    self.slack.postToSlack(self.pr.opened_by)
                else:
                    guideline_comment = GENERAL_COMMENT
                    guideline_comment = self.add_extra_comment(GENERAL_COMMENT)
                self.github.comment_pr(self.pr.comments_section, guideline_comment)
                LOG.info("**** Added Comment of dev guidelines ***")
                return {"msg": "Added Comment of dev guidelines"}
            return {"msg": "Skipped commenting because DEBUG is on "}
        return {"msg": "Skipped commenting because its not PR opened"}

    def add_extra_comment(self, predefined_comment):
        new_comment = {}
        comments = predefined_comment["body"]
        for comment in ADDITIONAL_COMMENT:
            comments = comments + comment
        new_comment["body"] = comments
        return new_comment



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
        return {"msg": "skipped slack personally to %s because its not merge event" % self.created_by}

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
            return {"msg": "skipped closing PR=%s because not raised to mainBranch %s" %(self.pr.link_pretty,
                                                                                         master_branch)}
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
            "msg": "Skipped sensitive files alerts because its not PR merge event %s" %
                   self.pr.config.devOpsTeamToBeNotified}


    def notify_qa_sign_off(self):
        """
        Notify to respective folks when qa is passed and code is moved to main branch Eg. master
        :return:
        """
        if self.pr.is_merged and self.pr.base_branch == self.pr.config.mainBranch \
                and self.pr.head_branch == self.pr.config.testBranch:
            msg = MSG_QA_SIGN_OFF.format(person=self.pr.config.personToBeNotified, pr=self.pr.link_pretty,
                                         dev_ops_team=self.pr.config.devOpsTeamToBeNotified,
                                         tech_team=self.pr.config.techLeadsToBeNotified)

            self.slack.postToSlack(self.pr.config.alertChannelName, msg,
                               data=self.slack.getBot(self.pr.config.alertChannelName, self.merged_by))

            """ for bot to keep data ready for future use"""
            write_to_file_from_top(self.pr.config.releaseFreezeDetailsPath, ":clubs:" +
                                   str(datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
                                       '%B %d,%Y at %I.%M %p')) + " with <" + self.pr.link_pretty + "|master> code")
            clear_file(self.pr.config.codeFreezeDetailsPath)


    def notify_channel_on_merge(self):
        """
        pass entry in fixed channel for all code merge details (merged to any of sensitive branch)
        :return: relevant response dict
        """
        if self.pr.is_merged:
            LOG.debug("**** Repo=%s, new merge came to=%s, setting trace to=%s channel"
                      %(self.pr.repo, self.pr.base_branch, self.pr.config.codeChannelName))
            msg = MSG_CODE_CHANNEL.format(title=self.pr.title, desc=self.pr.description, pr=self.pr.link,
                                          head_branch=self.pr.head_branch, base_branch=self.pr.base_branch,
                                          pr_by=self.created_by, merge_by=self.merged_by)
            self.slack.postToSlack(self.pr.config.codeChannelName, msg)
            LOG.info("informed %s because pr=%s is merged into sensitive branch=%s" %
                     (self.pr.config.codeChannelName, self.pr.link_pretty, self.pr.base_branch))
            return {"msg":"informed %s because pr=%s is merged into sensitive branch=%s" %
                     (self.pr.config.codeChannelName, self.pr.link_pretty, self.pr.base_branch)}
        return {"msg", "Skipped posting to code channel because '%s' is not merge event" %self.pr.action}


    def notify_code_freeze(self):
        """
        gathers accumulated data after last qa_signOff and send an attachment into channel announcing details of code freeze
        :return: relevant response dict
        """
        if self.pr.is_merged and (self.pr.base_branch == self.pr.config.testBranch \
                and self.pr.head_branch == self.pr.config.devBranch):
            LOG.debug("*** PR merged from {dev_branch} to {qa_branch}, posting release items to slack".
                      format(dev_branch=self.pr.config.devBranch, qa_branch=self.pr.config.testBranch))

            write_to_file_from_top(self.pr.config.codeFreezeDetailsPath, ":clubs:" + str(
                datetime.now(pytz.timezone(self.pr.config.timezone)).strftime(
                    '%B %d at %I.%M %p')) + " with <" + self.pr.link_pretty + "|PR>")

            try:
                msg  = read_from_file(self.pr.config.releaseItemsFilePath)
                LOG.debug("final msg =" + msg)
            except Exception, e:
                return {"msg": "Skipped posting code-freeze because no details found in file %s"
                               % self.pr.config.releaseItemsFilePath}


            CODE_FREEZE_TEXT[0]["pretext"] = CODE_FREEZE_TEXT[0]["pretext"].format(dev_branch=self.pr.config.devBranch,
                                                                                   test_branch=self.pr.config.testBranch)
            CODE_FREEZE_TEXT[0]["fields"][0]["title"] =  CODE_FREEZE_TEXT[0]["fields"][0].get("title")\
                .format(test_branch=self.pr.config.testBranch)
            CODE_FREEZE_TEXT[0]["fields"][1]["value"] = CODE_FREEZE_TEXT[0]["fields"][1]["value"].format(pr=self.pr.link_pretty)
            CODE_FREEZE_TEXT[0]["text"] = CODE_FREEZE_TEXT[0]["text"].format(msg=msg)
            CODE_FREEZE_TEXT[0]["title_link"] = CODE_FREEZE_TEXT[0]["title_link"]\
                .format(release_notes_link=self.pr.config.release_notes_link)

            self.slack.postToSlack(channel=self.pr.config.alertChannelName, attachments=CODE_FREEZE_TEXT)
            self.remind_all_finally_to_update_release_notes()
            return {"msg": "informed code-freeze on %s for pr=%s" % (self.pr.config.alertChannelName,
                                                                     self.pr.link_pretty)}
        return {"msg", "Skipped posting to code-freeze because its not code-freeze event, {pr_action}ed from "
                       "{dev_branch} -> {qa_branch} ".format(pr_action=self.pr.action,
                        dev_branch=self.pr.config.devBranch, qa_branch=self.pr.config.testBranch)}


    def remind_all_finally_to_update_release_notes(self):
        """
        Final reminder to the folks who had merged code till the time code freeze was taken
        """
        names = read_from_file(self.pr.config.releaseItemsFileMergedBy)
        LOG.debug("final names list =" + names)
        if names:
            time.sleep(10)

            msg = RELEASE_NOTES_REMINDER.format(msg=names, release_notes_link=self.pr.config.release_notes_link,
                                                qa_team=self.pr.config.qaTeamMembers)
            self.slack.postToSlack(channel=self.pr.config.alertChannelName, msg=msg)
            self.clean_up_for_next_cycle()

    def clean_up_for_next_cycle(self):
        """ backup & clean-up file for next release """
        shutil.copy(self.pr.config.releaseItemsFilePath, self.pr.config.backupFilesPath + '_'
                    + str(datetime.now().strftime('%m-%d-%Y:%I.%M%p')) + '.txt')  # take backup before clearing
        clear_file(self.pr.config.releaseItemsFileMergedBy)
        clear_file(self.pr.config.releaseItemsFilePath)  # clear file for next release content
        # NOTE: user has to manually delete data added when in debug mode

    def add_label_to_issue(self, repo, pr_no, list_labels):
        """
         Example : self.set_labels("MoEngage", 13319, ["Alice_test2"])
         :return:
         """
        api_label = repo_site_url + "repos/moengage/%s/issues/%s/labels" % (repo, str(pr_no))
        headers = {"Authorization": "token " + self.github.GITHUB_TOKEN}
        return ApiManager.post(api_label, headers, json.dumps(list_labels))

    def get_files_pull_request(self, files_endpoint):
        """
        Here we get files pages in paginated way as github has restricted the response to 300 files.
        Inputo : url of pull request
        :return:
        """
        files_list = []
        page_no = 1
        while True:
            url_with_page = files_endpoint + "?page=%s" % page_no
            headers = {"Authorization": "token " + self.github.GITHUB_TOKEN}
            response = ApiManager.get(url_with_page, headers)
            req = response["response"].request
            self.print_curl(req)
            res = json.loads(response["content"])
            if not res or (isinstance(res, dict) and "limit exceeded" in res.get("message")):
                break
            files_list += res
            page_no += 1
        return files_list, ""  # For specific commit, it's inside "files" key

    def get_files_commit(self, files_endpoint):
        """
        Input : url of pull request
        :return:
        TODO docstring
        """
        files_endpoint = self.pr.link
        response = ApiManager.get(files_endpoint, {"Authorization": "token " + self.github.GITHUB_TOKEN})
        res = json.loads(response.get("content"))
        try:
            return res.get("files"), res.get("commit").get("message")  # For specific commit, it's inside files
        except Exception:
            return res

    def get_files(self, files_endpoint):
        if "files" in files_endpoint:
            files_content, message = self.get_files_pull_request(files_endpoint)
        if "commits" in files_endpoint:
            files_content, message = self.get_files_commit(files_endpoint)
        if not self.is_pr_file_content_available(files_content):
            raise PRFilesNotFoundException(files_content)
        return files_content, message

    def is_pr_file_content_available(self, response):
        return not (isinstance(response, dict) and 'message' in response and response['message'] == "Not Found")

    def hit_jenkins_job(self, jenkins_instance, token, job_name, pr_link, params_dict, pr_by_slack):
        a = datetime.datetime.now()
        print("**Hitting Job {0} on PR link {1}".format(job_name, pr_link))
        try:
            print("params_dict %s token=%s" % (params_dict, token))
            queue_info = jenkins_instance.get_queue_info()
            print("queue size=", len(queue_info))
            build_response = jenkins_instance.build_job(job_name, params_dict, {'token': token})
            print("*** triggerd the job", build_response)
            queue_info = jenkins_instance.get_queue_info()
            print("queue size=", len(queue_info))
            print("1st queue_info=", queue_info[0])
            b = datetime.datetime.now()
            c = b - a
            print(int(c.total_seconds()), " seconds")
            msg = "<@{0}> started job, PR by={0} PR={1}".format(
                pr_by_slack, pr_link)
            print(msg)
        except Exception, e:
            print(e)
            traceback.print_exc()
            raise Exception(e)

    def run_for_angular(self, context_angular, job_dir, repo, pr_by_slack_name, is_change_angular, jenkins_instance, token, pr_by_slack_uid):
        self.jenkins.change_status(self.pr.statuses_url, "pending", context=context_angular,
                                   description="Hold on!",
                                   details_link="")
        job_name = job_dir + "shield_dashboard_angular"
        params_dict = dict(repo=repo, head_branch=self.pr.head_branch, base_branch=self.pr.base_branch, sha=self.pr.head_sha,
                                           description="Syntax Validation [React Code]", author=pr_by_slack_name,
                                           author_github=self.pr.opened_by, pr_no=self.pr.link_pretty,
                                           shield_angular=is_change_angular)
        self.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job_name,
                                   pr_link=self.pr.link_pretty,
                                   params_dict=params_dict, pr_by_slack=pr_by_slack_uid)

    def run_for_react(self, job_dir, repo, pr_by_slack_name, jenkins_instance, token,pr_by_slack_uid):
        job_name = job_dir + "shield_dashboard_react_linter"
        params_dict = dict(repo=repo, head_branch=self.pr.head_branch, base_branch=self.pr.base_branch,
                           sha=self.pr.head_sha,
                           description="Syntax Validation [React Code]", author=pr_by_slack_name,
                           author_github=self.pr.opened_by, pr_no=self.pr.link_pretty,
                           shield_react=True)
        self.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job_name,
                                   pr_link=self.pr.link_pretty,
                                   params_dict=params_dict, pr_by_slack=pr_by_slack_uid)

    def alert_pm(self):
        if self.pr.action.find("close") != -1 and self.pr.is_merged == True and (
                self.pr.base_branch == master_branch and self.pr.head_branch == staging_branch):

            """ ********** Remind PM teams to update release notes for next release ************ """
            for item in alice_product_team:
                self.slack.postToSlack(item,
                            "\n:bell: hi " + item + " master is updated & release is going live shortly. "
                                                    "Hoping <https://docs.google.com/a/moengage.com/spreadsheets/d/1eW3y-GxGzu8Jde8z4EYC6fRh1Ve4TpbW5qv2-iWs1ks/edit?usp=sharing|Release Notes> have mention of all the items planned to go in \"Next Release\"",
                            data={"username": bot_name}, parseFull=False)
            """ for bot """
            for item in alice_qa_team:
                self.slack.postToSlack(item, "\n hi <" + item + "> " + random.choice(
                    applaud_list) + " :+1: thank you for the QA signOff\n :bell:"
                                    " <https://github.com/moengage/MoEngage/wiki/Post-Release-deployment-Check#for-qa-engineer|" + random.choice(
                    post_checklist_msg) + ">",
                            data={"username": bot_name}, parseFull=False)
            write_to_file_from_top(release_freeze_details_path, ":clubs:" +
              str(datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
                  '%B %d,%Y at %I.%M %p')) + " with <" + self.pr.link_pretty + "|master> code")  # on:" + str(datetime.datetime.now().strftime('%B %d, %Y @ %I.%M%p'))
            clear_file(code_freeze_details_path)  # clear last code freeze

    def check_valid_contributor(self):
        if self.pr.action == "closed" and self.pr.is_merged == True and self.pr.base_branch == staging_branch and (
                self.pr.merged_by not in self.pr.config.valid_contributors):
            merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(self.pr.merged_by)
            msg = "Very Bad <@" + merged_by_slack_uid + "> :rage4: :rage4: !! " + self.pr.link_pr \
                  + " is merged directly into `" + self.pr.base_branch + \
                  "`, but not by QA team, soon these kind of requests will be automatically reverted CC: " +\
                  alice_dev_team_MoEngage_repo
            print(msg)
            print(self.slack.postToSlack(channel_name, msg, data={"username": bot_name}))

    def code_freeze(self):

        if (self.pr.base_branch == staging_branch and self.pr.head_branch == dev_branch) \
                and (self.pr.action.find("opened") != -1 or self.pr.action.find("merged") != -1):

            print("************ code freeze PR is opened from dev to QA, auto create PRs for dependent packages")
            self.slack.postToSlack(channel_name,
                        "@channel Freezing code now. Any pending merge? please reach QA team within 10 minutes",
                        data={"username": bot_name}, parseFull=False)
            self.freeze_other_repos("staging")

    def freeze_other_repos(self, freeze_type):
        """
        :param freeze_type: staging(dev -> qa) or live (qa ->master)
        """
        timestamp = str(datetime.datetime.now(pytz.timezone('Asia/Calcutta')).strftime('%d/%m/%y %I.%M%p'))
        repos = ["segmentation", "commons", "product-recommendation", "product-management", "inapp-rest-service",
                 "campaigns-core", "s2s", "url_tracking", "email-campaigns"]

        if freeze_type == "staging":
            head = "develop"
            base = "release"
            title = "Code Freeze-" + timestamp
            alert = "\n:bell: MoEngage Repo: Code freeze time:: Please freeze your package(s)"
            body = "Please merge these for code freeze. Release testing is getting started with MoEngage repo freeze\n" \
                   "cc: @prashanthegde9 @BhuvanThejaChennuru @gagana11 @geetima12",
        elif freeze_type == "live":
            head = "release"
            base = "master"
            title = "{head} -> {base} {time}".format(head=head, base=base, time=timestamp)
            alert = "\n:bell: MoEngage Repo: Release time:: Please verify your package(s) if they needs to go live"
            body = "RELEASENOTES.md at root"  # read release notes file

        """ Announce on channel """
        self.slack.postToSlack(channel_name, alert, data={"username": bot_name})

        """Create PRs and post links"""
        cnt = 1
        for repo in repos:
            if freeze_type == "live":
                body = "[release notes](https://github.com/moengage/{repo}/blob/release/RELEASENOTES.md)".format(
                    repo=repo)

            pr_data = {
                "title": title,
                "body": body,
                "head": head,
                "base": base
            }
            pr_endpoint = repo_site_url + "repos/moengage/" + repo + "/pulls"
            response = requests.post(pr_endpoint, headers={
                "Authorization": "token " + self.github.GITHUB_TOKEN}, data=json.dumps(pr_data))
            res = json.loads(response.content)
            if not res.get("errors"):
                # for person in pkg_people_to_notify:
                self.slack.postToSlack(channel_name,
                            "%s *%s:* %s number <%s|%s>" % (cnt, repo, pkg_people_to_notify.get(repo, "@pooja"),
                                                            res.get("html_url"), res.get("number")),
                            data={"username": bot_name}, parseFull=False)
            else:
                try:
                    error_message = res["errors"][0]["message"]
                    custom_message = "%s) *%s:* %s %s <%s|check here> " % (
                    cnt, repo, pkg_people_to_notify.get(repo, "@pooja"),
                    "Pull Request is already open",
                    repo_site_url + "moengage/"
                    + repo + "/compare/" + base + "..." + head)
                    if "no commits" in error_message.lower():
                        custom_message = "%s *%s:* %s %s <%s|check here> " % (
                        cnt, repo, pkg_people_to_notify.get(repo, "@pooja"),
                        error_message, repo_site_url + "moengage/" + repo + "/compare/" + base + "..." + head)

                    SlackHelper.postToSlack(channel_name, custom_message, data={"username": bot_name})
                    SlackHelper.postToSlack("@pooja", ":warning: creating automatic PR for %s failed, response=\n%s"
                                % (repo, json.dumps(res)))
                except Exception, e:
                    print e
                    SlackHelper.postToSlack("@pooja",
                                ":skull: error in sending failure message on PR creation failure, response=\n%s"
                                % (repo, e.message))
            cnt += 1

    def release_alert(self):
        if self.pr.action.find("close") != -1 and self.pr.is_merged == True and (
                self.pr.base_branch == master_branch and self.pr.head_branch == staging_branch):


            """ ************* inform channel *************** """
            msg = "{2} QA passed :+1: `master` is <{1}|updated> for release \n cc: <@{0}> {3} {4} \n <!channel> ".format(
                to_be_notified, self.pr.link_pretty,
                dev_ops_team, tech_leads_to_notify_always_slack, product_notify_slack)

            self.slack.postToSlack(channel_name, msg, data=CommonUtils.getBot(channel_name, merged_by_slack_name),
                        parseFull=False)

        if self.pr.action.find("open") != -1 and self.pr.base_branch == master_branch and self.pr.head_branch == staging_branch:

            pr_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(self.pr.opened_by)
            print "************ MoEngage repo:: PR opened to " + self.pr.base_branch + " Notify Alice & comment guidelines ****"
            msg = "MoEngage repo:: <{link_pr}|{title_pr}> is opened to `{base_branch}` by:*<@{pr_by_slack}>* " \
                .format(link_pr=self.pr.link_pr, title_pr=self.pr.title, pr_by_slack=pr_by_slack_uid, base_branch=self.pr.base_branch)

            self.add_comment_to_master()

            for item in alice_tech_leads_MoEngage_Repo:
                self.slack.postToSlack(item, msg + "\n Please review and approve with +1, Release preparation starts...",
                            data={"username": bot_name}, parseFull=False)
            self.freeze_other_repos("live")

            for item in alice_qa_team:
                self.slack.postToSlack(item,
                            "\n\n:bell: *Bugs clean time* :: please make out 20 minutes max to cleanup no longer valid old issues and share a rough number of issues we cleaned or require attention <https://docs.google.com/spreadsheets/d/1WeWLuIE7Dt5G8lWACZs21WO0B07-naQ7JlUb8cHcxVA/edit#gid=1591591107|sheet link>",
                            data={"username": bot_name}, parseFull=False)
            for item in alice_product_team:
                self.slack.postToSlack(item,
                            "\n:bell: Hi " + item + " *Release notes update required*: Current release is getting ready to go Live, please help us with next release planning by having \"Next Release\" <https://docs.google.com/a/moengage.com/spreadsheets/d/1eW3y-GxGzu8Jde8z4EYC6fRh1Ve4TpbW5qv2-iWs1ks/edit?usp=sharing|sheet> updated",
                            data={"username": bot_name}, parseFull=False)

    def add_comment_to_master(self):
        guideline_comment = {
            "body": "**Attention!** \n Release Checklist\n"
                    "- [ ] Inform Yashwanth with the PR link\n"
                    "- [ ] Check release notes(top or bottom), if anything is pending from any developer\n"
                    "- [ ] No code/PR to be reverted? check release notes\n"
                    "- [ ] [Unit Tests](http://ci.moengage.com/job/Unit_Tests/) Passed?\n"
                    "- [ ] [Api functional tests](http://ci.moengage.com/view/API_Tests/job/Api_Tests/) passed?\n"
                    "- [ ] [S2S Tests](http://ci.moengage.com/view/API_Tests/job/S2S_Tests/) passed?\n"
                    "- [ ] [Transaction Tests](http://ci.moengage.com/view/API_Tests/job/Txn_Push_API_Tests/) passed?\n"
                    "- [ ] QA report linked?\n"
                    "- [ ] Release Notes linked?"
        }
        header = {"Authorization": "token " + self.github.GITHUB_TOKEN}
        ApiManager.post(self.pr.comments_section, header, json.dumps(guideline_comment))
        print("**** Added comment of Release guidelines")

    def get_diff(self, repo):
        from alice.helper.api_manager import ApiManager
        """
        First, It fetches commits of a repo, then we compare
        top two commit of a repo and we get the file difference.
        300 is rate limiting by Github, Pagination is also not working.
        """
        first_branch = str(self.pr.head_branch)
        second_branch = str(self.pr.base_branch)
        url = repo_site_url + "repos/moengage/" + self.pr.repo + "/compare/" + first_branch \
              + "..." + second_branch
        header = {"Authorization": "token " + self.actor.github.GITHUB_TOKEN}
        res = ApiManager.get(url, header)["response"].json()
        return res["files"]

    def print_curl(self, req):
        method = req.method
        uri = req.url
        headers = ['"{0}: {1}"'.format(k, v) for k, v in req.headers.items()]
        headers = " -H ".join(headers)
        command = "curl -X {method} -H {headers} '{uri}'"
        print("************* cURL=", command.format(method=method, headers=headers, uri=uri))

    def trigger_task_on_pr(self):

        jenkins_setting = self.pr.global_config.config["jenkins"]
        token = jenkins_setting["token"]
        jenkins_instance = jenkins.Jenkins(jenkins_setting["JENKINS_BASE"],
                                           username=jenkins_setting["username"], password=token)
        repo = self.pr.repo
        merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(self.pr.merged_by)
        merged_by_slack_name = CommonUtils.getSlackNicksFromGitNicks(self.pr.merged_by)
        pr_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(self.pr.opened_by)
        pr_by_slack_name = CommonUtils.getSlackNicksFromGitNicks(self.pr.opened_by)

        """
        First we check whether pr is open, then we run our task
        """
        if self.pr.action in action_commit_to_investigate:

            # 1) First task Done
            self.close_dangerous_pr()

            """
            2) Begining of shield - Second task
            Shield runs for three repos -  Moengage, Dashboard_ui, Inap_rest_service
            commons, segmentation, campaigns-core, 
            Basic working of shield - It first update status to pending , then get file content,
            if file content found, then move forward, else return and skip testing.

            Dashboard_ui has two context - react and angular
            moengage has two context - syntax and unit_test
            Inapp_rest_service has moengage + integration context.

            """

            # 2.1) Run for dashboard_ui
            if repo in ui_repo and self.pr.is_sensitive_branch:

                is_change_angular = False
                is_change_react = False
                print ":INFO: repo=%s" % repo
                msg = "base={0} head={1}, action={2} Do nothing".format(self.pr.base_branch, self.pr.head_branch,
                                                                        self.pr.action)
                job_dir = "Dashboard/"

                self.jenkins.change_status(self.pr.statuses_url, "pending", context=context_react,
                                                 description="Hold on!",
                                                 details_link="")

                try:
                    files_contents, message = self.get_files(self.pr.link + "/files")
                except PRFilesNotFoundException, e:
                    files_contents = e.pr_response

                if not files_contents or "message" in files_contents:
                    print ":DEBUG: no files found in the diff: SKIP shield, just update the status"
                    self.jenkins.change_status(self.pr.statuses_url, "success", context=context,
                                                     description="SKIP: No diff, check the Files count",
                                                     details_link="")
                    self.jenkins.change_status(self.pr.statuses_url, "success", context=context_react,
                                                     description="SKIP: No diff, check the Files count",
                                                     details_link="")
                    return files_contents  # STOP as files not found

                # If file contents are found, check which content we have to run.
                for item in files_contents:
                    file_path = item["filename"]
                    if file_path.startswith("static/app_react"):
                        is_change_react = True
                    if file_path.startswith("static/app"):
                        is_change_angular = True

                if is_change_angular:
                    self.run_for_angular(context_angular, job_dir, repo, pr_by_slack_name,
                                               is_change_angular, jenkins_instance, token, pr_by_slack_uid)

                """ hit react job"""  # Hit always even config changes can be possible
                self.run_for_react(job_dir, repo, pr_by_slack_name, jenkins_instance, token, pr_by_slack_uid)
                msg = "ui repo checks started"
                return {"msg": msg}

            elif repo in python_repo:
                """
                2.2) for moengage repo and inap_rest_service
                We have several cases, 
                First case is for particular branches, we skip alice, 
                Second case is we bypass shield testing for back merge(from master to dev and all..)
                Third case is when we run shield for moengage and python branch
                """
                if "feature/melora" in self.pr.base_branch or "feature/melora" in self.pr.head_branch:  # by pass for alice dev/test

                    print ":SKIP: alice code changes on melora branch"
                    return ":SKIP: alice code changes on " + repo

                elif repo.lower() == organization_repo and (
                        (self.pr.base_branch == staging_branch and self.pr.head_branch == master_branch) or
                        (self.pr.base_branch == dev_branch and self.pr.head_branch == staging_branch)):

                    print ":SKIP: back merge: checks call, repo={repo} pr={link_pr} title={title_pr}" \
                        .format(repo=repo, link_pr=self.pr.link_pr, title_pr=self.pr.title)
                    self.jenkins.change_status(self.pr.statuses_url, "success", context=context,
                                                     description="checks bypassed for back merge",
                                                     details_link="")
                    self.jenkins.change_status(self.pr.statuses_url, "success", context="shield-unit-test-python",
                                                     description="checks bypassed for back merge",
                                                     details_link="")
                    self.jenkins.change_status(self.pr.statuses_url, "success", context="shield-linter-react",
                                                     description="checks bypassed for back merge",
                                                     details_link="")

                else:
                    print ":INFO: repo=%s to validate, for PR=%s" % (repo, self.pr.number)
                    if self.pr.base_branch in sensitive_branches_repo_wise.get(repo.lower(),
                                                                               sensitive_branches_default):

                        print "******* PR " + self.pr.action + "ed to " + self.pr.base_branch + ", Triggering tests ************"

                        # variable declaration
                        pr_link = self.pr.link_pretty
                        head_repo = self.pr.ssh_url
                        path = ""
                        files_ops = False

                        self.jenkins.change_status(self.pr.statuses_url, "pending", context=context,
                                                         description=context_description,
                                                         details_link="")  # status to go in pending quick
                        self.jenkins.change_status(self.pr.statuses_url, "pending",
                                                         context="shield-unit-test-python", description="Hold on!",
                                                         details_link="")
                        try:
                            print ":DEBUG: check_file_path", self.pr.link + "/files"
                            files_contents, message = self.get_files(self.pr.link + "/files")
                        except PRFilesNotFoundException, e:
                            files_contents = e.pr_response
                        if not files_contents or "message" in files_contents:
                            print ":DEBUG: no files found in the diff: SKIP shield, just update the status"
                            self.jenkins.change_status(self.pr.statuses_url, "success", context=context,
                                                             description="SKIP: No diff, check the Files count",
                                                             details_link="")
                            self.jenkins.change_status(self.pr.statuses_url, "success",
                                                             context="shield-unit-test-python",
                                                             description="SKIP: No diff, check the Files count",
                                                             details_link="")
                            return files_contents  # STOP as files not found

                        # print "files_contents after found", files_contents
                        for item in files_contents:
                            file_path = item["filename"]
                            if str(file_path).endswith(".py") and item["status"] != "removed":
                                path += " " + file_path

                            elif str(file_path).endswith((".conf", ".cfg", ".init", ".sh")):
                                files_ops = True

                            # elif str(file_path).endswith((".html", ".css", ".js", ".tpl", ".less", ".scss", ".json")):
                            #     files_frontend = True
                            # else:
                            #     files_backend = True

                        if repo.lower() == organization_repo and files_ops and self.pr.action \
                                in action_commit_to_investigate:

                            self.add_label_to_issue(repo, self.pr.number,
                                            ["DevOps_Review "])

                        else:  # all dependencies moved to separate virtual env
                            job_dir = "package_shield/"
                            job_name = job_dir + "shield" + "_" + repo
                            head_repo_owner = self.pr.head_label.split(":")[0]  # FORK cases
                            params_dict = dict(GIT_REPO=head_repo, GIT_HEAD_BRANCH=self.pr.head_branch,
                                               GIT_BASE_BRANCH=self.pr.base_branch,
                                               GIT_HEAD_BRANCH_OWNER=head_repo_owner, GIT_PULL_REQUEST_LINK=pr_link,
                                               GIT_SHA=self.pr.head_sha, AUTHOR_SLACK_NAME=pr_by_slack_name,
                                               GIT_PR_AUTHOR=self.pr.opened_by)

                            if repo == "inapp-rest-service":
                                """
                                2.3) Run for inapp_rest_services(one extra test) + moengage repo
                                """
                                job_dir = "inapps/"
                                job_name = job_dir + "integration_tests_webinapp"
                                head_repo_owner = self.pr.head_label.split(":")[0]  # FORK cases
                                api_params_dict = dict(GIT_REPO=head_repo, GIT_HEAD_BRANCH=self.pr.head_branch,
                                                       GIT_BASE_BRANCH=self.pr.base_branch,
                                                       GIT_HEAD_BRANCH_OWNER=head_repo_owner,
                                                       GIT_PULL_REQUEST_LINK=pr_link,
                                                       GIT_SHA=self.pr.head_sha, AUTHOR_SLACK_NAME=pr_by_slack_name,
                                                       GIT_PR_AUTHOR=self.pr.opened_by)
                                print("hit api tests, params_dict=", api_params_dict)
                                self.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token,
                                                           job_name=job_name,
                                                           pr_link=pr_link, params_dict=api_params_dict,
                                                           pr_by_slack=pr_by_slack_uid)

                        # Run main test
                        self.actor.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job_name,
                                        pr_link=pr_link, params_dict=params_dict,
                                        pr_by_slack=pr_by_slack_uid)

            # 3) Third Task - set_labels
            self.add_label_to_issue(repo, self.pr.number, [])

            # 4) Comment Checklist
            self.comment_on_pr()

            # 5) code_freeze alert
            self.code_freeze()

            # 6) release_freeze_alert
            self.release_alert()

        else:
            """
            3) last task task, When pull request is merged, 
            we run two checks.
            First, We alert if pull request is merged_by a person,
             who is not a valid contributor.
            Second, DM to pm for qa.
            """

            # 3.1)
            self.code_freeze_alert()

            # 3.2)
            self.release_freeze_alert()

            # 3.3)
            self.valid_contributors()

            # 3.4)
            self.notify_pm()
