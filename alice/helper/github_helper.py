import json
import requests
from alice.helper.api_manager import ApiManager
from alice.helper.constants  import API_GITHUB_REVIEW_ACCEPT_KEY, EP_REVIEWS, API_GITHUB_REPO_MEMBER, API_GITHUB_ISSUES, \
    EP_COMMENTS
from alice.helper.decorators.retry import Retry
from alice.helper.log_utils import LOG


class PRFilesNotFoundException(Exception):
    def __init__(self, pr_response):
        self.pr_response = pr_response
        super(PRFilesNotFoundException, self).__init__(str(self.pr_response))


class PRContentNotFoundException(Exception):
    def __init__(self, pr_response):
        self.pr_response = pr_response
        super(PRContentNotFoundException, self).__init__(str(self.pr_response))


class GithubHelper(object):

    def __init__(self, pr):
        self.GITHUB_TOKEN = pr.config.githubToken
        self.pr_api_link =  pr.link
        self.headers = {"Authorization": "token " + self.GITHUB_TOKEN}
        self.pr = pr

        url = API_GITHUB_REPO_MEMBER.format(org=self.pr.config.organisation, repo=self.pr.repo)
        response = ApiManager.get(url=url, headers=self.headers)
        if response["status_code"] != 200:
            raise Exception(response["content"], "Please check the provided Github Token, "
                                                 "either user doesn't have permission to"
                                                 " the organisation or the repository")

    def comment_pr(self, comment_section, comment):
        resp = requests.post(comment_section, headers=self.headers,
                             data=json.dumps(comment))
        LOG.debug(resp.content)

    def modify_pr(self, msg, state):
        data = {
            "title": msg,
            "state": state
        }
        resp = requests.post(self.pr_api_link, json.dumps(data), headers=self.headers)
        LOG.debug(resp.content)

    def get_reviews(self):
        url = self.pr_api_link + "/" + EP_REVIEWS
        self.headers["Accept"] = API_GITHUB_REVIEW_ACCEPT_KEY
        return requests.get(url, headers=self.headers)

    def get_files_requests(self):
        url = self.pr_api_link + "/files"
        files = ApiManager.get(url, headers=self.headers)
        return files["response"].json()

    def is_pr_file_content_available(self, response):
        return not (isinstance(response, dict) and 'message' in response and response['message'] == "Not Found")

    @Retry(PRFilesNotFoundException, max_retries=20)
    def get_files(self):
        files_content = self.get_files_requests()
        if not self.is_pr_file_content_available(files_content):
            raise PRFilesNotFoundException(files_content)
        return files_content

    @Retry(PRContentNotFoundException, max_retries=3)
    def get_comments(self):
        comments_end_point = API_GITHUB_ISSUES.format(org=self.pr.config.organisation, repo=self.pr.repo) \
                             + "/" + str(self.pr.number) + "/" + EP_COMMENTS
        return ApiManager.get(comments_end_point, self.headers)

