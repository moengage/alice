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