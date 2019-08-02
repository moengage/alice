from alice.main.checks import Checks
import requests
import json

class PRFilesNotFoundException(Exception):
    def __init__(self, pr_response):
        self.pr_response = pr_response
        super(PRFilesNotFoundException, self).__init__(str(self.pr_response))


class PRFilesNotFoundException(Exception):
    def __init__(self, pr_response):
        self.pr_response = pr_response
        super(PRFilesNotFoundException, self).__init__(str(self.pr_response))


class CheckImpl(Checks):

    def __init__(self, push_payload_parser):
        super(CheckImpl, self).__init__(push_payload_parser)
        self.pr = push_payload_parser
        self.merge_code()

    # def get_diff_files(self, repo):
    #     #Implement old function only
    #     from subprocess import Popen, PIPE, STDOUT
    #     import subprocess
    #     import os
    #     """
    #     First, It fetches commits of a repo, then we compare
    #     top two commit of a repo and we get the file difference.
    #     :param repo:
    #     :return:
    #     """
    #     # command = 'git log -2'
    #     # run_cmd = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    #     # commit_data = run_cmd.stdout.read()
    #     # commits = []
    #     # for line in commit_data.split('\n'):
    #     #     first_six = line[:6]
    #     #     if first_six == 'commit':
    #     #         commits.append(line.split(' ')[1])
    #     # first_commit = str(commits[0])
    #     # second_commit = str(commits[1])
    #     first_commit = str(self.pr.base_sha)
    #     second_commit = str(self.pr.head_sha)
    #     command = 'git diff %s'%second_commit + '...%s'%first_commit
    #     p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE)
    #     diff_data = p.stdout.read()
    #     file_edited = []
    #     for line in diff_data.split('\n'):
    #         first_three = line[:3]
    #         if first_three == "+++":
    #             file_name = line.split('+++')[1].split('/')[1:]
    #             file_path = "/".join(file_name)
    #             file_edited.append(file_path)
    #     print(file_edited)
    #     return file_edited

    def trigger_task_on_pr(self):
        from alice.helper.common_utils import CommonUtils
        from alice.helper.constants import *

        repo = self.pr.repo
        merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(self.pr.merged_by)
        merged_by_slack_name = CommonUtils.getSlackNicksFromGitNicks(self.pr.merged_by)
        pr_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(self.pr.opened_by)
        pr_by_slack_name = CommonUtils.getSlackNicksFromGitNicks(self.pr.opened_by)

        """
        First we check whether pr is open, then we run our task
        """
        if self.pr.action in action_commit_to_investigate :

             #1) First task Done
             self.close_dangerous_pr()

            """
            2) Begining of shield - Second task
            Shield runs for three repos -  Moengage, Dashboard_ui, Inap_rest_service
            Basic working of shield - It first update status to pending , then get file content,
            if file content found, then move forward, else return and skip testing.

            Dashboard_ui has two context - react and angular
            moengage has two context - syntax and unit_test
            Inapp_rest_service has moengage + integration context.

            """

            # 2.1) Run for dashboard_ui
            if repo in ui_repo and self.pr.is_sensitive_branch:

                is_change_angular = False
                is_change_react = False
                print ":INFO: repo=%s" % repo
                msg = "base={0} head={1}, action={2} Do nothing".format(self.pr.base_branch, self.pr.head_branch, self.pr.action)
                job_dir = "Dashboard/"
                self.actor.jenkins.changeStatus(self.pr.statuses_url, "pending", context=context_react,
                             description="Hold on!",
                             details_link="")

                try:
                    files_contents, message = self.get_files_task(self.pr.link + "/files")
                except PRFilesNotFoundException, e:
                    files_contents = e.pr_response

                if not files_contents or "message" in files_contents:
                    print ":DEBUG: no files found in the diff: SKIP shield, just update the status"
                    self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context=context,
                                 description="SKIP: No diff, check the Files count",
                                 details_link="")
                    self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context=context_react,
                                 description="SKIP: No diff, check the Files count", details_link="")
                    return files_contents  # STOP as files not found

                # If file contents are found, check which content we have to run.
                for item in files_contents:
                    file_path = item["filename"]
                    if file_path.startswith("static/app_react"):
                        is_change_react = True
                    if file_path.startswith("static/app"):
                        is_change_angular = True

                if is_change_angular:
                    self.actor.run_for_angular(context_angular, job_dir, repo, pr_by_slack_name,
                                               is_change_angular, jenkins_instance, token, pr_by_slack_uid)

                """ hit react job"""  # Hit always even config changes can be possible
                self.actor.run_for_react(job_dir, repo, pr_by_slack_name, jenkins_instance, token,pr_by_slack_uid)
                msg = "ui repo checks started"
                return {"msg": msg}

            elif repo in python_repo:
                """
                2.2) for moengage repo and inap_rest_service
                We have several cases,
                First case is for particular branches, we skip alice,
                Second case is we bypass shield testing for back merge(from master to dev and all..)
                Third case is when we run shield for moengage and python branch
                """
                if "feature/melora" in self.pr.base_branch or "feature/melora" in self.pr.head_branch:  # by pass for alice dev/test

                    print ":SKIP: alice code changes on melora branch"
                    return ":SKIP: alice code changes on " + repo

                elif repo.lower() == 'moengage' and (
                        (self.pr.base_branch == "qa" and self.pr.head_branch in ["master", "master_py2"]) or
                        (self.pr.base_branch == "dev" and self.pr.head_branch == "qa")):

                    print ":SKIP: back merge: checks call, repo={repo} pr={link_pr} title={title_pr}" \
                        .format(repo=repo, link_pr=self.pr.link_pr, title_pr=self.pr.title)
                    self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context=context,
                                                    description="checks bypassed for back merge",
                                                    details_link="")
                    self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context="shield-unit-test-python",
                                                    description="checks bypassed for back merge",
                                                    details_link="")
                    self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context="shield-linter-react",
                                                    description="checks bypassed for back merge",
                                                    details_link="")

                else:
                    print ":INFO: repo=%s to validate, for PR=%s" % (repo, self.pr.number)
                    if self.pr.base_branch in sensitive_branches_repo_wise.get(repo.lower(), sensitive_branches_default):

                        print "******* PR " + self.pr.action + "ed to " + self.pr.base_branch + ", Triggering tests ************"

                        pr_link = self.pr.link_pretty
                        head_repo = self.pr.ssh_url
                        path = ""
                        files_ops = False

                        self.actor.jenkins.changeStatus(self.pr.statuses_url, "pending", context=context,
                                                        description=context_description,
                                                        details_link="")  # status to go in pending quick
                        self.actor.jenkins.changeStatus(self.pr.statuses_url, "pending",
                                                        context="shield-unit-test-python", description="Hold on!",
                                                        details_link="")
                        try:
                            print ":DEBUG: check_file_path", self.pr.link + "/files"
                            files_contents, message = self.get_files_task(self.pr.link + "/files")
                        except PRFilesNotFoundException, e:
                            files_contents = e.pr_response
                        if not files_contents or "message" in files_contents:
                            print ":DEBUG: no files found in the diff: SKIP shield, just update the status"
                            self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context=context,
                                                            description="SKIP: No diff, check the Files count",
                                                            details_link="")
                            self.actor.jenkins.changeStatus(self.pr.statuses_url, "success",
                                                            context="shield-unit-test-python",
                                                            description="SKIP: No diff, check the Files count",
                                                            details_link="")
                            return files_contents  # STOP as files not found

                        # print "files_contents after found", files_contents
                        for item in files_contents:
                            file_path = item["filename"]
                            if str(file_path).endswith(".py") and item["status"] != "removed":
                                path += " " + file_path

                            elif str(file_path).endswith((".conf", ".cfg", ".init", ".sh")):
                                files_ops = True

                            # elif str(file_path).endswith((".html", ".css", ".js", ".tpl", ".less", ".scss", ".json")):
                            #     files_frontend = True
                            # else:
                            #     files_backend = True

                        if repo.lower() == 'moengage' and files_ops and self.pr.action \
                                in action_commit_to_investigate:

                            self.set_labels(repo, self.pr.number,
                                                    ["DevOps_Review "])

                        else:  # all dependencies moved to separate virtual env
                            job_dir = "package_shield/"
                            job_name = job_dir + "shield" + "_" + repo
                            head_repo_owner = self.pr.head_label.split(":")[0]  # FORK cases
                            params_dict = dict(GIT_REPO=head_repo, GIT_HEAD_BRANCH=self.pr.head_branch,
                                               GIT_BASE_BRANCH=self.pr.base_branch,
                                               GIT_HEAD_BRANCH_OWNER=head_repo_owner, GIT_PULL_REQUEST_LINK=pr_link,
                                               GIT_SHA=self.pr.head_sha, AUTHOR_SLACK_NAME=pr_by_slack_name,
                                               GIT_PR_AUTHOR=self.pr.opened_by)

                            if repo == "inapp-rest-service":
                                """
                                2.3) Run for inapp_rest_services(one extra test) + moengage repo
                                """
                                job_dir = "inapps/"
                                job_name = job_dir + "integration_tests_webinapp"
                                head_repo_owner = self.pr.head_label.split(":")[0]  # FORK cases
                                api_params_dict = dict(GIT_REPO=head_repo, GIT_HEAD_BRANCH=self.pr.head_branch,
                                                       GIT_BASE_BRANCH=self.prbase_branch,
                                                       GIT_HEAD_BRANCH_OWNER=head_repo_owner,
                                                       GIT_PULL_REQUEST_LINK=pr_link,
                                                       GIT_SHA=self.pr.head_sha, AUTHOR_SLACK_NAME=pr_by_slack_name,
                                                       GIT_PR_AUTHOR=self.pr.opened_by)
                                print "hit api tests, params_dict=", api_params_dict
                                self.actor.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job_name,
                                                pr_link=pr_link, params_dict=api_params_dict, pr_by_slack=pr_by_slack_uid)

                        #Run main test
                        self.actor.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job_name,
                                        pr_link=pr_link, params_dict=params_dict,
                                        pr_by_slack=pr_by_slack_uid)

        else :
            """
            3) Third task, When pull request is merged,
            we run two checks.
            First, We alert if pull request is merged_by a person,
             who is not a valid contributor.
            Second, DM to pm for qa.
            """

    # def get_diff_files(self, repo):
    #     #Implement old function only
    #     from subprocess import Popen, PIPE, STDOUT
    #     import subprocess
    #     import os
    #     """
    #     First, It fetches commits of a repo, then we compare
    #     top two commit of a repo and we get the file difference.
    #     :param repo:
    #     :return:
    #     """
    #     # command = 'git log -2'
    #     # run_cmd = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    #     # commit_data = run_cmd.stdout.read()
    #     # commits = []
    #     # for line in commit_data.split('\n'):
    #     #     first_six = line[:6]
    #     #     if first_six == 'commit':
    #     #         commits.append(line.split(' ')[1])
    #     # first_commit = str(commits[0])
    #     # second_commit = str(commits[1])
    #     first_commit = str(self.pr.base_sha)
    #     second_commit = str(self.pr.head_sha)
    #     command = 'git diff %s'%second_commit + '...%s'%first_commit
    #     p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE)
    #     diff_data = p.stdout.read()
    #     file_edited = []
    #     for line in diff_data.split('\n'):
    #         first_three = line[:3]
    #         if first_three == "+++":
    #             file_name = line.split('+++')[1].split('/')[1:]
    #             file_path = "/".join(file_name)
    #             file_edited.append(file_path)
    #     print(file_edited)
    #     return file_edited

    def merge_code(self):
        from alice.helper.common_utils import CommonUtils
        from alice.helper.github_helper import GithubHelper
        from alice.helper.jenkins_helper import JenkinsHelper
        import jenkins
        """
        sha - head sha
        repo - defined
        statuses_url - defined
        head_ref - defined
        head_branch - defined
        base_branch - defined
        is_merged - defined
         merged_by = defined
         pr_by - opened_by
         title_pr - title
         body_pr - description
         link_pr - defined
         gitlink_pr - link
         pr_link - link_pretty
         pr_no - number

        """
        repo = self.pr.repo
        merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(self.pr.merged_by)
        merged_by_slack_name = CommonUtils.getSlackNicksFromGitNicks(self.pr.merged_by)
        pr_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(self.pr.opened_by)
        pr_by_slack_name = CommonUtils.getSlackNicksFromGitNicks(self.pr.opened_by)

        if self.pr.is_sensitive_branch:
            is_desired_branch = 1
        else:
            is_desired_branch = 0

        jenkins_instance = jenkins.Jenkins(JENKINS_BASE, username=username, password=token)
        is_change_in_react = False


        if self.pr.action.find("closed") != -1 and self.pr.is_merged == True and is_desired_branch and repo in ["moengage",
                                                                                                          "dashboard-ui"]:
            print "new merge came to dev/qa"
            merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(merged_by)
            # pr_by_slack = CommonUtils.getSlackNicksFromGitNicks(pr_by)
            msg = "Title=\"{0}\",  Description=\"{1}\" \nPR: {2}\n from {3} into `{4}` By: <@{5}>, mergedBy: <@{6}>\n".format(
                title_pr, body_pr, link_pr, head_branch, base_branch, pr_by_slack_uid, merged_by_slack_uid)
            postToSlack(code_merge_MoEngage, msg, data={"username": bot_name})  # code-merged
            # postToSlack("#experiment", msg,  data={"username": "github-bot"})

        if repo in ui_repo:
            print ":INFO: repo=%s" % repo
            msg = "base={0} head={1}, action={2} Do nothing".format(self.pr.base_branch, self.pr.head_branch, self.pr.action)
            self.close_dangerous_pr()
            job_dir = "Dashboard/"
            if self.pr.action in action_commit_to_investigate and self.pr.is_sensitive_branch:
                self.actor.jenkins.changeStatus(self.pr.statuses_url, "pending", context=context_react,
                             description="Hold on!",
                             details_link="")
                try:
                    # print ":DEBUG: check_file_path",  + "/files"
                    files_contents, message = self.get_files_task(self.pr.link + "/files")
                except PRFilesNotFoundException, e:
                    files_contents = e.pr_response
                if not files_contents or "message" in files_contents:
                    print ":DEBUG: no files found in the diff: SKIP shield, just update the status"
                    self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context=context,
                                 description="SKIP: No diff, check the Files count",
                                 details_link="")
                    self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context=context_react,
                                 description="SKIP: No diff, check the Files count", details_link="")
                    return files_contents  # STOP as files not found

                # print "files_contents after found", files_contents
                is_change_angular = False
                is_change_react = False
                for item in files_contents:
                    file_path = item["filename"]
                    if file_path.startswith("static/app_react"):
                        is_change_react = True
                    if file_path.startswith("static/app"):
                        is_change_angular = True

                if is_change_angular:
                    self.actor.run_for_angular(context_angular, job_dir, repo, pr_by_slack_name,
                                               is_change_angular, jenkins_instance, token, pr_by_slack_uid)

                """ hit react job"""  # Hit always even config changes can be possible
                self.actor.run_for_react(job_dir, repo, pr_by_slack_name, jenkins_instance, token,pr_by_slack_uid)
                msg = "ui repo checks started"

            if self.pr.is_merged is True and self.pr.action.find("close") != -1 \
                    and self.pr.base_branch in package_builder_branches_repo_wise.get(repo.lower()):
                msg = self.actor.jenkins.after_merge(job_dir, repo, self.pr.number, self.pr.title, pr_by_slack_uid, merged_by_slack_uid, self.pr.base_branch, self.pr.head_branch)
            return {"msg": msg}

        if repo in python_repo:
            if "feature/melora" in self.pr.base_branch or "feature/melora" in self.pr.head_branch:  # by pass for alice dev/test
                print ":SKIP: alice code changes on melora branch"
                return ":SKIP: alice code changes on " + repo
            if repo.lower() == 'moengage' and (
                    (self.pr.base_branch == "qa" and self.pr.head_branch in ["master", "master_py2"]) or
                    (self.pr.base_branch == "dev" and self.pr.head_branch == "qa")):
                print ":SKIP: back merge: checks call, repo={repo} pr={link_pr} title={title_pr}" \
                    .format(repo=repo, link_pr=self.pr.link_pr, title_pr=self.pr.title)
                self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context=context, description="checks bypassed for back merge",
                             details_link="")
                self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context="shield-unit-test-python",
                             description="checks bypassed for back merge",
                             details_link="")
                self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context="shield-linter-react",
                             description="checks bypassed for back merge",
                             details_link="")
                # or (base_branch == "release" and head_branch == "master") or (base_branch == "develop" and head_branch == "release") FOR PACKAGE repos
            else:
                print ":INFO: repo=%s to validate, for PR=%s" % (repo, self.pr.number)
                if self.pr.action in action_commit_to_investigate and (
                        self.pr.base_branch in sensitive_branches_repo_wise.get(repo.lower(), sensitive_branches_default)):
                    print "******* PR " + self.pr.action + "ed to " + self.pr.base_branch + ", Triggering tests ************"
                    pr_link = self.pr.link_pretty
                    pr_api_link = self.pr.link
                    # statuses_url = data["pull_request"]["statuses_url"] #moved above for re-usability
                    # sha = statuses_url.rsplit("/", 1)[1]
                    head_repo = self.pr.ssh_url
                    path = ""
                    files_backend = False
                    files_frontend = False
                    files_ops = False
                    # if repo.lower() != 'moengage':
                    #     context = "shield-syntax-validator"
                    self.actor.jenkins.changeStatus(self.pr.statuses_url, "pending", context=context, description=context_description,
                                 details_link="")  # status to go in pending quick
                    self.actor.jenkins.changeStatus(self.pr.statuses_url, "pending", context="shield-unit-test-python", description="Hold on!",
                                 details_link="")
                    try:
                        print ":DEBUG: check_file_path", self.pr.link + "/files"
                        files_contents, message = self.get_files_task(self.pr.link + "/files")
                    except PRFilesNotFoundException, e:
                        files_contents = e.pr_response
                    if not files_contents or "message" in files_contents:
                        print ":DEBUG: no files found in the diff: SKIP shield, just update the status"
                        self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context=context,
                                     description="SKIP: No diff, check the Files count",
                                     details_link="")
                        self.actor.jenkins.changeStatus(self.pr.statuses_url, "success", context="shield-unit-test-python",
                                     description="SKIP: No diff, check the Files count", details_link="")
                        return files_contents  # STOP as files not found

                    # print "files_contents after found", files_contents
                    for item in files_contents:
                        file_path = item["filename"]
                        if str(file_path).endswith(".py") and item["status"] != "removed":
                            path += " " + file_path

                        if str(file_path).endswith((".html", ".css", ".js", ".tpl", ".less", ".scss", ".json")):
                            files_frontend = True
                        elif str(file_path).endswith((".conf", ".cfg", ".init", ".sh")):
                            files_ops = True
                        else:
                            files_backend = True
                        # print "POOJA: "+file_path
                        if "dashboard/static/app_react/" in str(file_path):
                            is_change_in_react = True
                        # if any(x in str(file_path) for x in sensitive_files):
                        #     sensitive_file_alert = True
                        #     sensitive_modified_file_name = str(file_path)

                    # React_Files in entire pull request, not just the current commit
                    if self.pr.base_branch in ["master", "qa", "master_py2"]:
                        is_change_in_react = True

                    print "is_change_in_react=", is_change_in_react

                    if repo.lower() == 'moengage':
                        # ADD REVIEW LABEL
                        if self.pr.action in action_commit_to_investigate:
                            # if files_backend:
                            #     self.set_labels(repo, self.pr.number, ["Required_Backend_Review :skull:"])
                            #
                            # if files_frontend:
                            #     self.set_labels(repo, self.pr.number, ["Required_FrontEnd_Review :sunglasses:"])

                            if files_ops:
                                self.set_labels(repo, self.pr.number, ["Required_DevOps_Review :building_construction:"])

                        job_name = job_name + "_" + repo
                        params_dict = dict(repo=head_repo, head_branch=self.pr.head_branch, base_branch=self.pr.base_branch,
                                           pr_no=pr_link, checker_tool="pyflakes", lint_path=path,
                                           additional_flags="", msg="", machine="", sha=self.pr.head_sha, author=pr_by_slack_name,
                                           author_github=self.pr.opened_by,
                                           shield_react=is_change_in_react)
                    else:  # all dependencies moved to separate virtual env
                        job_dir = "package_shield/"
                        job_name = job_dir + "shield" + "_" + repo
                        head_repo_owner = self.pr.head_label.split(":")[0]  # FORK cases
                        params_dict = dict(GIT_REPO=head_repo, GIT_HEAD_BRANCH=self.pr.head_branch, GIT_BASE_BRANCH=self.pr.base_branch,
                                           GIT_HEAD_BRANCH_OWNER=head_repo_owner, GIT_PULL_REQUEST_LINK=pr_link,
                                           GIT_SHA=self.pr.head_sha, AUTHOR_SLACK_NAME=pr_by_slack_name,
                                           GIT_PR_AUTHOR=self.pr.opened_by)
                        if repo == "inapp-rest-service":
                            job_dir = "inapps/"
                            job_name = job_dir + "integration_tests_webinapp"
                            head_repo_owner = self.pr.head_label.split(":")[0]  # FORK cases
                            api_params_dict = dict(GIT_REPO=head_repo, GIT_HEAD_BRANCH=self.pr.head_branch,
                                                   GIT_BASE_BRANCH=self.prbase_branch,
                                                   GIT_HEAD_BRANCH_OWNER=head_repo_owner, GIT_PULL_REQUEST_LINK=pr_link,
                                                   GIT_SHA=self.pr.head_sha, AUTHOR_SLACK_NAME=pr_by_slack_name,
                                                   GIT_PR_AUTHOR=self.pr.opened_by)
                            print "hit api tests, params_dict=", api_params_dict
                    #         hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job_name,
                    #                         pr_link=pr_link, params_dict=api_params_dict, pr_by_slack=pr_by_slack_uid)
                    #
                    # hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job_name,
                    #                 pr_link=pr_link, params_dict=params_dict,
                    #                 pr_by_slack=pr_by_slack_uid)  # Hit main test



                    # print "params_dict", params_dict
                    # a = datetime.now()
                    # print "**Hitting Job '{0}' on PR link {1}".format(job_name, pr_link)
                    # try:
                    #     build_response = jenkins_instance.build_job(job_name, params_dict,
                    #                              {'token': token})
                    #     print "params_dict", params_dict
                    #     print "token="+ token
                    #     print "*** triggerd the job", build_response
                    #     b = datetime.now()
                    #     c = b - a
                    #     print int(c.total_seconds()), " seconds"
                    #     msg = "<@{0}> started tests, PR will be updated after tests are finished, check bottom for more details PR={1}".format(
                    #         pr_by_slack_uid, pr_link)
                    #     print msg
                    # except Exception, e:
                    #     print e
                    #     traceback.print_exc()
                    #     raise Exception(e)

                    # if sensitive_file_alert:
                    #     postToSlack(channel_name, dev_ops_team + " "+sensitive_modified_file_name
                    #                 + " is modified in PR="+pr_link+" by @"+pr_by_slack, data={"username": bot_name}, parseFull=False)
                    # return {"msg": msg} # respective channels-> entry should be saved so don't return

        if is_merged:
            is_desired_branch = base_branch in sensitive_branches_repo_wise.get(repo.lower(),
                                                                                sensitive_branches_default)
            if is_desired_branch and data["action"].find("closed") != -1:
                if (base_branch == "qa" and head_branch in ["master","master_py2"]) or (
                        base_branch == "dev" and head_branch == "qa"):  # or (base_branch == "release" and head_branch == "master") or (base_branch == "develop" and head_branch == "release"):
                    print ":SKIP: back merge: ignore status alert, repo={repo} pr={link_pr} title={title_pr}". \
                        format(repo=repo, link_pr=link_pr, title_pr=title_pr)
                else:
                    print ":DEBUG: merged into sensitive branch, checking PR's checks status"
                    checks_status_url = base_api_cmd + repo + "/status/" + sha

                    res_status = requests.get(checks_status_url, headers={"Authorization": "token " + GIT_TOKEN})
                    status_dict = json.loads(res_status.content)
                    print ":DEBUG: status response content", status_dict
                    msg_start = repo + " repo: PR <{link_pr}|{title_pr}> is merged into `{base_branch}` "
                    msg_end = " Merged by:*<@{merged_by_slack}>*, Author:*<@{pr_by_slack}>*"

                    if merged_by != "moeoperation":
                        if status_dict["state"] == "failure":
                            status_list = status_dict["statuses"]
                            context_description = ""
                            err_syntax_tests = ""
                            for item in status_list:
                                if item["context"].find("unit-tests") != -1 and item["state"] == "failure":
                                    context_description = item["description"]
                                if item["context"] == "shield-syntax-validator-python" and item["state"] == "failure":
                                    err_syntax_tests = item["description"]

                            if context_description.lower().find("miss coverage") != -1:
                                actual_coverage = \
                                parse("{}Coverage: {actual_coverage} is {} {two} {}", context_description).named[
                                    "actual_coverage"]
                                msg = msg_start.format(link_pr=link_pr, title_pr=title_pr, base_branch=base_branch) \
                                      + " with *{actual_coverage}* coverage.".format(actual_coverage=actual_coverage) \
                                      + msg_end.format(pr_by_slack=pr_by_slack_uid, merged_by_slack=merged_by_slack_uid)
                                postToSlack(channel_low_cover, msg, data={"username": bot_name}, parseFull=False)
                                print ":INFO: missed coverage found and still merged, logged in into ci-rules-bypassed channel " + link_pr
                            else:
                                rule_broken = ""
                                if err_syntax_tests:
                                    rule_broken = rule_broken + "*Syntax status:* " + err_syntax_tests + "\n"
                                if context_description:
                                    rule_broken = rule_broken + "*Unit tests status:* " + context_description
                                msg = msg_start.format(link_pr=link_pr, title_pr=title_pr, base_branch=base_branch) \
                                      + "\n{rule} ".format(rule=rule_broken) \
                                      + msg_end.format(pr_by_slack=pr_by_slack_uid, merged_by_slack=merged_by_slack_uid)
                                postToSlack(channel_rules_broken_other_than_low_cover, msg, data={"username": bot_name},
                                            parseFull=False)
                                print ":INFO: check fails and still merged, notified pooja " + link_pr
                        elif status_dict["state"] == "pending":
                            msg = "Very Bad :rage1: <@%s> you have misused 'admin' power by merging *without waiting for checks to complete*." % merged_by_slack_uid \
                                  + msg_start.format(link_pr=link_pr, title_pr=title_pr, base_branch=base_branch) \
                                  + "unchecked code is prone to break in production. cc: <@pooja> <@satya>"
                            postToSlack(channel_rules_broken_other_than_low_cover, msg, data={"username": bot_name},
                                        parseFull=False)
                            print ":INFO: check is still running but PR is merged by force. notified pooja " + link_pr
                        else:
                            print ":DEBUG: good merge, all checks looks pass pr=" + pr_link

        commit_api = gitlink_pr + "/files"
        if action == "synchronize":
            commit_api = "https://api.github.com/repos/moengage/%s/commits/%s" % (
            repo, sha)  # works for forked as well (no need of owner change)
        sensitive_file_alert, sensitive_modified_file_name, ui_change, is_automatic_base_merge_commit = is_sensitive(
            commit_api)
        print "\nPull request=", pr_link
        print "Sensitive file alert=", sensitive_file_alert
        print "File name(s)=", sensitive_modified_file_name
        print "ui_change found=", ui_change
        print "is_change_in_react=", is_change_in_react
        """
        if action in action_commit_to_investigate:
            print "going to check sensitive files in the commit"
            if not is_automatic_base_merge_commit: #process only when not an automatic commit

                if sensitive_file_alert and pr_by_slack_name != "moeoperation":
                    message = dev_ops_team + " " + str(sensitive_modified_file_name) + " is modified in PR=" \
                              + pr_link + " by <@" + pr_by_slack_uid + ">"
                    if repo != "MoEngage":
                        is_changelog = False
                        is_releasenotes = False
                        changed_file = ""
                        for item in sensitive_modified_file_name: #releasenotes if release->master and changelog if any to release
                            print base_branch, item.lower()
                            if base_branch == "release" and "changelog" in item.lower():  # reduce(lambda a, x: True if 'changelog' in x else a, sensitive_modified_file_name, False)
                                is_changelog = True
                                changed_file = item
                            elif base_branch == "master" and "releasenotes" in item.lower():
                                is_releasenotes = True
                                changed_file = item
                            else:
                                message = ""

                        if is_changelog or is_releasenotes:
                            message = "Dependency change: *{repo}* : <{pr_link}/files|{sensitive_modified_file_name}> " \
                                      "by {pr_by_slack} cc: {to_notify}".format(repo=repo,
                                                               sensitive_modified_file_name=changed_file,
                                                               pr_link=pr_link, pr_by_slack=pr_by_slack_name,
                                                               to_notify=backend_leads_to_notify_slack)
                    print "*** message=", message
                    postToSlack("#development", message, data={"username": bot_name}, parseFull=False)
                else:
                    message = "no sensitive file found in "+commit_api
                    print message
            else:
                print "SKIP: alerting sensitive file, automatic update with base received"
            """
        # print "*** message=", message
        # postToSlack("#development", message, data={"username": bot_name}, parseFull=False)
        if repo in ['segmentation', 'commons']:
            is_desired_branch = base_branch in sensitive_branches_repo_wise.get(repo.lower(),
                                                                                sensitive_branches_default)
            cc_team = alice_dev_team_segmentation_repo
            code_merge_channel = code_merge_segmentation
            if repo == "commons":
                cc_team = alice_dev_team_segmentation_repo + " @pruthvi"
                code_merge_channel = code_merge_commons

            if action.find("open") != -1 and is_desired_branch:
                print "***** " + repo + ":: PR opened to develop/release/qa/master, Notify Alice & comment guidelines ****"
                msg = repo + " repo:: <{link_pr}|{title_pr}> is {action} to `{base_branch}` by:*<@{pr_by_slack}>* " \
                    .format(link_pr=link_pr, title_pr=title_pr, pr_by_slack=pr_by_slack_uid, base_branch=base_branch,
                            action=action)
                if action == "opened":
                    add_comment(data)
                postToSlack('@' + to_be_notified, msg, data={"username": bot_name}, parseFull=False)
                return {"msg": msg}

            if data["action"].find("closed") != -1 and is_merged and is_desired_branch:
                print "**** Repo=" + repo + ", new merge came to " + base_branch + " set trace to " + code_merge_channel + " channel"
                merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(merged_by)
                msg = "Title=\"{0}\",  Description=\"{1}\" \nPR: {2}\n from {3} into `{4}` By: *<@{5}>*, mergedBy: <@{6}>\n".format(
                    title_pr, body_pr, link_pr, head_branch, base_branch, pr_by_slack_uid, merged_by_slack_uid)
                postToSlack(code_merge_channel, msg, data={"username": bot_name})  # code-merged

            if data["action"] == "closed" and is_merged and base_branch == "release" \
                    and (merged_by not in valid_contributors_segmentation_repo):
                print "**** Repo=" + repo + ", merged in branch=" + base_branch + " and is not authentic, alert the culprit " + merged_by + " to channel"
                merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(merged_by)
                msg = "Very Bad <@" + merged_by_slack_uid + "> :rage4: :rage4: !! " + data["pull_request"]["_links"][
                    "html"][
                    "href"] + " is merged directly into `" + base_branch + "`, but not by Akshay/Pruthvi/Pooja, soon these kind of requests will be automatically reverted CC: " + cc_team
                print msg
                # print postToSlack("#experiment", msg,  data={"username": "github-bot"})
                print postToSlack(channel_name, msg, data={"username": bot_name})

            review_code(data, requests, is_desired_branch, cc_team, valid_contributors_segmentation_repo)
            return

        if repo != "MoEngage":
            return

        # ******************* check starts here *************************
        # pr_link =data["pull_request"]["html_url"] FOR DEBUG
        # write_to_file(code_freeze_details_path, "latest code freezed @ `qa` on " + str(datetime.datetime.now().strftime(
        #     '%B %d @%I.%M%p')) + " \n with PR: " + pr_link + " please read release notes for more clarity.")
        # write_to_file(release_freeze_details_path,
        #               "Released to `master` on:" + str(datetime.datetime.now().strftime(
        #             '%B %d, %Y @ %I.%M%p')) + "\n but you know, based on traffic exact release date may differ so please check release notes, just type \"release notes\" to get the link")
        # #clear_file(code_freeze_details_path)
        # #return {}

        close_pr_if_required(data, base_branch, head_branch, pr_by_slack_uid, pr_link, title_pr, channel_name)

        if data["action"].find("open") != -1 and base_branch in sensitive_branches_repo_wise.get(repo.lower(),
                                                                                                 sensitive_branches_default):
            print "************ MoEngage repo:: PR opened to " + base_branch + " Notify Alice & comment guidelines ****"
            msg = "MoEngage repo:: <{link_pr}|{title_pr}> is opened to `{base_branch}` by:*<@{pr_by_slack}>* " \
                .format(link_pr=link_pr, title_pr=title_pr, pr_by_slack=pr_by_slack_uid, base_branch=base_branch)

            if base_branch in ["master", "master_py2"] and head_branch == "qa":
                add_comment_to_master(data)
                for item in alice_tech_leads_MoEngage_Repo:
                    postToSlack(item, msg + "\n Please review and approve with +1, Release preparation starts...",
                                data={"username": bot_name}, parseFull=False)
                freeze_other_repos("live")

                for item in alice_qa_team:
                    postToSlack(item,
                                "\n\n:bell: *Bugs clean time* :: please make out 20 minutes max to cleanup no longer valid old issues and share a rough number of issues we cleaned or require attention <https://docs.google.com/spreadsheets/d/1WeWLuIE7Dt5G8lWACZs21WO0B07-naQ7JlUb8cHcxVA/edit#gid=1591591107|sheet link>",
                                data={"username": bot_name}, parseFull=False)
                for item in alice_product_team:
                    postToSlack(item,
                                "\n:bell: Hi " + item + " *Release notes update required*: Current release is getting ready to go Live, please help us with next release planning by having \"Next Release\" <https://docs.google.com/a/moengage.com/spreadsheets/d/1eW3y-GxGzu8Jde8z4EYC6fRh1Ve4TpbW5qv2-iWs1ks/edit?usp=sharing|sheet> updated",
                                data={"username": bot_name}, parseFull=False)
            else:
                add_comment(data)
                postToSlack('@' + to_be_notified, msg, data={"username": bot_name}, parseFull=False)

            # return {"msg": msg}
        """ moved up for dashboard-ui and other repos
        if data["action"].find("closed") != -1 and is_merged == True and (is_desired_branch):
            print "new merge came to dev/qa"
            merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(merged_by)
            # pr_by_slack = CommonUtils.getSlackNicksFromGitNicks(pr_by)
            msg = "Title=\"{0}\",  Description=\"{1}\" \nPR: {2}\n from {3} into `{4}` By: <@{5}>, mergedBy: <@{6}>\n".format(
                title_pr, body_pr, link_pr, head_branch, base_branch, pr_by_slack_uid, merged_by_slack_uid)
            postToSlack(code_merge_MoEngage, msg, data={"username": bot_name})  # code-merged
            # postToSlack("#experiment", msg,  data={"username": "github-bot"})
        """
        """
        if base_branch == "qa" and is_merged is True and data["action"].find("close") != -1:
            bump_version_job_dict = dict(release_type="minor", repo=repo, pr_no=pr_no, pr_title=title_pr,
                                         pr_by_slack=pr_by_slack_uid, approved_by=merged_by_slack_uid,
                                         merged_by_slack=merged_by_slack_uid, base_branch=base_branch,
                                         head_branch=head_branch, is_ui_change=ui_change)
            hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name="front_end_builder",
                            pr_link=pr_link, params_dict=bump_version_job_dict, pr_by_slack=pr_by_slack_uid)
        """

        if data["action"].find("close") != -1 and is_merged == True and (
                base_branch in ["master", "master_py2"] and head_branch == "qa"):
            merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(merged_by)
            # msg = dev_ops_team + " let's take release live :+1: `master` is <" + data["pull_request"][
            #    "html_url"] + "|updated here> \n cc: <!channel>"
            # msg = '@' + to_be_notified + " QA passed :+1: <" + data["pull_request"][
            #    "html_url"] + "|Release QA Details>  Awaiting your go ahead. cc: "+dev_ops_team +" "+ tech_leads_to_notify_always_slack

            """ ************* inform channel *************** """
            msg = "{2} QA passed :+1: `master` is <{1}|updated> for release \n cc: <@{0}> {3} {4} \n <!channel> ".format(
                to_be_notified, data["pull_request"][
                    "html_url"], dev_ops_team, tech_leads_to_notify_always_slack, product_notify_slack)

            postToSlack(channel_name, msg, data=CommonUtils.getBot(channel_name, merged_by_slack_name), parseFull=False)

            """ ********** Bump Version ************** """
            print ":DEBUG: before hitting patch job is_ui_change=", ui_change
            bump_version_job_dict = dict(release_type="major", repo=repo, pr_no=pr_no, pr_title=title_pr,
                                         pr_by_slack=pr_by_slack_uid, approved_by=merged_by_slack_uid,
                                         merged_by_slack=merged_by_slack_uid, sha=sha, head_branch=head_branch,
                                         is_ui_change=ui_change)
            hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name="VersionBumper_MoEngage",
                            pr_link=pr_link, params_dict=bump_version_job_dict, pr_by_slack=pr_by_slack_uid)

            """ ********** Remind PM teams to update release notes for next release ************ """
            for item in alice_product_team:
                postToSlack(item,
                            "\n:bell: hi " + item + " master is updated & release is going live shortly. Hoping <https://docs.google.com/a/moengage.com/spreadsheets/d/1eW3y-GxGzu8Jde8z4EYC6fRh1Ve4TpbW5qv2-iWs1ks/edit?usp=sharing|Release Notes> have mention of all the items planned to go in \"Next Release\"",
                            data={"username": bot_name}, parseFull=False)
            """ for bot """
            for item in alice_qa_team:
                postToSlack(item, "\n hi <" + item + "> " + random.choice(
                    applaud_list) + " :+1: thank you for the QA signOff\n :bell: <https://github.com/moengage/MoEngage/wiki/Post-Release-deployment-Check#for-qa-engineer|" + random.choice(
                    post_checklist_msg) + ">",
                            data={"username": bot_name}, parseFull=False)
            write_to_file_from_top(release_freeze_details_path, ":clubs:" +
                                   str(datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
                                       '%B %d,%Y at %I.%M %p')) + " with <" + pr_link + "|master> code")  # on:" + str(datetime.datetime.now().strftime('%B %d, %Y @ %I.%M%p'))
            clear_file(code_freeze_details_path)  # clear last code freeze

        if data["action"].find("close") != -1 and is_merged == True and (
                base_branch in ["master", "master_py2"] and head_branch.startswith("patch")):
            # if title_pr.lower().startswith("patch"):
            msg = "MoEngage Repo: A patch came from head=" + head_branch
            print msg

            """ ********** Bump Version ************** """
            checks_status_url = "%s%s/pulls/%s/reviews" % (base_api_cmd, repo, pr_no)
            print "**** get reviews if there is any approval api=***", checks_status_url
            res_status = requests.get(checks_status_url, headers={"Authorization": "token " + GIT_TOKEN})
            print "res_status=", res_status.content
            review_list = json.loads(res_status.content)
            approved_by_list = []
            for item in review_list:
                print item
                if str(item["state"]).lower() == "approved":
                    approved_by_list.append(item["user"]["login"])

            approved_by = ""
            for name in approved_by_list:
                approved_by += CommonUtils.getSlackNicksFromGitNicks(name) + " "

            bump_version_job_dict = dict(release_type="patch", repo=repo, pr_no=pr_no, pr_title=title_pr,
                                         pr_by_slack=pr_by_slack_uid, approved_by=approved_by,
                                         merged_by_slack=merged_by_slack_uid, sha=sha, head_branch=head_branch,
                                         is_ui_change=ui_change)
            print ":DEBUG: before hitting patch job is_ui_change=", ui_change
            hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name="VersionBumper_MoEngage",
                            params_dict=bump_version_job_dict, pr_link=pr_link, pr_by_slack=pr_by_slack_uid)

            # """ ****** Raise Infra Request *******"""  # MOVED TO JENKINS as can't wait for bump here
            # request_body = """```
            #     +1 from one of the tech leads/peers :
            #     Cluster region  :
            #     Where to Deploy :
            #     ```
            #     **To-Dos**
            #     - Fill this [Patch Form](http://bit.ly/2kqKwFF)
            #     - Patch PR: {pr}
            #     """.format(pr=pr_link)
            # infra_request_data = {
            #     "title": title_pr,
            #     "body": request_body,
            #     "labels": [
            #         "patch",
            #         "user-action-pending"
            #     ],
            #     #"assignees": ["shahp00ja"]  # "pruthvintss",
            # }
            # ISSUES_ENDPOINT = "https://api.github.com/repos/{owner}/{repo}/issues"
            # response_infra_req = requests.post(ISSUES_ENDPOINT.format(owner="moengage", repo="infrarequests"),
            #                         data=json.dumps(infra_request_data), headers={"Authorization": "token " + GIT_TOKEN})
            # res_infra_req = response_infra_req.json()
            # if "errors" or "message" in res_infra_req:
            #     try:
            #         msg = res_infra_req.get("errors")[0].get("message")
            #     except:
            #         msg = res_infra_req.get("message")
            #         postToSlack(failure_alert, msg, data=CommonUtils.getBot(channel_name, merged_by_slack_name), parseFull=False)
            # else:
            #     ticket_no = res_infra_req.get("html_url")
            #     msg = "Hi <@{pr_by_slack}> and <@{merged_by_slack}>, your <{ticket_no}|patch request> is received," \
            #     " please make sure to fill the required details in description and assign to take it live".format(pr_by_slack=pr_by_slack, merged_by_slack=merged_by_slack, ticket_no=ticket_no)
            #     postToSlack("#infrarequests", msg, data=CommonUtils.getBot(channel_name, merged_by_slack_name), parseFull=False)

        if data["action"].find("closed") != -1 and is_merged == True and (base_branch == "dev"):
            # pr_by_slack = CommonUtils.getSlackNicksFromGitNicks(pr_by)
            time.sleep(5)
            postToSlack('@' + pr_by_slack_uid,
                        "Hi <@" + pr_by_slack_uid + "> : you have merged " + link_pr + " into `dev`\n now, be nice & mention it in Release Notes for getting it `QAed and released` under Sheet name as respective Date \n https://docs.google.com/spreadsheets/d/1V6-cr3JZwavJaHt_pLpesfnd_sqJZCnBPNO5mFdGElI/edit?usp=sharing",
                        data={"username": bot_name})
            print "have sent reminder to" + pr_by_slack_uid + " to mention in Release Notes"
            with open(file_path, "a") as f:
                msg = ":beer: Title=\"{0}\",  Description=\"{1}\" \nPR: {2} By: <@{3}>".format(title_pr, body_pr,
                                                                                               link_pr,
                                                                                               pr_by_slack_uid)
                f.write(msg + '\n\n')
                print msg + ' added to file ' + file_path
                f.close()
            with open(file_mergedBy, "a+") as f:
                name = "<@{0}>".format(pr_by_slack_uid)
                existing_names = f.read()
                if name not in existing_names:
                    f.write(name + ", ")
                    print msg + ' added unique names to file ' + file_mergedBy
                f.close()

        if (base_branch == "qa" and head_branch == "dev") and data["action"].find("opened") != -1:
            print "************ code freeze PR is opened from dev to QA, auto create PRs for dependent packages"
            postToSlack(channel_name,
                        "@channel Freezing code now. Any pending merge? please reach QA team within 10 minutes",
                        data={"username": bot_name}, parseFull=False)
            freeze_other_repos("staging")

        if data["action"].find("closed") != -1 and is_merged == True and (base_branch == "qa" and head_branch == "dev"):
            print "from 'dev' to 'qa', posting release items to slack"

            write_to_file_from_top(code_freeze_details_path, ":clubs:" + str(
                datetime.now(pytz.timezone('Asia/Calcutta')).strftime(
                    '%B %d at %I.%M %p')) + " with <" + pr_link + "|PR>")

            msg = ""
            with open(file_path) as f:
                msg = f.read()
                # print 'loop msg=' + msg
                f.close()
            print "final msg 30 chars=" + msg[:30]
            if msg:
                # postAttachmentToSlack("#experiment",msg,data={"username": "github-bot"})
                postAttachmentToSlack(channel_name, pr_link, msg, data={"username": bot_name}, parseFull=False)

                shutil.copy(file_path, '/opt/alice/release_items_' + str(
                    datetime.now().strftime('%m-%d-%Y:%I.%M%p')) + '.txt')  # take backup beforing clearing
                if debug is False:
                    open(file_path, 'w').close()  # clear file for next release content

            name = ""
            with open(file_mergedBy) as f:
                name = f.read()
                f.close()
            print "final name list =" + name
            if name:
                time.sleep(10)
                # postFinalWarningToSlack("#experiment",name,data={"username": "github-bot"})
                postFinalWarningToSlack(channel_name, name, data={"username": bot_name})
                open(file_mergedBy, 'w').close()

        if data["action"] == "closed" and is_merged == True and base_branch == "qa" and (
                merged_by not in valid_contributors):
            merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(merged_by)
            msg = "Very Bad <@" + merged_by_slack_uid + "> :rage4: :rage4: !! " + data["pull_request"]["_links"][
                "html"][
                "href"] + " is merged directly into `" + base_branch + "`, but not by QA team, soon these kind of requests will be automatically reverted CC: " + alice_dev_team_MoEngage_repo
            print msg
            # print postToSlack("#experiment", msg,  data={"username": "github-bot"})
            print postToSlack(channel_name, msg, data={"username": bot_name})

        # raise alert when +1 not found
        review_code(data, requests, is_desired_branch, alice_dev_team_MoEngage_repo, valid_contributors)

        return {}

    def check_valid_contributor(self):
        from alice.helper.common_utils import CommonUtils
        valid_contributors = ["ajishnair", "shahp00ja", "vandanamoriwal", "geetima12", "akgoel-mo", "naveenkumarkokku",
                              "prashanthegde9", "moeoperation", "BhuvanThejaChennuru", "kanikapuniya2", "siri-murthy",
                              "gagana11", "madhurjyaparashar", "rkjas12", "Madhukirankm"]


        if self.pr.action == "closed" and self.pr.is_merged == True and self.pr.base_branch == "qa" and (
                self.pr.merged_by not in valid_contributors):
            merged_by_slack_uid = CommonUtils.getSlackNicksFromGitNicks(self.pr.merged_by)
            msg = "Very Bad <@" + merged_by_slack_uid + "> :rage4: :rage4: !! " + data["pull_request"]["_links"][
                "html"][
                "href"] + " is merged directly into `" + base_branch + "`, but not by QA team, soon these kind of requests will be automatically reverted CC: " + alice_dev_team_MoEngage_repo
            print msg
            print postToSlack(channel_name, msg, data={"username": bot_name})

