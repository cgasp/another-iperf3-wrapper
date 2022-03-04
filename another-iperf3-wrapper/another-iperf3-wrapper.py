#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO:
# - Add Logging
# - Comment & Docstring

from asyncio import subprocess
import datetime
import itertools
import re
import json
import csv
import logging
import os
import sys
import statistics

import arg_parse

import time
from subprocess import Popen, PIPE, check_output, run

from rich import print

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


def get_timestamp_now(fmt="%Y%m%d-%H%M%S"):
    """generate timestamp to now

    Args:
        fmt (str, optional): format for timestamp. Defaults to "%Y%m%d-%H%M%S".

    Returns:
        str: timestamp with selected format
    """
    return datetime.datetime.now().strftime(fmt)


def parse_text_to_list(regex, text):
    """parse given 'text' with given 'regex' and return list of matches

    Args:
        regex (r-str): regex
        text (str): text to parse

    Returns:
        list: with dict of matches
    """
    # rex = re.compile(regex, re.MULTILINE)
    # result = rex.search(text).groupdict()

    matches = re.finditer(regex, text, re.MULTILINE)

    matches_list = []
    for match in matches:
        matches_list.append(match.groupdict())

    return matches_list


def probe_iperf3(host, ports_list, required_ports=2):
    """function to probe open port on iperf3 server - usefull when several port opens

    Args:
        host (str): iperf3 server
        ports_list (list): port to probe
        required_ports (int, optional): define amount of required port for running iperf3. Defaults to 2.

    Returns:
        list: available port for running iperf3
    """
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
            if len(available_ports) == required_ports:
                break
        except Exception as e:
            log.debug(f"exception: {e}")
    if len(available_ports) < required_ports:
        log.warning("not enough ports to run tests")
        exit(1)
    log.info(
        f"probe finished - following port available to be used => {available_ports}"
    )
    return available_ports


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


def run_commands(commands):
    """run commands dict from a

    Args:
        commands (dict): commands to run and sleep time between them

    Returns:
        dict: output from command execution
    """
    processes = {}
    output = {}
    if not args.dry_run:
        for cmd, sleep_time in commands.items():
            log.info(f"Execute cmd: '{cmd}' in a new process")
            processes[cmd] = Popen(cmd.split(), stdout=PIPE, universal_newlines=True)
            time.sleep(sleep_time)
        log.info("processes check start")
        for t in range(1, args.timeout):
            for cmd, process in processes.items():
                log.debug(f"process pid: {process.pid} cmd: {cmd}")

                try:
                    outs, errs = process.communicate(timeout=1)
                    log.debug(outs)
                    output[cmd] = outs  # process.stdout.read()
                    # make sure process completed
                    process.kill()
                    del processes[cmd]
                    # break to re-iterate over
                    break
                except Exception as e:
                    log.debug(f"Exception: {e}")
                    time.sleep(1)

            if not processes:
                break
            time.sleep(1)
        log.info("processes finished")

    else:
        # dry-run mode - load output from file
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
    """parse pint output with regex

    Args:
        output (str): text to parse

    Returns:
        dict: parsed data (stats and pckts_stats) in dict
    """
    stats = {}

    # Parse line => 15 packets transmitted, 15 received, 0% packet loss, time 14021ms
    regex = r"(?P<pckts_tx>\d+) packets transmitted, (?P<pckts_rx>\d+) received, (?P<pckts_loss_perc>[\d\.]+)% packet loss, time (?P<time>\d+)ms"
    parsed_data = parse_text_to_list(regex, output)
    stats.update(parsed_data[0])

    # Parse line => rtt min/avg/max/mdev = 7.360/16.159/31.052/9.404 ms
    regex = r"rtt min/avg/max/mdev = (?P<rtt_min>[\d\.]+)/(?P<rtt_avg>[\d\.]+)/(?P<rtt_max>[\d\.]+)/(?P<rtt_mdev>[\d\.]+) ms"
    parsed_data = parse_text_to_list(regex, output)
    stats.update(parsed_data[0])

    # Parse lines =>
    # [1645533781.102614] 64 bytes from 172.16.1.238: icmp_seq=1 ttl=60 time=7.36 ms
    # [1645533782.109318] 64 bytes from 172.16.1.238: icmp_seq=2 ttl=60 time=12.3 ms
    # [1645533783.107913] 64 bytes from 172.16.1.238: icmp_seq=3 ttl=60 time=9.35 ms
    #

    # TODO : support ipv6
    regex = r"\[(?P<unix_time>\d+\.\d+)\]\s\d+\sbytes\sfrom\s(?P<target_host>([\d\.]+)):\sicmp_seq=(?P<icmp_seq>\d+)\sttl=(?P<icmp_ttl>\d+)\stime=(?P<icmp_time>([\d\.]+))\sms"
    pckts_stats = parse_text_to_list(regex, output)

    ping_results = {"stats": stats, "pckts_stats": pckts_stats}
    return ping_results


