### Sensitive Branch
A git branch is sensitive if it's code is going to be released and meant to be protected. In simple words, which is moved for testing and be released.
Eg. `develop`, `qa`, `master`

### Code Review
- I keep checking the Pull request on it's merge event, and if I don't find a code review by peer member, I raise concern by notifying on slack channel mentioning respective developer and lead/QA members

  Eg. use case: you are a product manager and want to ensure no one changes the frozen ui flow you had approved earlier, you can opt for `Product Review` check
**Pre-requisites:** [Protect](https://help.github.com/articles/enabling-required-reviews-for-pull-requests/) your sensitive branches (half of the work is done)

The code review is classified in 2 checks:
1. **Tech Review:** Needs +1 or github's thumbsup icon in comments of [Approve](https://help.github.com/articles/approving-a-pull-request-with-required-reviews/) section

2. **Product Review:** Needs +1 or github's thumbsUp icon by any of the product manager on your team you have [configured in config](https://github.com/moengage/alice/blob/master/docs/setup_config.md) file


### Remind Guidelines
I remind to particular
- remind_direct_release_guideline_on_merge: direct message on slack to follow release guidelines on moving code to next [sensitive branch](https://github.com/moengage/alice/blob/master/docs/checks.md#sensitive-branch)
   On [configured](https://github.com/moengage/alice/blob/master/docs/setup_config.md) action settings, I notify respective folk directly on slack

- github_comment_guidelines:
  Eg. use case: if the code is merged to master/release branch and you want to remind the release pre-requisite checklist like
     ```
     **Attention!**
     Release Checklist
        - [x] JS version Update? check index.html
        - [x] No code/PR to be reverted? check release notes
        - [x] Unit Tests Passed?
        - [x] Api Tests passed?
        - [x] QA report linked?
        - [x] Release Notes linked?
     ```


### Auto Close Pull Request
As soon as I sense if Pull request is mistakenly created between wrong branches, I auto close them and notify the respective on channel as [configured](https://github.com/moengage/alice/blob/master/docs/setup_config.md)
Eg. the Pull Request raised from `feature` branch to `master` should not be merged hence I'll close the Pull Request specifying the reason like:
![image](https://cloud.githubusercontent.com/assets/12966925/25894823/12a71068-359b-11e7-9687-8efd2d10d2ae.png)

### Alerts to devOps for modification of sensitive file(s)
This check is specially made for devOps at present
As soon as a Pull request is merged into a [sensitive branch](https://github.com/moengage/alice/blob/master/docs/checks.md#Sensitive-Branch)
I sense for the given file(s) pattern in [config](https://github.com/moengage/alice/blob/master/docs/setup_config.md) file and if any of those files are modified, I inform the respective devOps members

### Notify on commits
This is to notify direct/channel on slack based on git commits

- notify_lead_on_given_action:  This check notifies [configured member](https://github.com/moengage/alice/blob/master/docs/setup_config.md) (Eg. lead) about the activity as per given action
Eg. use-case: you are a tech lead and you want to be notified for each Pull Request open (to a [sensitive branch](https://github.com/moengage/alice/blob/master/docs/checks.md#sensitive-branch)) so you can supervise them if all are following the basic principles or not

- notify_channel_on_merge: This stores entries of Pull request merged with respective essential details (when base is a sensitive branch) in slack channel as [configured](https://github.com/moengage/alice/blob/master/docs/setup_config.md)
Eg. ![image](https://cloud.githubusercontent.com/assets/12966925/25896695/db4ff6ea-35a2-11e7-91ad-048907407cc5.png)