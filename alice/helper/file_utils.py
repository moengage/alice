import os
import yaml
import simplejson as json


def get_dict_from_config_file(file_path):
    if file_path.endswith(".yaml"):
        data = get_dict_from_yaml(file_path)
    elif file_path.endswith(".json"):
        try:
            with open(file_path) as data_file:
                data = json.load(data_file)
        except Exception as e:
            print "\nPlease validate your config file, if it is correct. Can use https://jsonlint.com/ to debug quicker"
            raise (e)
    else:
        raise Exception("Config Format mismatch: The config file should be either yaml or json type")
    return data


def get_dict_from_yaml(file_path):
    data = {}
    with open(file_path, 'r') as stream:
        try:
            data = yaml.load(stream)
        except yaml.YAMLError as exc:
            print "\nPlease validate your config file, if it is correct. Can use http://www.yamllint.com/ to debug quicker"
            raise (exc)
    return data


def write_to_file_from_top(file_path, msg):
    create_if_not_found(file_path)
    with open(file_path, "r+") as f:
        first_line = f.readline()
        lines = f.readlines()
        f.seek(0)
        f.write(msg)
        f.write("\n" + first_line)
        f.writelines(lines)
        f.close()

def read_from_file(file_name):
    with open(file_name) as f:
        contents = f.read()
        f.close()
    return contents

def append_to_file(file_path, msg):
    create_if_not_found()
    with open(file_path, "a+") as f:
        f.write(msg + '\n')
        f.close()


def create_if_not_found(file_name):
    if not os.path.exists(os.path.dirname(file_name)):
        try:
            os.makedirs(os.path.dirname(file_name))
        except OSError as exc:  # Guard against race condition
            if exc.errno != exc.errno.EEXIST:
                raise
    if not os.path.exists(file_name):
        open(file_name, 'w').close()


def clear_file(_file):
    print "************** CLEARNING FILE=" +_file
    open(_file, 'w').close()

