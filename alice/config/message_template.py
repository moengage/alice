MSG_BAD_START = "Very Bad @"
MSG_NO_TECH_REVIEW = "{name} :rage: {pr} is merged into `{branch}` without a \"Tech +1\", soon these kind of requests will" \
      " be automatically reverted CC: {team}"
MSG_NO_PRODUCT_REVIEW = "{name} :rage: {pr} is merged into `{branch}` without \"Product +1\", soon these kind of requests will" \
                " be automatically reverted CC: {team}"

MSG_CODE_CHANNEL = "Title=\"{title}\", Description=\"{desc}\" \nPR: {pr}\n from {head_branch} into `{base_branch}`" \
                   " By: *{pr_by}*, mergedBy: {merge_by}\n" #can remove not required data

MSG_RELEASE_PREPARATION = "\n Please review and approve with +1, Release preparation starts..."

general_comment = { "body": "Did you remember to?\n"
            "- [ ] Add Test Case(s) [how to check](https://github.com/moengage/MoEngage/wiki/jenkins#unit-tests)\n"
            "- [ ] P0 Tests Executed EndToEnd? [what is it](https://github.com/moengage/MoEngage/wiki/p0%20list)?\n"
}

special_comment = {
    "body": "**Attention!** \n Release Checklist\n"
            "- [ ] JS version Update? check index.html\n"
            "- [ ] No code/PR to be reverted? check release notes\n"
            "- [ ] Unit Tests Passed?\n"
            "- [ ] Api Tests passed?\n"
            "- [ ] QA report linked?\n"
            "- [ ] Release Notes linked?"
}