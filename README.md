Hi, I'm alice!

I'm being made with :heart: for spreading love among teams (i.e. developers, qa can be friends, o yes! that is possible having me)

### Why do I exist
Recall a Release Day @ your workplace and some of the features started breaking all of a sudden, tested features are not working anymore, its going to take time to figure out whom to reach & people start passing the buck?
![image](https://s3.amazonaws.com/qa-ops/no.gif) Experienced such stormy sail on your release day?
Amidst all this, losing time for release deployment as the traffic on your product is peaking up or exceeding the deadline promised to the clients. Manual monitoring wasn’t a solution as it isn’t scalable?
- Already nodding your head in agreement ? Many times somewhere deep down, did you feel like escaping from the heated discussion or wished there were snapshots of all the important events which could give you the clues/traceback to hunt & chuck the wrong commits out of the system and move ahead. Or even better some software which you could just hook to your system which would never let us reach such a chaotic state itself by blocking/notifying any wrong doings.
- Or are you someone just starting off your company and do not want to go through the same challenges we went through & help your developers focus only on building the awesome stuff which you wanted to


### How do I solve the problems
I help the teams "preventing last moment panic moments" by:
- monitoring/reminding/blocking/alerting teams/individuals to maintain code hygiene
- enabling every member in team to get any info about the system @ any time
- enabling saving some brains whose most of the work time goes in answering same questions about the system
- having a trustworthy 24x7 code monitoring system from dev to release phase which can prevent & alert for any unhealthy action for the code


### Want to hire me?

1. **Install:** pip install alice-pro
2. **Start:**

   2.1 Give your team specific input [setup your config file](https://github.com/moengage/alice/blob/master/docs/setup_config.md)

   2.2. Start Alice (any 1 way is fine):
   -  run as flask app
      `export FLASK_APP='alice/main/actor.py' config='config.yaml'; flask run --host 0.0.0.0 --port <PORT_NO>`
   -  run as uwsgi process
      `export config="config.yaml"; uwsgi --socket 0.0.0.0:<PORT_NO> --protocol=http -w alice.main.actor --callable app`

    **Note:** can change port number as needed

   2.3 Plug it in with your system
   - test locally with any pull request payload:
     ```
     http://0.0.0.0:<PORT_NO>
     ```
     it should return "welcome" message
   - activate on your github
     Create [web-hook in github](https://developer.github.com/webhooks/creating/) and set it to <IP_WHERE_ALICE_IS_LISTNING>/alice

     Example:

     ![image](https://cloud.githubusercontent.com/assets/12966925/25573710/925362ea-2e65-11e7-93db-fa3f261f81dc.png)
3. **Want to talk to me as well**
  - integrate me with hubot
    - install [hubot](https://hubot.github.com/docs/)
    - [add/edit coffee scripts in the scripts folder](https://github.com/github/hubot/blob/master/docs/scripting.md)


O yay! all set. let's rock :smile:
![](https://cloud.githubusercontent.com/assets/12966925/25533071/ffc4f7c8-2c4c-11e7-9308-ae295a9f34b7.gif)

### Want to Contribute
Please read [CONTRIBUTING.md](https://github.com/moengage/alice/tree/master/.github/CONTRIBUTING.md) before submitting your pull requests.


### Credits
- [Hitesh Mantrala](https://github.com/hittudiv)
- [Akshay Goel](https://github.com/akgoel-mo)
- [Satya](https://github.com/satyamoengage)
- [GitHub Api docs](https://developer.github.com/)
- [Slack Api docs](https://api.slack.com/)
- [Hubot community](https://github.com/github/hubot)
- Jenkins Community
