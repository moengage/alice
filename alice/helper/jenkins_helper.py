import requests
import json
from alice.helper.api_manager import ApiManager


class JenkinsHelper(object):
    def __init__(self, pr):
        self.pr = pr

    def changeStatus(self, status_url_link, status, context, description, details_link="", data = {"username": "Alice", "icon_url": "http://at-cdn-s01.audiotool.com/2012/06/11/documents/KmtKAOyrXXhbLljeworCHj6r3Au2j/0/cover256x256-6bcce4f28f0b451e95d61ccb25420634.jpg", }, parseFull=True):
        payload = {
            "description": description,
            "state": status,
            "target_url": details_link,
            "context": context
        }
        response = ApiManager.post(status_url_link, {"Authorization": "token "}, json.dumps(payload))
        print "*** modified status to "+status
        print response["response"].content
        return response["response"].content

    def after_merge(self, job_dir, repo, pr_no, title_pr, pr_by_slack_uid, merged_by_slack_uid, base_branch, head_branch):
        """ Cases
                    head    base
                    dev     qa                      staging build
                    qa      master                  prod  build
                    patch   master                  prod  build
                    feature qa                      staging
                    feature master                  nothing
                    feature dev                     nothing
                    f1           f2                 nothing
        """
        release_type = ""
        dashboard_job_name = ""

        if self.pr.base_branch == "qa":
            release_type = "minor"
            dashboard_job_name = job_dir + "dashboard_builder_staging"
        elif self.pr.base_branch == "master" and self.pr.head_branch.startswith("patch"):
            release_type = "patch"
            dashboard_job_name = job_dir + "dashboard_builder_prod"
        elif self.pr.base_branch == "master" and self.pr.head_branch == "qa":
            release_type = "major"
            dashboard_job_name = job_dir + "dashboard_builder_prod"
        else:
            msg = "******  NOT TO BUILD CASE base_branch=%s head_branch=%s" % (self.pr.base_branch, self.pr.head_branch)
            print(msg)
            return {"msg": msg}

        bump_version_job_dict = dict(release_type=release_type, repo=repo, pr_no=pr_no, pr_title=title_pr,
                                     pr_by_slack=pr_by_slack_uid, approved_by=merged_by_slack_uid,
                                     merged_by_slack=merged_by_slack_uid, sha=self.pr.base_sha, base_branch=base_branch,
                                     head_branch=head_branch, is_ui_change=True)
        # self.actor.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=dashboard_job_name,
        #                            pr_link=pr_link, params_dict=bump_version_job_dict, pr_by_slack=pr_by_slack_uid)
        msg = "dashboard builder started"

        return {"msg": msg}