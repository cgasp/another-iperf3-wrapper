import logging

from utils import args, common, run_commands, output_operations

log = logging.getLogger("another-iperf3-wrapper")


def run(scenario_cmds):
    """main function to run iperf3 standalone or on bufferbloat test

    Args:
        scenario_cmds (dict): contains commands to run 

    Returns:
        dict: with results 
    """

    runtest_time = common.get_timestamp_now()

    output_commands = run_commands.run_commands(scenario_cmds)

    output_commands = output_operations.parse_output_commands(output_commands)

    # save raw output
    if args.obj.save_outputs:
        log.debug("save raw output enabled")
        for cmd, output in output_commands.items():
            str_cmd = cmd.replace("-", "_").replace(" ", "")
            fn = f"{args.obj.result_dst_path}{str_cmd}_{runtest_time}.{output['ext']}"
            log.info(f"raw output saved : {fn}")
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
                        # if the timestamp doesn't exist
                        interval_stats[rounded_timestamp] = {"ping": {}}
                    elif not interval_stats[rounded_timestamp].get("ping", False):
                        # if there is no ping data
                        interval_stats[rounded_timestamp]["ping"] = {}

                    interval_stats[rounded_timestamp]["ping"].update(pckts_stats)

                for stat_name, stat_value in values["output_parsed"]["stats"].items():
                    summary_stats[f"imcp_{stat_name}"] = stat_value

            if values["type"] == "iperf3":

                stream_direction = (
                    "downstream"
                    if values["output_parsed"]["start"]["test_start"]["reverse"] == 1
                    else "upstream"
                )

                interval_stats = output_operations.set_iperf3_results_by_timestamp(
                    interval_stats, stream_direction, values["output_parsed"]
                )

                summary_stats[f"{stream_direction}_bits_per_second"] = int(
                    values["output_parsed"]["end"]["sum_received"]["bits_per_second"]
                )

                if not any(arg in cmd for arg in ["-u", "-R"]):
                    summary_stats.update(
                        output_operations.calculate_streams_rtt_stats(
                            output_commands[cmd]["output_parsed"]["intervals"]
                        )
                    )

    return interval_stats, summary_stats
