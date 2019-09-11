
import simplejson as json
import pkg_resources
import os
import json
from alice.helper.api_manager import ApiManager
from alice.helper.constants import API_GITHUB_MEMBERS_LIST, API_GITHUB_USERS, SLACK_USER_LIST
from alice.helper.file_utils import get_dict_from_config_file
from alice.helper.constants import git_mappings
slack_mappings = {}


class CommonUtils(object):
    config_file = os.environ["config"]
    config = get_dict_from_config_file(config_file)

    GIT_TOKEN = config.get('tokens').get("github")
    SLACK_TOKEN = config.get('tokens').get("slack")
    organisation = config.get('organisation')
    constants = ConfigProvider().constants

    @staticmethod
    def get_github_users():
        git_mappings = json.loads(CommonUtils.constants.get('git_mappings'))
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
    def get_slack_users():
        if slack_mappings:
            return slack_mappings
        response = ApiManager.get(SLACK_USER_LIST + CommonUtils.SLACK_TOKEN, headers={})
        users = json.loads(response["content"])

        for item in users["members"]:
            slack_mappings[item["name"]] = item["profile"].get("email","bot@gmail.com")
        print(slack_mappings)

    @staticmethod
    def get_slack_nicks_from_git_name_nicks(key):
        name_mapping = json.loads(CommonUtils.constants.get('git_mappings_with_slack_name'))
        if key in name_mapping:
            return name_mapping[key]
        return key

    @staticmethod
    def get_slack_nicks_from_git(key):
        git_mappings = json.loads(CommonUtils.constants.get('git_mappings'))
        if key in git_mappings:
            return git_mappings[key]
        return key

    @staticmethod
    def read_resource_json(module, path):
        json_string = CommonUtils.read_resource_string(module, path)
        return json.loads(json_string)

    @staticmethod
    def read_resource_string(module, path):
        return pkg_resources.resource_string(module, path)

    @staticmethod
    def get_bot(channel, user):
        if channel=="#support":
            return {"username": user, "icon_url":"http://www.dshservices.com/CSP.jpg"}
        elif channel == "#bugs" :
            return {"username": user, "icon_url":"https://thesnarkyblonde.files.wordpress.com/2015/06/scared-bug.jpg"} #"username": "Bug"
        else:
            return {"username": user, "icon_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTPUZ-_hA1URdXhUssFYYguQJNo2nbqgIflGTQby0HRYshzB82t4w"}
                # "https://encrypted-tbn1.gstatic.com/images?q=tbn:ANd9GcRou8PqU98565BjRsp4AN7o62cxjGi3172ejTSI88ntik3VXrfW"}
                # "https://encrypted-tbn1.gstatic.com/images?q=tbn:ANd9GcSP3AjyC5tfdRhEkscR5BkC9bAkxALjFi3i0sqjfM9HoqYDd1bfdg"}
                # "https://encrypted-tbn2.gstatic.com/images?q=tbn:ANd9GcQRZS74Kz3vZ8eoPIxkBpbufcEUiM0byiRSx85doEJ9bXZjTtQDyA"}
                # "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQFPqaeo99hxPn48XHkc5fRVQzvKvExO20NmdceY0uCUeVeULip"}
                # "http://www.cutestpaw.com/wp-content/uploads/2011/11/My-Best-Friend.jpg"}
                # "https://s-media-cache-ak0.pinimg.com/236x/d3/e9/fc/d3e9fc222c9bd0d12e0ff126acf7df00.jpg"}
                # "https://encrypted-tbn2.gstatic.com/images?q=tbn:ANd9GcTQMP3_ng13f2qtljxGA5U_1SvxLd0Z_y6u-AHlrWcwyXeHYzzV"}
