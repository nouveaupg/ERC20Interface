# singleton which monitors the status of the node

import ipc_socket
import rpc_interface
import util
import logging
import json


class TransactionData:
    def __init__(self, from_address=None, gas=None, gas_price=None, tx_hash=None,
                 to_address=None, wei_value=None, json_data=None):
        if json_data:
            tx_data = json.loads(json_data)
            self.from_address = tx_data["from"]
            self.gas = tx_data["gas"]
            self.gas_price = tx_data["gas_price"]
            self.tx_hash = tx_data["hash"]
            self.to_address = tx_data["to"]
            self.wei_value = tx_data["value"]
        else:
            self.from_address = from_address
            self.gas = gas
            self.gas_price = gas_price
            self.tx_hash = tx_hash
            self.to_address = to_address
            self.wei_value = wei_value

    def __str__(self):
        output = dict()
        output["from"] = self.from_address
        output["gas"] = self.gas
        output["gas_price"] = self.gas_price
        output["hash"] = self.tx_hash
        output["to"] = self.to_address
        output["value"] = self.wei_value
        return json.dumps(output)


class BlockData:
    def __init__(self, block_number=None, block_hash=None, block_timestamp=None, gas_used=None, gas_limit=None,
                 block_size=None, tx_count=None, json_data=None):
        if json_data:
            block_data = json.loads(json_data)
            self.block_number = block_data["block_number"]
            self.block_hash = block_data["block_hash"]
            self.block_timestamp = block_data["block_timestamp"]
            self.gas_used = block_data["gas_used"]
            self.gas_limit = block_data["gas_limit"]
            self.block_size = block_data["block_size"]
            self.tx_count = block_data["tx_count"]
            self.transactions = []
            for each_tx in block_data["transactions"]:
                self.transactions.append(TransactionData(json_data=each_tx))
        else:
            self.block_number = block_number
            self.block_hash = block_hash
            self.block_timestamp = block_timestamp
            self.gas_used = gas_used
            self.gas_limit = gas_limit
            self.block_size = block_size
            self.tx_count = tx_count
            self.transactions = []

    def __str__(self):
        tr_strings = []
        for each_tx in self.transactions:
            tr_strings.append(str(each_tx))
        output = dict()
        output["transactions"] = tr_strings
        output["block_number"] = self.block_number
        output["block_hash"] = self.block_hash
        output["block_timestamp"] = self.block_timestamp
        output["gas_used"] = self.gas_used
        output["gas_limit"] = self.gas_limit
        output["block_size"] = self.block_size
        output["tx_count"] = self.tx_count
        return json.dumps(output)


UNIT_TESTING = False
if UNIT_TESTING:
    import ipc_test_harness


