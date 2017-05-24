from alice.helper.colors import Blinking_Colors

MSG_BAD_START = "Very Bad "
MSG_NO_TECH_REVIEW = "{name} :rage: <{pr}|{title}> is merged into `{branch}` without a \"Tech +1\"," \
                     " soon these kind of requests will be automatically reverted CC: {team}"
MSG_NO_PRODUCT_REVIEW = "{name} :rage: <{pr}|{title}>  is merged into `{branch}` without \"Product +1\"," \
                        " soon these kind of requests will be automatically reverted CC: {team}"

MSG_CODE_CHANNEL = "Title=\"{title}\", Description=\"{desc}\" \nPR: {pr}\n from {head_branch} into `{base_branch}`" \
                   " By: *{pr_by}*, mergedBy: {merge_by}\n"

MSG_RELEASE_PREPARATION = "\n Please review and approve with +1, Release preparation starts..."

MSG_GUIDELINE_ON_MERGE = "Hi @{person} you have merged <{pr}|{title}> into {base_branch}\n now, be nice & mention it " \
                         "in <{release_notes_link}|Release Notes> for getting it `QAed and released` " \
                         "under Sheet name as respective Date"

MSG_AUTO_CLOSE = "alice have auto-closed it because she sensed it an accidental PR (only \"{tested_branch}\" " \
                 "can be merged to \"{main_branch}\") \n Alice is smart! Be like Alice!"

GENERAL_COMMENT = {"body": "Did you remember to?\n"
                           "- [ ] Add Test Case(s)"
                           "- [ ] P0 Tests Executed EndToEnd?"
                   }

MSG_OPENED_TO_MAIN_BRANCH = "{repo} repo:: <{pr}|{title}> is {action} to `{main_branch}` by:*{pr_by}* " \
                            "\n Please review as Release preparation starts now ..."
MSG_OPENED_TO_PREVENTED_BRANCH = "{repo} repo:: <{pr}|{title}> is {action} to `{base_branch}` by:*{pr_by}* "

MSG_QA_SIGN_OFF = "<@{person}>  QA passed :+1: {main_branch} is updated <{pr}|Details here> Awaiting your go ahead." \
                  " \n cc: {dev_ops_team} {tech_team} "
MSG_SENSITIVE_FILE_TOUCHED = "{notify_folks} {file}  is modified in <{pr}|{pr_number}> by @{pr_by}"

SPECIAL_COMMENT = {
    "body": "**Attention!** \n Release Checklist\n"
            "- [ ] JS version Update? check index.html\n"
            "- [ ] No code/PR to be reverted? check release notes\n"
            "- [ ] Unit Tests Passed?\n"
            "- [ ] Api Tests passed?\n"
            "- [ ] QA report linked?\n"
            "- [ ] Release Notes linked?"
}

DOC_CHECK_NOT_FOUND = "\"{check_name}\" Check is not found (please cross check the checks defined in config file). \n" \
                      "If you wish to implement this new check yourself, please read here: " + Blinking_Colors.OKBLUE + \
                      "{doc_link}" + Blinking_Colors.END
ISSUE_FOUND = "\nOo this looks like i've messed up, Please raise this as issue at: " + Blinking_Colors.OKBLUE \
              + "{issue_link}" + Blinking_Colors.END + " will try to help you asap"

CODE_FREEZE_TEXT = [{
                "pretext": "<!channel>: Code is Frozen ({dev_branch}->{test_branch}) for Release testing\n "
                           "Release Items for this week :bow:",
                "fields": [
                    {
                        "title": "Use {test_branch} branch",
                        "value": "to give fixes, branch out from it",
                        "short": True
                    },
                    {
                        "title": "to check if your code is part of",
                        "value": "verify <{pr}|PR link>",
                        "short": True
                    }
                ],
                "title": "MoEngage Release Notes Link :battery: \n\n",
                "title_link": "{release_notes_link}",
                "text": "{msg}",
                "color": "#764FA5"
            }]

RELEASE_NOTES_REMINDER = "|Final Reminder| :raising_hand: \n Hi {msg}\n There are changes on your name as mentioned *above*. " \
                         "Please do mention them in release notes & inform immediately if it needs QA " \
                         "*else will be treated as self tested* (ignore, only if done already):\n {release_notes_link} " \
                         " \t\tcc: {qa_team}"

DATA_SAVE_MERGED = ":beer: Title=\"{title}\",  Description=\"{desc}\" \nPR: {pr} By: @{by}"
