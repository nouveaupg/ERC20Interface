from web3 import Web3
from web3.gas_strategies.rpc import rpc_gas_price_strategy
import time
import logging
import json
import random

CONSOLE_LOG_LEVEL = logging.INFO
FILE_LOG_LEVEL = logging.DEBUG

# Change this to IPC for production
web3 = Web3(Web3.HTTPProvider("http://10.0.0.8:8545"))


def find_target_gas_price(max_gas_price_gwei):
    max_gas_price = Web3.toWei(max_gas_price_gwei, 'gwei')

    web3.eth.setGasPriceStrategy(rpc_gas_price_strategy)
    node_gas_price = web3.eth.generateGasPrice()

    if max_gas_price < node_gas_price:
        node_gwei = web3.fromWei(node_gas_price, 'gwei')
        super().log_error(
            "Node reported gas price of {0} GWei is less than the maximum allowed gas price of {1} GWei".format(
                node_gwei,
                max_gas_price
            ))
        return -1

    # split the difference between maximum and min using triangular RNG towards the minimum

    difference = max_gas_price - node_gas_price
    split = random.triangular(0, 1, 0.25)
    target_gas_price = int(difference * split)

    return target_gas_price


class ERC20Error(Exception):
    """
    Base class for exceptions in this module
    """
    pass


class ExecutionAlreadyFinished(ERC20Error):
    """
    This instance of ExecuteERC20Contract has already called a function
    """

    def __init__(self, last_function):
        self.last_function = last_function


def amount_to_tokens(amount):
    tokens = amount / (10 ** 18)
    return int(tokens)


def tokens_to_amount(tokens):
    amount = tokens * (10 ** 18)
    return int(amount)


class LoggingBase:
    def __init__(self, use_logger=None):
        self.logger = use_logger

    def log_message(self, message):
        if self.logger:
            self.logger.info(message)
        else:
            print("{0} - (INFO) - {1}".format(time.asctime(), message))

    def log_error(self, error_message):
        if self.logger:
            self.logger.error(error_message)
        else:
            print("{0} - (ERROR) - {1}".format(time.asctime(), error_message))


class ExecuteERC20Contract(LoggingBase):
    TOTAL_SUPPLY = 1
    TRANSFER = 2
    BURN_TOKENS = 3
    REMAINING_SUPPLY = 4

    def __init__(self, config, contract_address, use_logger=None):
        self.config = config
        self.contract_address = contract_address
        abi_stream = open(config['abi'], "r")
        self.erc20abi = abi_stream.read()
        abi_stream.close()
        self.tx_hash = None
        self.tx_receipt = None
        self.last_function = None

        super().__init__(use_logger)

    def burn_tokens(self, tokens, gas_price):
        if self.last_function:
            raise ExecutionAlreadyFinished(self.last_function)
        self.last_function = self.BURN_TOKENS

        target_gas_price = find_target_gas_price(gas_price)
        if target_gas_price < 0:
            return
        super().log_message("Using gas price: {0}".format(Web3.fromWei(target_gas_price, 'gwei')))

        web3.eth.defaultAccount = web3.eth.accounts[0]
        web3.personal.unlockAccount(web3.eth.defaultAccount, self.config['account_password'], 30)

        erc20_contract = web3.eth.contract(address=self.contract_address, abi=self.erc20abi)
        amount = tokens_to_amount(tokens)

        gas = erc20_contract.functions.transfer(self.contract_address, amount).estimateGas()
        gas_limit = gas * target_gas_price
        transaction = erc20_contract.functions.transfer(self.contract_address, amount).buildTransaction(
            {'gas_price': gas_limit})
        self.tx_hash = web3.eth.sendTransaction(transaction)
        super().log_message("Sent transaction hash {0}".format(self.tx_hash.hex()))
        return True

    def total_supply(self):
        if self.last_function:
            raise ExecutionAlreadyFinished(self.last_function)
        self.last_function = self.TOTAL_SUPPLY

        erc20_contract = web3.eth.contract(address=self.contract_address, abi=self.erc20abi)
        new_supply = erc20_contract.functions.totalSupply().call()
        tokens = amount_to_tokens(new_supply)
        super().log_message("totalSupply: {0}".format(tokens))

        return tokens

    def remaining_tokens(self):
        if self.last_function:
            raise ExecutionAlreadyFinished(self.last_function)
        self.last_function = self.REMAINING_SUPPLY

        erc20_contract = web3.eth.contract(address=self.contract_address, abi=self.erc20abi)
        amount_remaining = erc20_contract.functions.balanceOf(web3.eth.accounts[0]).call()
        tokens = amount_to_tokens(amount_remaining)
        super().log_message("remaining tokens: {0}".format(tokens))

        return tokens

    def transfer(self, tokens, address, gas_price):
        """
        transfers tokens to address

        :param tokens: integer number of tokens to transfer
        :param address: address (not EIP-55 validated since this is not meant for currency tokens!)
        :param gas_price: maximum gas price in Gwei
        :return: True is successful, otherwise False
        """
        if self.last_function:
            raise ExecutionAlreadyFinished(self.last_function)
        self.last_function = self.TRANSFER

        target_gas_price = find_target_gas_price(gas_price)
        if target_gas_price < 0:
            return

        web3.eth.defaultAccount = web3.eth.accounts[0]
        web3.personal.unlockAccount(web3.eth.defaultAccount, self.config['account_password'], 30)

        erc20_contract = web3.eth.contract(address=self.contract_address, abi=self.erc20abi)
        amount = tokens_to_amount(tokens)
        super().log_message("Using gas price: {0}".format(Web3.fromWei(target_gas_price, 'gwei')))

        gas = erc20_contract.functions.transfer(address, amount).estimateGas()
        gas_limit = gas * target_gas_price
        transaction = erc20_contract.functions.transfer(address, amount).buildTransaction({'gas_price': gas_limit})
        self.tx_hash = web3.eth.sendTransaction(transaction)
        super().log_message("Sent transaction hash {0}".format(self.tx_hash.hex()))
        return True


