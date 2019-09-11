from alice.helper.constants import SLACK_ICON
from slacker import Slacker
from alice.helper.log_utils import LOG
from alice.helper.api_manager import ApiManager

import json


class SlackHelper(object):
    def __init__(self, config):
        self.config = config
        self.slack = Slacker(self.config.slackToken)
        self.icon = SLACK_ICON

    def postToSlack(self, channel, msg=None, data=None, parseFull=None, as_user=True, *args, **kwargs):
        LOG.info("\n************** NOTIFYING ******************\n"
                    "**************  %s      *************\n"
                    "Message= %s\n"
                    "******************************************* " % (channel, msg))
        try:
            self.slack.chat.post_message(channel=channel, text=msg, icon_url=self.icon, as_user=as_user, *args, **kwargs)
        except Exception as ex:
            LOG.error("Error while posting alert to slack, please check if: \n1. The provided slack/hubot token for alice is correct " \
                  "and it has access to the channel=%s" \
                  "\n2.The channel name is correct\n" %(channel))
            raise ex

    def directSlack(self, person, msg=None, as_user=False, *args, **kwargs):
        if self.config.is_debug:
            person = self.config.debug_folks
        LOG.info("\n************** NOTIFYING ******************\n"
                    "**************  %s      *************\n"
                    "Message= %s\n"
                    "******************************************* " % (person, msg))
        self.slack.chat.post_message(channel=person, text=msg, icon_url=self.icon, username="alice", as_user=as_user, *args, **kwargs)

    def getBot(self, channel, user):
        icon_url = "https://cloud.githubusercontent.com/assets/12966925/25274594/528675da-26ae-11e7-8331-25f25c41b75d.png"
        return {"username": user, "icon_url": icon_url}

    def postFinalWarningToSlack(self, channel, msg, data, parseFull=True):
        release_notes = "<https://docs.google.com/a/moengage.com/spreadsheets/d/1eW3y-GxGzu8Jde8z4EYC6fRh1Ve4TpbW5qv2-iWs1ks/edit?usp=sharing|Release Notes>"
        data["channel"] = channel
        data["link_names"] = True
        data[
            "text"] = "|Final Reminder| :raising_hand: \n Hi " + msg + "\n There are changes on your name as mentioned *above*. Please do mention them in release notes & inform immediately if it" \
                                                                       " needs QA *else will be treated as self tested* (ignore, only if done already):\n" + release_notes + " \t\tcc: <@U7Z8GH7MK> <@geetima> <@vandana> <@U8DSU7L00> <@U8DSJFENL> <@UBLNGFELC>"
        response = ApiManager.post(url = channel, headers={"content-type": "text/javascript"}, data=json.dumps(data))
        return response["content"]

    def postAttachmentToSlack(self, channel, pr_link, msg, data,parseFull=True):
        data["channel"] = channel
        data["link_names"] = True
        if (parseFull):
            data[
                "parse"] = "full"  # for solving issue for notifying slack names with '.' https://api.slack.com/docs/formatting

        final_json = {"attachments": [
            {
                "pretext": "<!channel>: Code is Frozen (dev->qa) for Release testing\n Release Items for this week :bow:",
                "fields": [
                    {
                        "title": "Use qa branch",
                        "value": "to give fixes, branch out from it",
                        "short": True
                    },
                    {
                        "title": "to check if your code is part of",
                        "value": "verify <" + pr_link + "|PR link>",
                        "short": True
                    }
                ],
                "title": "MoEngage Release Notes Link :battery: \n\n",
                "title_link": "https://docs.google.com/a/moengage.com/spreadsheets/d/1eW3y-GxGzu8Jde8z4EYC6fRh1Ve4TpbW5qv2-iWs1ks/edit?usp=sharing",
                "text": msg,
                "color": "#764FA5"
            }
        ]
        }
        final_json.update(data)
        response = ApiManager.post(url= channel, data=json.dumps(final_json), headers={"content-type": "text/javascript"})
        return response["content"]