class NodeInfo:
    def __init__(self, logger):
        # Global config
        self.config = util.load_config_from_file()
        if UNIT_TESTING:
            if logger:
                logger.warn("UNIT_TESTING is enabled. Kill process immediately if not in test environment!")
            else:
                print("UNIT_TESTING is enabled. Kill process immediately if not in test environment!")
        self.rpc_interface = rpc_interface.RPCInterface()
        self.logger = logger
        self.enode = None
        self.name = None
        self.eth_node_id = None
        # useful statistics on RPC responsiveness
        # will at least tell us if it's connected to a test harness!
        self.total_rpc_calls = 0
        self.total_rpc_delay = 0
        self.gas_price = None
        self.synced = False
        self.blocks_behind = 0
        self.balance = 0
        self.peers = []
        self.latest_block = None

    def get_block_data(self, block_number):
        result = self._eth_syncing()
        if result and self.synced:
            return self._getBlockData(block_number)

    def update(self):
        result = self._eth_syncing()
        if result and self.synced:
            self._eth_gasPrice()
            self._admin_peers()
            self._getLatestBlock()
            self._getBalance()

    @property
    def output_request(self):
        output = {"synchronized": self.synced,
                  "peers": len(self.peers),
                  "gas_price": self.gas_price,
                  "balance": self.balance,
                  "blocks_behind": self.blocks_behind}
        if self.latest_block:
            for each in self.latest_block.keys():
                output["latest_block_" + each] = self.latest_block[each]
        return output

    def _admin_node_info(self):
        request_data = self.rpc_interface.get_node_info()
        if UNIT_TESTING:
            ipc = ipc_test_harness.IPCTestHarness(request_data, self.config)
        else:
            ipc = ipc_socket.GethInterface(request_data, self.config)
        response_stream = ipc.send()
        response_data = self.rpc_interface.process_response(response_stream)

        if type(response_data) == dict:
            self.total_rpc_delay += response_data["delay"]
            self.total_rpc_calls += 1
            if "result" in response_data:
                result_data = response_data["result"]
                self.enode = result_data["enode"]
                self.name = result_data["name"]
                self.eth_node_id = result_data["id"]
                message = "Successful admin_nodeInfo IPC call: " + str(response_data["delay"]) + " seconds"
                if self.logger:
                    self.logger.info(message)
                else:
                    print(message)
                return True
        message = "admin_nodeInfo API call failed."
        if self.logger:
            self.logger.error(message)
        else:
            print(message)
        return False

    def _admin_peers(self):
        request_data = self.rpc_interface.get_peers()
        if UNIT_TESTING:
            ipc = ipc_test_harness.IPCTestHarness(request_data, self.config)
        else:
            ipc = ipc_socket.GethInterface(request_data, self.config)
        response_stream = ipc.send()
        response_data = self.rpc_interface.process_response(response_stream)

        if type(response_data) == dict:
            self.total_rpc_delay += response_data["delay"]
            self.total_rpc_calls += 1
            if "result" in response_data:
                result_data = response_data["result"]
                self.peers = []
                for each in result_data:
                    self.peers.append(dict(enode=each["enode"],
                                           caps=each["caps"],
                                           id=each["id"],
                                           network=each["network"]))
                message = "Successful admin_Peers IPC call: " + str(response_data["delay"]) + " seconds"
                message += "(" + str(len(self.peers)) + " peers)"
                if self.logger:
                    self.logger.info(message)
                else:
                    print(message)
                return True
        message = "admin_peers IPC call failed."
        if self.logger:
            self.logger.error(message)
        else:
            print(message)
        return False

    def _eth_gasPrice(self):
        request_data = self.rpc_interface.eth_gas_price()
        if UNIT_TESTING:
            ipc = ipc_test_harness.IPCTestHarness(request_data, self.config)
        else:
            ipc = ipc_socket.GethInterface(request_data, self.config)
        response_stream = ipc.send()
        response_data = self.rpc_interface.process_response(response_stream)

        if type(response_data) == dict:
            self.total_rpc_delay += response_data["delay"]
            self.total_rpc_calls += 1
            if "result" in response_data:
                gas_price = util.hex_to_dec(response_data["result"])
                self.gas_price = gas_price
                message = "Successful eth_gasPrice IPC call: " + str(response_data["delay"]) + " seconds"
                if self.logger:
                    self.logger.info(message)
                else:
                    print(message)
                return True
        message = "eth_gasPrice IPC call failed."
        if self.logger:
            self.logger.error(message)
        else:
            print(message)
        return False

    def _getBlockData(self, block_number):
        request_data = self.rpc_interface.get_block_transactions(block_number)
        if UNIT_TESTING:
            ipc = ipc_test_harness.IPCTestHarness(request_data, self.config)
        else:
            ipc = ipc_socket.GethInterface(request_data, self.config)
        response_stream = ipc.send()
        response_data = self.rpc_interface.process_response(response_stream)

        if type(response_data) == dict:
            self.total_rpc_delay += response_data["delay"]
            self.total_rpc_calls += 1
            if "result" in response_data:
                result_data = response_data["result"]
                if result_data is None:
                    message = "getBlockByNumber API call: block still pending"
                    if self.logger:
                        self.logger.error(message)
                    else:
                        print(message)
                    return None
                block_data = BlockData(util.hex_to_dec(result_data["number"]),
                                       result_data["hash"],
                                       util.hex_to_dec(result_data["timestamp"]),
                                       util.hex_to_dec(result_data["gasUsed"]),
                                       util.hex_to_dec(result_data["gasLimit"]),
                                       util.hex_to_dec(result_data["size"]),
                                       len(result_data["transactions"]))

                for each_transaction in result_data["transactions"]:
                    new_obj = TransactionData(each_transaction["from"],
                                              util.hex_to_dec(each_transaction["gas"]),
                                              util.hex_to_dec(each_transaction["gasPrice"]),
                                              each_transaction["hash"],
                                              each_transaction["to"],
                                              util.hex_to_dec(each_transaction["value"]))
                    block_data.transactions.append(new_obj)
                message = "Successful getBlockByNumber IPC call: " + str(response_data["delay"]) + " seconds"
                if self.logger:
                    self.logger.info(message)
                else:
                    print(message)
                return block_data
        message = "getBlockByNumber API call failed."
        if self.logger:
            self.logger.error(message)
        else:
            print(message)
        return None

    def _getLatestBlock(self):
        request_data = self.rpc_interface.get_latest_block()
        if UNIT_TESTING:
            ipc = ipc_test_harness.IPCTestHarness(request_data, self.config)
        else:
            ipc = ipc_socket.GethInterface(request_data, self.config)
        response_stream = ipc.send()
        response_data = self.rpc_interface.process_response(response_stream)

        if type(response_data) == dict:
            self.total_rpc_delay += response_data["delay"]
            self.total_rpc_calls += 1
            if "result" in response_data:
                result_data = response_data["result"]
                self.latest_block = {'gas_limit': util.hex_to_dec(result_data["gasLimit"]),
                                     'gas_used': util.hex_to_dec(result_data["gasUsed"]), 'hash': result_data["hash"],
                                     'number': util.hex_to_dec(result_data["number"]),
                                     'size': util.hex_to_dec(result_data["size"]),
                                     'timestamp': util.hex_to_dec(result_data["timestamp"]),
                                     'transaction_count': len(result_data["transactions"])}
                message = "Successful getBlockByNumber IPC call: " + str(response_data["delay"]) + " seconds"
                if self.logger:
                    self.logger.info(message)
                else:
                    print(message)
                return True
        message = "getBlockByNumber API call failed."
        if self.logger:
            self.logger.error(message)
        else:
            print(message)
        return False

    def _getBalance(self):
        request_data = self.rpc_interface.get_balance(self.config["account"])
        if UNIT_TESTING:
            ipc = ipc_test_harness.IPCTestHarness(request_data, self.config)
        else:
            ipc = ipc_socket.GethInterface(request_data, self.config)
        response_stream = ipc.send()
        response_data = self.rpc_interface.process_response(response_stream)

        if type(response_data) == dict:
            self.total_rpc_delay = response_data["delay"]
            self.total_rpc_calls += 1
            if "result" in response_data:
                message = "Successful eth_getBalance IPC call: " + str(response_data["delay"]) + " seconds"
                if self.logger:
                    self.logger.info(message)
                else:
                    print(message)
                self.balance = util.wei_to_ether(util.hex_to_dec(response_data["result"]))
                return True
        message = "eth_getBalance API call failed."
        if self.logger:
            self.logger.error(message)
        else:
            print(message)
        return False

    def _eth_syncing(self):
        request_data = self.rpc_interface.check_sync()
        if UNIT_TESTING:
            ipc = ipc_test_harness.IPCTestHarness(request_data, self.config)
        else:
            ipc = ipc_socket.GethInterface(request_data, self.config)
        response_stream = ipc.send()
        response_data = self.rpc_interface.process_response(response_stream)

        if type(response_data) == dict:
            self.total_rpc_delay += response_data["delay"]
            self.total_rpc_calls += 1
            if "result" in response_data:
                syncing = response_data["result"]
                if type(syncing) == dict:
                    highest_block = util.hex_to_dec(syncing["highestBlock"])
                    current_block = util.hex_to_dec(syncing["currentBlock"])
                    self.synced = False
                    self.blocks_behind = highest_block - current_block
                else:
                    self.synced = True
                    self.blocks_behind = 0
                message = "Successful eth_syncing API call: " + str(response_data["delay"]) + " seconds"
                if self.logger:
                    self.logger.info(message)
                else:
                    print(message)
                return True
        else:
            message = "eth_syncing API called failed."
            if self.logger:
                self.logger.error(message)
            else:
                print(message)
            return False


if __name__ == "__main__":
    logger = logging.getLogger("NodeInformation")
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)

    node_info = NodeInfo(logger)
    block_data = node_info.get_block_data(7102577)
    import pdb; pdb.set_trace()