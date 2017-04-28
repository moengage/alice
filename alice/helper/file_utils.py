import os
import yaml
import simplejson as json

def get_dict_from_config_file(file_path):
    if file_path.endswith(".yaml"):
        data = get_dict_from_yaml(file_path)
    elif file_path.endswith(".json"):
        with open(file_path) as data_file:
            data = json.load(data_file)
    else:
        raise Exception("The config file should be either yaml or json type")
    return data


def get_dict_from_yaml(file_path):
    data = {}
    with open(file_path, 'r') as stream:
        try:
            data = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return data


def write_to_file_from_top(file_path, msg):
    dir_path = file_path.rpartition("/")[0]
    try:
        os.makedirs(dir_path)
    except:
        if not os.path.isdir(dir_path):
            raise
    with open(file_path, "r+") as f:
        first_line = f.readline()
        lines = f.readlines()
        f.seek(0)
        f.write(msg)
        f.write("\n" + first_line)
        f.writelines(lines)
        f.close()


def write_to_file(file_path, msg):
    dir_path = file_path.rpartition("/")[0]  # partitions from last occurence
    try:
        os.makedirs(dir_path)
    except:
        if not os.path.isdir(dir_path):
            raise
    with open(file_path, "a+") as f:
        f.write(msg + '\n')
        f.close()



def clear_file(file):
    open(file, 'w').close()