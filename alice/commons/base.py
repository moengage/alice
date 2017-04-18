import logging
from alice.config.config_provider import ConfigProvider
from alice.helper.common_utils import CommonUtils

class Base(object):
    API_START_PR = "https://api.github.com/repos/moengage/MoEngage/pulls/"
    API_START_ISSUES = "https://api.github.com/repos/moengage/MoEngage/issues/"


class PushPayloadParser(Base):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def __init__(self, request, payload):
        self.request = request
        self.payload = payload
        self.pr = payload["pull_request"]
        self.config = ConfigProvider(self.repo)

    @property
    def repo(self):
        return self.payload["repository"]["name"]#self.data["head"]["repo"]["name"]

    @property
    def merged_by(self):
        return self.pr["merged_by"]["login"]

    @property
    def link_pretty(self):
        return self.pr["html_url"]

    @property
    def link(self):
        return self.pr["url"]

    @property
    def by(self):
        return self.pr["user"]["login"]

    @property
    def is_merged(self):
        return self.pr["merged"]

    @property
    def is_opened(self):
        return self.pr["action"] == "opened"

    @property
    def is_reopened(self):
        return self.pr["action"] == "reopened"

    @property
    def action(self):
        return self.payload["action"]

    @property
    def base_branch(self):
        return self.pr["base"]["ref"]

    @property
    def head_branch(self):
        return self.pr["head"]["ref"]
    
    @property
    def comments_section(self):
        return self.pr["_links"]["comments"]["href"]

    @property
    def is_sensitive_branch(self):
        return self.base_branch in self.config.sensitiveBranches()

    @property
    def merged_by_slack_nick(self):
        return CommonUtils.getSlackNicksFromGitNicks(self.merged_by)

    @property
    def created_by_slack_nick(self):
        return CommonUtils.getSlackNicksFromGitNicks(self.by)


