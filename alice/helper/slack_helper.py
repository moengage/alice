import json
import requests
from alice.config.message_template import *
from alice.helper.constants import SLACK_ICON
from slacker import Slacker
from alice.helper.log_utils import LOG
class SlackHelper(object):


    def __init__(self, config):
        self.config = config
        self.slack = Slacker(self.config.slackToken)
        self.icon = SLACK_ICON


    def postToSlack(self, channel, msg=None, *args, **kwargs):
        LOG.info("\n************** NOTIFYING ******************\n"
                    "**************  %s      *************\n"
                    "Message= %s\n"
                    "******************************************* " % (channel, msg))
        self.slack.chat.post_message(channel=channel, text=msg, icon_url=self.icon, username="Alice", *args, **kwargs)

    def directSlack(self, person, msg=None, *args, **kwargs):
        if self.config.is_debug:
            person = self.config.debug_folks
        LOG.info("\n************** NOTIFYING ******************\n"
                    "**************  %s      *************\n"
                    "Message= %s\n"
                    "******************************************* " % (person, msg))
        self.slack.chat.post_message(channel=person, text=msg, icon_url=self.icon, username="Alice", *args, **kwargs)


    def getBot(self, channel, user):
        icon_url = "https://cloud.githubusercontent.com/assets/12966925/25274594/528675da-26ae-11e7-8331-25f25c41b75d.png"
        return {"username": user, "icon_url": icon_url}