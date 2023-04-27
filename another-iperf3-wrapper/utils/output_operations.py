import datetime
import logging
import re
import json
import statistics

from utils import args, common, output_operations

log = logging.getLogger("another-iperf3-wrapper")


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


def parse_iperf3_intervals(output_commands):
    """parse intervals in iperf3 output to save later in CSV

    Args:
        output_commands (dict): iperf3 output

    Returns:
        dict: with intervals_streams_stats and intervals_sum_stats
    """
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
                epochtime = start_ts + int(round(interval["sum"]["start"], 0))
                timestamp = datetime.datetime.fromtimestamp(epochtime)

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


def convert_streams_list_to_dict(interval_stats):
    """convert list of stream in iperf3 output to dict

    Args:
        interval_stats (dict): stats from interval

    Returns:
        dict: stats from interval with stream with new format
    """

    for timestamp, stats_per_ts in interval_stats.items():
        if stats_per_ts.get("streams", False):
            for stream_type, stream_type_stats in stats_per_ts["streams"].items():
                streams_dict = {}
                for id, stream in enumerate(stream_type_stats):
                    streams_dict[str(id)] = stream

                interval_stats[timestamp]["streams"][stream_type] = streams_dict
    return interval_stats


def set_iperf3_results_by_timestamp(interval_stats, stream_direction, output_parsed):
    """reorganize iperf3 results by timestamp

    Args:
        interval_stats (dict): stats from interval
        stream_direction (str): stream direction
        output_parsed (dict): iperf3 output parsed

    Returns:
        dict: stats from interval
    """

    start_ts = output_parsed["start"]["timestamp"]["timesecs"]

    stats_type = ["sum", "streams"]

    for interval in output_parsed["intervals"]:
        timestamp = start_ts + int(round(interval["sum"]["start"], 0))

        for stat_type in stats_type:

            if not interval_stats.get(timestamp, False):
                interval_stats[timestamp] = {}

            if not interval_stats[timestamp].get(stat_type, False):
                interval_stats[timestamp][stat_type] = {}

            if not interval_stats[timestamp][stat_type].get(stream_direction, False):
                interval_stats[timestamp][stat_type][stream_direction] = {}

            interval_stats[timestamp][stat_type][stream_direction] = interval[stat_type]

    return interval_stats


def prepare_iperf3_interval_results_for_CSV(interval_stats):
    """save iperf3 interval results into CSV

    Args:
        interval_stats (dict): stats from interval
    """

    interval_stats = convert_streams_list_to_dict(interval_stats)

    # Prepare data to save in CSV
    timestamps_sorted = list(sorted(interval_stats.keys()))

    CSV_content = []
    for timestamp in timestamps_sorted:
        CSV_line = {
            "timestamp": datetime.datetime.fromtimestamp(timestamp).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }
        flatten_data = common.flatten(interval_stats[timestamp], "", ".")
        CSV_line.update(flatten_data)
        CSV_content.append(CSV_line)

    header = [key for dict in CSV_content for key in dict]
    header = sorted(set(header))
    header.remove("timestamp")
    header.insert(0, "timestamp")

    # for sum data to be on first column
    for h in header:
        if "sum" in h:
            header.remove(h)
            header.insert(1, h)

    return header, CSV_content


def calculate_streams_rtt_stats(intervals):
    """for given intervals stream information retrieve RTT and calculate basic stats

    Args:
        intervals (dict): contain intervals information

    Returns:
        dict: with min, mean, max, mdev
    """

    streams_rtt = []
    for interval in intervals:
        for stream in interval["streams"]:
            streams_rtt.append(float(stream["rtt"] / 1000))

    return {
        "avg": round(statistics.mean(streams_rtt), 3),
        "max": round(max(streams_rtt), 3),
        "min": round(min(streams_rtt), 3),
        "mdev": round(statistics.stdev(streams_rtt), 3),
    }


def save_to_CSV(test_type, runtest_time, summary_stats, interval_stats):
    """save information to CSV

    Args:
        test_type (str): test type to be included in filename
        runtest_time (str): runtime information to be included in filename
        summary_stats (dict): summarize information to saved in CSV
        interval_stats (dict): interval information to saved in CSV
    """
    description = (
        f'{summary_stats["description"]}_' if summary_stats["description"] else ""
    )

    # summary-stats
    fn = (
        f"{args.obj.result_dst_path}{test_type}_summary_{description}{runtest_time}.csv"
    )
    common.save_CSV(fn, list(summary_stats.keys()), [summary_stats])
    log.info(f"summary stats data saved in: {fn}")

    fn = f"{args.obj.result_dst_path}{test_type}_intervals_{description}{runtest_time}.csv"
    header, CSV_content = output_operations.prepare_iperf3_interval_results_for_CSV(
        interval_stats
    )
    common.save_CSV(fn, header, CSV_content)
    log.info(f"interval stats data saved in: {fn}")


def save_to_JSON(test_type, runtest_time, summary_stats, interval_stats):
    """save information to JSON

    Args:
        test_type (str): test type to be included in filename
        runtest_time (str): runtime information to be included in filename
        summary_stats (dict): summarize information to saved in JSON
        interval_stats (dict): interval information to saved in JSON
    """
    description = (
        f'{summary_stats["description"]}_' if summary_stats["description"] else ""
    )

    # summary-stats
    fn = f"{args.obj.result_dst_path}{test_type}_summary_{description}{runtest_time}.json"
    common.save_JSON(fn, summary_stats)
    log.info(f"summary stats data saved in: {fn}")

    fn = f"{args.obj.result_dst_path}{test_type}_intervals_{description}{runtest_time}.json"
    common.save_JSON(fn, interval_stats)
    log.info(f"interval stats data saved in: {fn}")


def display_summary_stats(summary_stats):
    """display summarize stats

    Args:
        summary_stats (dict): data to be displayed
    """

    summary_stats["description"] = args.obj.description

    download_bps = common.units_to_humanReadable(
        summary_stats.get("downstream_bits_per_second", "")
    )
    download_bps = f"{download_bps}bps" if download_bps else "N/A"

    upload_bps = common.units_to_humanReadable(
        summary_stats.get("upstream_bits_per_second", "")
    )
    upload_bps = f"{upload_bps}bps" if upload_bps else "N/A"

    # only upstream test will display values
    iperf3_rtt_stats = ""
    rtt_elements = ["avg", "min", "max", "mdev"]

    for rtt_element in rtt_elements:
        iperf3_rtt_stat = (
            f"  rtt {rtt_element}: {summary_stats[rtt_element]} ms\n"
            if summary_stats[rtt_element]
            else f"  rtt {rtt_element}: N/A\n"
        )
        iperf3_rtt_stats += iperf3_rtt_stat

    print_summary_stats = (
        f"runtime: {summary_stats['timestamp']}\n"
        f"iperf3:\n"
        f"  download: {download_bps}\n"
        f"  upload: {upload_bps}\n"
        f"{iperf3_rtt_stats}"
        f"ICMP:\n"
        f"  packets tx/rx/loss: {summary_stats['icmp_pckts_tx']}/{summary_stats['icmp_pckts_rx']}/{summary_stats['icmp_pckts_loss_perc']}\n"
        f"  rtt avg: {summary_stats['icmp_rtt_avg']} ms\n"
        f"  rtt min: {summary_stats['icmp_rtt_min']} ms\n"
        f"  rtt max: {summary_stats['icmp_rtt_max']} ms\n"
        f"  rtt mdev: {summary_stats['icmp_rtt_mdev']} ms\n"
        # avg/max/mdev: /// ms\n"
    )

    print(f"# summary_stats \n{print_summary_stats}")
