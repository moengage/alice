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
