import logging
import re
import time 

from utils import args, common, run_commands, output_operations
from modules import bufferbloat, unidirectional_test

log = logging.getLogger("another-iperf3-wrapper")

def all_tests_run():
    """
    Run all tests (download, upload, and bufferbloat) for a specified number of iterations.
    
    This function performs the following steps:
    1. Runs the download test.
    2. Runs the upload test.
    3. Runs the bufferbloat test.
    4. Repeats the above steps for the specified number of iterations.
    5. Saves the results to CSV and/or JSON files if specified in the arguments.
    """
    
    all_interval_stats = []
    all_summary_stats = []

    all_tests_run_iterations = args.obj.iterations
    args.obj.iterations = 1 
    
    for i in range(all_tests_run_iterations):
        log.info(f"Running iteration {i + 1} of {all_tests_run_iterations}") if all_tests_run_iterations > 1 else None
        
        # Download 
        log.info("Starting download test")
        args.obj.reverse = True
        run_commands.cmd_preparation()
        interval_stats, summary_stats = unidirectional_test.single_run() 
        log.info("Download test completed")
        
        all_interval_stats.append(interval_stats)
        all_summary_stats.append(summary_stats)
        
        # Upload
        log.info("Starting upload test")
        args.obj.reverse = False
        run_commands.cmd_preparation()
        interval_stats, summary_stats = unidirectional_test.single_run() 
        log.info("Upload test completed")
        
        all_interval_stats.append(interval_stats)
        all_summary_stats.append(summary_stats)
        
        # Bufferbloat
        log.info("Starting bufferbloat test")
        interval_stats, summary_stats = bufferbloat.single_run()
        log.info("Bufferbloat test completed")
        
        all_interval_stats.append(interval_stats)
        all_summary_stats.append(summary_stats)
            
        if i < all_tests_run_iterations - 1:
            log.info(f"Sleeping for {args.obj.sleep} seconds before next iteration")
            time.sleep(args.obj.sleep)

    # Save all results after all iterations
    if args.obj.csv:
        log.info("Saving results to CSV")
        runtest_time = common.get_timestamp_now()
        output_operations.save_to_CSV(
            f"{args.obj.test_name}ALL", runtest_time, all_summary_stats, all_interval_stats
        )

    if args.obj.json:
        log.info("Saving results to JSON")
        output_operations.save_to_JSON(
            f"{args.obj.test_name}ALL", runtest_time, all_summary_stats, all_interval_stats
        )