def save_outputs(filename, output):
    """save output from process into filename

    Args:
        filename (str): target filename with full path
        output (str): content to save
    """
    with open(filename, "a") as f:
        f.write(output)


def fill_dict(keys, dict):
    """copy key/values from a dict and add empty entries if keys not present

    Args:
        keys (list): keys to add empty str
        dict (dict): source dictionary to normalize

    Returns:
        dict: dict with empty keys
    """
    d = {}
    d.update({k: dict[k] for k in keys if k in dict})
    d.update({k: "" for k in keys if k not in dict})
    return d


def save_CSV(dst_filename, header, csv_content):
    """save into CSV file

    Args:
        dst_filename (str): CSV file destination
        header (list): list of keys to be saved
        csv_content (list): list of dict with keys
    """
    with open(dst_filename, "w") as output_file:
        dict_writer = csv.DictWriter(output_file, header)
        dict_writer.writeheader()
        dict_writer.writerows(csv_content)
        log.info(f"CSV wrote in {dst_filename}")


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


def calculate_tput_BDP(buffer_size, latency):
    """return max throughtput achievable with given buffer size and latency

    Args:
        buffer_size ([type]): in bytes
        latency ([type]): in ms
    """

    buffer_size_bits = buffer_size * 8
    latency_sec = latency * pow(10, -3)

    return buffer_size_bits / latency_sec


def get_max_tcp_mem(type):
    """[summary]

    Args:
        type ([type]): tcp_wmem or tcp_rmem
    """
    # current receiver window size 'cat /proc/sys/net/ipv4/tcp_rmem'
    cmd = f"cat /proc/sys/net/ipv4/{type}"
    tcp_mem = run(cmd.split(), capture_output=True, text=True).stdout

    # receiving data
    log.debug(f"tcp_mem {type}: {tcp_mem}")

    return float(tcp_mem.strip().split("\t")[-1])


def bps_to_humanReadable(bps):

    unit_suffix = {
        3: {"divider": 1, "unit": ""},
        6: {"divider": 1000, "unit": "k"},
        9: {"divider": 1000000, "unit": "M"},
        12: {"divider": 1000000000, "unit": "G"},
    }

    len_str_bps = len(str(int(bps)))
    for length, suffix in unit_suffix.items():
        if len_str_bps < length:
            str_bps = str(round(bps / suffix["divider"], 2))
            return f"{str_bps} {suffix['unit']}bps"


