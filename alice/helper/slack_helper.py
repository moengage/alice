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


# WEBHOOK_ROUTE="https://hooks.slack.com/services/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" #yash's incoming webhook
# def postToSlack(channel,msg, data = {"username": "alice", "icon_url": "http://at-cdn-s01.audiotool.com/2012/06/11/documents/KmtKAOyrXXhbLljeworCHj6r3Au2j/0/cover256x256-6bcce4f28f0b451e95d61ccb25420634.jpg",},parseFull=True):
#     data["channel"] = channel
#     data["text"] = msg
#     if(parseFull):
#         data["parse"] = "full"
#         data["link_names"] = 1
#
#     r = requests.post(WEBHOOK_ROUTE, data=json.dumps(data), headers={"content-type": "text/javascript"})
#     return r.content
#
# def postAttachmentToSlack(channel,pr_link,msg, data = {"username": "alice", "icon_url": "http://at-cdn-s01.audiotool.com/2012/06/11/documents/KmtKAOyrXXhbLljeworCHj6r3Au2j/0/cover256x256-6bcce4f28f0b451e95d61ccb25420634.jpg",},parseFull=True):
#     data["channel"] = channel
#     if(parseFull):
#         data["parse"] = "full" #for solving issue for notifying slack names with '.' https://api.slack.com/docs/formatting
#
#     final_json = {"attachments": [
#         {
#             "pretext": "<!channel>: Code is Frozen (dev->qa) for Release testing\n Release Items for this week :bow:",
#             "fields": [
#                 {
#                     "title": "Use qa branch",
#                     "value": "to give fixes, branch out from it",
#                     "short": True
#                 },
#                 {
#                     "title": "to check if your code is part of",
#                     "value": "verify <"+pr_link+"|PR link>",
#                     "short": True
#                 }
#             ],
#             "title": "MoEngage Release Notes Link :battery: \n\n",
#             "title_link": "https://docs.google.com/a/moengage.com/spreadsheets/d/1eW3y-GxGzu8Jde8z4EYC6fRh1Ve4TpbW5qv2-iWs1ks/edit?usp=sharing",
#             "text": msg,
#             "color": "#764FA5"
#         }
#     ]
#     }
#     final_json.update(data)
#
#     r = requests.post(WEBHOOK_ROUTE, data=json.dumps(final_json), headers={"content-type": "text/javascript"})
#     return r.content
#
#
# def postFinalWarningToSlack(channel,msg, data = {"username": "alice", "icon_url": "http://at-cdn-s01.audiotool.com/2012/06/11/documents/KmtKAOyrXXhbLljeworCHj6r3Au2j/0/cover256x256-6bcce4f28f0b451e95d61ccb25420634.jpg",},parseFull=True):
#     # pass
#     release_notes = "<https://docs.google.com/a/moengage.com/spreadsheets/d/1eW3y-GxGzu8Jde8z4EYC6fRh1Ve4TpbW5qv2-iWs1ks/edit?usp=sharing|Release Notes>"
#     data["channel"] = channel
#     data["text"] = "|Final Reminder| :raising_hand: \n Hi "+msg + "\n There are changes on your name as mentioned *above*. Please do mention them in release notes & inform immediately if it needs QA *else will be treated as self tested* (ignore, only if done already):\n" + release_notes +" \t\tcc: <@geetima>, <@vandana>, <@sneh>"
#     r = requests.post(WEBHOOK_ROUTE, data=json.dumps(data), headers={"content-type": "text/javascript"})
#     return r.content

