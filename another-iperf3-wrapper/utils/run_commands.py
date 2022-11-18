import logging
import time

from subprocess import Popen, PIPE, check_output

from utils import args


log = logging.getLogger("another-iperf3-wrapper")


def run_commands(commands):
    """run commands dict from a

    Args:
        commands (dict): commands to run and sleep time between them

    Returns:
        dict: output from command execution
    """
    processes = {}
    output = {}
    if not args.obj.dry_run:
        for cmd, sleep_time in commands.items():
            log.info(f"run cmd: '{cmd}'")
            processes[cmd] = Popen(cmd.split(), stdout=PIPE, universal_newlines=True)
            time.sleep(sleep_time)
        log.debug("processes check start")
        for t in range(1, args.obj.timeout):
            for cmd, process in processes.items():
                log.debug(f"process pid: {process.pid} cmd: {cmd}")

                try:
                    outs, errs = process.communicate(timeout=1)
                    log.debug(outs)
                    output[cmd] = outs  # process.stdout.read()
                    # make sure process completed
                    process.kill()
                    del processes[cmd]
                    # break to re-iterate over
                    break
                except Exception as e:
                    log.debug(f"Exception: {e}")
                    time.sleep(1)

            if not processes:
                break
            time.sleep(1)
        log.debug("processes finished")

    else:
        # dry-run mode - load output from file
        with open(
            "samples/iperf3_c172.16.1.238_p5201_t5_P10_J_20220222-170451.json",
            "r",
        ) as f:
            output["iperf3 -c 172.16.1.238 -p 5201 -t 5 -P 10 -J   "] = f.read()

        with open(
            "samples/iperf3_c172.16.1.238_p5201_t5_P10_J_R_20220222-170451.json",
            "r",
        ) as f:
            output["iperf3 -c 172.16.1.238 -p 5201 -t 5 -P 10 -J  -R "] = f.read()

        with open(
            "samples/ping172.16.1.238_c15_D_20220222-170451.log",
            "r",
        ) as f:
            output["ping 172.16.1.238 -c 15 -D"] = f.read()

    return output


def probe_iperf3(host, ports_list, required_ports=2):
    """function to probe open port on iperf3 server - usefull when several port opens

    Args:
        host (str): iperf3 server
        ports_list (list): port to probe
        required_ports (int, optional): define amount of required port for running iperf3. Defaults to 2.

    Returns:
        list: available port for running iperf3
    """
    log.debug(
        f"start probing for available iperf3 ports - port range: {ports_list[0]} - {ports_list[-1]} | amount of required ports: {required_ports}"
    )
    available_ports = []
    for port in ports_list:
        cmd = f"iperf3 -4 -c {host} -t 1 -P 1 -p {port} --connect-timeout 500"
        try:
            log.debug(f"probing port {port}")
            result = check_output(cmd, universal_newlines=True, shell=True)
            if "iperf Done." in result:
                available_ports.append(port)
            if len(available_ports) == required_ports:
                break
        except Exception as e:
            log.debug(f"exception: {e}")
    if len(available_ports) < required_ports:
        log.warning("not enough ports to run tests")
        exit(1)
    log.debug(
        f"probe finished - following port available to be used => {available_ports}"
    )
    return available_ports
