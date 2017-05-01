while running alice, you need to pass your team specific config to help alice take better decisions
all you to do is download the sample config file and pass it with `--config` flag
Ex.
-  direct as flask app
      `export FLASK_APP="alice/main/actor.py" config="config.yml"; flask run --host 0.0.0.0 --port 5005`
   -  as a uwsgi process
      `export config="config.json"; uwsgi --socket 0.0.0.0:5005 --protocol=http -w alice.main.actor --callable app`
   - Note: can change port number as needed

*Note:* config file name should be ending with `.yml` or `.json`


- Easy yaml way
  - just [download sample](https://github.com/moengage/alice/blob/master/docs/config.yml)
  - set your tokens, repo specific and checks you wish to enable

- For json lovers:
   - just [download sample](https://github.com/moengage/alice/blob/master/docs/config.json)
   - set your tokens, repo specific and checks you wish to enable

