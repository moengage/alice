### Setup your team specific configurations
While running alice, you need to pass your [team specific config](https://github.com/moengage/alice/blob/master/docs/samples/config.yml) to help alice take better decisions
all you need to do is [download](https://github.com/moengage/alice/blob/master/docs/setup_config.md#config-file-required-changes) the sample config file, modify it and pass it with `--config` flag to alice

Eg.
  Modify the commands with particular **config.yaml** or **config.json** file path & port number
   -  run as uwsgi process

      	```
      	export config="config.yaml"; uwsgi --socket 0.0.0.0:5005 --protocol=http -w alice --callable app
      	```
      	or
   -  run as flask app

      	```
      	export FLASK_APP=alice config='config.yaml'; flask run --host 0.0.0.0 --port 5005
      	```

   **Note:** can change port number as needed
      
*Note:* config file name should be ending with `.yml` or `.json`

#### Config file required changes:
Download the config file from below link, modify as per your team settings as the instructions given in comments in [yaml](https://github.com/moengage/alice/blob/master/docs/samples/config.yml) file
- Easy yaml way (with all hints on what to fill in)
  - [sample yaml](https://github.com/moengage/alice/blob/master/docs/samples/config.yml)

 or

- For json lovers:
   - [sample json](https://github.com/moengage/alice/blob/master/docs/samples/config.json)
   
**Steps:** download -> edit -> save your config file at a safe path and use this path in alice execution command

**Important changes:**
1. Set your tokens, repo specific data and checks you wish to enable
2. Github vs slack user name mappings (if writing manually is huge then follow [this](https://gist.github.com/p00j4/18be94b7261ff564d13241d0899f7101) to get individually automatically and just copy paste in right places)
3. Your Code Repository specific settings


