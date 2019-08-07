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
        self.trigger_task_on_pr()

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

        from alice.helper.common_utils import CommonUtils
        from alice.helper.constants import *
        import jenkins
        jenkins_setting = self.pr.global_config.config["jenkins"]
        token = jenkins_setting["token"]
        jenkins_instance = jenkins.Jenkins(jenkins_setting["JENKINS_BASE"],
                                           username=jenkins_setting["username"], password=token)
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
            commons, segmentation, campaigns-core,
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
                self.actor.jenkins.change_status(self.pr.statuses_url, "pending", context=context_react,
                                                 description="Hold on!",
                                                 details_link="")

                try:
                    files_contents, message = self.get_files_task(self.pr.link + "/files")
                except PRFilesNotFoundException, e:
                    files_contents = e.pr_response

                if not files_contents or "message" in files_contents:
                    print ":DEBUG: no files found in the diff: SKIP shield, just update the status"
                    self.actor.jenkins.change_status(self.pr.statuses_url, "success", context=context,
                                                     description="SKIP: No diff, check the Files count",
                                                     details_link="")
                    self.actor.jenkins.change_status(self.pr.statuses_url, "success", context=context_react,
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
                self.actor.run_for_react(job_dir, repo, pr_by_slack_name, jenkins_instance, token, pr_by_slack_uid)
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

                elif repo.lower() == organization_repo and (
                        (self.pr.base_branch == staging_branch and self.pr.head_branch in master_branch) or
                        (self.pr.base_branch == dev_branch and self.pr.head_branch == staging_branch)):

                    print ":SKIP: back merge: checks call, repo={repo} pr={link_pr} title={title_pr}" \
                        .format(repo=repo, link_pr=self.pr.link_pr, title_pr=self.pr.title)
                    self.actor.jenkins.change_status(self.pr.statuses_url, "success", context=context,
                                                     description="checks bypassed for back merge",
                                                     details_link="")
                    self.actor.jenkins.change_status(self.pr.statuses_url, "success", context="shield-unit-test-python",
                                                     description="checks bypassed for back merge",
                                                     details_link="")
                    self.actor.jenkins.change_status(self.pr.statuses_url, "success", context="shield-linter-react",
                                                     description="checks bypassed for back merge",
                                                     details_link="")

                else:
                    print ":INFO: repo=%s to validate, for PR=%s" % (repo, self.pr.number)
                    if self.pr.base_branch in sensitive_branches_repo_wise.get(repo.lower(), sensitive_branches_default):

                        print "******* PR " + self.pr.action + "ed to " + self.pr.base_branch + ", Triggering tests ************"

                        #variable declaration
                        pr_link = self.pr.link_pretty
                        head_repo = self.pr.ssh_url
                        path = ""
                        files_ops = False

                        self.actor.jenkins.change_status(self.pr.statuses_url, "pending", context=context,
                                                         description=context_description,
                                                         details_link="")  # status to go in pending quick
                        self.actor.jenkins.change_status(self.pr.statuses_url, "pending",
                                                         context="shield-unit-test-python", description="Hold on!",
                                                         details_link="")
                        try:
                            print ":DEBUG: check_file_path", self.pr.link + "/files"
                            files_contents, message = self.get_files_task(self.pr.link + "/files")
                        except PRFilesNotFoundException, e:
                            files_contents = e.pr_response
                        if not files_contents or "message" in files_contents:
                            print ":DEBUG: no files found in the diff: SKIP shield, just update the status"
                            self.actor.jenkins.change_status(self.pr.statuses_url, "success", context=context,
                                                             description="SKIP: No diff, check the Files count",
                                                             details_link="")
                            self.actor.jenkins.change_status(self.pr.statuses_url, "success",
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

                        if repo.lower() == organization_repo and files_ops and self.pr.action \
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
                                print("hit api tests, params_dict=", api_params_dict)
                                self.actor.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job_name,
                                                pr_link=pr_link, params_dict=api_params_dict, pr_by_slack=pr_by_slack_uid)

                        #Run main test
                        # self.actor.hit_jenkins_job(jenkins_instance=jenkins_instance, token=token, job_name=job_name,
                        #                 pr_link=pr_link, params_dict=params_dict,
                        #                 pr_by_slack=pr_by_slack_uid)

            # 3) Third Task - set_labels
            self.set_labels(repo, self.pr.number, [])

            # 4) Comment Checklist
            self.github_comment_guidelines()

            # 5) code_freeze alert
            self.code_freeze_alert()

            #6) release_freeze_alert
            self.release_freeze_alert()

        else:
                """
                3) last task task, When pull request is merged,
                we run two checks.
                First, We alert if pull request is merged_by a person,
                 who is not a valid contributor.
                Second, DM to pm for qa.
                """

                #3.1)
                self.code_freeze_alert()

                #3.2)
                self.release_freeze_alert()

                #3.3)
                self.valid_contributors()

                #3.4)
                self.notify_pm()


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
