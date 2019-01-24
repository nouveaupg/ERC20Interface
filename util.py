import json

# should probably change this in production to an absolute path
DEFAULT_CONFIG_PATH = "/home/ethereum/ERC20Interface/config/config.json"


def wei_to_ether(wei):
    return 1.0 * wei / 10**18


def ether_to_wei(ether):
    return ether * 10**18


def hex_to_dec(x):
    return int(x, 16)


def clean_hex(d):
    return hex(d).rstrip('L')


def load_config_from_file(filename=DEFAULT_CONFIG_PATH):
    try:
        fp = open(filename, "r")
        json_data = json.load(fp)
        fp.close()
        return json_data
    except IOError as e:
        if e.errno == 2:
            return None