# class for injection dependency testing node_information.py off an active ETH node
import json
import ipc_socket


NODE_SYNCED = False


class IPCTestHarness(ipc_socket.GethInterface):

    def send(self):
        request_data = json.loads(self.request_data)
        if type(request_data) == dict:
            if request_data["method"] == "admin_nodeInfo":
                response_stream = open("geth_test_responses/admin_nodeInfo.json", "r")
                response_data = json.load(response_stream)
                response_stream.close()
                response_data["id"] = request_data["id"]
                return response_data
            elif request_data["method"] == "admin_peers":
                response_stream = open("geth_test_responses/admin_peers.json", "r")
                response_data = json.load(response_stream)
                response_stream.close()
                response_data["id"] = request_data["id"]
                return response_data
            elif request_data["method"] == "eth_gasPrice":
                response_stream = open("geth_test_responses/eth_gasPrice.json", "r")
                response_data = json.load(response_stream)
                response_stream.close()
                response_data["id"] = request_data["id"]
                return response_data
            elif request_data["method"] == "eth_getBlockByNumber":
                if "params" in request_data:
                    args = request_data["params"]
                    if type(args) is list:
                        if type(args[0]) is not str:
                            raise TypeError("Expected string for first param")
                        if args[0] != "latest":
                            raise ValueError("First argument should only be 'latest'")
                        if type(args[1]) is not bool:
                            raise TypeError("Expected bool for second param")
                        if args[1] is not False:
                            raise ValueError("Second argument should only by False")
                        response_stream = open("geth_test_responses/eth_getBlockByNumber.json", "r")
                        response_data = json.load(response_stream)
                        response_stream.close()
                        response_data["id"] = request_data["id"]
                        return response_data
                    else:
                        raise TypeError("Expected params list in request")
            elif request_data["method"] == "eth_syncing":
                if NODE_SYNCED:
                    response_stream = open("geth_test_responses/eth_syncing.json", "r")
                    response_data = json.load(response_stream)
                    response_stream.close()
                    response_data["id"] = request_data["id"]
                    return response_data
                else:
                    response_stream = open("geth_test_responses/eth_not_syncing.json", "r")
                    response_data = json.load(response_stream)
                    response_stream.close()
                    response_data["id"] = request_data["id"]
                    return response_data
            elif request_data["method"] == "eth_getBalance":
                args = request_data["params"]
                if type(args) is list:
                    if type(args[0]) is not str:
                        raise TypeError("Expected string for first param")
                    if type(args[1]) is not str:
                        raise TypeError("Expected string for second param")
                    if args[1] != 'latest':
                        raise ValueError("Second argument should only be 'latest'")
                else:
                    raise TypeError("Expected parameter list in request data")
                response_stream = open("geth_test_responses/eth_getBalance.json", "r")
                response_data = json.load(response_stream)
                response_stream.close()
                response_data["id"] = request_data["id"]
                return response_data
            else:
                raise ValueError("Unsupported method")
        else:
            raise TypeError("Stream output did not JSON deserialize into expected object")
