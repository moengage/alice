
import simplejson as json
import pkg_resources
import os
from alice.helper.api_manager import ApiManager
from alice.helper.constants import API_GITHUB_MEMBERS_LIST, API_GITHUB_USERS, SLACK_USER_LIST
from alice.helper.file_utils import get_dict_from_config_file
git_mappings = {}
slack_mappings = {}


class CommonUtils(object):
    config_file = os.environ["config"]
    config = get_dict_from_config_file(config_file)

    GIT_TOKEN = config.get('tokens').get("github")
    SLACK_TOKEN = config.get('tokens').get("slack")
    organisation = config.get('organisation')

    @staticmethod
    def getGithubUsers():
        if git_mappings:
            return git_mappings
        users = []
        page = 1
        while True:
            member_api = "%s%s" % (API_GITHUB_MEMBERS_LIST.format(org=CommonUtils.organisation), page)
            response = ApiManager.get(member_api, headers={"Authorization": "token " + CommonUtils.GIT_TOKEN})
            if not response:
                break
            users += json.loads(response["content"])
            page += 1

        for item in users:
            user_name = item["login"]
            ApiManager.get(API_GITHUB_USERS + "/" + user_name)
            git_mappings[item["login"]] = item["login"]
        return git_mappings

    @staticmethod
    def getSlackUsers():
        if slack_mappings:
            return slack_mappings
        response = ApiManager.get(SLACK_USER_LIST + CommonUtils.SLACK_TOKEN, headers={})
        users = json.loads(response["content"])

        for item in users["members"]:
            slack_mappings[item["name"]] = item["profile"].get("email","bot@gmail.com")
        print slack_mappings

    @staticmethod
    def getSlackNicksFromGitNicks(key):
        if key in git_mappings:
            return git_mappings[key]
        return key

    @staticmethod
    def readResourceJson(module, path):
        json_string = CommonUtils.readResourceString(module, path)
        return json.loads(json_string)

    @staticmethod
    def readResourceString(module, path):
        return pkg_resources.resource_string(module, path)


