### Alice
A bot for code monitoring and more...
________________________________

Hi, I'm alice, made with :heart: on top of [python](https://www.python.org/) using [Flask](http://flask.pocoo.org/) for preventing last minute chaos situation and improving Quality Assurance (Oh yes! it is possible having me)

I'm your friendly robot sidekick. Install me in your company to dramatically improve teams' efficiency.

### Why Me
Use me if:
- You are facing last minute panic moments like
  - Sudden breaking of features or you are about to release and bump into new bugs all of a sudden and it takes very long to figure out whom to reach out to get the fix faster and move ahead.
- Or you want to bring a free automated solution which can improve the collaboration and productivity of your team by leaving code supervising tasks on it.
**Note** current implementation is for [Github](https://github.com/) & [Slack](https://slack.com/) users however I'm open to expand it more. Please Read [here](https://github.com/moengage/alice#want-to-contribute) to go ahead

### What I do
I can be your assistant who can monitor code flow, right from development to release phases which help you preventing mistakes in your entire Software Development Life Cycle.

This repository provides a library that's distributed by [pip](https://pypi.python.org/pypi/alice-core) that you can use for building your own in-house robot mate.
In most cases, you'll probably never have to hack on this repo directly. But if you do, check out [CONTRIBUTING.md](https://github.com/p00j4/alice/blob/master/.github/CONTRIBUTING.md)

### How I do it
I help teams "preventing last moment panic moments" by:
- Monitoring/reminding/blocking/alerting teams/individuals to maintain code hygiene
- Enabling every member in team to get any info about the system @ any time
- Enabling saving some brains whose most of the work time goes in answering same questions about the system
- Having a trustworthy 24x7 code monitoring system from dev to release phase which can prevent & alert for any unhealthy action for the code

### Current Features
For all sensitive branches (Eg. master, qa, develop)
- [Code Review](https://github.com/moengage/alice/blob/master/docs/checks.md#code-review)
- [Remind team](https://github.com/moengage/alice/blob/master/docs/checks.md#remind-duidelines) members to follow Guidelines
- [Auto close](https://github.com/moengage/alice/blob/master/docs/checks.md#auto-close-pull-request) suspicious Pull Request
- Alerts on modification of [sensitive file(s)](https://github.com/moengage/alice/blob/master/docs/checks.md#alerts-to-devops-for-modification-of-sensitive-file(s))
- Notify on specific [action on a Pull Request](https://github.com/moengage/alice/blob/master/docs/checks.md#notify-on-commits)
- Your own [check implementer](https://github.com/moengage/alice/blob/master/docs/extend_alice.md#adding-more-checks)


### Want to hire me

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

     - Create [web-hook in github](https://developer.github.com/webhooks/creating/) and set it to <IP_WHERE_ALICE_IS_LISTNING>/alice

     Example:

     ![image](https://cloud.githubusercontent.com/assets/12966925/25574851/72ea088c-2e6f-11e7-9ddf-9512a425729a.png)

### Want to talk to me
  - integrate me with hubot
    Hubot is a talkative bot, all you need is to know a little bit of [CoffeScript](http://coffeescript.org/) and [Regular Expressions](https://www.w3schools.com/js/js_regexp.asp) to start with
    and the same you can plug with alice to route tasks to/from it as per need.
    - install [hubot](https://hubot.github.com/docs/)
    - [add/edit coffee scripts in the scripts folder](https://github.com/github/hubot/blob/master/docs/scripting.md)



 Yay! all set. let's rock 

----------------------
 <center> <img src="https://cloud.githubusercontent.com/assets/12966925/25533071/ffc4f7c8-2c4c-11e7-9308-ae295a9f34b7.gif" alt="Drawing" style="width: 100px;"/> </center>

----------------------

### Willing to Contribute
Please read [CONTRIBUTING.md](https://github.com/moengage/alice/tree/master/.github/CONTRIBUTING.md) before submitting your pull requests.
If you'd like to chat, stop by our slack team [joinalice](https://joinalice.slack.com/messages)

### Future in plan
- More Features
  - Notify QA signOff
  - Notify Code Freeze

- Continuous Integration

### Credits
- [Hitesh Mantrala](https://github.com/hittudiv)
- [Akshay Goel](https://github.com/akgoel-mo)
- [Satya](https://github.com/satyamoengage) & [Yashwanth](https://github.com/yashwanth2)
- Jenkins Community
- [GitHub Api docs](https://developer.github.com/)
- [Slack Api docs](https://api.slack.com/)
- [Hubot community](https://github.com/github/hubot)


