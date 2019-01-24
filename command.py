from urllib.request import Request, urlopen, URLError
import ssl
import sys
import util
import json
import logging
import time
from node_information import NodeInfo

HELP = """
python3 command.py <mode>

modes: undirected_command
"""

MAX_ATTEMPTS = 5


class NodeApiError(Exception):
    def __init__(self, error_message):
        self.error_message = error_message

    def __str__(self):
        return "NodeApiException: " + self.error_message


class CommandModule:
    def __init__(self, use_logger=None):
        self.logger = use_logger
        self.node_info = NodeInfo(use_logger)
        self.config = util.load_config_from_file()
        self.max_attempts = self.config['max_rpc_tries']

    def _get_block_data(self, block_number, command_id):
        block_data = node_info.get_block_data(block_number)
        if block_data:
            output = dict(success=True,
                          command_id=command_id,
                          input=str(block_data))
            api_endpoint_url = config["api_endpoint"] + "node_api/command_output/" + config["api_key"]
            logger.debug("Making request to api_endpoint: " + api_endpoint_url)

            req = Request(api_endpoint_url,
                          data=json.dumps(output).encode('utf-8'),
                          headers={'Content-Type': 'application/json',
                                   'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'},
                          method="POST")
            max_attempts = self.max_attempts
            while max_attempts > 0:
                try:
                    urlopen(req, context=ssl_context)
                    logger.info("Node information updated successfully.")
                except URLError as err:
                    logger.error("Error from Node API update endpoint: {0}".format(err))
                    error_delay = config['polling_interval']
                    logger.info("Sleeping for {0} seconds".format(error_delay))
                    time.sleep(error_delay)
                    max_attempts -= 1
                    logger.info("Retrying request to Node API, {0} remaining".format(max_attempts))
        else:
            output = dict(success=False,
                          command_id=command_id,
                          input="",
                          error_message="Could not get block data. (might still be pending)")
            endpoint_url = config["api_endpoint"] + "node_api/command_output/" + config["api_key"]
            logger.debug("Making request to api_endpoint: " + endpoint_url)

            req = Request(endpoint_url,
                          data=json.dumps(output).encode('utf-8'),
                          headers={'Content-Type': 'application/json',
                                   'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'},
                          method="POST")

            max_attempts = self.max_attempts
            while max_attempts > 0:
                try:
                    urlopen(req, context=ssl_ctx)
                    logger.info("Node information updated successfully.")
                    break
                except URLError as err:
                    logger.error("URLError from Node API endpoint: {0}".format(err))
                    error_delay = config['polling_interval']
                    logger.info("Sleeping for {0} seconds".format(error_delay))
                    time.sleep(error_delay)
                    max_attempts -= 1
                    logger.info("Retrying request to Node API, {0} remaining".format(max_attempts))

    def undirected_command(self):
        dispatch_undirected_url = self.config["api_endpoint"]
        dispatch_undirected_url += "node_api/dispatch_undirected_command/" + self.config["api_key"]
        ssl_ctx = ssl.SSLContext()
        ssl_ctx.load_default_certs()
        try:
            response_data = json.load(urlopen(dispatch_undirected_url, context=ssl_ctx))
            if response_data["result"] == "OK":
                command_data = response_data["command_data"]
                if 'get_block_data' in command_data:
                    command_id = command_data["command_id"]
                    block_number = command_data["get_block_data"]
                    self._get_block_data(block_number, command_id)
            elif response_data["result"] == "Error":
                self.logger.error("Node API Error: {0}".format(response_data["error_message"]))
                raise NodeApiError(response_data["error_message"])
            else:
                self.logger.error("Unrecognized response from Node API endpoint: " + self.config["api_endpoint"])

        except URLError as err:
            logger.error("URLError: {0}".format(URLError))
            return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(help)
    mode = sys.argv[1]
    loop = False
    if len(sys.argv) > 2:
        if sys.argv[2] == "loop":
            loop = True

    logger = logging.getLogger("Command Executioner v1")
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)

    node_info = NodeInfo(logger)
    if mode == "undirected_command":
        config = util.load_config_from_file()
        url = config["api_endpoint"] + "node_api/dispatch_undirected_command/" + config["api_key"]
        ssl_context = ssl.SSLContext()
        ssl_context.load_default_certs()
        try:
            remote_file = urlopen(url)
            response_data = json.load(remote_file)
            if response_data["result"] == "OK":
                command_data = response_data["command_data"]
                if 'get_block_data' in command_data:
                    command_id = command_data["command_id"]
                    block_data = node_info.get_block_data(command_data['get_block_data'])
                    if block_data:
                        output = dict(success=True,
                                      command_id=command_id,
                                      input=str(block_data))
                        api_endpoint_url = config["api_endpoint"] + "node_api/command_output/" + config["api_key"]
                        logger.debug("Making request to api_endpoint: " + api_endpoint_url)

                        req = Request(api_endpoint_url,
                                      data=json.dumps(output).encode('utf-8'),
                                      headers={'Content-Type': 'application/json',
                                               'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'},
                                      method="POST")
                        try:
                            response = urlopen(req, context=ssl_context)
                            logger.info("Node information updated successfully.")
                        except URLError as err:
                            logger.error("Error from Node API update endpoint: {0}".format(err))
                            error_delay = config['polling_interval']
                            logger.info("Sleeping for {0} seconds".format(error_delay))
                            time.sleep(error_delay)
                    else:
                        output = dict(success=False,
                                      command_id=command_id,
                                      input="",
                                      error_message="Could not get block data.")
                        api_endpoint_url = config["api_endpoint"] + "node_api/command_output/" + config["api_key"]
                        logger.debug("Making request to api_endpoint: " + api_endpoint_url)

                        req = Request(api_endpoint_url,
                                      data=json.dumps(output).encode('utf-8'),
                                      headers={'Content-Type': 'application/json',
                                               'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'},
                                      method="POST")
                        try:
                            response = urlopen(req, context=ssl_context)
                            logger.info("Node information updated successfully.")
                        except URLError as err:
                            logger.error("Error from Node API update endpoint: {0}".format(err))
                            error_delay = config['polling_interval']
                            logger.info("Sleeping for {0} seconds".format(error_delay))
                            time.sleep(error_delay)

        except URLError:
            logger.error("Error connecting to " + url)