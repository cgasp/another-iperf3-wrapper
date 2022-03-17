import datetime
import logging
import re
import csv
import time
import json

from subprocess import Popen, PIPE, check_output, run

import args

log = logging.getLogger("another-iperf3-wrapper")

# common data
data = {}


def get_timestamp_now(fmt="%Y%m%d-%H%M%S"):
    """generate timestamp to now

    Args:
        fmt (str, optional): format for timestamp. Defaults to "%Y%m%d-%H%M%S".

    Returns:
        str: timestamp with selected format
    """
    return datetime.datetime.now().strftime(fmt)


def probe_iperf3(host, ports_list, required_ports=2):
    """function to probe open port on iperf3 server - usefull when several port opens

    Args:
        host (str): iperf3 server
        ports_list (list): port to probe
        required_ports (int, optional): define amount of required port for running iperf3. Defaults to 2.

    Returns:
        list: available port for running iperf3
    """
    log.debug(
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
    log.debug(
        f"probe finished - following port available to be used => {available_ports}"
    )
    return available_ports


def run_commands(commands):
    """run commands dict from a

    Args:
        commands (dict): commands to run and sleep time between them

    Returns:
        dict: output from command execution
    """
    processes = {}
    output = {}
    if not args.obj.dry_run:
        for cmd, sleep_time in commands.items():
            log.debug(f"Execute cmd: '{cmd}' in a new process")
            processes[cmd] = Popen(cmd.split(), stdout=PIPE, universal_newlines=True)
            time.sleep(sleep_time)
        log.debug("processes check start")
        for t in range(1, args.obj.timeout):
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
        log.debug("processes finished")

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


def save_outputs(filename, output):
    """save output from process into filename

    Args:
        filename (str): target filename with full path
        output (str): content to save
    """
    with open(filename, "a") as f:
        f.write(output)


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


def parse_output_commands(output_commands):
    """parse output commands

    Args:
        output_commands (dict): contain RAW command outputs

    Returns:
        dict: output_commands with parsed data
    """
    for cmd, output in output_commands.items():
        if "iperf3" in cmd:
            output_commands[cmd] = {
                "raw": output,
                "output_parsed": json.loads(output),
                "type": "iperf3",
                "ext": "json",
            }

        elif "ping" in cmd:
            output_commands[cmd] = {
                "raw": output,
                "output_parsed": parse_ping_output(output),
                "type": "ping",
                "ext": "log",
            }

    return output_commands


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


def get_str_cmd(cmd):
    return cmd.replace("-", "_").replace(" ", "")


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


def units_to_humanReadable(bps):
    """convert units to suitable human readable unit

    Args:
        bps (int): bits per second

    Returns:
        str: human readable bps
    """

    unit_suffix = {
        4: {"divider": 1, "unit": ""},
        7: {"divider": 1000, "unit": "k"},
        10: {"divider": 1000000, "unit": "M"},
        13: {"divider": 1000000000, "unit": "G"},
    }

    len_str_bps = len(str(int(bps)))
    for length, suffix in unit_suffix.items():
        if len_str_bps < length:
            str_bps = str(round(bps / suffix["divider"], 2))
            return f"{str_bps} {suffix['unit']}"


def calculate_tput_BDP(buffer_size, latency):
    """return max throughtput achievable with given buffer size and latency

    Args:
        buffer_size (int): in bytes
        latency (int): in ms
    """

    buffer_size_bits = buffer_size * 8
    latency_sec = latency * pow(10, -3)

    return buffer_size_bits / latency_sec


def calculate_mem_BDP(latency, bps=1e9):
    """return needed memory setting to reach target throughput with given latency

    Args:
        buffer_size (int): in bytes
        latency (int): in ms
    """
    latency_sec = latency * pow(10, -3)

    return bps * latency_sec


def get_max_tcp_mem(type):
    """get max configured tcp mem

    Args:
        type (str): tcp_wmem or tcp_rmem
    """
    cmd = f"cat /proc/sys/net/ipv4/{type}"
    tcp_mem = run(cmd.split(), capture_output=True, text=True).stdout

    # receiving data
    log.debug(f"tcp_mem {type}: {tcp_mem}")

    return float(tcp_mem.strip().split("\t")[-1])


def parse_iperf3_intervals(output_commands):
    interval_stats = {}
    intervals_streams_stats = []
    intervals_sum_stats = []
    for cmd, values in output_commands.items():
        test_error = values["output_parsed"].get("error", False)
    if test_error:
        log.error(f"test invalid - error: {test_error}")
    else:
        if values["type"] == "iperf3":
            header_prefix = (
                "DS"
                if values["output_parsed"]["start"]["test_start"]["reverse"] == 1
                else "US"
            )

            start_ts = values["output_parsed"]["start"]["timestamp"]["timesecs"]
            for interval in values["output_parsed"]["intervals"]:
                timestamp = start_ts + int(round(interval["sum"]["start"], 0))

                # interval stream stats
                for stream in interval["streams"]:
                    interval_stream_stats = {"timestamp": timestamp}
                    interval_stream_stats.update(stream)

                    intervals_streams_stats.append(interval_stream_stats)

                # interval sum stats
                interval_sum_stats = {"timestamp": timestamp}
                interval_sum_stats.update(interval["sum"])
                
                intervals_sum_stats.append(interval_sum_stats)

    return {
        "intervals_streams_stats": intervals_streams_stats,
        "intervals_sum_stats": intervals_sum_stats,
    }
