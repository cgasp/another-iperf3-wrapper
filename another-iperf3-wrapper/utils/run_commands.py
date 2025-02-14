import logging
import time
import itertools
import re

from subprocess import Popen, PIPE, check_output

from utils import args, common


log = logging.getLogger("another-iperf3-wrapper")


def check_port_arg(arg_port):
    """parse port argument into port list

    Args:
        arg_port (str): port argument

    Returns:
        list: port list
    """

    port_list = []
    try:
        port_list = [int(arg_port)]
    except ValueError:
        log.debug(f"ValuError: {arg_port}")
        range_char = [",", "-"]
        is_range = any([char in arg_port for char in range_char])
        if is_range:
            if "," in arg_port:
                ranges = arg_port.split(",")
            else:
                ranges = [arg_port]

            for r in ranges:
                r_count_sep = r.count("-")
                if r_count_sep == 1:
                    start_port, end_port = r.split("-")
                    try:
                        port_list_range = list(
                            range(int(start_port), int(end_port) + 1)
                        )
                        if port_list_range:
                            port_list.extend(port_list_range)
                        else:
                            log.debug(f"Not a valid range: {start_port} -> {end_port}")
                    except ValueError:
                        log.debug(f"Not a valid number: {r}")

                elif r_count_sep == 0:
                    try:
                        port_list.append(int(r))
                    except ValueError:
                        log.debug(f"Not a valid number: {r}")
                else:
                    log.debug(f"range invalid: {r}")
    log.debug(f"port list: {port_list}")

    return port_list


def generate_cmds(base_cmd, cmds_args):
    """from given iperf3 args generate commands

    Args:
        cmds_args (list): list of arguments for iperf3 commands

    Returns:
        cmd: commands list
    """
    # generate command
    cmds = []
    for cmd_args in cmds_args:
        cmd = base_cmd
        for arg in cmd_args:
            cmd += f" {arg}"
        # remove duplicate whitespaces and remove trailing space
        cmd = re.sub(r"\s+", r" ", cmd).strip()
        cmds.append(cmd)
    return cmds


def expand_cmds_args(cmds_args):
    """expand numeric values from list and range on args

    Args:
        cmds_args (dict): arguments to expand

    Returns:
        dict: arguments expanded
    """
    cmds_args_expanded = {}
    new_arg_value = []
    for arg, value in cmds_args.items():
        new_arg_value = []
        # split if ',' else return list
        value = value.split(",") if "," in value else [value]
        for v in value:
            if "-" in v:
                # try to expand numerical range
                try:
                    range_n = v.split("-")
                    new_v = [
                        str(element)
                        for element in list(range(int(range_n[0]), int(range_n[1])))
                    ]
                    new_arg_value.extend(new_v)
                except Exception as e:
                    log.debug(f"Exception: {e}")
                    log.warning(f"seems not a valid range: {range_n}")
                    new_arg_value.append(v)
            else:
                new_arg_value.append(v)
        # save new value
        cmds_args_expanded[arg] = new_arg_value

    log.debug(f"arguments expanded: {cmds_args_expanded}")

    return cmds_args_expanded


def generate_cmds_args(cmds_args_expanded):
    """generate all possible commands by given arguments

    Args:
        cmds_args_expanded (dict): expanded arguments

    Returns:
        list: given arguments return list of possible commands
    """

    ls = []
    for arg, value in cmds_args_expanded.items():
        arg_list = []
        for v in value:
            arg_list.append(f"{arg} {v}")
        ls.append(arg_list)

    cmds_args_all_permutations = list(itertools.product(*ls))
    log.debug(f"generated commands: {cmds_args_all_permutations}")
    return cmds_args_all_permutations


def cmd_preparation():
    """prepare command for execution

    Args:
        cmd (str): command to run

    Returns:
        str: prepared command
    """    
    common.data["port_list"] = check_port_arg(args.obj.port)

    cmds_args = {
        "-c": args.obj.host,
        "-p": str(common.data["port_list"][0]),
        "-t": args.obj.time,
        "-P": args.obj.parallel,
        # json output format
        "-J": "",
        # zerocopy
        "-Z": "",
    }

    if args.obj.reverse:
        cmds_args["-R"] = ""

    if args.obj.udp:
        cmds_args["-u"] = ""

    if args.obj.bitrate:
        cmds_args["-b"] = args.obj.bitrate

    if args.obj.iperf3_args:
        iperf3_args = str(args.obj.iperf3_args).replace("\\", "")
        cmds_args[iperf3_args] = ""

    cmds_args_expanded = expand_cmds_args(cmds_args)
    cmds_args_generated = generate_cmds_args(cmds_args_expanded)
    common.data["commands"] = generate_cmds("iperf3", cmds_args_generated)
    
    
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
