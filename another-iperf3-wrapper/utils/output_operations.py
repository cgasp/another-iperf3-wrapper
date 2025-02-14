import csv
import datetime
import logging
import re
import os
import json
import statistics
from rich.console import Console
from rich.table import Table
from rich import box

from utils import args, common, output_operations, data_parsers

log = logging.getLogger("another-iperf3-wrapper")

def save_to_CSV(test_type, runtest_time, summary_stats_list, interval_stats_list):
    """save information to CSV

    Args:
        test_type (str): test type to be included in filename
        runtest_time (str): runtime information to be included in filename
        summary_stats_list (list): list of summarize information to be saved in CSV
        interval_stats_list (list): list of interval information to be saved in CSV
    """
    description = (
        f'{summary_stats_list[0]["description"]}_' if summary_stats_list[0]["description"] else ""
    )
    
    # Ensure the directory exists
    result_dst_path = os.path.expanduser(args.obj.result_dst_path)
    os.makedirs(result_dst_path, exist_ok=True)

    # summary-stats
    summary_fn = (
        f"{result_dst_path}{test_type}_summary_{description}{runtest_time}.csv"
    )
    with open(summary_fn, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=summary_stats_list[0].keys())
        writer.writeheader()
        for summary_stats in summary_stats_list:
            writer.writerow(summary_stats)
    log.info(f"summary stats data saved in: {summary_fn}")

    for index, interval_stats in enumerate(interval_stats_list):
        interval_fn = f"{result_dst_path}{test_type}_intervals_{description}{runtest_time}_{index}.csv"
        header, CSV_content = data_parsers.prepare_iperf3_interval_results_for_CSV(
            interval_stats
        )
        common.save_CSV(interval_fn, header, CSV_content)
        log.debug(f"interval stats data saved in: {interval_fn}")
    log.info(f"interval stats data saved in: {interval_fn}")


def save_to_JSON(test_type, runtest_time, summary_stats_list, interval_stats_list):
    """save information to JSON

    Args:
        test_type (str): test type to be included in filename
        runtest_time (str): runtime information to be included in filename
        summary_stats_list (list): list of summarize information to be saved in JSON
        interval_stats_list (list): list of interval information to be saved in JSON
    """
    description = (
        f'{summary_stats_list[0]["description"]}_' if summary_stats_list[0]["description"] else ""
    )

    # Ensure the directory exists
    result_dst_path = os.path.expanduser(args.obj.result_dst_path)
    os.makedirs(result_dst_path, exist_ok=True)

    # summary-stats
    summary_fn = f"{result_dst_path}{test_type}_summary_{description}{runtest_time}.json"
    common.save_JSON(summary_fn, summary_stats_list)
    log.info(f"summary stats data saved in: {summary_fn}")

    for index, interval_stats in enumerate(interval_stats_list):
        interval_fn = f"{result_dst_path}{test_type}_intervals_{description}{runtest_time}_{index}.json"
        common.save_JSON(interval_fn, interval_stats)
        log.debug(f"interval stats data saved in: {interval_fn}")
    log.info(f"interval stats data saved in: {interval_fn}")


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

    console = Console()

    table = Table(box=box.ASCII, title=f"Summary Stats (runtime: {summary_stats['timestamp']})")
    table.add_column("type", justify="right")
    table.add_column("rx", justify="right")
    table.add_column("tx", justify="right")
    table.add_column("rtt avg", justify="right")
    table.add_column("rtt min", justify="right")
    table.add_column("rtt max", justify="right")
    table.add_column("rtt mdev", justify="right")
    table.add_column("pckts_loss", justify="right")

    # Add iperf3 row
    table.add_row(
        f"[bold]iperf3[/bold]",
        download_bps,
        upload_bps,
        f"{summary_stats.get('avg', 'N/A')} ms",
        f"{summary_stats.get('min', 'N/A')} ms",
        f"{summary_stats.get('max', 'N/A')} ms",
        f"{summary_stats.get('mdev', 'N/A')} ms",
        ""
    )

    # Add ICMP row
    table.add_row(
        f"[bold]ICMP[/bold]",
        f"{summary_stats['icmp_pckts_tx']} pckts",
        f"{summary_stats['icmp_pckts_rx']} pckts",
        f"{summary_stats['icmp_rtt_avg']} ms",
        f"{summary_stats['icmp_rtt_min']} ms",
        f"{summary_stats['icmp_rtt_max']} ms",
        f"{summary_stats['icmp_rtt_mdev']} ms",
        f"{summary_stats['icmp_pckts_loss_perc']}%"
    )

    console.print(table)

