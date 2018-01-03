import sys
import yaml

config = None
with open(sys.argv[1]) as f:
    config = yaml.load(f)
# print config