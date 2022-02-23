#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO:
# - Add Logging
# - Comment & Docstring

import datetime
import itertools
import re
import json
import csv
import logging
import os
import sys

import arg_parse

import time
from subprocess import Popen, PIPE, check_output

from rich import print

# get main logger
log = logging.getLogger("another-iperf3-wrapper")


def setup_logger(logging_level):

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


def get_timestamp_now(fmt="%Y%m%d-%H%M%S"):
    """generate timestamp to now

    Args:
        fmt (str, optional): format for timestamp. Defaults to "%Y%m%d-%H%M%S".

    Returns:
        str: timestamp with selected format
    """
    return datetime.datetime.now().strftime(fmt)


def execute_cmd_bg_save_output(cmd, write_mode="w", outputfile=""):

    with open(outputfile, write_mode) as f:
        Popen(cmd.split(), stdout=f)  # This will run in the background


def probe_iperf3(host, ports_list, required_ports=2):
    log.info(
        f"start probing for available iperf3 ports - port range: {ports_list[0]} - {ports_list[-1]} | amount of required ports: {required_ports}"
    )
    available_ports = []
    for port in ports_list:
        cmd = f"iperf3 -4 -c {host} -t 1 -P 1 -p {port} --connect-timeout 500"
        try:
            log.debug(f"probing port {port}")
            result = check_output(cmd, universal_newlines=True, shell=True)
            if "iperf Done." in result:
                available_ports.append(port)
            if len(available_ports) == 2:
                break
        except Exception as e:
            print(f"exception: {e}")
    if len(available_ports) < required_ports:
        print("not enough ports to run tests")
        exit(1)
    log.info(
        f"probe finished - following port available to be used => {available_ports}"
    )
    return available_ports


def generate_iperf3_cmds(cmds_args_iperf3):
    # generate command
    cmds = []
    for cmd_args in cmds_args_iperf3:
        cmd = f"iperf3"
        for arg in cmd_args:
            cmd += f" {arg}"
            cmd.strip()
        cmds.append(cmd)
    return cmds


def expand_iperf3_args(args_iperf3):
    args_iperf3_expanded = {}
    for arg, value in args_iperf3.items():
        value = value.split(",") if "," in value else [value]
        for v in value:
            if "-" in v:
                range_n = v.split("-")
                new_value = list(range(int(range_n[0]), int(range_n[1])))
            else:
                new_value = value
        args_iperf3_expanded[arg] = new_value
    return args_iperf3_expanded


def generate_iperf3_cmds_args(args_iperf3_expanded):
    l = []
    for arg, value in args_iperf3_expanded.items():
        arg_list = []
        for v in value:
            arg_list.append(f"{arg} {v}")
        l.append(arg_list)

    args_iperf3_all_permutations = list(itertools.product(*l))
    return args_iperf3_all_permutations
    # print(args_iperf3_all_permutations)


def run_commands(commands):
    processes = {}
    output = {}
    if not args.dry_run:
        for cmd, sleep_time in commands.items():
            processes[cmd] = Popen(cmd.split(), stdout=PIPE, universal_newlines=True)
            time.sleep(sleep_time)
        for t in range(1, args.timeout):
            for cmd, process in processes.items():
                if not process.poll() is None:
                    # print(process.stdout.read())
                    output[cmd] = process.stdout.read()
                    del processes[cmd]
                    break
                else:
                    time.sleep(0.1)
            if not processes:
                break
            time.sleep(1)
    else:
        with open(
            "samples/iperf3_c172.16.1.238_p5201_t5_P10_J_20220222-170451.json",
            "r",
        ) as f:
            output["iperf3 -c 172.16.1.238 -p 5201 -t 5 -P 10 -J   "] = f.read()

        with open(
            "samples/iperf3_c172.16.1.238_p5201_t5_P10_J_R_20220222-170451.json",
            "r",
        ) as f:
            output["iperf3 -c 172.16.1.238 -p 5201 -t 5 -P 10 -J  -R "] = f.read()

        with open(
            "samples/ping172.16.1.238_c15_D_20220222-170451.log",
            "r",
        ) as f:
            output["ping 172.16.1.238 -c 15 -D"] = f.read()
    return output


