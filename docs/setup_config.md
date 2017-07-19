## Setup your team specific configurations
While running alice, you need to pass your team specific configurations to help alice take better decisions.

**Steps:** 

1. **Download** the sample[config](https://github.com/moengage/alice/blob/master/docs/samples/config.yaml) file
click on `raw` -> save file (ctrl/cmd+s) -> remove `.text` from end -> edit as per need -> save your config file at a safe path and use this path in alice execution command

*Note:* config file name should be ending with `.yaml` or `.json`

2. **Modify** the config:
Modify the sample file as per your team settings as the instructions given in comments inside the [yaml](https://github.com/moengage/alice/blob/master/docs/samples/config.yaml) file

    **Most important changes:**

    - Set your tokens, repo specific data and checks you wish to enable
    - Give user map properly in GithubName:slackName style (if writing manually is painful then follow [this](https://gist.github.com/p00j4/18be94b7261ff564d13241d0899f7101) to get individually automatically and just copy paste in right places)
    - Your Code Repository specific settings like mainBranch, channel names etc.
    - Set debug key true or false as required.

    **Note** Make sure to set debug False when you go live

    and the config is supported in 2 formats
    - Easy yaml way (with all hints on what to fill in)
      - [sample yaml](https://github.com/moengage/alice/blob/master/docs/samples/config.yaml)
     or
    - For json lovers:
       - [sample json](https://github.com/moengage/alice/blob/master/docs/samples/config.json)


3. **Run**

Pass on the modified config file along with `--config` flag to alice
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