def main(args):
    """main run

    Args:
        args (obj): main program obj
    """

    runtest_time = get_timestamp_now()

    if args.description:
        args.description += "_"

    port_list = check_port_arg(args.port)

    cmds_args = {
        "-c": args.host,
        "-p": str(port_list[0]),
        "-t": args.time,
        "-P": args.parallel,
        "-J": "",
    }

    if args.reverse:
        cmds_args["R"] = ""

    cmds_args_expanded = expand_cmds_args(cmds_args)
    cmds_args_generated = generate_cmds_args(cmds_args_expanded)
    commands = generate_cmds("iperf3", cmds_args_generated)

    if args.cmd == "bdp":
        cmd = f"ping {args.host} -c 5 -i 0.2 -D"

        measure_latency = run(cmd.split(), capture_output=True, text=True).stdout

        latency_values = parse_ping_output(measure_latency)

        log.debug(f"latency_values: {latency_values}")

        max_mem = get_max_tcp_mem("tcp_wmem")
        print(f"max_mem: {max_mem} bytes")

        rtt_min = float(latency_values["stats"]["rtt_min"])
        rtt_avg = float(latency_values["stats"]["rtt_avg"])

        print(f"rtt_min: {rtt_min}ms")
        print(f"rtt_avg: {rtt_avg}ms")

        max_tput = bps_to_humanReadable(calculate_tput_BDP(max_mem, rtt_min))
        print(f"max sending theoritical tput: {max_tput}")

        max_tput = bps_to_humanReadable(calculate_tput_BDP(max_mem, rtt_avg))
        print(f"avg sending theoritical tput: {max_tput}")

        max_mem = get_max_tcp_mem("tcp_rmem")
        print(f"max_mem: {max_mem} bytes")

        max_tput = bps_to_humanReadable(calculate_tput_BDP(max_mem, rtt_min))
        print(f"max receiving theoritical tput: {max_tput}")

        max_tput = bps_to_humanReadable(calculate_tput_BDP(max_mem, rtt_avg))

        print(f"avg receiving theoritical tput: {max_tput}")

    if args.cmd == "probe":
        if not args.no_probe and not args.dry_run:
            free_ports = probe_iperf3(args.host, port_list, required_ports=1)

            cmd = commands[0]
            cmd = re.sub(
                r"-p\s+\d+\s",
                f"-p {free_ports[0]} ",
                cmd,
            )

        scenario_cmds = {
            cmd: 0.1,
        }

        output_commands = run_commands(scenario_cmds)

        for cmd, output in output_commands.items():
            if "iperf3" in cmd:
                output_commands[cmd] = {
                    "output_parsed": json.loads(output),
                    "type": "iperf3",
                }
                ext = ".json"

                streams_rtt = []
                for interval in output_commands[cmd]["output_parsed"]["intervals"]:
                    streams_rtt.append(float(interval["streams"][0]["rtt"] / 1000))

                mean_streams_rtt = statistics.mean(streams_rtt)

                print(f"mean_streams_rtt: {mean_streams_rtt}")

                max_mem = get_max_tcp_mem("tcp_wmem")

                max_tput = calculate_tput_BDP(max_mem, mean_streams_rtt)

                print(f"max sending theoritical tput: {max_tput}")

                max_mem = get_max_tcp_mem("tcp_rmem")

                max_tput = calculate_tput_BDP(max_mem, mean_streams_rtt)

                print(f"max receiving theoritical tput: {max_tput}")

                # print(output)

        output_commands["iperf3 -c 62.202.138.238 -p 5003 -t 5 -P 1 -J "][
            "output_parsed"
        ]["intervals"][4]["streams"][0]["rtt"]

    if args.cmd == "bufferbloat":

        if len(port_list) == 1:
            port_list[1] = port_list[0] + 1
            log.warn(
                f"Only one port given ({port_list[0]}) - 2 required - automatically added a second one next to first one {port_list[1]}"
            )
        """
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
        """
        if "-R" in commands[0]:
            cmd_iperf3_us = commands[0].replace("-R", "")
            cmd_iperf3_ds = commands[0]
        else:
            cmd_iperf3_us = commands[0]
            cmd_iperf3_ds = f"{commands[0]} -R"

        bufferbloat_iperf3_commands = [cmd_iperf3_ds, cmd_iperf3_us]

        if not args.no_probe and not args.dry_run:
            free_ports = probe_iperf3(args.host, port_list, required_ports=2)

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

        summary_stats["description"] = args.description

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
            csv_content_line = fill_dict(relevant_keys, csv_content_line)
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
    log.debug(f"config: \n{config}")

    main(args)
