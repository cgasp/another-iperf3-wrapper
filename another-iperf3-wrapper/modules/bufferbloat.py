import logging
import re

from utils import args, common, run_commands, output_operations
from modules import run_iperf

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
    """main function to run bufferbloat test"""

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
        free_ports = run_commands.probe_iperf3(
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

    interval_stats, summary_stats = run_iperf.run(scenario_cmds)
    runtest_time = common.get_timestamp_now()
    summary_stats["timestamp"] = runtest_time
    summary_stats["description"] = args.obj.description

    #
    # Display data
    #
    output_operations.display_summary_stats(summary_stats)

    #
    # Bufferbloat specific
    #
    if log.level in (10, 20):
        effective_latency_inc = float(summary_stats["icmp_rtt_max"]) - float(
            summary_stats["icmp_rtt_min"]
        )

        print(
            f"bufferbloat grade: {bufferbloat_grade(round(effective_latency_inc, 2))}"
        )

    #
    # Save data
    #
    if args.obj.csv:

        output_operations.save_to_CSV(
            f"{args.obj.prefix_description}BBT", runtest_time, summary_stats, interval_stats
        )
