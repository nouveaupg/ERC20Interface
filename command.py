from urllib.request import Request, urlopen, URLError
from node_information import NodeInfo
import erc20
import ssl
import sys
import util
import json
import logging
import time

HELP = """
python3 command.py <mode>

modes: undirected_command (loop)

With loop specified, the command module will request new commands after completing a command
automatically, stopping when it receives any error from the Node API
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
        self.ssl_ctx = ssl.SSLContext()
        self.ssl_ctx.load_default_certs()
        self.command_id = 0

    def _api_response(self, success, command_id, data):
        config = self.config
        if success:
            output = dict(success=True,
                          command_id=command_id,
                          input=data)
            api_endpoint_url = config["api_endpoint"] + "node_api/command_output/" + config["api_key"]
            logger.debug("Making request to api_endpoint: " + api_endpoint_url)

            req = Request(api_endpoint_url,
                          data=json.dumps(output).encode('utf-8'),
                          headers={'Content-Type': 'application/json',
                                   'User-Agent': config['user_agent']},
                          method="POST")
            max_attempts = self.max_attempts
            while max_attempts > 0:
                try:
                    urlopen(req, context=self.ssl_ctx)
                    logger.info("Node information updated successfully.")
                    break
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
                                   'User-Agent': config['user_agent']},
                          method="POST")

            max_attempts = self.max_attempts
            while max_attempts > 0:
                try:
                    urlopen(req, context=self.ssl_ctx)
                    logger.info("Node information updated successfully.")
                    break
                except URLError as err:
                    logger.error("URLError from Node API endpoint: {0}".format(err))
                    error_delay = config['polling_interval']
                    logger.info("Sleeping for {0} seconds".format(error_delay))
                    time.sleep(error_delay)
                    max_attempts -= 1
                    logger.info("Retrying request to Node API, {0} remaining".format(max_attempts))

    def _publish_contract(self, name, symbol, initial_supply, command_id, token_id):
        config = self.config

        new_contract = erc20.PublishERC20Contract(config, name, symbol, initial_supply)
        contract_address = new_contract.deploy()

        if contract_address:
            self._api_response(True, command_id, json.dumps({"new_contract_address": contract_address,
                                                             "token_id": token_id}))
        else:
            self._api_response(False, command_id, json.dumps({"error_message": "Failed to create contract.",
                                                              "token_id": token_id}))

    def _burn_tokens(self, contract_address, tokens, gas_price, token_id):
        config = self.config
        command_id = self.command_id

        contract = erc20.ExecuteERC20Contract(config, contract_address, self.logger)
        result = False
        if contract:
            result = contract.burn_tokens(tokens, gas_price)

        if result:
            self._api_response(True, command_id, json.dumps({"erc20_function": "burn",
                                                             "contract_address": contract_address,
                                                             "tokens": tokens,
                                                             "token_id": token_id,
                                                             "gas_price": gas_price}))
        else:
            self._api_response(False, command_id, {"error_message": "ERC20 burn command failed.",
                                                   "token_id": token_id})

    def _total_supply(self, contract_address, token_id):
        config = self.config
        command_id = self.command_id

        contract = erc20.ExecuteERC20Contract(config, contract_address, self.logger)
        if contract:
            result = contract.total_supply()
            if result:
                self._api_response(True, command_id, json.dumps({"total_supply": result,
                                                                 "token_id": token_id}))
        self._api_response(False, command_id, {"error_message": "ERC20 total supply failed.",
                                               "token_id": token_id})

    def _transfer(self, contract_address, tokens, address, gas_price, token_id):
        config = self.config
        command_id = self.command_id

        contract = erc20.ExecuteERC20Contract(config, contract_address, self.logger)
        if contract:
            result = contract.transfer(tokens, address, gas_price)
            if result:
                output = {"erc20_function": "transfer",
                          "address": address,
                          "gas_price": gas_price,
                          "tokens": tokens,
                          "token_id": token_id,
                          "contract_address": contract_address}
                self._api_response(True, command_id, json.dumps(output))
        self._api_response(False, command_id, {"error_message": "ERC20 transfer failed.",
                                               "token_id": token_id})

    def _get_block_data(self, block_number, command_id):
        config = self.config

        block_data = self.node_info.get_block_data(block_number)
        if block_data:
            output = dict(success=True,
                          command_id=command_id,
                          input=str(block_data))
            api_endpoint_url = config["api_endpoint"] + "node_api/command_output/" + config["api_key"]
            logger.debug("Making request to api_endpoint: " + api_endpoint_url)

            req = Request(api_endpoint_url,
                          data=json.dumps(output).encode('utf-8'),
                          headers={'Content-Type': 'application/json',
                                   'User-Agent': config['user_agent']},
                          method="POST")
            max_attempts = self.max_attempts
            while max_attempts > 0:
                try:
                    urlopen(req, context=self.ssl_ctx)
                    logger.info("Node information updated successfully.")
                    break
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
                                   'User-Agent': config['user_agent']},
                          method="POST")

            max_attempts = self.max_attempts
            while max_attempts > 0:
                try:
                    urlopen(req, context=self.ssl_ctx)
                    logger.info("Node information updated successfully.")
                    break
                except URLError as err:
                    logger.error("URLError from Node API endpoint: {0}".format(err))
                    error_delay = config['polling_interval']
                    logger.info("Sleeping for {0} seconds".format(error_delay))
                    time.sleep(error_delay)
                    max_attempts -= 1
                    logger.info("Retrying request to Node API, {0} remaining".format(max_attempts))

    def directed_command(self):
        directed_dispatch_url = self.config["api_endpoint"]
        directed_dispatch_url += "node_api/dispatch_directed_command/" + self.config["api_key"]
        ssl_ctx = self.ssl_ctx
        try:
            response_data = json.load(urlopen(directed_dispatch_url, context=ssl_ctx))
            if response_data["result"] == "OK":
                command_data = response_data["command_data"]
                if 'command_id' in command_data:
                    command_id = command_data["command_id"]
                    self.command_id = command_id
                else:
                    self.logger.error("Node API Error: {0}".format("command_id not found in response_data"))
                    raise NodeApiError("command_id not found in response_data")
                if 'erc20_function' in command_data:
                    if command_data['erc20_function'] == "publish":
                        token_name = command_data["token_name"]
                        token_symbol = command_data["token_symbol"]
                        token_count = command_data["token_count"]
                        token_id = command_data["token_id"]
                        self._publish_contract(token_name, token_symbol, token_count, command_id, token_id)
                    if command_data['erc20_function'] == "burn":
                        contract_address = command_data["contract_address"]
                        token_count = command_data["token_count"]
                        gas_price = command_data["gas_price"]
                        token_id = command_data["token_id"]
                        self._burn_tokens(contract_address, token_count, gas_price, token_id)
                    elif command_data['erc20_function'] == "transfer":
                        contract_address = command_data["contract_address"]
                        token_count = command_data["token_count"]
                        gas_price = command_data["gas_price"]
                        address = command_data["address"]
                        token_id = command_data["token_id"]
                        self._transfer(contract_address, token_count, address, gas_price, token_id)
                    elif command_data['erc20_function'] == "total_supply":
                        contract_address = command_data["contract_address"]
                        token_id = command_data["token_id"]
                        self._total_supply(contract_address, token_id)

            elif response_data["result"] == "Error":
                self.logger.error("Node API Error: {0}".format(response_data["error_message"]))
                raise NodeApiError(response_data["error_message"])
            else:
                self.logger.error("Unrecognized response from Node API endpoint: " + self.config["api_endpoint"])
        except URLError as err:
            logger.error("URLError: {0}".format(err))

    def undirected_command(self):
        dispatch_undirected_url = self.config["api_endpoint"]
        dispatch_undirected_url += "node_api/dispatch_undirected_command/" + self.config["api_key"]
        ssl_ctx = self.ssl_ctx
        try:
            response_data = json.load(urlopen(dispatch_undirected_url, context=ssl_ctx))
            if response_data["result"] == "OK":
                command_data = response_data["command_data"]
                if 'get_block_data' in command_data:
                    command_id = command_data["command_id"]
                    block_number = command_data["get_block_data"]
                    self.logger.info("Received get_block_data: {0} command_id: {1}".format(block_number, command_id))
                    self._get_block_data(block_number, command_id)
            elif response_data["result"] == "Error":
                self.logger.error("Node API Error: {0}".format(response_data["error_message"]))
                raise NodeApiError(response_data["error_message"])
            else:
                self.logger.error("Unrecognized response from Node API endpoint: " + self.config["api_endpoint"])

        except URLError as err:
            logger.error("URLError: {0}".format(err))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(help)
        exit(0)
    mode = sys.argv[1]
    loop = False
    if len(sys.argv) > 2:
        if sys.argv[2] == "loop":
            loop = True

    logger = logging.getLogger("Command Executor v2")
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)

    command_module = CommandModule(logger)
    if mode == "undirected_command":
        if loop:
            logger.info("Starting undirected command loop.")
            try:
                while True:
                    command_module.undirected_command()
            except NodeApiError:
                logger.info("Ending undirected command loop.")
        else:
            command_module.undirected_command()
    elif mode == "directed_command":
        if loop:
            logger.info("Starting directed command loop.")
            try:
                while True:
                    command_module.directed_command()
            except NodeApiError:
                logger.info("Ending directed command loop.")
        else:
            command_module.directed_command()
