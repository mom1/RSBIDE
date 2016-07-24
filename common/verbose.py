from RSBIDE.common.config import config

IGNORE = ["dbHelp"]


def log(*args):
    if config["LOG"]:
        print("RSB\t", *args)


def verbose(*args):
    if config["DEBUG"] is True and not args[0] in IGNORE:
        print("RSB\t", *args)


def warn(*args):
    print("RSB -WARNING-\t", *args)
