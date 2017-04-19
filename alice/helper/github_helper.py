import requests
import json
import time
from alice.helper.constants  import GITHUB_REVIEW_ACCEPT_KEY, EP_REVIEWS
from alice.helper.decorators.retry import Retry
from alice.helper.constants import GITHUB_MEMBERS

class PRFilesNotFoundException(Exception):
    def __init__(self, pr_response):
        self.pr_response = pr_response
        super(PRFilesNotFoundException, self).__init__(str(self.pr_response))


class GithubHelper:

    def __init__(self, org, github_token, pr_api_link):
        self.GITHUB_TOKEN = github_token
        self.pr_api_link = pr_api_link

        #response = requests.get("https://api.github.com/user?access_token="+self.GITHUB_TOKEN)
        response = requests.get(GITHUB_MEMBERS.format(org=org),
                                headers={"Authorization": "token "+ self.GITHUB_TOKEN}).content
        resp = json.loads(response)
        if isinstance(resp, dict) and "bad" in resp.get("message",""):
            raise Exception(response)
        elif isinstance(resp, list) and len(resp) <= 0:
            raise Exception("Please check the Github Token, user doesn't have permission to the organisation or the repository")


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

    def get_reviews(self):
        reviews = requests.get(self.pr_api_link + "/" + EP_REVIEWS, headers={
            "Authorization": "token " + self.GITHUB_TOKEN, "Accept": GITHUB_REVIEW_ACCEPT_KEY})
        print "********** REVIEW ********************"
        return reviews

    def get_files_requests(self):
        files = requests.get(self.pr_api_link + "/files", headers={"Authorization": "token " + self.GITHUB_TOKEN})
        return json.loads(files.content)

    def is_pr_file_content_available(self, response):
        return not (isinstance(response, dict) and 'message' in response and response['message'] == "Not Found")


    @Retry(PRFilesNotFoundException, max_retries=10,
           default_value={"message": "Not Found", "documentation_url": "https://developer.github.com/v3"})
    def get_files(self):
        #import pdb; pdb.set_trace()
        files_content = self.get_files_requests()
        if not self.is_pr_file_content_available(files_content):
            raise PRFilesNotFoundException(files_content)
        print "********** FILE CONTENT ********************"
        #print files_content
        return files_content


