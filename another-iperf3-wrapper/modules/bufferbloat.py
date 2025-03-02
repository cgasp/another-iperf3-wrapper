import logging
import re
import time

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


def single_run():
    """
    Main function to run bufferbloat test.
    This function performs the following steps:
    1. Checks if only one port is provided and automatically adds a second port if needed.
    2. Prepares the iperf3 commands for both upload and download tests.
    3. Probes for free ports if probing is not disabled and it's not a dry run.
    4. Constructs the scenario commands including ping and iperf3 commands.
    5. Logs the commands to be executed.
    6. Runs the iperf3 test and collects interval and summary statistics.
    7. Displays the summary statistics.
    8. Calculates and prints the bufferbloat grade if the log level is debug or info.
    9. Saves the results to CSV and/or JSON files if specified.
    Returns:
        tuple: A tuple containing interval statistics and summary statistics.
    """
    
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

    scenario_time = str(int(args.obj.time) + 4)

    scenario_cmds = {
        f"ping {args.obj.host} -c {scenario_time} -D": 2,
        bufferbloat_iperf3_commands[0]: 0.1,
        bufferbloat_iperf3_commands[1]: 0.1,
    }
    
    for cmd in scenario_cmds.keys():
        log.info(f"commands: {cmd}")

    runtest_time = common.get_timestamp_now()
    interval_stats, summary_stats = run_iperf.run(scenario_cmds)
    
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
            f"{args.obj.test_name}BBT", runtest_time, [summary_stats], [interval_stats]
        )

    if args.obj.json:
        output_operations.save_to_JSON(
            f"{args.obj.test_name}BBT", runtest_time, [summary_stats], [interval_stats]
        )
        
    return interval_stats, summary_stats



def bufferbloat_run():
    """main function to run bufferbloat test"""

    all_interval_stats = []
    all_summary_stats = []
    
    run_commands.cmd_preparation()

    for i in range(args.obj.iterations):
        log.info(f"Running iteration {i + 1} of {args.obj.iterations}") if args.obj.iterations > 1 else None

        interval_stats, summary_stats = single_run()

        all_interval_stats.append(interval_stats)
        all_summary_stats.append(summary_stats)
        
        if i < args.obj.iterations - 1:
            log.info(f"Sleeping for {args.obj.sleep} seconds before next iteration")
            time.sleep(args.obj.sleep)

    return all_interval_stats, all_summary_stats