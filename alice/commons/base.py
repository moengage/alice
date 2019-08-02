from alice.config.config_provider import ConfigProvider
from alice.helper.common_utils import CommonUtils
from alice.helper.log_utils import LOG


class Base(object):
    pass


class PushPayloadParser(Base):
    """
    Adding global config as we want to
    want to access jenkins token
    """

    def __init__(self, payload):
        self.payload = payload
        self.pr = payload["pull_request"]
        LOG.debug("Repo=" + self.repo)
        self.config = ConfigProvider(self.repo)
        self.global_config = ConfigProvider()

    @property
    def repo(self):
        return self.payload["repository"]["name"]

    @property
    def number(self):
        return self.payload["number"]

    @property
    def opened_by(self):
        return self.pr["user"]["login"]

    @property
    def merged_by(self):
        return "paras"
      #  return self.pr["merged_by"]["login"]

    @property
    def merged_by_slack(self):
        return CommonUtils.get_slack_nicks_from_git(self.merged_by)

    @property
    def opened_by_slack(self):
        return CommonUtils.get_slack_nicks_from_git(self.opened_by)

    @property
    def link_pretty(self):
        return self.pr["html_url"]

    @property
    def link(self):
        return self.pr["url"]

    @property
    def is_merged(self):
        return self.pr["merged"]

    @property
    def action(self):
        return self.payload["action"]

    @property
    def is_opened(self):
        return self.action == "opened"

    @property
    def is_reopened(self):
        return self.action == "reopened"

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
    def pr_state(self):
        return self.pr["state"]

    @property
    def is_sensitive_branch(self):
        if self.config.sensitiveBranches is None:
            return None
        if self.config.sensitive_partial_branches is not None:
            for branch in self.config.sensitive_partial_branches:
                if self.base_branch.startswith(branch):
                    return 1
        return self.base_branch in self.config.sensitiveBranches

    @property
    def title(self):
        return self.pr["title"]

    @property
    def description(self):
        return self.pr["body"]

    @property
    def head_ref(self):
        return self.pr["base"]

    @property
    def head_label(self):
        return self.pr["head"]["label"]

    @property
    def ssh_url(self):
        return self.pr["head"]["repo"]["ssh_url"]

    @property
    def link_pr(self):
        return self.payload["pull_request"]["_links"]["html"]["href"]

    @property
    def statuses_url(self):
        return self.payload["pull_request"]["statuses_url"]

    @property
    def head_sha(self):
        return self.payload["pull_request"]["head"]["sha"]

    @property
    def base_sha(self):
        return self.payload["pull_request"]["base"]["sha"]

    @property
    def changes(self):
        return self.payload["changes"]
