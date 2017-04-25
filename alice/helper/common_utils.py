from alice.helper.constants  import *
import simplejson as json
import requests
import pkg_resources

from alice.helper.api_manager import ApiManager
API_GITHUB_ORG_MEMBER = "https://api.github.com/orgs/moengage/members?page="
API_GITHUB_USER = "https://api.github.com/users/"
API_SLACK_MEMEBRS ="https://slack.com/api/users.list?token="

git_mappings = {}
slack_mappings = {}

class CommonUtils(object):
    @staticmethod
    def getGithubUsers():
        if git_mappings:
            return git_mappings
        users = []
        page = 1
        while True:
            member_api = "%s%s" % (API_GITHUB_ORG_MEMBER, page)
            response = ApiManager.get(member_api, headers={"Authorization": "token " + GIT_TOKEN})
            if not response:
                break
            users += json.loads(response["content"])
            page += 1

        for item in users:
            user_name = item["login"]
            ApiManager.get(API_GITHUB_USER+"/"+user_name)
            git_mappings[item["login"]] = item["login"]
        return git_mappings

    @staticmethod
    def getSlackUsers():
        if slack_mappings:
            return slack_mappings
        response = ApiManager.get(API_SLACK_MEMEBRS + SLACK_TOKEN, headers={})
        users = json.loads(response["content"])

        for item in users["members"]:
            slack_mappings[item["name"]] = item["profile"].get("email","bot@gmail.com")
        print slack_mappings

    @staticmethod
    def getSlackNicksFromGitNicks(key):
        if key in CommonUtils.git_mappings:
            return CommonUtils.git_mappings[key]
        return key

    @staticmethod
    def readResourceJson(module, path):
        json_string = CommonUtils.readResourceString(module, path)
        return json.loads(json_string)

    @staticmethod
    def readResourceString(module, path):
        return pkg_resources.resource_string(module, path)

    @staticmethod
    def getDictFromJson(json_path):
        return json.load(open(json_path))
