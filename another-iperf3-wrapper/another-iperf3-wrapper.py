#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import re
import json
import logging
import os
import sys

from rich import print

import bufferbloat
import args
import common
import probe
import bdp


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


def generate_cmds(base_cmd, cmds_args):
    """from given iperf3 args generate commands

    Args:
        cmds_args (list): list of arguments for iperf3 commands

    Returns:
        cmd: commands list
    """
    # generate command
    cmds = []
    for cmd_args in cmds_args:
        cmd = base_cmd
        for arg in cmd_args:
            cmd += f" {arg}"
            cmd.strip()
        cmds.append(cmd)
    return cmds


def expand_cmds_args(cmds_args):
    """expand numeric values from list and range on args

    Args:
        cmds_args (dict): arguments to expand

    Returns:
        dict: arguments expanded
    """
    cmds_args_expanded = {}
    new_arg_value = []
    for arg, value in cmds_args.items():
        new_arg_value = []
        # split if ',' else return list
        value = value.split(",") if "," in value else [value]
        for v in value:
            if "-" in v:
                # try to expand numerical range
                try:
                    range_n = v.split("-")
                    new_v = [
                        str(element)
                        for element in list(range(int(range_n[0]), int(range_n[1])))
                    ]
                    new_arg_value.extend(new_v)
                except Exception as e:
                    log.debug(f"Exception: {e}")
                    log.warning(f"seems not a valid range: {range_n}")
                    new_arg_value.append(v)
            else:
                new_arg_value.append(v)
        # save new value
        cmds_args_expanded[arg] = new_arg_value

    log.debug(f"arguments expanded: {cmds_args_expanded}")

    return cmds_args_expanded


def generate_cmds_args(cmds_args_expanded):
    """generate all possible commands by given arguments

    Args:
        cmds_args_expanded (dict): expanded arguments

    Returns:
        list: given arguments return list of possible commands
    """

    ls = []
    for arg, value in cmds_args_expanded.items():
        arg_list = []
        for v in value:
            arg_list.append(f"{arg} {v}")
        ls.append(arg_list)

    cmds_args_all_permutations = list(itertools.product(*ls))
    log.debug(f"generated commands: {cmds_args_all_permutations}")
    return cmds_args_all_permutations


def check_port_arg(arg_port):
    port_list = []
    try:
        port_list = [int(arg_port)]
    except ValueError:
        log.debug(f"ValuError: {arg_port}")
        range_char = [",", "-"]
        is_range = any([char in arg_port for char in range_char])
        if is_range:
            if "," in arg_port:
                ranges = arg_port.split(",")
            else:
                ranges = [arg_port]

            for r in ranges:
                r_count_sep = r.count("-")
                if r_count_sep == 1:
                    start_port, end_port = r.split("-")
                    try:
                        port_list_range = list(
                            range(int(start_port), int(end_port) + 1)
                        )
                        if port_list_range:
                            port_list.extend(port_list_range)
                        else:
                            log.debug(f"Not a valid range: {start_port} -> {end_port}")
                    except ValueError:
                        log.debug(f"Not a valid number: {r}")

                elif r_count_sep == 0:
                    try:
                        port_list.append(int(r))
                    except ValueError:
                        log.debug(f"Not a valid number: {r}")
                else:
                    log.debug(f"range invalid: {r}")
    log.debug(f"port list: {port_list}")

    return port_list


def main():
    """main run

    Args:
        args (obj): main program obj
    """

    if not args.obj.host:
        log.error("No valid host, please set a host with argument '-c'  \nexit")
        exit(0)

    if args.obj.description:
        args.obj.description += "_"

    common.data["port_list"] = check_port_arg(args.obj.port)

    cmds_args = {
        "-c": args.obj.host,
        "-p": str(common.data["port_list"][0]),
        "-t": args.obj.time,
        "-P": args.obj.parallel,
        "-J": "",
    }

    if args.obj.reverse:
        cmds_args["-R"] = ""

    cmds_args_expanded = expand_cmds_args(cmds_args)
    cmds_args_generated = generate_cmds_args(cmds_args_expanded)
    common.data["commands"] = generate_cmds("iperf3", cmds_args_generated)

    if args.obj.cmd == "bdp":
        bdp.bdp_run()

    if args.obj.cmd == "probe" and args.obj.host:
        probe.probe_run()

    if args.obj.cmd == "bufferbloat":
        bufferbloat.bufferbloat_run()

    # default iperf run
    if not args.obj.cmd:
        if not args.obj.no_probe and not args.obj.dry_run:
            free_ports = common.probe_iperf3(
                args.obj.host, common.data["port_list"], required_ports=1
            )

            cmd = common.data["commands"][0]
            cmd = re.sub(
                r"-p\s+\d+\s",
                f"-p {free_ports[0]} ",
                cmd,
            )

        scenario_cmds = {
            cmd: 0.1,
        }

        output_commands = common.run_commands(scenario_cmds)

        output_commands = common.parse_output_commands(output_commands)

        print(output_commands) if log.level in (10, 20) else None

        parsed_data = common.parse_iperf3_intervals(output_commands)

        for k, v in parsed_data.items():
            fn = f"{args.obj.result_dst_path}{common.get_str_cmd(cmd)}_{k}_{common.get_timestamp_now()}.csv"
            common.save_CSV(fn, v[0].keys(), v)


if __name__ == "__main__":

    config = {}
    try:
        config_file = "~/.config/another-iperf3-wrapper/another-iperf3-wrapper.json"

        expanded_config_file = os.path.expanduser(config_file)

        with open(expanded_config_file, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"FileNotFoundError: could not load config file: {config_file}")

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
    log.debug(f"config: \n{config}")

    main()
