import logging
import re
import time 

from utils import args, common, run_commands, output_operations
from modules import run_iperf, bufferbloat, single_test

log = logging.getLogger("another-iperf3-wrapper")


def all_tests_run():
    
    all_interval_stats = []
    all_summary_stats = []

    all_tests_run_iterations = args.obj.iterations
    args.obj.iterations = 1 
    
    for i in range(all_tests_run_iterations):
        log.info(f"Running iteration {i + 1} of {all_tests_run_iterations}") if all_tests_run_iterations > 1 else None

        """
        # run iperf3 probing
        if not args.obj.no_probe and not args.obj.dry_run:
            free_ports = run_commands.probe_iperf3(
                args.obj.host, common.data["port_list"], required_ports=1
            )

            cmd = common.data["commands"][0]
            cmd = re.sub(
                r"-p\s+\d+\s",
                f"-p {free_ports[0]} ",
                cmd,
            )

        scenario_cmds = {
            "ping {} -c {} -D".format(args.obj.host, str(int(args.obj.time) + 10)): 2,
            cmd: 0.1,
        }

        runtest_time = common.get_timestamp_now()
        interval_stats, summary_stats = run_iperf.run(scenario_cmds)
        summary_stats["description"] = args.obj.description
        # summary_stats["timestamp"] = runtest_time

        output_operations.display_summary_stats(summary_stats)
        """
        
        # Download 
        args.obj.reverse = True
        summary_stats, interval_stats = single_test.single_test_run() 
        
        # Upload
        args.obj.reverse = False
        summary_stats, interval_stats = single_test.single_test_run() 
        
        # Bufferbloat
        summary_stats, interval_stats = bufferbloat.bufferbloat_run()
                
        
        all_interval_stats.append(interval_stats)
        all_summary_stats.append(summary_stats)
        
        if i < all_tests_run_iterations - 1:
            log.info(f"Sleeping for {args.obj.sleep} seconds before next iteration")
            time.sleep(args.obj.sleep)

    # Save all results after all iterations
    if args.obj.csv:
        runtest_time = common.get_timestamp_now()
        output_operations.save_to_CSV(
            f"{args.obj.test_name}ST", runtest_time, all_summary_stats, all_interval_stats
        )

    if args.obj.json:
        output_operations.save_to_JSON(
            f"{args.obj.test_name}ST", runtest_time, all_summary_stats, all_interval_stats
        )