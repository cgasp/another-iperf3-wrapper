import argparse

obj = object()


def arg_parse(config_default):
    """main argument parser"""

    text_description = """
Wrapper to expand iperf3 capabilities 

# Main features
   - expand iperf3 command 
   - run iperf3 command 
   - probe open port before running
   - parse output to CSV (streams or summary)
   - bufferbloat evaluation
   - run set of predefine command in file (soon)
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
        default=config_default.get("parallel", "4"),
        required=False,
        help="number of parallel client streams to run (default 4)",
    )

    parser.add_argument(
        "-R",
        dest="reverse",
        action="store_true",
        required=False,
        help="reverse",
    )

    parser.add_argument(
        "-u",
        "--udp",
        dest="udp",
        action="store_true",
        required=False,
        help="use UDP",
    )

    parser.add_argument(
        "-b",
        "--bitrate",
        dest="bitrate",
        action="store",
        default=config_default.get("bitrate", False),
        required=False,
        help=(
            "target bitrate in bits/sec (0 for unlimited)"
            "(default 1 Mbit/sec for UDP, unlimited for TCP)"
            "(optional slash and packet count for burst mode)"
        ),
    )

    parser.add_argument(
        "-A",
        "--iperf3-args",
        dest="iperf3_args",
        action="store",
        type=str,
        # default=config_default.get("iperf3_args", False),
        required=False,
        help=(
            "user set additional iperf3 argument to use on wrapper"
            "/!\ escape - character => \-b 10M"
        ),
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
        "--json",
        dest="json",
        action="store_true",
        help="generate a json file with data",
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
        "--test-name",
        dest="test_name",
        default="",
        action="store",
        type=str,
        help="test_name to be included on file name",
    )

    parser.add_argument(
        "--result-dst-path",
        dest="result_dst_path",
        action="store",
        type=str,
        default=config_default.get("result_dst_path", "~/"),
        help="result_dst_path to save results",
    )

    parser.add_argument(
        "--save-outputs",
        dest="save_outputs",
        action="store_true",
        help="save raw output from commands",
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
        "--quiet",
        dest="quiet",
        action="store_true",
        help="no data displayed",
    )

    parser.add_argument(
        "--description",
        dest="description",
        action="store",
        type=str,
        default=config_default.get("description", ""),
        help="test description to be included on file name",
    )
    
    parser.add_argument(
        "--iterations",
        dest="iterations",
        action="store",
        type=int,
        default=config_default.get("iterations", 1),
        help="how many iterations to run (default: 1)",
    )
    
    parser.add_argument(
        "--sleep",
        dest="sleep",
        action="store",
        type=int,
        default=config_default.get("sleep", 2),
        help="sleep between iterations (default: 1)",
    )
    

    #
    # bufferbloat test with
    parser_bufferbloat = subparsers.add_parser(
        "bufferbloat",
        help="run iperf3 process to bufferbloat test\n ",
    )
    
    #
    # all test with
    parser_all = subparsers.add_parser(
        "all",
        help="run all tests\n ",
    )

    #
    # bufferbloat test with
    parser_probe = subparsers.add_parser(
        "probe",
        help="probe iperf3 server\n ",
    )

    #
    # perform BDP calculation
    parser_bdp = subparsers.add_parser(
        "bdp",
        help="calculate max tput\n ",
    )
    
    

    return parser.parse_args()
