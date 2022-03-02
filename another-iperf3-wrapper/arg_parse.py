import argparse


def arg_parse(config_default):
    text_description = """
Wrapper to expand iperf3 capabilities 

# Main features
   - expand iperf3 command 
   - run iperf3 command 
   - probe open port before running (soon)
   - parse output to CSV (streams or summary) (soon)
   - run set of predefine command in file (soon)
   - bufferbloat evaluation (soon) 
   - generate graphs with results (soon)
"""

    parser = argparse.ArgumentParser(
        description=text_description, formatter_class=argparse.RawTextHelpFormatter
    )

    #
    # CMD
    subparsers = parser.add_subparsers(
        help="sub-command help", title="commands ", dest="cmd"
    )

    parser.add_argument(
        "-c",
        dest="host",
        action="store",
        type=str,
        default=config_default.get("host", ""),
        required=False,
        help="connecting to <host>, if multiple will launch",
    )

    parser.add_argument(
        "-p",
        dest="port",
        action="store",
        type=str,
        default=config_default.get("port", "5201"),
        required=False,
        help="server port to connect",
    )

    parser.add_argument(
        "-t",
        dest="time",
        action="store",
        type=str,
        default=config_default.get("time", "10"),
        required=False,
        help="time in seconds to transmit for (default 5 secs)",
    )

    parser.add_argument(
        "-P",
        dest="parallel",
        action="store",
        type=str,
        default=config_default.get("parallel", "10"),
        required=False,
        help="number of parallel client streams to run",
    )

    parser.add_argument(
        "-R",
        dest="reverse",
        action="store_true",
        required=False,
        help="reverse",
    )

    parser.add_argument(
        "--port-range",
        dest="port_range",
        action="store",
        type=str,
        required=False,
        help="port range for probing",
    )

    parser.add_argument(
        "--no-probe",
        dest="no_probe",
        action="store_true",
        required=False,
        help="no probe",
    )

    parser.add_argument(
        "--csv",
        dest="csv",
        action="store_true",
        help="generate a CSV file with data",
    )

    parser.add_argument(
        "-i",
        "--input_file",
        dest="input_file",
        action="store",
        type=str,
        help="input file",
    )

    parser.add_argument(
        "--timeout",
        dest="timeout",
        action="store",
        type=int,
        default=30,
        help="timeout",
    )

    parser.add_argument(
        "--name",
        dest="name",
        action="store",
        type=str,
        help="input file",
    )

    parser.add_argument(
        "--scf",
        dest="scf",
        action="store",
        type=str,
        help="status cmd file for ibssh to configure GW",
    )

    parser.add_argument(
        "--result-dst-path",
        dest="result_dst_path",
        action="store",
        type=str,
        default=config_default.get("result_dst_path", ""),
        help="result_dst_path to save results",
    )

    parser.add_argument(
        "--save-outputs",
        dest="save_outputs",
        action="store_true",
        help="save output from commands",
    )

    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="dry run - no command runned",
    )

    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="debug info",
    )

    parser.add_argument(
        "--nl",
        dest="no_logging",
        action="store_true",
        help="no logging",
    )

    parser.add_argument(
        "--description",
        dest="description",
        action="store",
        type=str,
        default=config_default.get("description", ""),
        help="test description to be included on file name",
    )

    #
    # bufferbloat test with 
    parser_bufferbloat = subparsers.add_parser(
        "bufferbloat",
        help="run iperf3 process to bufferbloat test\n ",
    )

    #
    # bufferbloat test with 
    parser_probe = subparsers.add_parser(
        "probe",
        help="probe iperf3 server\n ",
    )

    return parser.parse_args()
