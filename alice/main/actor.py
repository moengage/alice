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
        self.channel_name = self.pr.config.constants.get('channel_name')
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
                    self.slack.postToSlack(self.pr.config.alertChannelName, msg)
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
                if self.pr.base_branch == self.pr.config.mainBranch:
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

        if self.base_branch == master_branch and head_branch != qa_branch:

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
            self.slack.postToSlack(self.pr.config.alertChannelName, self.get_slack_name_for_git_name(self.created_by) + ": " + msg)
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
            if self.pr.base_branch == master_branch:
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
        if self.pr.action in close_action and self.pr.is_merged and self.pr.base_branch == self.pr.config.mainBranch \
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
        res = json.loads(response["content"])
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

    def get_slack_name_for_git_name(self, name):
        """
        Had problem in sending messages as it was not recognized by slack.
        Using this function to get slack_id corresponding to git name
        """
        git_mapping = json.loads(self.pr.config.constants.get('git_mappings'))
        for key, value in git_mapping.items():
            if key == name:
                return "<@" + value + ">"
        return "<@" + name + ">"

    def get_slack_name_for_id(self, id):
        """
        Had problem in sending messages as it was not recognized by slack.
        Using this function to get slack_id corresponding to slack_name
        """
        slack_mapping = json.loads(self.pr.config.constants.get('slack_mappings'))
        if type(id) == type([]):
            new_list = []
            for item in id:
                if item in slack_mapping:
                    new_list.append("<@" + slack_mapping[item] + ">")
                else:
                    if item.startswith('@'):
                        new_list.append(item)
                    else:
                        new_list.append("<@" + item + ">")
            return ' '.join(map(str, new_list))
        else:
            for key, value in slack_mapping.items():
                if key == id:
                    return "<@" + value + ">"
                elif id.startswith('@'):
                    return id
            return "<@" + id + ">"

    def hit_jenkins_job(self, jenkins_instance, token, job_name, pr_link, params_dict, pr_by_slack):
        a = datetime.datetime.now()
        if self.pr.config.is_debug:
            return
        else:
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

            except HTTPError as err:
                print(err)
                msg = "<@UL91SP77H> Error in alice , Jenkins HTTP error"
                self.slack.postToSlack(ALICE_ERROR, msg)
                traceback.print_exc()
                raise TimeoutError
            except (ConnectionError, ConnectionRefusedError, ConnectionResetError, TimeoutError):
                print("Connection error")
                msg = "<@UL91SP77H> Error in alice , Jenkins Connection error"
                self.slack.postToSlack(ALICE_ERROR, msg)
                traceback.print_exc()
                raise TimeoutError
            except Exception as e:
                print(e)
                msg = "<@UL91SP77H> Error in alice , Jenkins Connection error"
                self.slack.postToSlack(ALICE_ERROR, msg)
                traceback.print_exc()
                raise Exception(e)

    def run_for_angular(self, context_angular, job_dir, repo, pr_by_slack_name, is_change_angular, jenkins_instance,
                        token, pr_by_slack_uid):
        self.jenkins.change_status(self.pr.statuses_url, "pending", context=context_angular,
                                   description="Hold on!",
                                   details_link="")
        job_name = job_dir + "shield_dashboard_angular"
        params_dict = dict(repo=repo, head_branch=self.pr.head_branch, base_branch=self.pr.base_branch,
                           sha=self.pr.head_sha,
                           description="Syntax Validation [React Code]", author=pr_by_slack_name,
                           author_github=self.pr.opened_by, pr_no=self.pr.link_pretty,
                           shield_angular=is_change_angular)
        self.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job_name,
                             pr_link=self.pr.link_pretty,
                             params_dict=params_dict, pr_by_slack=pr_by_slack_uid)

    def run_for_react(self, job_dir, repo, pr_by_slack_name, jenkins_instance, token, pr_by_slack_uid):
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
        """
        Prepare for next release, Sending Slack message to product and qa team.
        """
        if self.pr.action.find("close") != -1 and self.pr.is_merged == True and (
                self.pr.base_branch == master_branch and self.pr.head_branch == staging_branch):

            """ ********** Remind PM teams to update release notes for next release ************ """
            alice_product_team = json.loads(self.pr.config.constants.get('alice_product_team'))
            for item in alice_product_team:
                message = " current release <{pr_link}|{pr_title}>  is going live shortly. Please keep QA team updated " \
                          "about your next release plans".format(pr_link= self.pr.link_pr, pr_title= self.pr.title)
                self.slack.postToSlack(item, "\n:bell: hi " + self.get_slack_name_for_id(item) + message,
                                       data={"username": bot_name}, parseFull=False)
            """ for bot """
            alice_qa_team = json.loads(self.pr.config.constants.get('alice_qa_team'))
            for item in alice_qa_team:
                self.slack.postToSlack(item, "\n hi " + self.get_slack_name_for_id(item)  +" " +random.choice(
                    applaud_list) + " :+1: thank you for the QA signOff\n :bell: " +
                                    "<{}|".format(self.pr.config.post_release_deployment) + random.choice(post_checklist_msg) + ">",
                                       data={"username": bot_name}, parseFull=False)  #TODO (Change hardcoded url to bring from commons
            write_to_file_from_top(release_freeze_details_path, ":clubs:" +
                                   str(datetime.datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
                                       '%B %d,%Y at %I.%M %p')) + " with <" + self.pr.link_pretty + "|master> code")  # on:" + str(datetime.datetime.now().strftime('%B %d, %Y @ %I.%M%p'))
            clear_file(code_freeze_details_path)  # clear last code freeze

    def check_valid_contributor(self):
        if self.pr.action == "closed" and self.pr.is_merged == True and self.pr.base_branch == staging_branch and (
                self.pr.merged_by not in self.pr.config.valid_contributors):
            merged_by_slack_uid = CommonUtils.get_slack_nicks_from_git(self.pr.merged_by)
            alice_dev_team_MoEngage_repo = json.loads(self.pr.config.constants.get('alice_dev_team_moengage_repo'))
            msg = "Very Bad <@" + merged_by_slack_uid + "> :rage4: :rage4: !! " + self.pr.link_pr \
                  + " is merged directly into `" + self.pr.base_branch + \
                  "`, but not by QA team, soon these kind of requests will be automatically reverted CC: " + \
                  self.get_slack_name_for_id(alice_dev_team_MoEngage_repo)
            print(msg)
            print(self.slack.postToSlack(self.channel_name, msg, data={"username": bot_name}))

    def code_freeze(self):

        if (self.pr.base_branch == staging_branch and self.pr.head_branch == dev_branch) \
                and (self.pr.action.find("opened") != -1):
            print("************ code freeze PR is opened from dev to QA, auto create PRs for dependent packages")
            self.slack.postToSlack(self.channel_name,
                                   "<!channel> Freezing code now. Any pending merge? please reach QA team within 10 minutes",
                                   data={"username": bot_name}, parseFull=False)
        # self.freeze_other_repos("staging")

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
            body = "Please merge these for code freeze. Release testing is getting started with MoEngage repo freeze\n " \
                   "cc: @prashanthegde9 @BhuvanThejaChennuru @gagana11 @geetima12"
        elif freeze_type == "live":
            head = "release"
            base = "master"
            title = "{head} -> {base} {time}".format(head=head, base=base, time=timestamp)
            alert = "\n:bell: MoEngage Repo: Release time:: Please verify your package(s) if they needs to go live"
            body = "RELEASENOTES.md at root"  # read release notes file

        """ Announce on channel """
        self.slack.postToSlack(self.channel_name, alert, data={"username": bot_name})

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
            data = json.dumps(pr_data)
            response = requests.post(pr_endpoint, headers={
                "Authorization": "token " + self.github.GITHUB_TOKEN}, data=json.dumps(pr_data))
            res = json.loads(response.content)
            notify_people = json.loads(self.pr.config.constants.get('pkg_people_to_notify'))
            if not res.get("errors"):
                # for person in pkg_people_to_notify:
                self.slack.postToSlack(self.channel_name,
                                       "%s) *%s:* %s number <%s|%s>" % (
                                       cnt, repo, self.get_slack_name_for_id(notify_people.get(repo, "pooja")),
                                       res.get("html_url"), res.get("number")),
                                       data={"username": bot_name}, parseFull=False)
            else:
                try:
                    error_message = res["errors"][0]["message"]
                    custom_message = "%s) *%s:* %s %s <%s|check here> " % (
                        cnt, repo, self.get_slack_name_for_id(notify_people.get(repo, "pooja")),
                        "Pull Request is already open",
                        github_site_url + "moengage/"
                        + repo + "/compare/" + base + "..." + head)
                    if "no commits" in error_message.lower():
                        custom_message = "%s) *%s:* %s <%s|check here> " % (
                            cnt, repo, error_message,
                            github_site_url + "moengage/" + repo + "/compare/" + base + "..." + head)

                    self.slack.postToSlack(channel = self.channel_name, msg = custom_message, data={"username": bot_name})
                    self.slack.postToSlack(channel = ALICE_ERROR, msg = "@pooja" +  ":warning: creating automatic PR for %s failed, response=\n%s"
                                            % (repo, json.dumps(res)))
                except Exception as e:
                    print(e)
                    self.slack.postToSlack("@pooja",
                                            ":skull: error in sending failure message on PR creation failure, response=\n%s"
                                            % (repo))
            cnt += 1

    def release_alert(self):
        """
        Alert when doing a release, when qa-> master it is release.
        """
        if self.pr.action.find("close") != -1 and self.pr.is_merged == True and (
                self.pr.base_branch == master_branch and self.pr.head_branch == staging_branch):
            """ ************* inform channel *************** """
            product_notify_slack = json.loads(self.pr.config.constants.get('product_notify_slack'))
            tech_leads_to_notify_always_slack = json.loads(self.pr.config.constants.get('tech_leads_to_notify_always_slack'))
            dev_ops_team = json.loads(self.pr.config.constants.get('dev_ops_team'))
            to_notify = self.pr.config.constants.get('to_be_notified')
            msg = "{2} QA passed :+1: `master` is <{1}|updated> for release \n cc: {0} {3} {4} \n <!channel> ".format(
                self.get_slack_name_for_id(to_notify), self.pr.link_pretty,
                self.get_slack_name_for_id(dev_ops_team), self.get_slack_name_for_id(tech_leads_to_notify_always_slack),
                self.get_slack_name_for_id(product_notify_slack))

            self.slack.postToSlack(self.channel_name, msg, data=CommonUtils.get_bot(self.channel_name, merged_by_slack_name),
                                   parseFull=False)

        if self.pr.action.find(
                "open") != -1 and self.pr.base_branch == master_branch and self.pr.head_branch == staging_branch:

            pr_by_slack_uid = CommonUtils.get_slack_nicks_from_git(self.pr.opened_by)
            print(
                "************ MoEngage repo:: PR opened to " + self.pr.base_branch + " Notify Alice & comment guidelines ****")
            msg = "MoEngage repo:: <{link_pr}|{title_pr}> is opened to `{base_branch}` by:*<@{pr_by_slack}>* " \
                .format(link_pr=self.pr.link_pr, title_pr=self.pr.title, pr_by_slack=pr_by_slack_uid,
                        base_branch=self.pr.base_branch)

            self.add_comment_to_master()

            alice_tech_leads_MoEngage_Repo = json.loads(self.pr.config.constants.get('alice_tech_leads_moengage_repo'))
            for item in alice_tech_leads_MoEngage_Repo:
                self.slack.postToSlack(item,
                                       msg + "\n Please review and approve with +1, Release preparation starts...",
                                       data={"username": bot_name}, parseFull=False)
            # self.freeze_other_repos("live")

            alice_qa_team = json.loads(self.pr.config.constants.get('alice_qa_team'))
            for item in alice_qa_team:
                self.slack.postToSlack(item,
                                       "\n\n:bell: *Bugs clean time* :: please make out 20 minutes max to cleanup no longer valid old issues and share a rough number of issues we cleaned or require attention <https://docs.google.com/spreadsheets/d/1WeWLuIE7Dt5G8lWACZs21WO0B07-naQ7JlUb8cHcxVA/edit#gid=1591591107|sheet link>",
                                       data={"username": bot_name}, parseFull=False)
            alice_product_team = json.loads(self.pr.config.constants.get('alice_product_team'))
            for item in alice_product_team:
                self.slack.postToSlack(item,
                                       "\n:bell: Hi " + self.get_slack_name_for_id(item) + " *Release notes update required*: Current release is getting ready to go Live, please help us with next release planning by having \"Next Release\" <https://docs.google.com/a/moengage.com/spreadsheets/d/1eW3y-GxGzu8Jde8z4EYC6fRh1Ve4TpbW5qv2-iWs1ks/edit?usp=sharing|sheet> updated",
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
        header = {"Authorization": "token " + self.github.GITHUB_TOKEN}
        res = ApiManager.get(url, header)["response"].json()
        return res["files"]

    def print_curl(self, req):
        method = req.method
        uri = req.url
        headers = ['"{0}: {1}"'.format(k, v) for k, v in req.headers.items()]
        headers = " -H ".join(headers)
        command = "curl -X {method} -H {headers} '{uri}'"
        print("************* cURL=", command.format(method=method, headers=headers, uri=uri))

    def broadcast_message(self, pr_by_slack_uid, merged_by_slack_uid):

        if self.pr.is_sensitive_branch and self.pr.repo in [moengage_repo, dashboard]:

            msg = "Title=\"{0}\",  Description=\"{1}\" \nPR: {2}\n from {3} into `{4}` By: <@{5}>, mergedBy: <@{6}>\n".format(
                self.pr.title, self.pr.description, self.pr.link_pr, self.pr.head_branch, self.pr.base_branch,
                pr_by_slack_uid, merged_by_slack_uid)
            channel_repo = self.pr.config.constants.get('code_merge_moengage')
            self.slack.postToSlack(channel_repo, msg, data={"username": bot_name})

    def dashboard_builder(self, pr_by_slack_uid, merged_by_slack_uid, jenkins_instance, token):
        repo = self.pr.repo
        msg = {"Package building not needed"}
        if self.pr.base_branch in package_builder_branches_repo_wise.get(repo.lower()):
            """ Cases
            head    base
            dev     qa                      staging build
            qa      master                  prod  build
            patch   master                  prod  build               
            feature qa                      staging
            feature master                  nothing
            feature dev                     nothing
            f1           f2                 nothing
            """
            release_type = ""
            dashboard_job_name = ""
            job_dir = "Dashboard/"

            if self.pr.base_branch == "qa":
                release_type = "minor"
                dashboard_job_name = job_dir + "dashboard_builder_staging"
            elif self.pr.base_branch == "master" and (self.pr.head_branch.startswith("patch") or
                                                      self.pr.head_branch.startswith("hotfix") or self.pr.head_branch.startswith("Hotfix")):
                release_type = "patch"
                dashboard_job_name = job_dir + "dashboard_builder_prod"
            elif self.pr.base_branch == "master" and self.pr.head_branch == "qa":
                release_type = "major"
                dashboard_job_name = job_dir + "dashboard_builder_prod"
            else:
                msg = "******  NOT TO BUILD CASE base_branch=%s head_branch=%s" % (
                self.pr.base_branch, self.pr.head_branch)
                print(msg)
                return {"msg": msg}

            sha = self.pr.statuses_url.rsplit("/", 1)[1]

            bump_version_job_dict = dict(release_type=release_type, repo=repo, pr_no=self.pr.number,
                                         pr_title=self.pr.title,
                                         pr_by_slack=pr_by_slack_uid, approved_by=merged_by_slack_uid,
                                         merged_by_slack=merged_by_slack_uid, sha=sha, base_branch=self.pr.base_branch,
                                         head_branch=self.pr.head_branch, is_ui_change=True)
            self.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=dashboard_job_name,
                                 pr_link=self.pr.link_pretty, params_dict=bump_version_job_dict,
                                 pr_by_slack=pr_by_slack_uid)
            msg = "dashboard builder started"
        return {"msg": msg}

    def after_merge_check(self, pr_by_slack_uid, merged_by_slack_uid):
        """
        When pull request is merged, we notify on slack ,
        whether it was merged correctly or not

        Todo - Frontend dashboard - react,
        Integration test - Inapp
        """
        repo = self.pr.repo
        sha = self.pr.statuses_url.rsplit("/", 1)[1]

        if self.pr.is_sensitive_branch and self.pr.action in close_action:
            if (self.pr.base_branch == staging_branch and self.pr.head_branch == master_branch) or (
                    self.pr.base_branch == dev_branch and self.pr.head_branch == staging_branch) or \
                    (self.pr.base_branch == staging_branch_commons and self.pr.head_branch == master_branch)\
                    or (self.pr.base_branch == dev_branch_commons and self.pr.head_branch == staging_branch_commons):

                print(":SKIP: back merge: ignore status alert, repo={repo} pr={link_pr} title={title_pr}".
                      format(repo=repo, link_pr=self.pr.link_pr, title_pr=self.pr.title))
            else:

                print(":DEBUG: merged into sensitive branch, checking PR's checks status")
                checks_status_url = base_api_cmd + repo + "/status/" + sha

                res_status = ApiManager.get(checks_status_url, headers={"Authorization": "token " + CommonUtils.GIT_TOKEN})

                status_dict = json.loads(res_status["content"])
                print(":DEBUG: status response content", status_dict)
                msg_start = repo + " repo: PR <{link_pr}|{title_pr}> is merged into `{base_branch}` "
                msg_end = " Merged by:*<@{merged_by_slack}>*, Author:*<@{pr_by_slack}>*"

                if self.pr.merged_by != "moeoperation":
                    if status_dict["state"] == "failure":

                        status_list = status_dict["statuses"]
                        context_description = ""
                        err_syntax_tests = ""
                        for item in status_list:
                            if item["context"].find("unit-test") != -1 and item["state"] == "failure":
                                context_description = item["description"]

                            if item["context"] == "shield-syntax-validator-python" and item["state"] == "failure":

                                err_syntax_tests = item["description"]

                        if context_description.lower().find("miss coverage") != -1:

                            actual_coverage = parse("{}Coverage: {actual_coverage} is {} {two} {}", context_description)
                            if actual_coverage:
                                actual_coverage = actual_coverage.named["actual_coverage"]
                            else:
                                return
                            msg = msg_start.format(link_pr=self.pr.link_pr, title_pr=self.pr.title, base_branch=self.pr.base_branch) \
                                  + " with *{actual_coverage}* coverage.".format(actual_coverage=actual_coverage) \
                                  + msg_end.format(pr_by_slack=pr_by_slack_uid, merged_by_slack=merged_by_slack_uid)
                            channel_slack = self.pr.config.constants.get('channel_low_cover')
                            self.slack.postToSlack(channel_slack, msg, data={"username": bot_name}, parseFull=False)
                            print(":INFO: missed coverage found and still merged, logged in into ci-rules-bypassed "
                                  "channel " + self.pr.link_pr)

                        else:

                            rule_broken = ""
                            if err_syntax_tests:
                                rule_broken = rule_broken + "*Syntax status:* " + err_syntax_tests + "\n"

                            if context_description:
                                rule_broken = rule_broken + "*Unit tests status:* " + context_description

                            msg = msg_start.format(link_pr=self.pr.link_pr, title_pr=self.pr.title, base_branch=self.pr.base_branch) \
                                  + "\n{rule} ".format(rule=rule_broken) \
                                  + msg_end.format(pr_by_slack=pr_by_slack_uid, merged_by_slack=merged_by_slack_uid)
                            channel_rule = self.pr.config.constants.get('channel_rules_broken_other_than_low_cover')
                            self.slack.postToSlack(channel_rule, msg, data={"username": bot_name}, parseFull=False)
                            print(":INFO: check fails and still merged, notified pooja " + self.pr.link_pr)

                    elif status_dict["state"] == "pending":

                        msg = "Very Bad :rage1: <@%s> you have misused 'admin' power by merging *without waiting for checks to complete*." % merged_by_slack_uid \
                              + msg_start.format(link_pr=self.pr.link_pr, title_pr=self.pr.title, base_branch=self.pr.base_branch) \
                              + "unchecked code is prone to break in production. cc: <@pooja> <@satya>"
                        channel_rule = self.pr.config.constants.get('channel_rules_broken_other_than_low_cover')
                        self.slack.postToSlack(channel_rule, msg, data={"username": bot_name},
                                    parseFull=False)
                        print(":INFO: check is still running but PR is merged by force. notified pooja " + self.pr.link_pr)
                    else:
                        print(":DEBUG: good merge, all checks looks pass pr=" + self.pr.link_pretty)

    def alert_on_slack(self, pr_by_slack_uid):
        """
        Post to slack when pr is opened or closed
        """

        repo = self.pr.repo
        if repo in repos_slack:

            cc_team = json.loads(self.pr.config.constants.get('alice_dev_team_segmentation_repo'))
            code_merge_channel = self.pr.config.constants.get('code_merge_segmentation')
            valid_contributors_segmentation_repo = json.loads(
                self.pr.config.constants.get('valid_contributors_segmentation_repo'))

            if repo == "commons":
                cc_team = json.loads(self.pr.config.constants.get('alice_dev_team_segmentation_repo'))
                cc_team.append("<@pruthvi>")
                code_merge_channel = self.pr.config.constants.get('code_merge_commons')

            if self.pr.action in open_action and self.pr.is_sensitive_branch:

                print("***** " + repo + ":: PR opened to develop/release/qa/master, Notify Alice & comment guidelines ****")
                msg = repo + " repo:: <{link_pr}|{title_pr}> is {action} to `{base_branch}` by:*<@{pr_by_slack}>* " \
                    .format(link_pr=self.pr.link_pr, title_pr=self.pr.title, pr_by_slack=pr_by_slack_uid,
                            base_branch=self.pr.base_branch, action=self.pr.action)

                to_notify = self.pr.config.constants.get('to_be_notified')
                self.slack.postToSlack('@' + to_notify, msg, data={"username": bot_name}, parseFull=False)
                return {"msg": msg}

            if self.pr.action in close_action and self.pr.is_merged and self.pr.is_sensitive_branch:

                print("**** Repo=" + repo + ", new merge came to " + self.pr.base_branch + " set trace to " + code_merge_channel + " channel")
                merged_by_slack_uid = CommonUtils.get_slack_nicks_from_git(self.pr.merged_by)

                msg = "Title=\"{0}\",  Description=\"{1}\" \nPR: {2}\n from {3} into `{4}` By: *<@{5}>*, mergedBy: <@{6}>\n".format(
                    self.pr.title, self.pr.description, self.pr.link_pr,
                    self.pr.head_branch, self.pr.base_branch, pr_by_slack_uid, merged_by_slack_uid)

                self.slack.postToSlack(code_merge_channel, msg, data={"username": bot_name})  # code-merged

            if self.pr.action in close_action and self.pr.is_merged and self.pr.base_branch == "release" \
                    and (self.pr.merged_by not in valid_contributors_segmentation_repo):

                print("**** Repo=" + repo + ", merged in branch=" + self.pr.base_branch +
                      " and is not authentic, alert the culprit " + self.pr.merged_by + " to channel")
                merged_by_slack_uid = CommonUtils.get_slack_nicks_from_git(self.pr.merged_by)
                msg = "Very Bad <@" + merged_by_slack_uid + "> :rage4: :rage4: !! " + self.pr.link_pr  + " is merged directly into " + \
                      self.pr.base_branch + "`, but not by Akshay/Pruthvi/Pooja, soon these kind of requests will be automatically reverted CC: " + \
                      self.get_slack_name_for_id(cc_team)
                print(msg)
                channel_alert = self.pr.config.constants.get('channel_name')
                self.slack.postToSlack(channel_alert, msg, data={"username": bot_name})

    def bump_version(self, pr_by_slack_uid, merged_by_slack_uid, jenkins_instance, token):
        repo = self.pr.repo
        sha = self.pr.statuses_url.rsplit("/", 1)[1]

        if repo == moengage_repo and self.pr.is_merged:

            if self.pr.base_branch == master_branch and self.pr.head_branch == staging_branch:

                """ ********** Bump Version ************** """
                print(":DEBUG: before hitting patch job is_ui_change=", ui_change)
                bump_version_job_dict = dict(release_type="major", repo=repo, pr_no=self.pr.number, pr_title=self.pr.title,
                pr_by_slack = pr_by_slack_uid, approved_by = merged_by_slack_uid,
                merged_by_slack = merged_by_slack_uid, sha = sha, head_branch = self.pr.head_branch,
                is_ui_change = ui_change)

                self.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name="VersionBumper_MoEngage",
                                     pr_link = self.pr.link_pretty, params_dict = bump_version_job_dict, pr_by_slack = pr_by_slack_uid)

            if self.pr.base_branch == master_branch and (self.pr.head_branch.startswith("patch") or
                                                         self.pr.head_branch.startswith("hotfix") or self.pr.head_branch.startswith("Hotfix")):
                msg = "MoEngage Repo: A patch came from head=" + self.pr.head_branch
                print(msg)

                """ ********** Bump Version ************** """
                checks_status_url = "%s%s/pulls/%s/reviews" % (base_api_cmd, repo, self.pr.number)
                print("**** get reviews if there is any approval api=***", checks_status_url)
                res_status = ApiManager.get(checks_status_url, headers={"Authorization": "token " + self.github.GITHUB_TOKEN})
                print("res_status=", res_status["content"])
                review_list = json.loads(res_status["content"])
                approved_by_list = []
                for item in review_list:
                    print(item)
                    if str(item["state"]).lower() == "approved":
                        approved_by_list.append(item["user"]["login"])

                approved_by = ""
                for name in approved_by_list:
                    approved_by += CommonUtils.get_slack_nicks_from_git(name) + " "

                bump_version_job_dict = dict(release_type="patch", repo=repo, pr_no=self.pr.number, pr_title=self.pr.title,
                                             pr_by_slack=pr_by_slack_uid, approved_by=approved_by,
                                             merged_by_slack=merged_by_slack_uid, sha=sha, head_branch=self.pr.head_branch,
                                             is_ui_change=ui_change)
                print(":DEBUG: before hitting patch job is_ui_change=", ui_change)
                self.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name="VersionBumper_MoEngage",
                                params_dict=bump_version_job_dict, pr_link=self.pr.link_pretty, pr_by_slack=pr_by_slack_uid)

    def post_to_slack_qa(self):
        """
        Posting release items to slack when merging to qa
        """
        if self.pr.base_branch == staging_branch and self.pr.head_branch == dev_branch:

            print("from 'dev' to 'qa', posting release items to slack")
            write_to_file_from_top(code_freeze_details_path, ":clubs:" + str(
                datetime.datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
                    '%B %d at %I.%M %p')) + " with <" + self.pr.link_pretty + "|PR>")

            msg = ""
            with open(file_path) as f:
                msg = f.read()
                # print 'loop msg=' + msg
                f.close()

            print("final msg 30 chars=" + msg[:30])
            if msg:
                # postAttachmentToSlack("#experiment",msg,data={"username": "github-bot"})
                self.slack.postAttachmentToSlack(self.channel_name, self.pr.link_pretty, msg, data={"username": bot_name}, parseFull=False)

                shutil.copy(file_path, '/opt/alice/release_items_' + str(
                    datetime.datetime.now().strftime('%m-%d-%Y:%I.%M%p')) + '.txt')  # take backup beforing clearing

                if not self.pr.config.is_debug:
                    open(file_path, 'w').close()  # clear file for next release content

            name = ""
            with open(file_mergedBy) as f:
                name = f.read()
                f.close()
            print("final name list =" + name)
            if name:
                time.sleep(10)
                # postFinalWarningToSlack("#experiment",name,data={"username": "github-bot"})
                self.slack.postFinalWarningToSlack(self.channel_name, name, data={"username": bot_name})
                open(file_mergedBy, 'w').close()

    def skip_checks(self,):
        """
        Added to avoid running our checks for bots like dependent bots where we dont need to run
        shield checks and all other things.
        :return:
        """
        if self.pr.opened_by in SKIP_SLACK_MESSAGE:
            return 1
        else:
            return 0

    def is_base_branch_changed(self):
        """
        When base branch is changed from x to y , all the shield checks that were run against x became of no use,
        so when this event occurs(EDIT), we rerun these shield checks
        :return:
        """
        if self.pr.action in edited_action:
            try:
                changes = self.pr.changes
                if "base" in changes and "ref" in changes["base"] and "from" in changes["base"]["ref"]:
                    print("BASE changed from ", changes["base"]["ref"]["from"], "Branch")
                    return 1
            except Exception as e:
                print(e)
                return 0
        return 0

    def is_ami_change_required(self):
        """
        1 -  required
        0 - not required
        ami change required.
        :return:
        """
        ami_change_required = 0

        if self.pr.repo == moengage_repo and (self.pr.base_branch == master_branch or
                                              self.pr.base_branch == ally_master_branch):

            if not self.file_content or "message" in self.file_content:
                print(":DEBUG: no files found in the diff: SKIP shield, just update the status")
                return 0  # STOP as files not found

            # If file contents are found, check which content we have to run.
            for item in self.file_content:
                file_path = item["filename"]
                if file_path.endswith("setup_bk.py") or file_path.endswith("fury.txt") or \
                        file_path.endswith("etc/init.d/moengage_package_manager.sh")\
                        or file_path.endswith("etc/init.d/moengage_package_manager_v2.sh"):
                    ami_change_required = 1

        return ami_change_required

    def get_labels_of_pr(self):
        """
        List all labels of pr
        :return:
        """
        pr_link = self.pr.link
        main_link = pr_link.split('pulls')[0]
        status_link = main_link + 'issues/' + str(self.pr.number) + '/labels'
        page_no = 1
        data = []
        while True:
            url_with_page = status_link + "?page=%s" % page_no
            headers = {"Authorization": "token " + self.github.GITHUB_TOKEN}
            response = ApiManager.get(url_with_page, headers)
            res = json.loads(response["content"])
            if not res or (isinstance(res, dict) and "limit exceeded" in res.get("message")):
                print(res)
                break
            data += res
            page_no += 1
        print("Labels Data", data)
        return data


    def is_send_to_slack(self):
        """
        To prevent duplicate messages on slack, we check for labels
        :return:
        """
        labels = self.get_labels_of_pr()
        send_to_slack = 1
        for label in labels:
            if "name" in label and label['name'] == AMI_LABEL:
                send_to_slack = 0
                break
        return send_to_slack

    def get_files_in_diff_and_set_in_function(self):
        try:
            files_contents, message = self.get_files(self.pr.link + "/files")
            self.file_content_message = message
        except PRFilesNotFoundException as e:
            files_contents = e.pr_response

        self.file_content = files_contents

    def trigger_task_on_pr(self):
        """
        For api test - we are following two different approaches,
        Moengage - we are checking whether there are some changes in certain location, we run api test
        Other repos - we take from config.yml and then run it ,
        """

        jenkins_setting = self.pr.global_config.config["jenkins"]
        token = jenkins_setting["token"]
        jenkins_instance = jenkins.Jenkins(jenkins_setting["JENKINS_BASE"],
                                           username=jenkins_setting["username"], password=token)
        repo = self.pr.repo
        merged_by_slack_uid = ""

        if self.pr.is_merged:
            merged_by_slack_uid = CommonUtils.get_slack_nicks_from_git(self.pr.merged_by)

        pr_by_slack_uid = CommonUtils.get_slack_nicks_from_git(self.pr.opened_by)
        pr_by_slack_name = CommonUtils.get_slack_nicks_from_git_name_nicks(self.pr.opened_by)

        """
        First we check whether pr is open, then we run our task
        """

        is_changed = self.is_base_branch_changed()

        if self.pr.action in action_commit_to_investigate or is_changed:

            is_skip = self.skip_checks() #added for dependent bots

            if is_skip == 1:
                return

            # 1) First task Done
            check_dangerous_pr = self.close_dangerous_pr()
            if not check_dangerous_pr:
                return {"msg": "closed dangerous PR %s" % self.pr.link_pretty}
            print("in trigger")

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
                print(":INFO: repo=%s" % repo)
                msg = "base={0} head={1}, action={2} Do nothing".format(self.pr.base_branch, self.pr.head_branch,
                                                                        self.pr.action)
                job_dir = "Dashboard/"

                self.jenkins.change_status(self.pr.statuses_url, "pending", context=context_react,
                                           description="Hold on!",
                                           details_link="")

                try:
                    files_contents, message = self.get_files(self.pr.link + "/files")
                except PRFilesNotFoundException as e:
                    files_contents = e.pr_response

                if not files_contents or "message" in files_contents:
                    print(":DEBUG: no files found in the diff: SKIP shield, just update the status")
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

                    print(":SKIP: alice code changes on melora branch")
                    return ":SKIP: alice code changes on " + repo

                elif repo.lower() == organization_repo and (
                        (self.pr.base_branch == staging_branch and self.pr.head_branch == master_branch) or
                        (self.pr.base_branch == dev_branch and self.pr.head_branch == staging_branch)):

                    print(":SKIP: back merge: checks call, repo={repo} pr={link_pr} title={title_pr}" \
                          .format(repo=repo, link_pr=self.pr.link_pr, title_pr=self.pr.title))
                    self.jenkins.change_status(self.pr.statuses_url, "success", context=context,
                                               description="checks bypassed for back merge",
                                               details_link="")
                    self.jenkins.change_status(self.pr.statuses_url, "success", context="shield-unit-test-python",
                                               description="checks bypassed for back merge",
                                               details_link="")

                else:
                    print(":INFO: repo=%s to validate, for PR=%s" % (repo, self.pr.number))
                    sensitive_branch = self.pr.config.sensitiveBranches

                    if self.pr.base_branch in sensitive_branch or self.pr.is_sensitive_branch:

                        # variable declaration
                        pr_link = self.pr.link_pretty
                        head_repo = self.pr.ssh_url
                        path = ""
                        is_lint_path='0'
                        files_ops = False
                        print("******* PR " + self.pr.action + "ed to " + self.pr.base_branch + ", Triggering tests ************")

                        self.get_files_in_diff_and_set_in_function()

                        change_required = self.is_ami_change_required()  # added this to avoid ami change

                        if change_required:
                            print("AMI change found")

                            do_slack = self.is_send_to_slack()
                            notify_regarding_ami_change = json.loads(self.pr.config.constants.get('ami_change_notify'))
                            msg = MSG_AMI_CHANGE.format(pr_link=pr_link, pr_name=self.pr.title,
                                                        person=self.get_slack_name_for_id(notify_regarding_ami_change))

                            self.jenkins.change_status(self.pr.statuses_url, "failure", context='Block-PR',
                                                       description="AMI dependency found, please contact Ajish",
                                                       details_link="")  # update status on jenkins and block pr
                            print("Slack status for version bumper", do_slack)
                            if do_slack:
                                channel_name_ami = self.pr.config.constants.get('ami_change_channel_name')
                                self.add_label_to_issue(repo, self.pr.number, [AMI_LABEL])
                                self.slack.postToSlack(self.channel_name, msg,
                                                       parseFull=False)  # update to ajish on weekly release

                        if repo in JAVA_REPO:
                            print("Bypassed pending status, as Context is different for Java Repos")
                            self.jenkins.change_status(self.pr.statuses_url, "pending", context=syntax_java,
                                                       description="Hold on!",
                                                       details_link="")  # status to go in pending quick
                            self.jenkins.change_status(self.pr.statuses_url, "pending",
                                                       context=unit_java, description="Hold on!",
                                                       details_link="")
                        else:
                            self.jenkins.change_status(self.pr.statuses_url, "pending", context=context,
                                                       description=context_description,
                                                       details_link="")  # status to go in pending quick
                            self.jenkins.change_status(self.pr.statuses_url, "pending",
                                                       context="shield-unit-test-python", description="Hold on!",
                                                       details_link="")
                        is_api_test = False

                        if not self.file_content or "message" in self.file_content:
                            print(":DEBUG: no files found in the diff: SKIP shield, just update the status")
                            self.jenkins.change_status(self.pr.statuses_url, "success", context=context_api_test,
                                                       description="SKIP: No diff, check the Files count",
                                                       details_link="")
                            self.jenkins.change_status(self.pr.statuses_url, "success",
                                                       context="shield-unit-test-python",
                                                       description="SKIP: No diff, check the Files count",
                                                       details_link="")
                            return self.file_content  # STOP as files not found

                        for item in self.file_content:
                            file_path = item["filename"]
                            if str(file_path).endswith(".py") and item["status"] != "removed":
                                path += " " + file_path
                                is_lint_path = '1'

                            elif str(file_path).endswith((".conf", ".cfg", ".init", ".sh")):
                                files_ops = True

                            if file_path.startswith(integration_test_file_path):
                                is_api_test = True
                            for folder in integration_test_folder_path:
                                if file_path.startswith(folder):
                                    is_api_test = True

                        if repo.lower() == organization_repo and files_ops and self.pr.action \
                                in action_commit_to_investigate:
                            self.add_label_to_issue(repo, self.pr.number,
                                                    ["DevOps_Review "])

                        # Run Jenkins for moengage repo
                        if repo == moengage_repo:
                            # For moengage repo we have to hit jenkins
                            # and we have some extra tasks also

                            """
                            API TESTING
                            Added task for Single sign on feature
                            When certain files are changed, then change flag of
                            """
                            for job in self.pr.config.shield_job:
                                job = job + "_" + self.pr.repo
                                params_dict = dict(repo=head_repo, head_branch=self.pr.head_branch,
                                                   base_branch=self.pr.base_branch,
                                                   pr_no=pr_link, lint_path=is_lint_path,
                                                   additional_flags="", msg="", machine="", sha=self.pr.head_sha,
                                                   author=pr_by_slack_name,
                                                   author_github=self.pr.opened_by,
                                                   is_api_test=is_api_test,
                                                   )
                                self.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job,
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
                            # run Jenkins for all other repo's
                            is_py_test = False
                            is_py_test = self.pr.config.py_test
                            is_api_test = self.pr.config.api_test

                            pr_link = self.pr.link_pretty
                            head_repo = self.pr.ssh_url

                            for job in self.pr.config.shield_job:
                                job_name = job
                                head_repo_owner = self.pr.head_label.split(":")[0]  # FORK cases
                                params_dict = dict(GIT_REPO=head_repo, GIT_HEAD_BRANCH=self.pr.head_branch,
                                                   GIT_BASE_BRANCH=self.pr.base_branch,
                                                   GIT_HEAD_BRANCH_OWNER=head_repo_owner, GIT_PULL_REQUEST_LINK=pr_link,
                                                   GIT_SHA=self.pr.head_sha, AUTHOR_SLACK_NAME=pr_by_slack_name,
                                                   GIT_PR_AUTHOR=self.pr.opened_by, RUN_PY_TEST=is_py_test,
                                                   RUN_API_TEST=is_api_test)
                                self.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token,
                                                     job_name=job_name,
                                                     pr_link=pr_link, params_dict=params_dict,
                                                     pr_by_slack=pr_by_slack_uid)

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

                            self.alert_on_slack(pr_by_slack_uid)

        elif self.pr.action in edited_action:
            """
            Adding this code because, we can edit pr to change base branch from qa to master, 
            thus want to check function of close pr in such case
            """
            check_dangerous_pr = self.close_dangerous_pr()
            if not check_dangerous_pr:
                return {"msg": "closed dangerous PR %s" % self.pr.link_pretty}


        elif self.pr.action in close_action:
            """
            3) When pull request is closed and merged ,
                we run following tasks-
                1) Build dashboad
                2) Broadcast message if pushed in sensitive branches
                3) After pr is merged post to slack whether pr was merged correctly or not.
            3) last task task, When pull request is merged/closed, 
            we run two checks.
            First, We alert if pull request is merged_by a person,
             who is not a valid contributor.
            Second, DM to pm for qa.
            """

            if self.pr.action in close_action and self.pr.is_merged:

                if repo in ui_repo:
                    """
                    For frontend repo run dashboard builder.
                    """
                    self.dashboard_builder(pr_by_slack_uid, merged_by_slack_uid, jenkins_instance, token)

                self.notify_channel_on_merge()
                # self.broadcast_message(pr_by_slack_uid, merged_by_slack_uid)
                self.after_merge_check(pr_by_slack_uid, merged_by_slack_uid)

                self.alert_on_slack(pr_by_slack_uid)

                if repo == moengage_repo:
                    # 3.2)
                    self.release_alert()

                    # 3.3)
                    self.check_valid_contributor()

                    # 3.4)
                    self.alert_pm()

                    # 3.5)
                    self.bump_version(pr_by_slack_uid, merged_by_slack_uid, jenkins_instance, token)

                    # 3.6)
                    self.post_to_slack_qa()


