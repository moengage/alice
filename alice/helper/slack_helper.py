import json
import requests
from alice.config.message_template import *
from alice.helper.constants import SLACK_ICON
from slacker import Slacker

class SlackHelper(object):

    def __init__(self, SLACK_API_TOKEN):
        self.slack = Slacker(SLACK_API_TOKEN)
        self.icon = SLACK_ICON

    def postToSlack(self, channel, msg=None, **kwargs):
        self.slack.chat.post_message(channel=channel, text="#"+msg, icon_url=self.icon, username="alice", **kwargs)
