README for Alice
==========================================

Alice is a bot specialised to do codebase supervising on your behalf to prevent chaos situation in any layer of SDLC cycle.

Install
-------

Installing is simple via pip
  **pip install alice-core**

How to use
----------
  1. Create your team specific input config file `setup your config file <https://github.com/moengage/alice/blob/master/docs/setup_config.md>`_

  2. Start Alice (any 1 way):

    modify the commands for particular config.yaml or config.json file path & port number
    * **run as flask app**
       SITE_PATH=`python -c "import site; print site.getsitepackages()[0]"`
       export FLASK_APP=$SITE_PATH"/alice/main/actor.py' config='config.yaml'; flask run --host 0.0.0.0 --port <GIVE_ORT_NO>

    * **run as uwsgi process**
        export config="config.yaml"; uwsgi --socket 0.0.0.0:<GIVE_PORT_NO> --protocol=http -w alice.main.actor --callable app

    **Note:** default port number is '5000' if not specified

  3. Create `web-hook in github <https://developer.github.com/webhooks/creating/>`_ set it to <IP_WHERE_ALICE_IS_LISTNING>/alice
  Example:

  .. image:: https://cloud.githubusercontent.com/assets/12966925/25574851/72ea088c-2e6f-11e7-9ddf-9512a425729a.png
     :width: 300px
     :height: 100px


Wh questions
------------
why, what & how `about Alice <https://github.com/moengage/alice/blob/master/README.md>`_


Who can use alice on the fly
----------------------------
Github & Slack users
If you are using other projects, look at "how to contribute" section


Willing to contribute
---------------------
Contributing `guidelines <https://github.com/moengage/alice/tree/master/.github/CONTRIBUTING.md>`_


Bugs/Requests
-------------
Please use the GitHub `issue <https://github.com/moengage/alice/issues/>`_ tracker to submit bugs or request features.


Changelog
---------
Consult the Changelog `page <https://github.com/moengage/alice/blob/master/changes.md>`_ for fixes and enhancements of each version.