class PublishERC20Contract(LoggingBase):
    def __init__(self, config, name, symbol, initial_supply, use_logger=None):
        self.config = config
        self.name = name
        self.symbol = symbol
        self.initial_supply = initial_supply
        abi_stream = open(config['abi'], "r")
        self.erc20abi = abi_stream.read()
        abi_stream.close()
        bin_stream = open(config['bin'], "r")
        self.erc20bin = json.load(bin_stream)
        bin_stream.close()
        super().__init__(use_logger)
        #
        self.tx_hash = None
        self.tx_receipt = None

    def deploy(self):
        web3.eth.defaultAccount = web3.eth.accounts[0]
        web3.personal.unlockAccount(web3.eth.defaultAccount, self.config['account_password'], 30)

        erc20_contract = web3.eth.contract(abi=self.erc20abi, bytecode=self.erc20bin["object"])
        self.log_message("Instantiated Ethereum contract")
        gas_estimate = erc20_contract.constructor(self.initial_supply,
                                                  self.name,
                                                  self.symbol).estimateGas()

        super().log_message("Gas estimate: {0}".format(gas_estimate))
        self.tx_hash = erc20_contract.constructor(self.initial_supply,
                                                  self.name,
                                                  self.symbol).transact()

        super().log_message("Received tx_hash: {0}, waiting for receipt...".format(self.tx_hash))
        while 1:
            try:
                self.tx_receipt = web3.eth.waitForTransactionReceipt(self.tx_hash)
                if self.tx_receipt
                    break
            except:
                super().log_message("Received timeout, retrying...")
                continue

        super().log_message("Received transaction receipt, contract address: {0}".format(
            self.tx_receipt.contractAddress))

        return self.tx_receipt.contractAddress


if __name__ == "__main__":
    print("ERC20Interface v1")
    print("Loading configuration...")
    config_stream = open("config/config.json", "r")
    config_data = json.load(config_stream)
    config_stream.close()
    print("Initializing logging...")

    logger = logging.getLogger("ERC20Interface")
    logger.setLevel(logging.INFO)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(config_data['log_file'])
    fh.setLevel(logging.INFO)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("Logging started")

    erc20_remaining_tokens = ExecuteERC20Contract(config_data, "0x476b4077Ff0fC082B6e4C639480BE1DFD2a3e22a",
                                                  use_logger=logger)
    erc20_remaining_tokens.remaining_tokens()
