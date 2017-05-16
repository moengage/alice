### Alice
A bot for code monitoring and more...
________________________________

Hi, I'm alice, made with :heart: on top of [python](https://www.python.org/) using [Flask](http://flask.pocoo.org/).
For any team, I prevent [last minute chaos situations](https://github.com/moengage/alice/blob/master/README.md#why-me?) and improve Quality Assurance (Oh yes! it's possible with me)

I'm your friendly robot sidekick. Integrate me with your product to dramatically improve your Release process (Pre and Post)

### Why Me?
Imagine your standard release day and a sudden **roadblock** is encountered.
Everyone in your team is running around with questions like:

- Which build is breaking the feature/code?
- Did we miss any steps while deploying code to staging?
- How had it been merged without review?
- How did it get passed through test cases, didn't they run?
- Which code to revert to, to fix this quickly?
- Who should I reach out to, for this?
- Were these configuration or dependency changes?
- Were these changes well informed to devOps team?
- How not to miss the respective DB/config/JS/dependency update changes from next time?

Are you looking for a **free automated** solution which can, not only prevent these but also improve the collaboration and productivity of your team by performing the required *code supervision* tasks.

### What I do?
I can be your assistant who can monitor code flow, right from development to release phase, thus preventing usual mistakes throughout your Development Life Cycle.

This library is distributed via [pip](https://pypi.python.org/pypi/alice-core) so that you can build your own in-house mate.

### How I do it?
I help teams avoid "last moment panic attacks" by using collaboration tool like [slack](https://slack.com/) by:
- Monitoring/reminding/blocking/alerting teams/individuals to maintain code hygiene
- Enabling every member in team to get required info about the system @ any time
- Answering repetitive and mundane questions about the system
- Having a trustworthy 24x7 code monitoring system from development to release phase

### Current Features
For all [sensitive branches](https://github.com/moengage/alice/blob/master/docs/checks.md#sensitive-branch) (Eg. master, qa, develop)
- [Code Review](https://github.com/moengage/alice/blob/master/docs/checks.md#code-review)
- [Remind team](https://github.com/moengage/alice/blob/master/docs/checks.md#remind-duidelines) members to follow Guidelines
- [Auto close](https://github.com/moengage/alice/blob/master/docs/checks.md#auto-close-pull-request) suspicious Pull Request
- Alerts on modification of [sensitive file(s)](https://github.com/moengage/alice/blob/master/docs/checks.md#alerts-to-devops-for-modification-of-sensitive-file(s))
- Notify on specific [action on a Pull Request](https://github.com/moengage/alice/blob/master/docs/checks.md#notify-on-commits)
- [Custom check](https://github.com/moengage/alice/blob/master/docs/extend_alice.md#adding-more-checks) implementations

**Note:** I am currently implemented for [Github](https://github.com/) & [Slack](https://slack.com/) users only. However I can be expanded to support other platforms as well. Please read [here](https://github.com/moengage/alice#want-to-contribute)

### Want to hire me?

1. **Installation:** 
   ```
   pip install alice-core
   ```
2. **Getting Started:**

   2.1  Create your team specific input config file [setup config file](https://github.com/moengage/alice/blob/master/docs/setup_config.md)

   2.2. Start Alice (any 1 way):

   Modify the commands with particular config.yaml or config.json file path & port number
 	-  run as flask app

      	```
      	export FLASK_APP=alice config='config.yaml'; flask run --host 0.0.0.0 --port 5005
      	```
        You should see success message like this

        ![image](https://cloud.githubusercontent.com/assets/12966925/25900478/3c801d38-35b1-11e7-9701-ee9a1ebb134f.png)

      or
    -  run as uwsgi process (Install uwsgi>=2.0.14 on machine yourself for using this)

      	```
      	export config="config.yaml"; uwsgi --socket 0.0.0.0:5005 --protocol=http -w alice --callable app
      	```
    **Note:** can change port number as needed



   2.3 Plug it in with your system
   - test locally with any pull request payload:
     ```
     http://0.0.0.0:<GIVE_PORT_NO>
     ```
     it should return "welcome" message

   - activate alice from your github repository

     - Create [web-hook in github](https://developer.github.com/webhooks/creating/) and set it to `<IP_WHERE_ALICE_IS_LISTENING>/alice`

     Example:

     ![image](https://cloud.githubusercontent.com/assets/12966925/25574851/72ea088c-2e6f-11e7-9ddf-9512a425729a.png)

### Want to talk to me
Integrate me with [**Hubot**](https://hubot.github.com/docs). It's a talkative bot and all you need to know is a little bit of [CoffeScript](http://coffeescript.org/) and [Regular Expressions](https://www.w3schools.com/js/js_regexp.asp)
You can use alice with hubot to route tasks to and fro.
- To use alice with hubot, [add/edit coffee scripts in the scripts folder](https://github.com/github/hubot/blob/master/docs/scripting.md)

Yay! all set. let's rock

----------------------
 <center> <img src="https://cloud.githubusercontent.com/assets/12966925/25533071/ffc4f7c8-2c4c-11e7-9308-ae295a9f34b7.gif" alt="Drawing" style="width: 100px;"/> </center>

----------------------

### Willing to Contribute
Please read [CONTRIBUTING.md](https://github.com/moengage/alice/tree/master/.github/CONTRIBUTING.md) before submitting your pull requests.
If you'd like to chat, stop by our slack team [joinalice](https://joinalice.slack.com/messages)

### Future plan
- More Features
  - Notify QA signOff
  - Notify Code Freeze

- Continuous Integration
- More Adapters like with HipChat, BitBucket. If you are using these or any other version control or communication tools, please come, let's discuss & [build it together](https://github.com/moengage/alice/blob/master/.github/CONTRIBUTING.md#32-adding-more-adapters)


### Credits
- Problems at work :smile:
- [Hitesh Mantrala](https://github.com/hittudiv) for giving it a start.
- [Akshay Goel](https://github.com/akgoel-mo) for the incessant support.
- [Satyanarayan Saini](https://github.com/satyamoengage) & [Yashwanth Kumar](https://github.com/yashwanth2) for having faith in me.
- Team [MoEngage](http://moengage.com/) for helping me pass through User Acceptance Testing.
- Jenkins Community for ideas
- [GitHub Api docs](https://developer.github.com/)
- [Slack Api docs](https://api.slack.com/)
- [Hubot community](https://github.com/github/hubot)


