# coding=utf-8
from alice.config.config_provider import ConfigProvider
from alice.helper.common_utils import CommonUtils
from alice.helper.log_utils import LOG


class Base(object):
    pass


class JiraPayloadParser(Base):

    def __init__(self, request, payload):
        self.assignee = dict()
        self.request = request
        self.payload = payload
        self.issue = payload["issue"]
        self.config = ConfigProvider()

        if isinstance(self.issue["fields"].get("assignee"), dict):
            self.assignee = self.issue["fields"].get("assignee")


    @property
    def webhook_event(self):
        return self.payload.get("webhookEvent")

    @property
    def comment(self):
        return (self.payload.get("comment", {}).get("body")).encode(encoding="utf-8")

    @property
    def commenter(self):
        return self.payload.get("comment", {}).get("updateAuthor", {}).get("displayName")

    @property
    def assignee_name(self):
        return self.assignee.get("name")

    @property
    def assignee_key(self):
        return self.assignee.get("key")

    @property
    def assignee_email(self):

        return self.assignee.get("emailAddress")

    @property
    def change_log(self):
        return self.payload.get("changelog", {}).get('items') # returns list of change log

    @property
    def issue_id(self):
        return self.issue.get("id")

    @property
    def issue_key(self):
        return self.issue.get("key")

    @property
    def issue_url(self):
        return 'https://moengagetrial.atlassian.net/browse/{issue_key}'.format(issue_key=self.issue_key)

    @property
    def issue_title(self):
        return self.issue['fields'].get('summary')

    @property
    def issue_reporter(self):
        return self.issue['fields'].get('reporter', {}).get('displayName')

    @property
    def issue_reporter_email(self):
        return self.issue['fields'].get('reporter', {}).get('emailAddress')

    @property
    def issue_description(self):
        desc = self.issue['fields'].get('description', '')
        if desc:
            desc = desc.encode(encoding="utf-8")
        return desc

    @property
    def issue_updated_by(self):
        return self.payload.get('user', {}).get('displayName')

    @property
    def issue_updated_by_email(self):
        return self.payload.get('user', {}).get('emailAddress')