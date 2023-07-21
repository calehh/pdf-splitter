import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--path", type=str)
parser.add_argument("--output", type=str)
args = parser.parse_args()
path = args.path
output = args.output

with open(path) as f:
    data = f.read()
    print(data.encode("utf-8").decode("unicode_escape"))
