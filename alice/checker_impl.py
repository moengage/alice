from alice.main.checks import Checks


class CheckImpl(Checks):

    def __init__(self, push_payload_parser):
        super(CheckImpl, self).__init__(push_payload_parser)
        self.pr = push_payload_parser


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

