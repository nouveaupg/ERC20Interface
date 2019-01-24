import random
import time
import json


class RPCInterface:
    def __init__(self):
        self.jsonversion = 2.0
        self.outstanding_requests = []

    def process_request(self, data):
        request_obj = dict(data)
        request_obj["jsonrpc"] = str(self.jsonversion)
        request_obj["id"] = random.randint(0, 100)
        self.outstanding_requests.append(dict(request_id=request_obj["id"],
                                              obj=request_obj,
                                              sent=time.time()))
        return json.dumps(request_obj)

    def process_response(self, json_data):
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as err:
            data = None
        if type(data) == dict and "id" in data:
            output = dict(data)
            ctr = 0
            for each in self.outstanding_requests:
                if each["request_id"] == data["id"]:
                    output["request_obj"] = each.copy()
                    output["delay"] = time.time() - each["sent"]
                    break
                ctr += 1
            if ctr < len(self.outstanding_requests):
                del self.outstanding_requests[ctr]
            return output
        else:
            return data

    def check_sync(self):
        data = {"method": "eth_syncing", "params": []}
        return self.process_request(data)

    def get_balance(self, eth_address):
        data = {"method": "eth_getBalance", "params": [eth_address, "latest"]}
        return self.process_request(data)

    def eth_gas_price(self):
        data = {"method": "eth_gasPrice", "params": []}
        return self.process_request(data)

    def get_node_info(self):
        data = {"method": "admin_nodeInfo", "params": []}
        return self.process_request(data)

    def get_transaction_receipt(self, hash):
        data = {"method": "eth_getTransactionReceipt", "params": [hash]}
        return self.process_request(data)

    def get_block_transactions(self, block_number):
        data = {"method": "eth_getBlockByNumber", "params": [hex(block_number), True]}
        return self.process_request(data)

    def get_latest_block(self):
        data = {"method": "eth_getBlockByNumber", "params": ["latest", False]}
        return self.process_request(data)

    def get_peers(self):
        data = {"method": "admin_peers", "params": []}
        return self.process_request(data)

    def eth_send_transaction(self, _from, data, to=None, gas=None, gas_price=None, value=None):
        params = {"from": _from, "data": data}
        if to:
            params["to"] = to
        if gas:
            params["gas"] = gas
        if gas_price:
            params["gas_price"] = gas_price
        if value:
            params["value"]
        request_data = {"method": "eth_sendTransaction", "params": params}
        return self.process_request(request_data)
