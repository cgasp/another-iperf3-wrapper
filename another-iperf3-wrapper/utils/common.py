import datetime
import logging
import csv
import json
import collections.abc
from os.path import expanduser

from subprocess import run

log = logging.getLogger("another-iperf3-wrapper")

# common data
data = {}


def get_timestamp_now(fmt="%Y%m%d-%H%M%S"):
    """generate timestamp to now

    Args:
        fmt (str, optional): format for timestamp. Defaults to "%Y%m%d-%H%M%S".

    Returns:
        str: timestamp with selected format
    """
    return datetime.datetime.now().strftime(fmt)


def save_outputs(filename, output):
    """save output from process into filename

    Args:
        filename (str): target filename with full path
        output (str): content to save
    """
    with open(expanduser(filename), "a") as f:
        f.write(output)


def fill_dict(keys, dict):
    """copy key/values from a dict and add empty entries if keys not present

    Args:
        keys (list): keys to add empty str
        dict (dict): source dictionary to normalize

    Returns:
        dict: dict with empty keys
    """
    d = {}
    d.update({k: dict[k] for k in keys if k in dict})
    d.update({k: "" for k in keys if k not in dict})
    return d


def get_str_cmd(cmd):
    return cmd.replace("-", "_").replace(" ", "")


def save_CSV(dst_filename, header, csv_content):
    """save into CSV file

    Args:
        dst_filename (str): CSV file destination
        header (list): list of keys to be saved
        csv_content (list): list of dict with keys
    """
    with open(expanduser(dst_filename), "w") as output_file:
        dict_writer = csv.DictWriter(output_file, header)
        dict_writer.writeheader()
        dict_writer.writerows(csv_content)
        log.debug(f"CSV saved in {dst_filename}")

def save_JSON(dst_filename, json_content):
    """save into JSON file

    Args:
        dst_filename (str): JSON file destination
        json_content (list): list of dict with keys
    """
    with open(expanduser(dst_filename), "w") as output_file:
        json.dump(json_content, output_file, indent=4)
        log.debug(f"JSON saved in {dst_filename}")


def units_to_humanReadable(bps):
    """convert units to suitable human readable unit

    Args:
        bps (int): bits per second

    Returns:
        str: human readable bps
    """

    unit_suffix = {
        4: {"divider": 1, "unit": ""},
        7: {"divider": 1000, "unit": "k"},
        10: {"divider": 1000000, "unit": "M"},
        13: {"divider": 1000000000, "unit": "G"},
    }
    if bps:
        len_str_bps = len(str(int(bps)))
        for length, suffix in unit_suffix.items():
            if len_str_bps < length:
                str_bps = str(round(bps / suffix["divider"], 2))
                return f"{str_bps} {suffix['unit']}"
    else:
        return False


def calculate_tput_BDP(buffer_size, latency):
    """return max throughtput achievable with given buffer size and latency

    Args:
        buffer_size (int): in bytes
        latency (int): in ms
    """

    buffer_size_bits = buffer_size * 8
    latency_sec = latency * pow(10, -3)

    return buffer_size_bits / latency_sec


def calculate_mem_BDP(latency, bps=1e9):
    """return needed memory setting to reach target throughput with given latency

    Args:
        buffer_size (int): in bytes
        latency (int): in ms
    """
    latency_sec = latency * pow(10, -3)

    return bps * latency_sec


def get_max_tcp_mem(type):
    """get max configured tcp mem

    Args:
        type (str): tcp_wmem or tcp_rmem
    """
    cmd = f"cat /proc/sys/net/ipv4/{type}"
    tcp_mem = run(cmd.split(), capture_output=True, text=True).stdout

    # receiving data
    log.debug(f"tcp_mem {type}: {tcp_mem}")

    return float(tcp_mem.strip().split("\t")[-1])


def flatten(d, parent_key='', sep='.'):
    """Recursively transform a dict in a flatten dict of values

    Args:
        d (dict): dictionary to flatten
        parent_key (str, optional). Defaults to "".
        sep (str, optional): separator between keys. Defaults to ".".

    Returns:
        dict: flatten dict [description]
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.abc.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