class Infra(object):

    def __init__(self):
        self.config = ConfigProvider()

    def infra_requests(self, payload):

        if "action" in payload and payload["action"] == "assigned":
            issue = {"assigned": False}
            issue["type"] = "infraRequests"
            issue["channel"] = self.config.constants.get('infra_channel')

            issue["url"] = payload["issue"]["html_url"]
            issue["title"] = payload["issue"]["title"]
            issue["labels"] = payload["issue"]["labels"]
            issue["assignee"] = ""
            try:
                issue["assignee"] = payload["assignee"]["login"]  # multi assignee case handle
            except Exception:
                issue["assignee"] = payload["issue"]["assignee"]["login"]

            issue["sender"] = payload["sender"]["login"]

            issue["slack_nick_assignee"] = CommonUtils.get_slack_nicks_from_git(issue["assignee"])
            issue["slack_nick_sender"] = CommonUtils.get_slack_nicks_from_git(issue["sender"])
            issue["slack_nick_creator"] = CommonUtils.get_slack_nicks_from_git(payload["issue"]["user"]["login"])

            issue["slack_nick_name_sender"] = issue["sender"]
            issue["slack_nick_name_creator"] = payload["issue"]["user"]["login"]

            msg = "hi <@{member}> could you please help me with this: <{pr_link}|{title}>".format(
                member=issue["slack_nick_assignee"], title=issue["title"],
                pr_link=issue["url"], by=issue["slack_nick_sender"])

            if issue["slack_nick_assignee"] not in self.config.constants.get('infra_members_verify'):

                msg = "<@{member}> Please verify and update the status or close it: <{pr_link}|{title}>".format(
                    member=issue["slack_nick_assignee"], title=issue["title"], pr_link=issue["url"])
                issue["slack_nick_name_creator"] = issue["slack_nick_name_sender"]

            SlackHelper(self.config).post_to_slack_infra(channel=issue["channel"], msg=msg, data=
                                                            CommonUtils.get_bot(issue["channel"],
                                                            issue["slack_nick_name_creator"]))

