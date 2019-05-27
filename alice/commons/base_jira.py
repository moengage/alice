from alice.config.config_provider import ConfigProvider
from alice.helper.common_utils import CommonUtils
from alice.helper.log_utils import LOG


class Base(object):
    pass


class JiraPayloadParser(Base):

    def __init__(self, request, payload):
        self.request = request
        self.payload = payload
        self.issue = payload["issue"]
        self.config = ConfigProvider()

    @property
    def webhook_event(self):
        return self.payload.get("webhookEvent")

    @property
    def comment(self):
        return self.payload.get("comment", {}).get("body")

    @property
    def commenter(self):
        return self.payload.get("comment", {}).get("updateAuthor", {}).get("displayName")

    @property
    def assignee_name(self):
        return self.issue["fields"].get("assignee",{}).get("name")

    @property
    def assignee_key(self):
        return self.issue["fields"].get("assignee",{}).get("key")

    @property
    def assignee_email(self):
        return self.issue["fields"].get("assignee",{}).get("emailAddress")

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
    def issue_description(self):
        desc = self.issue['fields'].get('description', '')
        desc = desc.encode(encoding="utf-8")
        return desc

    @property
    def issue_updated_by(self):
        return self.payload.get('user', {}).get('displayName')

        


