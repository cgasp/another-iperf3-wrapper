import re
import json
import logging
import statistics

import time
from subprocess import Popen, PIPE, check_output, run

from rich import print
from rich.panel import Panel

from utils import args, common, run_commands, output_operations

log = logging.getLogger("another-iperf3-wrapper")


def probe_run():
    print(
        Panel.fit(
            "Probe iperf3 server, available port and estimate maximum performance base on RTT and Memory configured",
            border_style="white",
        )
    )
    print(f"host: {args.obj.host}")

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

        if "-R" in cmd:
            log.warning("only US traffic supported -R removed")
            cmd = cmd.replace("-R", "")

    scenario_cmds = {
        cmd: 0.1,
    }

    output_commands = run_commands.run_commands(scenario_cmds)

    output_commands = output_operations.parse_output_commands(output_commands)

    for cmd, output in output_commands.items():
        if output["type"] == "iperf3":

            streams_rtt = []
            for interval in output_commands[cmd]["output_parsed"]["intervals"]:
                streams_rtt.append(float(interval["streams"][0]["rtt"] / 1000))

            mean_streams_rtt = statistics.mean(streams_rtt)

            print(f"Avg streams rtt: {round(mean_streams_rtt,2)}ms")

            print(f"\n# Sending (Upload)")

            max_mem = common.get_max_tcp_mem("tcp_wmem")
            print(f"max_wmem: {common.units_to_humanReadable(max_mem)}bytes")

            max_tput = common.units_to_humanReadable(
                common.calculate_tput_BDP(max_mem, mean_streams_rtt)
            )

            print(f"max sending theoritical throughput: {max_tput}bps")

            print(f"\n# Receiving (Download)")

            max_mem = common.get_max_tcp_mem("tcp_rmem")
            print(f"max_rmem: {common.units_to_humanReadable(max_mem)}bytes")

            max_mem = common.get_max_tcp_mem("tcp_rmem")

            max_tput = common.units_to_humanReadable(
                common.calculate_tput_BDP(max_mem, mean_streams_rtt)
            )

            print(f"max receiving theoritical throughput: {max_tput}bps")
