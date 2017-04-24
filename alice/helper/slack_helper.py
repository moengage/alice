import json
import requests
from alice.config.message_template import *
from alice.helper.constants import SLACK_ICON
from slacker import Slacker

class SlackHelper(object):

    def __init__(self, SLACK_API_TOKEN):
        self.slack = Slacker(SLACK_API_TOKEN)
        self.icon = SLACK_ICON

    def postToSlack(self, channel, msg=None, *args, **kwargs):
        print "************** NOTIFYING *******************"
        print "**************    %s      ******************" %channel
        print "********************************************"
        self.slack.chat.post_message(channel=channel, text=msg, icon_url=self.icon, username="Alice", *args, **kwargs)


    def getBot(self, channel, user):
        icon_url = "https://cloud.githubusercontent.com/assets/12966925/25274594/528675da-26ae-11e7-8331-25f25c41b75d.png"
        return {"username": user, "icon_url": icon_url}