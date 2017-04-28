
class OneTimeUtils(object):
    """
    functions can be used once in lifetime to get some details
    """

    organisation = "moengage"

    @staticmethod
    def getGithubUsers():
        """
        get github users, there is pagination so need to decide how many pages you want to go
        :return:
        """
        GITHUB_USER_LIST = "https://api.github.com/orgs/{org}/members?page=".format(org=organisation)
        users = []
        for page in range(1, 4):
            users += json.loads(requests.get(GITHUB_USER_LIST.format("moengage")) + str(page), headers={"Authorization": "token " + GITHUB_TOKEN})
            u = {}
            for item in users:
                u[item["login"]] = item["login"]
        return u


    @staticmethod
    def getSlackUsers():
        """
        :return: slack users list
        """
        users = json.loads(requests.get(SLACK_USER_LIST + SLACK_TOKEN).content)
        u = {}
        for item in users["members"]:
            u[item["name"]] = item["name"]
        print json.dumps(u)