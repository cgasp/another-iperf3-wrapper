import logging
import json
import re

import args
import common

log = logging.getLogger("another-iperf3-wrapper")


def bufferbloat_grade(effective_latency_inc):
    """return grade from given effective_latency_inc
    # source: http://www.dslreports.com/faq/17930

    Args:
        effective_latency_inc (str): grade with description
    """

    # default result
    grade = "F - 400 ms or greater latency increase"

    grades = {
        5: "A+ - Less than 5 ms latency increase",
        30: "A - Less than 30 ms latency increase",
        60: "B - Less than 60 ms latency increase",
        200: "C - Less than 200 ms latency increase",
        400: "D - Less than 400 ms latency increase",
    }

    for latency_grade, g in grades.items():
        if effective_latency_inc < latency_grade:
            grade = g
            break

    return grade


def bufferbloat_run():

    runtest_time = common.get_timestamp_now()

    if len(common.data["port_list"]) == 1:
        common.data["port_list"][1] = common.data["port_list"][0] + 1
        log.warn(
            f"Only one port given ({common.data['port_list'][0]}) - 2 required - automatically added a second one next to first one {common.data['port_list'][1]}"
        )

    if "-R" in common.data["commands"][0]:
        cmd_iperf3_us = common.data["commands"][0].replace("-R", "")
        cmd_iperf3_ds = common.data["commands"][0]
    else:
        cmd_iperf3_us = common.data["commands"][0]
        cmd_iperf3_ds = f"{common.data['commands'][0]} -R"

    bufferbloat_iperf3_commands = [cmd_iperf3_ds, cmd_iperf3_us]

    if not args.obj.no_probe and not args.obj.dry_run:
        free_ports = common.probe_iperf3(
            args.obj.host, common.data["port_list"], required_ports=2
        )

        for idx, cmd in enumerate(bufferbloat_iperf3_commands):
            bufferbloat_iperf3_commands[idx] = re.sub(
                r"-p\s+\d+\s",
                f"-p {free_ports[idx]} ",
                bufferbloat_iperf3_commands[idx],
            )

    scenario_time = str(int(args.obj.time) + 10)

    scenario_cmds = {
        f"ping {args.obj.host} -c {scenario_time} -D": 5,
        bufferbloat_iperf3_commands[0]: 0.1,
        bufferbloat_iperf3_commands[1]: 0.1,
    }
    for cmd in scenario_cmds.keys():
        log.info(f"commands: {cmd}")

    output_commands = common.run_commands(scenario_cmds)

    output_commands = common.parse_output_commands(output_commands)

    for cmd, output in output_commands.items():
        if args.obj.save_outputs:
            str_cmd = cmd.replace("-", "_").replace(" ", "")
            fn = f"{args.obj.result_dst_path}{str_cmd}_{runtest_time}.{output['ext']}"
            common.save_outputs(fn, output["raw"])

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
                    rounded_timestamp = int(round(float(pckts_stats["unix_time"]), 0))

                    if not interval_stats.get(rounded_timestamp, False):
                        interval_stats[rounded_timestamp] = {}

                    interval_stats[rounded_timestamp].update(pckts_stats)

                for stat_name, stat_value in values["output_parsed"]["stats"].items():
                    summary_stats[f"imcp_{stat_name}"] = stat_value

            if values["type"] == "iperf3":
                header_prefix = (
                    "DS"
                    if values["output_parsed"]["start"]["test_start"]["reverse"] == 1
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
                    values["output_parsed"]["end"]["sum_received"]["bits_per_second"]
                )

    summary_stats["description"] = args.obj.description

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
        csv_content_line = common.fill_dict(relevant_keys, csv_content_line)
        csv_content.append(csv_content_line)

    relevant_keys = sorted(list(relevant_keys))
    relevant_keys.remove("timestamp")
    relevant_keys.insert(0, "timestamp")

    log.debug(summary_stats)
    log.debug(csv_content)

    if args.obj.csv:
        # intervals-stats
        fn = f"{args.obj.result_dst_path}bb-test_intervals-stats_{args.obj.description}{runtest_time}.csv"
        common.save_CSV(fn, relevant_keys, csv_content)

        # summary-stats
        fn = f"{args.obj.result_dst_path}bb-test_summary-stats_{args.obj.description}{runtest_time}.csv"
        common.save_CSV(fn, list(summary_stats.keys()), [summary_stats])

    print_summary_stats = (
        f"  runtime: {summary_stats['timestamp']}\n"
        f"  download: {common.units_to_humanReadable(summary_stats['iperf3_DS_bits_per_second'])}bps\n"
        f"  upload: {common.units_to_humanReadable(summary_stats['iperf3_US_bits_per_second'])}bps\n"
        f"  ICMP packets TX: {summary_stats['imcp_pckts_tx']}\n"
        f"  ICMP packets RX: {summary_stats['imcp_pckts_rx']}\n"
        f"  ICMP packets loss: {summary_stats['imcp_pckts_loss_perc']}\n"
        f"  ICMP RTT min: {summary_stats['imcp_rtt_min']}\n"
        f"  ICMP RTT avg: {summary_stats['imcp_rtt_avg']}\n"
        f"  ICMP RTT max: {summary_stats['imcp_rtt_max']}\n"
        f"  ICMP RTT mdev: {summary_stats['imcp_rtt_mdev']}\n"
    )
    if log.level in (10, 20):
        effective_latency_inc = float(summary_stats["imcp_rtt_max"]) - float(
            summary_stats["imcp_rtt_min"]
        )
        print(f"summary_stats:\n{print_summary_stats}")

        print(
            f"bufferbloat grade: {bufferbloat_grade(round(effective_latency_inc, 2))}"
        )
