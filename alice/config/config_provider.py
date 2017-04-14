from alice.helper.common_utils import CommonUtils

class ConfigProvider(object):
    # __metaclass__ = SingletonMetaClass

    def __init__(self, repo):
        self.repo = repo
        config_file = 'config.json'
        self.config = CommonUtils.readResourceJson(__name__, config_file)

    def __str__(self):
        return "Alice - Common Config Provider"

    def getGithubToken(self):
        return self.config.get('tokens').get("github")

    def getAlertChannelName(self):
        if self.config.get("debug"):
            return self.config.get("repo").get('debug_alice', {}).get('alert_channel')
        return self.config.get("repo").get(self.repo, {}).get('alert_channel')

    def getRepo(self):
        return self.config.get("repo").get(self.repo, {})

    def getCodeChannelName(self):
        return self.getRepo().get('code_channel')

    def getSensitiveBranches(self):
        return self.getRepo().get('sensitive_branches')

    def getPersonToBeNotified(self):
        return self.getRepo().get('notify_direct', {}).get('person_to_be_notified')

    def getBranchListToBeNotifiedFor(self):
        return self.getRepo().get('notify_direct', {}).get('branch_list_to_be_notified')

    def getEventToBeNotifiedFor(self):
        return self.getRepo().get('notify_direct', {}).get('event_to_be_notified_on')

    def getWhiteListedMembers(self):
        return self.getRepo().get('whitelisted_git_members')

    def getOrganisation(self):
        return self.config.get('organisation')

    def getSpecialBranchNameToAddComment(self):
        return self.config.get(self.repo, {}).get('special_comment_branch')

