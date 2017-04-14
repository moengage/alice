from alice.helper.common_utils import CommonUtils

class ConfigProvider(object):
    # __metaclass__ = SingletonMetaClass

    def __init__(self, repo):
        self.repo = repo
        config_file = 'config.json'
        self.config = CommonUtils.readResourceJson(__name__, config_file)

    def __str__(self):
        return "Alice - Common Config Provider"

    @property
    def githubToken(self):
        return self.config.get('tokens').get("github")

    @property
    def alertChannelName(self):
        if self.config.get("debug"):
            return self.config.get("repo").get('debug_alice', {}).get('alert_channel')
        return self.config.get("repo").get(self.repo, {}).get('alert_channel')

    @property
    def repo(self):
        return self.config.get("repo").get(self.repo, {})

    @property
    def codeChannelName(self):
        return self.repo().get('code_channel')

    @property
    def sensitiveBranches(self):
        return self.repo().get('sensitive_branches')

    @property
    def branchListToBeNotifiedFor(self):
        return self.repo().get('notify_direct', {}).get('branch_list_to_be_notified')

    @property
    def actionToBeNotifiedFor(self):
        return self.repo().get('notify_direct', {}).get('action_to_be_notified_on')

    @property
    def whiteListedMembers(self):
        return self.repo().get('whitelisted_git_members')

    @property
    def organisation(self):
        return self.config.get('organisation')

    @property
    def mainBranch(self):
        return self.config.get(self.repo, {}).get('main_branch')

    @property
    def personToBeNotified(self):
        return self.repo().get('notify_direct', {}).get('person_to_be_notified')

    @property
    def techLeadsToBeNotified(self):
        return self.repo().get('notify_direct', {}).get('tech_leads_to_be_notified')


