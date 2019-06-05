# coding=utf-8
import json
import re

import requests
from slacker import Slacker

from alice.config.message_template import JIRA_COMMENT, JIRA_ISSUE_UPDATE
from alice.helper.api_manager import ApiManager
from alice.helper.constants import API_JIRA_USERS, API_JIRA_USERS_ACCOUNTID
from alice.helper.log_utils import LOG


class JiraActor():
    def __init__(self, parsed_data):
        self.parsed_data = parsed_data
        self.jira_token = parsed_data.config.jiraToken
        self.slack_token = parsed_data.config.slackToken
        self.jira_domain = parsed_data.config.jiraDomain
        self.tagged_users = list()
        self.jira_dict = dict()
        self.js_map_dict = dict()
        self.slack_dict = dict()
        self.description = ''

        if parsed_data.issue_description:
            self.description = parsed_data.issue_description

    def get_slack_users(self):
        slack = Slacker(self.slack_token)
        resp = slack.users.list()
        users = resp.body.get('members')
        for item in users:
            self.slack_dict[item["profile"].get("email")] = item["id"]

    def fetch_users(self):
        if self.parsed_data.comment:
            self.tagged_users = re.findall("\[~(.*?)\]", self.parsed_data.comment)
            return self.tagged_users
        else:
            return []

    def fetch_email(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.jira_token
        }
        for user in self.tagged_users:
            if 'accountid:' in user:
                account_id = user.replace('accountid:', '')
                url = API_JIRA_USERS_ACCOUNTID.format(account_id=account_id, jira_domain=self.jira_domain)
            else:
                url = API_JIRA_USERS.format(user_key=user, jira_domain=self.jira_domain)
            response = ApiManager.get(url=url, headers=headers)
            if response["status_code"] != 200:
                raise Exception(response["content"], "Please check the provided Jira Token, ")
            response = json.loads(response['content'])
            self.jira_dict[user] = response.get('emailAddress')
        return self.jira_dict
    
    def slack_jira_map(self):
        if self.jira_dict:
            for item in self.jira_dict:
                if self.slack_dict.has_key(self.jira_dict[item]):
                    self.js_map_dict[item] = self.slack_dict[self.jira_dict[item]]
        return self.js_map_dict

    def send_to_slack(self):
        final_text = str(self.parsed_data.comment)
        for item in self.js_map_dict:
            final_text = final_text.replace('[~{0}]'.format(item), '<@{0}>'.format(self.js_map_dict.get(item)))
        LOG.info('************ final comment ************ %s' % final_text)
        first_attach = JIRA_COMMENT.copy() # shallow copy
        first_attach["pretext"] = first_attach.get("pretext").format(commenter=self.parsed_data.commenter, issue_key=self.parsed_data.issue_key)
        first_attach["title"] = first_attach.get("title").format(issue_key=self.parsed_data.issue_key, issue_title=self.parsed_data.issue_title)
        first_attach["title_link"] = first_attach.get("title_link").format(issue_url=self.parsed_data.issue_url)
        first_attach["text"] = first_attach.get("text").format(final_text=final_text)
        attachment = list()
        attachment.append(first_attach)
        slack = Slacker(self.slack_token)
        for item in self.js_map_dict:
            resp = slack.chat.post_message(channel=self.js_map_dict.get(item), text="", username="alice", as_user=False, attachments=attachment)

    def handle_issue_update(self):
        assignee_slack_channel_id = self.slack_dict.get(self.parsed_data.assignee_email)
        reporter_slack_channel_id = self.slack_dict.get(self.parsed_data.issue_reporter_email)
        LOG.info('*********** assigne slack channel id update handler ************ %s' % assignee_slack_channel_id)
        LOG.info('*********** reporter slack channel id update handler ************ %s' % reporter_slack_channel_id)
        attachment = list()
        for change in self.parsed_data.change_log:
            attach = JIRA_ISSUE_UPDATE.copy()
            if change.get("field") == "description":
                attach['pretext'] = "*{issue_updated_by}* updated {issue_key} `{field}`".format(
                                                                issue_updated_by=self.parsed_data.issue_updated_by,
                                                                issue_key=self.parsed_data.issue_key,
                                                                field=change.get('field'),
                                                                )
            else:
                if change.get('fromString'):
                    attach['pretext'] = attach.get("pretext").format(issue_updated_by=self.parsed_data.issue_updated_by,
                                                                    issue_key=self.parsed_data.issue_key,
                                                                    field=change.get('field'),
                                                                    from_string=change.get('fromString'),
                                                                    to_string=change.get('toString'))
                else:
                    attach['pretext'] = "*{issue_updated_by}* updated {issue_key} `{field}` to `{to_string}`".format(
                                                                    issue_updated_by=self.parsed_data.issue_updated_by,
                                                                    issue_key=self.parsed_data.issue_key,
                                                                    field=change.get('field'),
                                                                    to_string=change.get('toString'))
            attach["title"] = attach.get("title").format(issue_key=self.parsed_data.issue_key, issue_title=self.parsed_data.issue_title)
            attach["title_link"] = attach.get("title_link").format(issue_url=self.parsed_data.issue_url)
            attach["text"] = attach.get("text").format(issue_desc=self.description)
            attachment.append(attach)
        slack = Slacker(self.slack_token)
        resp = slack.chat.post_message(channel=str(reporter_slack_channel_id), text="", username="alice", as_user=False, attachments=attachment)
        resp = slack.chat.post_message(channel=str(assignee_slack_channel_id), text="", username="alice", as_user=False, attachments=attachment)


    def handle_issue_create(self):
        assignee_slack_channel_id = self.slack_dict.get(self.parsed_data.assignee_email)
        LOG.info('*********** assigne slack channel id create handler ************ %s' % assignee_slack_channel_id)
        attachment = list()
        fields = list()
        for change in self.parsed_data.change_log:
            field_item = dict()
            field_list = ['assignee', 'description', 'priority', 'Status']
            if str(change.get("field")) in field_list:
                field_item["title"] = str(change.get("field"))
                field_item["value"] = str(change.get("toString"))
                fields.append(field_item)
        
        attach = JIRA_ISSUE_UPDATE.copy()
        attach['pretext'] = '*{issue_reporter}* reported issue *{issue_key}*'.format(issue_reporter=self.parsed_data.issue_reporter,
                                                                                    issue_key=self.parsed_data.issue_key)
        attach["title"] = attach.get("title").format(issue_key=self.parsed_data.issue_key, issue_title=self.parsed_data.issue_title)
        attach["title_link"] = attach.get("title_link").format(issue_url=self.parsed_data.issue_url)
        attach["text"] = ''
        attach["fields"] = fields
        attachment.append(attach)
        slack = Slacker(self.slack_token)
        resp = slack.chat.post_message(channel=str(assignee_slack_channel_id), text="", username="alice", as_user=False, attachments=attachment)