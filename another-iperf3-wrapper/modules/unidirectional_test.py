import logging
import re
import time

from utils import args, common, run_commands, output_operations
from modules import run_iperf

log = logging.getLogger("another-iperf3-wrapper")


def single_run():
    """
    Executes a single run of the iperf3 test.
    This function performs the following steps:
    1. Probes for free ports using iperf3 if probing is enabled and not a dry run.
    2. Constructs the command to run iperf3 with the free port obtained from probing.
    3. Defines the scenario commands including a ping command and the iperf3 command.
    4. Executes the scenario commands and collects interval and summary statistics.
    5. Displays the summary statistics.
    6. Optionally saves the results to CSV and/or JSON files.
    Returns:
        tuple: A tuple containing interval statistics and summary statistics.
    """
    # run iperf3 probing
    if not args.obj.no_probe and not args.obj.dry_run:
        free_ports = run_commands.probe_iperf3(
            args.obj.host, common.data["port_list"], required_ports=1
        )

        cmd = common.data["commands"][0]
        cmd = re.sub(r"-p\s+\d+\s", f"-p {free_ports[0]} ", cmd)
    else:
        cmd = common.data["commands"][0]

    scenario_cmds = {
        f"ping {args.obj.host} -c {str(int(args.obj.time) + 4)} -D": 2,
        cmd: 0.1,
    }
    
    runtest_time = common.get_timestamp_now()
    
    interval_stats, summary_stats = run_iperf.run(scenario_cmds)
    
    summary_stats["description"] = args.obj.description

    output_operations.display_summary_stats(summary_stats)
    # Save all results after all iterations
    if args.obj.csv:
        output_operations.save_to_CSV(
            f"{args.obj.test_name}ST", runtest_time, [summary_stats], [interval_stats]
        )

    if args.obj.json:
        output_operations.save_to_JSON(
            f"{args.obj.test_name}ST", runtest_time, [summary_stats], [interval_stats]
        )
    
    return interval_stats, summary_stats

    

def unidirectional_test():
    """main function to run single test"""

    all_interval_stats = []
    all_summary_stats = []
    
    run_commands.cmd_preparation()

    for i in range(args.obj.iterations):
        if args.obj.iterations > 1:
            log.info(f"Running iteration {i + 1} of {args.obj.iterations}")

        interval_stats, summary_stats = single_run()

        all_interval_stats.append(interval_stats)
        all_summary_stats.append(summary_stats)

        if i < args.obj.iterations - 1:
            log.info(f"Sleeping for {args.obj.sleep} seconds before next iteration")
            time.sleep(args.obj.sleep)

    return all_interval_stats, all_summary_stats  