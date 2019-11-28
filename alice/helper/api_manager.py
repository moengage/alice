import requests
import json
from alice.config.config_provider import ConfigProvider


class ApiManager(object):
    """
    Get function is used for making get calls
    Post function is used for making Post calls
    Check function is used for token rotation when we get rate limiting.
    Check function is called in get and post function for checking and rotating the token.
    """

    @staticmethod
    def get(url, headers, data=None):
        response = requests.get(url, headers=headers, data=data)
        response = ApiManager.check(response, url, headers, data, "get")
        return {"status_code": response.status_code, "content": response.content, "response": response}

    @staticmethod
    def post(url, headers, data=None):
        response = requests.post(url, headers=headers, data=data)
        response = ApiManager.check(response, url, headers, data, "post")
        return {"status_code": response.status_code, "content": response.content, "response": response}

    @staticmethod
    def check(response, url, headers, data, request_type):
        response_data = json.loads(response.content)
        if type(response_data) is dict and "message" in response_data and "documentation_url" in response_data:
            token = ConfigProvider().github_alternate_token
            headers["Authorization"] = "token %s"%token
            if request_type == "get":
                response = requests.get(url, headers=headers, data=data)
            else:
                response = requests.post(url, headers=headers, data=data)
            return response
        else:
            return response