def parse_ping_output(output):
    output_lines = output.split("\n")

    stats = {}
    stats.update(
        re.match(
            r"(?P<pckts_tx>\d+) packets transmitted, (?P<pckts_rx>\d+) received, (?P<pckts_loss_perc>[\d\.]+)% packet loss, time (?P<time>\d+)ms",
            output_lines[-3],
        ).groupdict()
    )
    stats.update(
        re.match(
            r"rtt min/avg/max/mdev = (?P<rtt_min>[\d\.]+)/(?P<rtt_avg>[\d\.]+)/(?P<rtt_max>[\d\.]+)/(?P<rtt_mdev>[\d\.]+) ms",
            output_lines[-2],
        ).groupdict()
    )
    pckts_stats_line_cnt = int(stats["pckts_tx"]) + 1

    pckts_stats = []
    for pckt_stats_line in output_lines[1:pckts_stats_line_cnt]:
        try:
            pckts_stats.append(
                re.match(
                    r"\[(?P<unix_time>\d+\.\d+)\]\s\d+\sbytes\sfrom\s(?P<target_host>([\d\.]+)):\sicmp_seq=(?P<icmp_seq>\d+)\sttl=(?P<icmp_ttl>\d+)\stime=(?P<icmp_time>([\d\.]+))\sms",
                    pckt_stats_line,
                ).groupdict()
            )
        except:
            print(f"Could not parse : {pckt_stats_line}")

    ping_results = {"stats": stats, "pckts_stats": pckts_stats}
    return ping_results


def save_outputs(filename, output):
    with open(filename, "a") as f:
        f.write(output)


def normalize_dict(keys, dict):
    d = {}
    d.update({k: dict[k] for k in keys if k in dict})
    d.update({k: "" for k in keys if k not in dict})
    return d


def save_CSV(dst_filename, header, csv_content):
    with open(dst_filename, "w") as output_file:
        dict_writer = csv.DictWriter(output_file, header)
        dict_writer.writeheader()
        dict_writer.writerows(csv_content)
        log.info(f"CSV wrote in {dst_filename}")


