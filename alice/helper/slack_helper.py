import json
import requests
from alice.helper.message_template import *
from slacker import Slacker

class SlackHelper(object):
    def __init__(self):
        self.slack = Slacker(SLACK_API_TOKEN)
        self.icon = SLACK_ICON

    def postToSlack(self, channel, msg=None, **kwargs):
        self.slack.chat.post_message(channel=channel, text="#"+msg, icon_url=self.icon, username="alice", **kwargs)
