README for Pylint - http://www.pylint.org/
==========================================

alice is a bot specialised to do codebase supervising on your behalf to prevent Chaos situation in SDLC cycle.

how do you do it alice?

.. image:: https://cloud.githubusercontent.com/assets/12966925/25533071/ffc4f7c8-2c4c-11e7-9308-ae295a9f34b7.gif

I'm being made with <3 for spreading love among teams (i.e. developers, qa can be friends, o yes!)

Why do I exist
--------------
Recall a Release Day @ your workplace and some of the features started breaking all of a sudden, tested features are not working anymore, its going to take time to figure out whom to reach & people start passing the buck?

.. image:: https://s3.amazonaws.com/qa-ops/no.gif


Experienced such stormy sail on your release day?
Amidst all this, losing time for release deployment as the traffic on your product is peaking up or exceeding the deadline promised to the clients. Manual monitoring wasn’t a solution as it isn’t scalable?
- Already nodding your head in agreement ? Many times somewhere deep down, did you feel like escaping from the heated discussion or wished there were snapshots of all the important events which could give you the clues/traceback to hunt & chuck the wrong commits out of the system and move ahead. Or even better some software which you could just hook to your system which would never let us reach such a chaotic state itself by blocking/notifying any wrong doings.
- Or are you someone just starting off your company and do not want to go through the same challenges we went through & help your developers focus only on building the awesome stuff which you wanted to


How do I solve the problems
---------------------------
I help the teams "preventing last moment panic moments" by:
- monitoring/reminding/blocking/alerting teams/individuals to maintain code hygiene
- enabling every member in team to get any info about the system @ any time
- enabling saving some brains whose most of the work time goes in answering same questions about the system
- having a trustworthy 24x7 code monitoring system from dev to release phase which can prevent & alert for any unhealthy action for the code


Want to hire me
---------------
1. Install: pip install alice-pro
2. Start:

  2.1 setup your config file

  2.2 execute

  * direct as flask app ::
       export FLASK_APP='alice/main/actor.py' config='config.json'; flask run --host 0.0.0.0 --port 5005


  * as a uwsgi process ::
          export config="config.json"; uwsgi --socket 0.0.0.0:5005 --protocol=http -w alice.main.actor --callable app


  * Note: can change port number as needed