def main(args):

    runtest_time = get_timestamp_now()

    if args.description:
        args.description += "_"

    args_iperf3 = {
        "-c": args.host,
        "-p": args.port,
        "-t": args.time,
        "-P": args.parallel,
        "-J": "",
        "-R": "",
    }

    args_iperf3_expanded = expand_iperf3_args(args_iperf3)
    cmds_args_iperf3_generated = generate_iperf3_cmds_args(args_iperf3_expanded)
    iperf3_cmds = generate_iperf3_cmds(cmds_args_iperf3_generated)
    commands = iperf3_cmds

    if args.cmd == "bufferbloat":

        if args.port_range:
            try:
                port_range = args.port_range.split("-")
                port_list = list(range(int(port_range[0]), int(port_range[1]) + 1))
                required_ports = 2
            except:
                print("not a valid port range")
                exit(0)
        else:
            port_list = [args.port]
            required_ports = 1

        if required_ports == 1:
            print("not a valid port range | --port-range required ")
            exit(0)

        if "-R" in commands[0]:
            cmd_iperf3_us = commands[0].replace("-R", "")
            cmd_iperf3_ds = commands[0]
        else:
            cmd_iperf3_us = commands[0]
            cmd_iperf3_ds = f"{commands[0]} -R"

        bufferbloat_iperf3_commands = [cmd_iperf3_ds, cmd_iperf3_us]

        if not args.no_probe:
            free_ports = probe_iperf3(args.host, port_list, required_ports)

        for idx, cmd in enumerate(bufferbloat_iperf3_commands):
            bufferbloat_iperf3_commands[idx] = re.sub(
                r"-p\s+\d+\s",
                f"-p {free_ports[idx]} ",
                bufferbloat_iperf3_commands[idx],
            )

        scenario_time = str(int(args.time) + 10)

        scenario_cmds = {
            f"ping {args.host} -c {scenario_time} -D": 5,
            bufferbloat_iperf3_commands[0]: 0.1,
            bufferbloat_iperf3_commands[1]: 0.1,
        }
        for cmd in scenario_cmds.keys():
            log.info(f"commands: {cmd}")

        output_commands = run_commands(scenario_cmds)

        for cmd, output in output_commands.items():
            if "iperf3" in cmd:
                output_commands[cmd] = {
                    "output_parsed": json.loads(output),
                    "type": "iperf3",
                }
                ext = ".json"

            elif "ping" in cmd:
                output_commands[cmd] = {
                    "output_parsed": parse_ping_output(output),
                    "type": "ping",
                }
                ext = ".log"

            if args.save_outputs:
                str_cmd = cmd.replace("-", "_").replace(" ", "")
                fn = f"{args.result_dst_path}{str_cmd}_{runtest_time}{ext}"
                save_outputs(fn, output)

        #
        # Stats
        #

        # Aggregate data
        interval_stats = {}

        summary_stats = {"timestamp": runtest_time}

        for cmd, values in output_commands.items():
            test_error = values["output_parsed"].get("error", False)
            if test_error:
                log.error(f"test invalid - error: {test_error}")
            else:
                if values["type"] == "ping":
                    for pckts_stats in values["output_parsed"]["pckts_stats"]:
                        rounded_timestamp = int(
                            round(float(pckts_stats["unix_time"]), 0)
                        )

                        if not interval_stats.get(rounded_timestamp, False):
                            interval_stats[rounded_timestamp] = {}

                        interval_stats[rounded_timestamp].update(pckts_stats)

                    for stat_name, stat_value in values["output_parsed"][
                        "stats"
                    ].items():
                        summary_stats[f"imcp_{stat_name}"] = stat_value

                if values["type"] == "iperf3":
                    header_prefix = (
                        "DS"
                        if values["output_parsed"]["start"]["test_start"]["reverse"]
                        == 1
                        else "US"
                    )

                    start_ts = values["output_parsed"]["start"]["timestamp"]["timesecs"]
                    for interval in values["output_parsed"]["intervals"]:
                        timestamp = start_ts + int(round(interval["sum"]["start"], 0))

                        if not interval_stats.get(timestamp, False):
                            interval_stats[timestamp] = {}

                        for k, v in interval["sum"].items():
                            interval_stats[timestamp][f"iperf3_{header_prefix}_{k}"] = v

                    summary_stats[f"iperf3_{header_prefix}_bits_per_second"] = int(
                        values["output_parsed"]["end"]["sum_received"][
                            "bits_per_second"
                        ]
                    )

        # Save data into CSV
        keys_sorted = list(sorted(interval_stats.keys()))

        relevant_keys = set(
            [
                "timestamp",
                "iperf3_DS_bits_per_second",
                "iperf3_US_bits_per_second",
                "icmp_time",
            ]
        )
        csv_content = []
        # header = set()
        for k in keys_sorted:
            interval_stats_datapoint = interval_stats[k]
            # print(f"{k}: {interval_stats_datapoint}")
            csv_content_line = {"timestamp": k}
            csv_content_line.update(interval_stats_datapoint)
            # header.update(list(csv_content_line.keys()))
            csv_content_line = normalize_dict(relevant_keys, csv_content_line)
            csv_content.append(csv_content_line)

        relevant_keys = sorted(list(relevant_keys))
        relevant_keys.remove("timestamp")
        relevant_keys.insert(0, "timestamp")

        if args.csv:
            # intervals-stats
            fn = f"{args.result_dst_path}bb-test_intervals-stats_{args.description}{runtest_time}.csv"
            save_CSV(fn, relevant_keys, csv_content)

            # summary-stats
            fn = f"{args.result_dst_path}bb-test_summary-stats_{args.description}{runtest_time}.csv"
            save_CSV(fn, list(summary_stats.keys()), [summary_stats])


if __name__ == "__main__":

    config_file = "~/.config/another-iperf3-wrapper/another-iperf3-wrapper.json"

    expanded_config_file = os.path.expanduser(config_file)

    with open(expanded_config_file, "r") as f:
        config = json.load(f)

    args = arg_parse.arg_parse(config["default"])

    # setup for logging
    if args.no_logging:
        # no log
        logging_level = logging.CRITICAL
    elif args.debug:
        # debug mode
        logging_level = logging.DEBUG
    else:
        # normal mode
        logging_level = logging.INFO

    setup_logger(logging_level)

    log = logging.getLogger("another-iperf3-wrapper")

    log.debug(f"args: \n{args}")

    main(args)
