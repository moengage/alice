import simplejson as json
import json as jon
from parse import parse
from alice.helper.file_utils import write_to_file_from_top, clear_file, read_from_file

from alice.commons.base import Base
from alice.config.message_template import MSG_BAD_START, MSG_AUTO_CLOSE, MSG_AMI_CHANGE, \
    MSG_OPENED_TO_MAIN_BRANCH, MSG_OPENED_TO_PREVENTED_BRANCH, SPECIAL_COMMENT, GENERAL_COMMENT, \
    MSG_RELEASE_PREPARATION, MSG_SENSITIVE_FILE_TOUCHED, MSG_QA_SIGN_OFF, MSG_CODE_CHANNEL, MSG_GUIDELINE_ON_MERGE, \
    CODE_FREEZE_TEXT, RELEASE_NOTES_REMINDER, DATA_SAVE_MERGED
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
from alice.config.config_provider import ConfigProvider
from urllib.error import HTTPError
from alice.helper.file_utils import get_dict_from_config_file

import os
import time
import pytz
import shutil
import datetime
import traceback

from alice.helper.api_manager import ApiManager


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
        self.channel_name = self.pr.config.constants.get('channel_name')
        self.alert_pr_channel = self.pr.config.constants.get('pr_alert_channel_name') #seperated as all alerts were spamming channels
        self.file_content = ''
        self.file_content_message = ''

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
        except PRFilesNotFoundException as e:
            LOG.exception(e)
        return sensitive_file_touched, change_requires_product_plus1

    def is_bad_pr(self):
        """
        parse approval's content to identify if PR is actually approved or just random approval click
        :return: bad_pr (boolean)
        """
        reviews = self.github.get_reviews()
        if 200 != reviews["status_code"]:
            raise Exception(reviews["content"])

        bad_pr = True
        LOG.info("***** Reading Reviews *****")
        for item in json.loads(reviews["content"]):
            if "APPROVED" == item["state"]:
                review_comment = item["body"]
                LOG.debug("review body= %s" + review_comment)
                thumbs_up_icon = THUMBS_UP_ICON in json.dumps(review_comment)
                LOG.debug("unicode thumbsUp icon present=%s" % (thumbs_up_icon))
                if self.pr.opened_by in self.pr.config.superMembers:  # FEW FOLKS TO ALLOW TO HAVE SUPER POWER
                    LOG.debug("PR is opened by %s who is the super user of repo %s, so NO alert'"
                              % (self.pr.opened_by_slack, self.pr.repo))
                    bad_pr = False
                    break
                LOG.info("***** review_comment %r" % review_comment)
                created_by = self.pr.config.getSlackName(self.pr.opened_by)
                if item["user"]["login"] != created_by and (review_comment.find("+1") != -1 or thumbs_up_icon):
                    LOG.debug("+1 is found from reviewer=%s marking No Alert " % item["user"]["login"])
                    bad_pr = False
                    break
        return bad_pr

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
                    self.slack.postToSlack(self.alert_pr_channel, msg)
                    LOG.info("Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=self.is_bad_pr))
                    return {"msg": "Bad PR={msg} repo:{repo}".format(repo=self.pr.repo, msg=self.is_bad_pr)}
                return {"msg": "Product approved so no alert, pr=%s" % self.pr.link_pretty}
            return {"msg": "Skipped product review because no changes found which requires product +1 as well, PR=%s"
                           % self.pr.link_pretty}
        return {"msg": "Skipped product review because the PR=%s is not merged" % self.pr.link_pretty}

    def is_plus_1_in_comments(self, comments, team):
        """
        parse comments and check if :+1: exists (symbol for approval)
        :param comments:
        :return: relevant response dict
        """
        is_plus_1 = False
        if self.change_requires_product_plus1:
            for comment in json.loads(comments["content"]):
                thumbs_up_icon = "\ud83d\udc4d" in json.dumps(comment["body"])
                if self.change_requires_product_plus1 and (comment["user"]["login"] in team) \
                        and (comment["body"].find("+1") != -1 or thumbs_up_icon):
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
                if self.pr.base_branch in self.pr.config.mainBranch:
                    guideline_comment = SPECIAL_COMMENT
                    guideline_comment = self.add_extra_comment(SPECIAL_COMMENT)
                    self.slack.postToSlack(self.pr.opened_by_slack, guideline_comment["body"])
                else:
                    guideline_comment = GENERAL_COMMENT
                    guideline_comment = self.add_extra_comment(GENERAL_COMMENT)
                self.github.comment_pr(self.pr.comments_section, guideline_comment["body"])
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
            if self.pr.base_branch in self.pr.config.mainBranch:
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
        return {"msg": "Skipped notify because its (%s) not desired event '%s'" % (self.pr.action, desired_action)}

    def remind_direct_release_guideline_on_merge(self):
        """
        Edge case - Can't send to mooperation
        remind individually to follow guidelines for QA process/ Sensitive branches.
        :return: relevant response dict
        """
        if self.pr.action in close_action and self.pr.is_merged:
            if self.base_branch in self.pr.config.sensitiveBranches or self.pr.is_sensitive_branch:
                msg = MSG_GUIDELINE_ON_MERGE.format(person=self.get_slack_name_for_git_name(self.created_by),
                                                    pr=self.pr.link_pretty,
                                                    base_branch=self.pr.base_branch, title=self.pr.title)
                if self.pr.config.is_debug:
                    self.slack.directSlack("UL91SP77H", msg)
                    LOG.info("slacked personally to %s" % "Paras")
                else:
                    git_mapping = json.loads(self.pr.config.constants.get('git_mappings'))
                    post_to_individual = git_mapping.get(self.created_by, None)
                    if post_to_individual is None:
                        return
                    self.slack.directSlack(post_to_individual, msg)
                    LOG.info("slacked personally to %s" % self.created_by)
                return {"msg": "slacked personally to %s" % self.created_by}
            return {"msg": "skipped slack personally because not sensitive branch"}
        return {"msg": "skipped slack personally to %s because its not merge event" % self.created_by}

    def close_dangerous_pr(self):
        """
        close a Pull Request which is not supposed to be opened Ex. base=master head=feature
        :return: relevant response dict
        """
        master_branch = self.pr.config.mainBranch
        qa_branch = self.pr.config.testBranch
        head_branch = self.head_branch

        if self.base_branch in master_branch and head_branch != qa_branch:

            if head_branch.lower().startswith("patch") or head_branch.lower().startswith("hotfix") or head_branch.lower().startswith("Hotfix"):
                print("*** SKIP closing, Its a patch from head_branch=", head_branch)
                msg = "PR opened to %s from %s" % (master_branch, head_branch)
                return {"msg": msg}

            if self.pr.pr_state == "closed":
                """
                This condition happens when we edit a PR to change its base branch to master, then we call
                close dangerous pr.
                Now, close dangerous pr first uses action "EDIT", to edit title and then close PR, now calling
                "EDIT" causes recursion, so this condition is base condition in recursion
                """
                msg = "PR is already closed"
                return 0

            if self.pr.repo in REPO_NOT_CLOSE:
                print("Repo closing skipped as Asked by tech leads")
                return 1

            msg = MSG_AUTO_CLOSE.format(tested_branch=qa_branch, main_branch=master_branch, pr_link=self.pr.link_pr)
            msg_to_github = "AUTO CLOSED : " + self.pr.title
            print("ALice is AUTO CLOSING PR")
            self.github.modify_pr(msg_to_github, "closed")
            self.slack.postToSlack(self.alert_pr_channel, self.get_slack_name_for_git_name(self.created_by) + ": " + msg)
            LOG.info("closed dangerous PR %s" % self.pr.link_pretty)
            return 0
        return 1

    def notify_if_sensitive_modified(self):
        """
        check & notify devOps team if any sensitive files are touched
        We only check for release note when merging into MASTER
        and changelog when merging into RELEASE
        """
        if self.pr.action in action_commit_to_investigate and self.pr.repo != moengage_repo:
            print("Checking Sensitive Files")
            commit_id = self.pr.head_sha
            base_url = "https://api.github.com/repos/moengage/{}".format(self.pr.repo) + "/commits/{}".format(commit_id)
            header = {"Authorization": "token " + "%s" % self.github.GITHUB_TOKEN}
            flag = 0
            channel_name = self.pr.config.constants.get('channel_name')
            commit_id_url = self.pr.link_pr + "/commits/%s"%commit_id
            if self.pr.base_branch in master_branch:
                response = ApiManager.get(base_url, header)
                data = json.loads(response["content"])
                if "files" in data:
                    file_data = data["files"]
                    for file in file_data:
                        if file["filename"] == sensitive_files_master:
                            flag = 1
                    if flag == 1:
                        msg = MSG_SENSITIVE_FILE_TOUCHED.format(file=sensitive_files_master, pr=self.pr.link_pr
                                                                , id=commit_id_url)
                        self.slack.postToSlack(channel_name, msg=msg)

            elif self.pr.base_branch == staging_branch_commons and self.pr.head_branch == dev_branch_commons:
                response = ApiManager.get(base_url, header)
                data = json.loads(response["content"])
                if "files" in data:
                    file_data = data["files"]
                    for file in file_data:
                        if file["filename"] == sensitive_files_release:
                            flag = 1
                    if flag == 1:
                        msg = MSG_SENSITIVE_FILE_TOUCHED.format(file=sensitive_files_release, pr=self.pr.link_pr
                                                                , id=commit_id_url)
                        self.slack.postToSlack(channel_name, msg=msg)

    def notify_qa_sign_off(self):
        """
        Notify to respective folks when qa is passed and code is moved to main branch Eg. master
        :return:
        """
        if self.pr.action in close_action and self.pr.is_merged and self.pr.base_branch in self.pr.config.mainBranch \
                and self.pr.head_branch == self.pr.config.testBranch:
            msg = MSG_QA_SIGN_OFF.format(person=self.get_slack_name_for_id(self.pr.config.personToBeNotified),
                                         pr=self.pr.link_pretty,
                                         dev_ops_team=self.get_slack_name_for_id(self.pr.config.devOpsTeamToBeNotified),
                                         main_branch = self.pr.config.mainBranch,
                                         tech_team=self.get_slack_name_for_id(self.pr.config.techLeadsToBeNotified))

            self.slack.postToSlack(self.pr.config.alertChannelName, msg,
                                   data=self.slack.getBot(self.pr.config.alertChannelName, self.merged_by))

            """ for bot to keep data ready for future use"""
            write_to_file_from_top(self.pr.config.releaseFreezeDetailsPath, ":clubs:" +
                                   str(datetime.datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
                                       '%B %d at %I.%M %p')) + " with <" + self.pr.link_pretty + "|master> code")
            clear_file(self.pr.config.codeFreezeDetailsPath)
            self.alert_pm()

    def notify_channel_on_merge(self):
        """
        pass entry in fixed channel for all code merge details (merged to any of sensitive branch)
        :return: relevant response dict
        """
        if self.pr.is_merged:
            LOG.debug("**** Repo=%s, new merge came to=%s, setting trace to=%s channel"
                      % (self.pr.repo, self.pr.base_branch, self.pr.config.codeChannelName))
            msg = MSG_CODE_CHANNEL.format(title=self.pr.title, desc=self.pr.description, pr=self.pr.link_pr,
                                          head_branch=self.pr.head_branch, base_branch=self.pr.base_branch,
                                          pr_by=self.get_slack_name_for_git_name(self.created_by),
                                          merge_by=self.get_slack_name_for_git_name(self.merged_by))
            channel_name = self.pr.config.codeChannelName
            self.slack.postToSlack(channel_name, msg)
            LOG.info("informed %s because pr=%s is merged into sensitive branch=%s" %
                     (self.pr.config.codeChannelName, self.pr.link_pretty, self.pr.base_branch))
            return {"msg": "informed %s because pr=%s is merged into sensitive branch=%s" %
                           (self.pr.config.codeChannelName, self.pr.link_pretty, self.pr.base_branch)}
        return {"msg", "Skipped posting to code channel because '%s' is not merge event" % self.pr.action}

    def notify_code_freeze(self):
        """
        gathers accumulated data after last qa_signOff and send an attachment into channel announcing details of code freeze
        :return: relevant response dict
        """
        if self.pr.action in close_action and self.pr.is_merged and (self.pr.base_branch == self.pr.config.testBranch \
                                  and self.pr.head_branch == self.pr.config.devBranch):
            LOG.debug("*** PR merged from {dev_branch} to {qa_branch}, posting release items to slack".
                      format(dev_branch=self.pr.config.devBranch, qa_branch=self.pr.config.testBranch))

            write_to_file_from_top(self.pr.config.codeFreezeDetailsPath, ":clubs:" + str(
                datetime.datetime.now(pytz.timezone(self.pr.config.timezone)).strftime(
                    '%B %d at %I.%M %p')) + " with <" + self.pr.link_pretty + "|PR>")

            try:
                msg = read_from_file(self.pr.config.releaseItemsFilePath)
                LOG.debug("final msg =" + msg)
            except Exception as e:
                return {"msg": "Skipped posting code-freeze because no details found in file %s"
                               % self.pr.config.releaseItemsFilePath}

            CODE_FREEZE_TEXT[0]["pretext"] = CODE_FREEZE_TEXT[0]["pretext"].format(dev_branch=self.pr.config.devBranch,
                                                                                   test_branch=self.pr.config.testBranch)
            CODE_FREEZE_TEXT[0]["fields"][0]["title"] = CODE_FREEZE_TEXT[0]["fields"][0].get("title") \
                .format(test_branch=self.pr.config.testBranch)
            CODE_FREEZE_TEXT[0]["fields"][1]["value"] = CODE_FREEZE_TEXT[0]["fields"][1]["value"].format(
                pr=self.pr.link_pretty)
            CODE_FREEZE_TEXT[0]["text"] = CODE_FREEZE_TEXT[0]["text"].format(msg=msg)
            CODE_FREEZE_TEXT[0]["title_link"] = CODE_FREEZE_TEXT[0]["title_link"] \
                .format(release_notes_link=self.pr.config.release_notes_link)

            self.slack.postToSlack(channel=self.pr.config.alertChannelName, attachments=CODE_FREEZE_TEXT)
            self.remind_all_finally_to_update_release_notes()
            return {"msg": "informed code-freeze on %s for pr=%s" % (self.pr.config.alertChannelName,
                                                                     self.pr.link_pretty)}
        return {"msg", "Skipped posting to code-freeze because its not code-freeze event, {pr_action}ed from "
                       "{dev_branch} -> {qa_branch} ".format(pr_action=self.pr.action,
                                                             dev_branch=self.pr.config.devBranch,
                                                             qa_branch=self.pr.config.testBranch)}

    def remind_all_finally_to_update_release_notes(self):
        """
        Final reminder to the folks who had merged code till the time code freeze was taken
        """
        names = read_from_file(self.pr.config.releaseItemsFileMergedBy)
        LOG.debug("final names list =" + names)
        if names:
            time.sleep(10)
            alice_qa_team = json.loads(self.pr.config.constants.get('alice_qa_team'))
            msg = RELEASE_NOTES_REMINDER.format(msg=names, release_notes_link=self.pr.config.release_notes_link,
                                                qa_team=self.get_slack_name_for_id(alice_qa_team))
            self.slack.postToSlack(channel=self.pr.config.alertChannelName, msg=msg)
            self.clean_up_for_next_cycle()

    def clean_up_for_next_cycle(self):
        """ backup & clean-up file for next release """
        shutil.copy(self.pr.config.releaseItemsFilePath, self.pr.config.backupFilesPath + '_'
                    + str(datetime.datetime.now().strftime('%m-%d-%Y:%I.%M%p')) + '.txt')  # take backup before clearing
        clear_file(self.pr.config.releaseItemsFileMergedBy)
        clear_file(self.pr.config.releaseItemsFilePath)  # clear file for next release content
        # NOTE: user has to manually delete data added when in debug mode

    def add_label_to_issue(self, repo, pr_no, list_labels):
        """
         Example : self.set_labels("MoEngage", 13319, ["Alice_test2"])
         :return:
         """
        api_label = "https://api.github.com/repos/moengage/%s/issues/%s/labels" % (repo, str(pr_no))
        headers = {"Authorization": "token " + self.github.GITHUB_TOKEN}
        return ApiManager.post(api_label, headers, json.dumps(list_labels))

    def diff_files_commits(self,repo):
        return

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
        self.jenkins.changeStatus(self.pr.statuses_url, "pending", context=context_angular,
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

    def print_curl(self, req):
        method = req.method
        uri = req.url
        headers = ['"{0}: {1}"'.format(k, v) for k, v in req.headers.items()]
        headers = " -H ".join(headers)
        command = "curl -X {method} -H {headers} '{uri}'"
        print("************* cURL=", command.format(method=method, headers=headers, uri=uri))
