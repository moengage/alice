while running alice, you need to pass your team specific config to help alice take better decisions
all you need to do is download the sample config file and pass it with `--config` flag

Ex.
 Modify the commands with particular **config.yaml** or **config.json** file path & port number
   -  run as flask app

      ```
      SITE_PATH=`python -c "import site; print site.getsitepackages()[0]"`;
      export FLASK_APP=$SITE_PATH"/alice/main/actor.py" config='GIVE_PATH_TO_YOUR_config.yaml'; flask run --host 0.0.0.0 --port 5005
      ```
   -  run as uwsgi process

      ```
      export config="config.yaml"; uwsgi --socket 0.0.0.0:5005 --protocol=http -w alice.main.actor --callable app
      ```
      
*Note:* config file name should be ending with `.yml` or `.json`

#### Config file required changes:
1. set your tokens, repo specific data and checks you wish to enable
2. github vs slack user name mappings (if writing manually is huge then follow [this](https://gist.github.com/p00j4/18be94b7261ff564d13241d0899f7101) to get individually automactically and just copy paste in right places)

- Easy yaml way (with all hints on what to fill in)
  - just [download sample](https://github.com/moengage/alice/blob/master/docs/config.yml)
  
- For json lovers:
   - just [download sample](https://github.com/moengage/alice/blob/master/docs/config.json)
   
- edit->save and keep your config file in a safe place and use this path in alice execution command
   

