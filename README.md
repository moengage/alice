### Alice
A bot for code monitoring and more
________________________________

Hi, I'm alice, made with :heart: for spreading love among teams (i.e. developers, qa can be friends, o yes! that is possible having me)

I can be your assistant who monitors flow of the code in order to prevent mistakes in your Software Development Life Cycle.

This repository provides a library that's distributed by `pip` that you can use for building your own inhouse robot mate.
In most cases, you'll probably never have to hack on this repo directly. But if you do, check out [CONTRIBUTING.md](https://github.com/p00j4/alice/blob/master/.github/CONTRIBUTING.md)


### How I do it
I help teams "preventing last moment panic moments" by:
- monitoring/reminding/blocking/alerting teams/individuals to maintain code hygiene
- enabling every member in team to get any info about the system @ any time
- enabling saving some brains whose most of the work time goes in answering same questions about the system
- having a trustworthy 24x7 code monitoring system from dev to release phase which can prevent & alert for any unhealthy action for the code

### Current Features
For all sensitive branches (Ex. master, qa, develop)
- Tech Review
- Comment branch specific guidelines
- Remind release guideline on merge
- Auto close dangerous Pull Request
- Alert for sensitive file(s) modified
- Notify channel on merge
- Notify lead on given action
- Your own Check Implementer


### Want to hire me

1. **Installation:** 
   ```
   pip install alice-core
   ```
2. **Getting Started:**

   2.1 Create your team specific input config file [setup config file](https://github.com/moengage/alice/blob/master/docs/setup_config.md)

   2.2. Start Alice (any 1 way):

   Modify the commands with particular config.yaml or config.json file path & port number
 	-  run as uwsgi process

      	```
      	export config="config.yaml"; uwsgi --socket 0.0.0.0:5005 --protocol=http -w alice.main.actor --callable app
      	```
 	-  run as flask app

      	```
      	export FLASK_APP=alice.main.actor config='config.yaml'; flask run --host 0.0.0.0 --port 5005
      	```
      
       **Note:** can change port number as needed

   2.3 Plug it in with your system
   - test locally with any pull request payload:
     ```
     http://0.0.0.0:<GIVE_PORT_NO>
     ```
     it should return "welcome" message
   - activate on your github
     Create [web-hook in github](https://developer.github.com/webhooks/creating/) and set it to <IP_WHERE_ALICE_IS_LISTNING>/alice

     Example:

     ![image](https://cloud.githubusercontent.com/assets/12966925/25574851/72ea088c-2e6f-11e7-9ddf-9512a425729a.png)
3. **Want to talk to me as well**
  - integrate me with hubot
    - install [hubot](https://hubot.github.com/docs/)
    - [add/edit coffee scripts in the scripts folder](https://github.com/github/hubot/blob/master/docs/scripting.md)



 Yay! all set. let's rock 

----------------------
 <center> <img src="https://cloud.githubusercontent.com/assets/12966925/25533071/ffc4f7c8-2c4c-11e7-9308-ae295a9f34b7.gif" alt="Drawing" style="width: 100px;"/> </center>

----------------------

### Want to Contribute
Please read [CONTRIBUTING.md](https://github.com/moengage/alice/tree/master/.github/CONTRIBUTING.md) before submitting your pull requests.
If you'd like to chat, drop by [joinalice](https://joinalice.slack.com/messages) on slack channel

### Future in plan
- More Features
  - Notify QA signOff
  - Notify Code Freeze

- Continuous Integration

### Credits
- [Hitesh Mantrala](https://github.com/hittudiv)
- [Akshay Goel](https://github.com/akgoel-mo)
- [Satya](https://github.com/satyamoengage)
- [GitHub Api docs](https://developer.github.com/)
- [Slack Api docs](https://api.slack.com/)
- [Hubot community](https://github.com/github/hubot)
- Jenkins Community
