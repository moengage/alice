import os
from alice.helper.file_utils import get_dict_from_config_file, get_dict_from_yaml
from alice.helper.log_utils import LOG
from configparser import ConfigParser


class ConfigProvider(object):
    # __metaclass__ = SingletonMetaClass

    def __init__(self, repo=None):
        config_file = os.environ["config"]
        # LOG.info("********** config file=" + config_file)
        LOG.info("********** config file={config_file}".format(config_file=config_file))
        # absolute path to keep file anywhere
        self.config = get_dict_from_config_file(config_file)
        self.repo_name = repo
        config = ConfigParser()
        file_path = os.path.dirname(os.path.abspath(__file__))
        file_path = file_path[:file_path.rfind('/')] + '/constants.ini'
        config.read(file_path)
        if self.is_debug:
            self.constants = dict(config.items('testing_config'))
        else:
            self.constants = dict(config.items('config'))

    def __str__(self):
        return "Alice - Common Config Provider"

    @property
    def organisation(self):
        return self.config.get('organisation')

    @property
    def githubToken(self):
        return self.config.get('tokens').get("github")

    @property
    def github_alternate_token(self):
        return self.config.get('tokens').get("github_alternate")

    @property
    def slackToken(self):
        return self.config.get('tokens').get("slack")

    @property
    def jiraToken(self):
        return self.config.get('tokens').get("jira")

    @property
    def drone_token(self):
        return self.config.get('tokens').get("drone_token")

    @property
    def drone_secret(self):
        return self.config.get('tokens').get("drone_webhook_secret")

    @property
    def jiraDomain(self):
        return self.config.get('jira_domain')

    @property
    def is_debug(self):
        return self.config.get("debug", False)

    @property
    def repo(self):
        return self.config.get("repo", {}).get(self.repo_name, {})

    @property
    def sensitiveBranches(self):
        return self.repo.get('sensitive_branches')

    @property
    def sensitive_partial_branches(self):
        return self.repo.get('partial_sensitive_branches')

    @property
    def sensitiveFiles(self):
        return self.repo.get("sensitive_files")

    @property
    def branchListToBeNotifiedFor(self):
        return self.repo.get('notify_direct', {}).get('branch_list_to_be_notified')

    @property
    def actionToBeNotifiedFor(self):
        return self.repo.get('notify_direct', {}).get('action_to_be_notified_on', "opened")

    @property
    def superMembers(self):
        return self.repo.get('super_git_members')

    @property
    def mainBranch(self):
        main_branch = self.repo.get('main_branch')
        return [main_branch] if isinstance(main_branch, str) else main_branch

    @property
    def testBranch(self):
        return self.repo.get('test_branch')

    @property
    def devBranch(self):
        return self.repo.get('dev_branch')

    @property
    def shield_job(self):
        return self.repo.get('shields_check')

    @property
    def valid_contributors(self):
        return self.repo.get('valid_contributors')

    @property
    def debug_folks(self):
        return self.config.get('debug_alice', {}).get('debug_folks')

    @property
    def debug_channel(self):
        return self.config.get('debug_alice', {}).get('debug_channel')

    @property
    def alertChannelName(self):
        if self.is_debug:
            return self.debug_channel
        alert_channel = self.config.get('alert_channel')
        if self.repo and self.repo.get('alert_channel'):  # override repo wise settings
            alert_channel = self.repo.get('alert_channel')
        return alert_channel

    @property
    def cc_tech_team(self):
        if self.is_debug:
            return self.debug_folks
        return self.repo.get('cc_members')

    @property
    def codeChannelName(self):
        if self.is_debug:
            return self.debug_channel
        return self.repo.get('code_channel')

    @property
    def personToBeNotified(self):
        if self.is_debug:
            return self.debug_folks
        return self.repo.get('notify_direct', {}).get('person_to_be_notified')

    @property
    def techLeadsToBeNotified(self):
        if self.is_debug:
            return self.debug_folks
        return self.repo.get('notify_direct', {}).get('tech_leads_to_be_notified_on_release_freeze')

    @property
    def productTeamToBeNotified(self):
        if self.is_debug:
            return self.debug_folks
        return self.repo.get('product_team')

    @property
    def productTeamGithub(self):
        return self.repo.get('product_team_github_names')

    @property
    def productPlusRequiredDirPattern(self):
        return self.repo.get('product_plus_required_dir_pattern')

    @property
    def devOpsTeamToBeNotified(self):
        if self.is_debug:
            return self.debug_folks
        return self.config.get("dev_ops_team", "")

    @property
    def devOpsTeamMembers(self):
        return self.config.get("dev_ops_team", "")

    @property
    def qaTeamMembers(self):
        return self.config.get("qa_team", "")

    @property
    def checks(self):
        return self.repo.get("checks", [])

    @property
    def release_notes_link(self):
        return self.config.get("release_notes_link")

    def getSlackName(self, github_name):
        return self.config.get('user_map', {}).get(github_name, github_name)

    @property
    def post_release_deployment(self):
        return self.config.get("post_release_deployment", "")

    @property
    def releaseFreezeDetailsPath(self):
        return self.config.get("release_freeze_details_path", "")

    @property
    def codeFreezeDetailsPath(self):
        return self.config.get("code_freeze_details_path", "")

    @property
    def releaseItemsFilePath(self):
        return self.config.get("release_items_file_path", "")

    @property
    def releaseItemsFileMergedBy(self):
        return self.config.get("release_items_file_mergedBy", "")

    @property
    def backupFilesPath(self):
        return self.config.get("backup_files_path", "")

    @property
    def timezone(self):
        return self.config.get("timezone", "")

    @property
    def inspector(self):
        return self.config.get("inspector", "")