"""
    Implement your check here, will be automatically called

    To get pull request related data, access with self.pr Ex.
        self.pr.repo
        self.pr.number
        self.pr.opened_by
        self.pr.merged_by
        self.pr.merged_by_slack
        self.pr.opened_by_slack
        self.pr.link_pretty   -> readable link
        self.pr.link          -> api link
        self.pr.action
        self.pr.is_merged
        self.pr.is_opened
        self.pr.is_reopened
        self.pr.base_branch
        self.pr.head_branch
        self.pr.comments_section
        self.pr.is_sensitive_branch
        self.pr.title
        self.pr.description


   To get inputs from config file, access with self.pr.config
       self.pr.config.organisation
       self.pr.config.githubToken
       self.pr.config.slackToken
       self.pr.config.is_debug
       self.pr.config.repo
       self.pr.config.sensitiveBranches
       self.pr.config.sensitiveFiles
       self.pr.config.branchListToBeNotifiedFor
       self.pr.config.actionToBeNotifiedFor
       self.pr.config.whiteListedMembers
       self.pr.config.superMembers
       self.pr.config.mainBranch
       self.pr.config.testBranch
       self.pr.config.debug_folks
       self.pr.config.debug_channel
       self.pr.config.alertChannelName
       self.pr.config.codeChannelName
       self.pr.config.personToBeNotified
       self.pr.config.techLeadsToBeNotified
       self.pr.config.productPlusRequiredDirPattern
       self.pr.config.devOpsTeam
       self.pr.config.checks
       self.pr.config.getSlackName(github_name)

    """
