import requests
import json
import time
from alice.helper.constants  import GITHUB_REVIEW_ACCEPT_KEY, EP_REVIEWS
from alice.helper.decorators.retry import Retry


class PRFilesNotFoundException(Exception):
    def __init__(self, pr_response):
        self.pr_response = pr_response
        super(PRFilesNotFoundException, self).__init__(str(self.pr_response))


class GithubHelper:

    def __init__(self, github_token):
        self.GITHUB_TOKEN = github_token
        response = requests.get("https://api.github.com/user?access_token="+self.GITHUB_TOKEN)
        resp = response.content
        if "bad" in json.loads(resp.lower()).get("message",""):
            raise Exception(resp)

    def comment_pr(self, comment_section, comment):
        resp = requests.post(comment_section, headers={"Authorization": "token " + self.GITHUB_TOKEN},
                             data=json.dumps(comment))
        print resp.content

    def modify_pr(self, msg, state):
        data = {
            "title": msg,
            "state": state
        }
        resp = requests.post(pr_api_link, json.dumps(data), headers={"Authorization": "token " + self.GITHUB_TOKEN})
        print resp.content

    def get_reviews(self, pr_link):
        reviews = requests.get(pr_link + "/" + EP_REVIEWS, headers={
            "Authorization": "token " + self.GITHUB_TOKEN, "Accept": GITHUB_REVIEW_ACCEPT_KEY})
        print "********** REVIEW ********************"
        return reviews

    def get_files_requests(self, gitlink_pr):
        files = requests.get(gitlink_pr + "/files", headers={"Authorization": "token " + self.GITHUB_TOKEN})
        return json.loads(files.content)

    def is_pr_file_content_available(self, response):
        return not (isinstance(response, dict) and 'message' in response and response['message'] == "Not Found")

    @Retry(PRFilesNotFoundException, max_retries=40,
           default_value={"message": "Not Found", "documentation_url": "https://developer.github.com/v3"})
    def get_files(self, gitlink_pr):
        files_content = self.get_files_requests(gitlink_pr)
        if not self.is_pr_file_content_available(files_content):
            raise PRFilesNotFoundException(files_content)
        print "********** FILE CONTENT ********************"
        #print files_content
        return files_content


