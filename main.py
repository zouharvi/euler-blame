import os
import random
import tqdm
import numpy as np
import argparse

random.seed(0)

args = argparse.ArgumentParser()
args.add_argument("--level-true-cutoff", type=int, default=5)
args.add_argument("--level-max", type=int, default=60)
args.add_argument("--rand-prop", type=float, default=0.1)
args.add_argument("--user", default=None)
args = args.parse_args()

BLACKLIST = {"dosdevices/z:/"}

def get_size_count(path, level=0):
    if level > args.level_max or any(x in path for x in BLACKLIST):
        return None

    if os.path.isfile(path) and not os.path.islink(path):
        # return None if it can not be read
        if not os.access(path, os.R_OK):
            return None

        # in GB
        return (os.path.getsize(path) / 1024 / 1024 / 1024, 1)
    elif os.path.isdir(path):
        # return None if it can not be executed (listed)
        if not os.access(path, os.X_OK) or not os.access(path, os.R_OK):
            return None
            
        # in some weird configurations the previous check does not fire
        try:
            children = [os.path.join(path, child) for child in os.listdir(path)]
        except Exception:
            return None
        
        if not children:
            return (0, 0)
        
        # don't do estimation for top directories
        if level > args.level_true_cutoff:
            # select children for which true size will be calculated
            children_true = random.sample(children, k=int(len(children)*(1-args.rand_prop)))
        else:
            children_true = children

        children_true = [get_size_count(child, level+1) for child in children_true]
        children_true = [x for x in children_true if x is not None]
        
        if not children_true:
            return (0, 0)
        avg_size_count = np.average(children_true, axis=0)
        return avg_size_count*len(children)
    else:
        return (0, 0)

def format_output(dir_size, dir_count):
    if dir_size < 1:
        dir_size = "<1GB"
    else:
        dir_size = f"{dir_size:.0f}GB"

    if dir_count < 1000:
        dir_count = "<1k"
    else:
        dir_count = f"{dir_count/1000:.0f}k nodes"
    return f"{dir_size} ({dir_count})"


def get_top_level(path):
    try:
        _get_top_level(path)
    except Exception:
        pass

def _get_top_level(path):
    if not os.path.isdir(path) or path.split("/")[-1].startswith("."):
        return
    out = []
    for x in tqdm.tqdm(
        os.listdir(path),
        desc=f"{path:<40}",
        bar_format='{l_bar}{bar}',
        dynamic_ncols=True,
        leave=False,
    ):
        out.append(get_size_count(os.path.join(path, x), level=1))

    if not out:
        print(f"{path:<40}:", format_output(0, 0))
    else:
        print(f"{path:<40}:", format_output(*np.average(out, axis=0)))

if args.user:
    get_top_level(os.path.join("/cluster/project/sachan/", args.user))
    get_top_level(os.path.join("/cluster/work/sachan/", args.user))
else:
    for user in sorted(os.listdir("/cluster/project/sachan/")):
        get_top_level(os.path.join("/cluster/project/sachan/", user))

    for user in sorted(os.listdir("/cluster/work/sachan/")):
        get_top_level(os.path.join("/cluster/work/sachan/", user))