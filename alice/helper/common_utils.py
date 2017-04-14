from alice.helper.constants  import *
import simplejson as json
import requests
import pkg_resources

class CommonUtils(object):
    git_mappings = {  # keep this static by executing  getGithubUsers function once periodically as needed
        "p00j4": "pooja",
    }
    slack_mappings = {  # keep this static by executing getSlackUsers function once periodically as needed
        "pooja": "poojashah",
    }

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