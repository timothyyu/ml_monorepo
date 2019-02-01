import argparse
import os
parser = argparse.ArgumentParser()
parser.add_argument("--dir", help="the root directory", type=str, default='.')
args = parser.parse_args()
root = args.dir
folders = []
data_dir = root + "/data"
folders.append(data_dir)
folders.append(data_dir + "/all")
folders.append(data_dir + "/all_graphs")
folders.append(data_dir + "/hl")
folders.append(data_dir + "/locates")
folders.append(data_dir + "/raw")
folders.append(data_dir + "/blotter")
folders.append(data_dir + "/opt")

for i in range(len(folders)):
    dir = folders[i]
    if not os.path.exists(dir):
        os.makedirs(dir)
print("A directory structure is created under %s" % root)

