README for Alice
==========================================

Alice is a bot specialised to do codebase supervising on your behalf to prevent Chaos situation in SDLC cycle.

INSTALL
-------
Installing is simple
 ``pip install alice-pro``


How to use
----------
  1. `setup your config file <https://github.com/moengage/alice/docs/setup_config.md>`_

  2. To start alice:

  * direct as flask app ::
       export FLASK_APP='alice/main/actor.py' config='config.json'; flask run --host 0.0.0.0 --port <PORT_NO>

  * as a uwsgi process ::
        export config="config.json"; uwsgi --socket 0.0.0.0:<PORT_NO> --protocol=http -w alice.main.actor --callable app

  * Note: can change port number as needed, default is '5000'

  3. `Create web-hook in github <https://developer.github.com/webhooks/creating/>`_ set it to <IP_WHERE_ALICE_IS_LISTNING>/alice


Wh questions
------------
`What, what & how about Alice <https://github.com/moengage/alice/blob/master/README.md>`_

Who can use on the fly
----------------------
Github & Slack users


Willing to contribute
---------------------
`how to contribute <https://github.com/moengage/alice/CONTRIBUTING.md>`_
