import logging

from rich import print
from rich.panel import Panel

from utils import args, common, output_operations

log = logging.getLogger("another-iperf3-wrapper")


def bdp_run():
    """calculate maximum Bandwidth delay product"""

    cmd = f"ping {args.obj.host} -c 5 -i 0.2 -D"

    measure_latency = common.run(cmd.split(), capture_output=True, text=True).stdout

    latency_values = output_operations.parse_ping_output(measure_latency)

    log.debug(f"latency_values: {latency_values}")

    print(Panel.fit("BDP (Bandwidth-delay Product) calculation", border_style="white"))
    print(f"host: {args.obj.host}")
    print(f"\n# Latency")

    rtt_min = float(latency_values["stats"]["rtt_min"])
    rtt_avg = float(latency_values["stats"]["rtt_avg"])

    print(f"rtt_min: {round(rtt_min,2)}ms")
    print(f"rtt_avg: {round(rtt_avg,2)}ms")

    print(f"\n# Sending (Upload)")

    max_mem = common.get_max_tcp_mem("tcp_wmem")
    print(f"max_wmem: {common.units_to_humanReadable(max_mem)}bytes")

    max_tput = common.units_to_humanReadable(
        common.calculate_tput_BDP(max_mem, rtt_min)
    )
    print(f"max sending theoritical throughput: {max_tput}bps")

    max_tput = common.units_to_humanReadable(
        common.calculate_tput_BDP(max_mem, rtt_avg)
    )
    print(f"avg sending theoritical throughput: {max_tput}bps")

    print(f"\n# Receiving (Download)")

    max_mem = common.get_max_tcp_mem("tcp_rmem")
    print(f"max_rmem: {common.units_to_humanReadable(max_mem)}bytes")

    max_tput = common.units_to_humanReadable(
        common.calculate_tput_BDP(max_mem, rtt_min)
    )
    print(f"max receiving theoritical throughput: {max_tput}bps")

    max_tput = common.units_to_humanReadable(
        common.calculate_tput_BDP(max_mem, rtt_avg)
    )
    print(f"avg receiving theoritical throughput: {max_tput}bps")

    print(f"\n# BDP")

    print(
        f"required tcp buffer to reach 10Gbps with RTT of {rtt_min}ms: {common.units_to_humanReadable(common.calculate_mem_BDP(rtt_min,1e9))}bytes"
    )
    print(
        f"required tcp buffer to reach 10Gbps with RTT of {rtt_avg}ms: {common.units_to_humanReadable(common.calculate_mem_BDP(rtt_avg,1e9))}bytes"
    )
