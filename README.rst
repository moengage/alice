README for Alice
==========================================

Alice is a bot specialised to do codebase supervising on your behalf to prevent chaos situation in any layer of SDLC cycle.

INSTALL
-------

Installing is simple via pip ::
         ``pip install alice-core``

How to use
----------
  1. Give your team specific input `setup your config file <https://github.com/moengage/alice/blob/master/docs/setup_config.md>`_

  2. Start Alice (any 1 way):

  * **run as flask app** ::
       export FLASK_APP='alice/main/actor.py' config='config.yaml'; flask run --host 0.0.0.0 --port <PORT_NO>

  * **run as uwsgi process** ::
        export config="config.yaml"; uwsgi --socket 0.0.0.0:<PORT_NO> --protocol=http -w alice.main.actor --callable app

   **Note:** can change port number as needed, default is '5000'

  3. Create `web-hook in github <https://developer.github.com/webhooks/creating/>`_ set it to <IP_WHERE_ALICE_IS_LISTNING>/alice
  Example:

  .. image:: https://cloud.githubusercontent.com/assets/12966925/25573710/925362ea-2e65-11e7-93db-fa3f261f81dc.png
     :width: 250pt


Wh questions
------------
`why, what & how about Alice <https://github.com/moengage/alice/blob/master/README.md>`_

Who can use on the fly
----------------------
Github & Slack users
If you are using other projects, look at "how to contribute" section

Willing to contribute
---------------------
contributing `guidelines <https://github.com/moengage/alice/tree/master/.github/CONTRIBUTING.md>`_
