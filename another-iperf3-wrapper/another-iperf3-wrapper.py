#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import logging
import os
import sys

from rich import print

from modules import bufferbloat, probe, bdp, run_iperf, unidirectional_test, all_tests
from utils import args, common, run_commands, output_operations


# get main logger
log = logging.getLogger("another-iperf3-wrapper")


def setup_logger(logging_level):
    """setup logger for logging

    Args:
        logging_level (obj): logging.CRITICAL|DEBUG|INFO
    """
    # create logger
    logger = logging.getLogger("another-iperf3-wrapper")
    logger.setLevel(logging_level)

    # create console handler and set level to debug
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging_level)

    # create formatter
    formatter = logging.Formatter(
        fmt=(
            "[%(asctime)s.%(msecs)03d][%(levelname)s]"
            "(%(module)s.%(funcName)s) %(message)s"
        ),
        datefmt="%Y%m%d-%H%M%S",
    )

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)


def get_host_list():
    """get host list from config file

    Returns:
        list: host list
    """
    host_list = []
    try:
        # open in app folder the json file contaning list of hosts
        with open(__file__) as f:
            hosts = json.load(f)
            for host in hosts:
                host_list.append(host["host"])

        """with open(common.data["config_file"]) as f:
            for line in f:
                if line.startswith("host:"):
                    host_list.append(line.split(":")[1].strip())
        """
    except Exception as e:
        log.debug(f"Exception: {e}")
        log.warning("No host found in config file")
        return None
    return host_list

def select_host(host_list):
    """select a host from list

    Args:
        host_list (list): list of host
    """
    print("Select a host from list:")
    for i, host in enumerate(host_list):
        print(f"{i+1}) {host}")
    print("0) Exit")
    try:
        host_index = int(input("Select a host: "))
        if host_index == 0:
            return None
        else:
            return host_list[host_index-1]
    except Exception as e:
        log.debug(f"Exception: {e}")
        log.warning("No valid host selected")
        return None

def main():
    """main run

    Args:
        args (obj): main program obj
    """
    
    if not args.obj.host:
        log.warning("No valid host, please set a host with argument '-c'  \nexit")
        exit(0)
        
        # Prototype - ask if user wish to select a host from list
        host_list = get_host_list()
        if host_list:
            host = select_host(host_list)
            if host:
                args.obj.host = host
            else:
                log.warning("No valid host selected, exit")
                exit(0)


    args.obj.test_name = f"{args.obj.test_name}-" if args.obj.test_name else ""

    if args.obj.cmd == "bdp":
        bdp.bdp_run()

    if args.obj.cmd == "probe" and args.obj.host:
        probe.probe_run()

    if args.obj.cmd == "bufferbloat":
        bufferbloat.bufferbloat_run()
        
    if args.obj.cmd == "all":
        all_tests.all_tests_run()

    # default iperf run
    if not args.obj.cmd:
        unidirectional_test.unidirectional_test()
        


if __name__ == "__main__":
    """app entry point"""

    configFileNotFoundError = False
    config = {}
    try:
        # default config file
        config_file = "~/.config/another-iperf3-wrapper/another-iperf3-wrapper.json"

        expanded_config_file = os.path.expanduser(config_file)

        with open(expanded_config_file, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        configFileNotFoundError = True

    args.obj = args.arg_parse(config.get("default", {}))
    # args_dict = vars(common.args)

    # setup for logging
    if args.obj.no_logging:
        # no log
        logging_level = logging.CRITICAL
    elif args.obj.debug:
        # debug mode
        logging_level = logging.DEBUG
    else:
        # normal mode
        logging_level = logging.INFO

    setup_logger(logging_level)

    log = logging.getLogger("another-iperf3-wrapper")

    log.debug(f"args: \n{args.obj}")

    if configFileNotFoundError:
        log.debug(f"FileNotFoundError: could not load config file: {config_file}")
    else:
        log.debug(f"config: \n{config}")

    main()
