import json
import os
import random
import time
from datetime import datetime, timezone

import requests
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import (
    EntryFunction,
    TransactionArgument,
    TransactionPayload
)
from aptos_sdk.type_tag import TypeTag, StructTag
from tqdm import tqdm

from config import (
    ATTEMPTS_COUNT,
    TOKENS_SLIPPAGES,
    AUTODECREASE_SLIPPAGE,
    AUTODECREASE_SLIPPAGE_STEP,
    SLEEP_TIME, TOKENS,
)
from core.clients.base_client import BaseClient
from core.clients.utils import (
    get_liquidswap_type_args,
    get_liquidswap_resource_type,
    get_simple_swap_type_args,
    extract_amount_y_out_value,
    get_old_aptos_name_data,
    get_thala_swap_type_args,
    extract_amount_out_value,
    get_old_aptos_name_wia_wapal
)
from core.constants import (
    TORTUGA,
    APT_TOKEN,
    DITTO,
    APTOS_SEND,
    LAYERZERO_BRIDGE,
    APTOS_NAMES,
    LIQUIDSWAP_V2,
    PANCAKESWAP,
    LIQUIDSWAP_V1,
    SUSHISWAP,
    THALASWAP,
    USDC_TOKEN,
    GATOR,
    PONTEM_URL,
    GRAPHQL_URL,
    LIQUIDSWAP_V1_TOKENS,
    APTOSLABS_URL,
    KANALABS_URL,
    ARIES_URL,
    THAPT_TOKEN, ECONIA_PRICES_URL
)
from core.decorators import retry_on_error
from core.models.token import Token
from core.models.wallet import Wallet
from logger import logger


class Client(BaseClient):
    def __init__(self, wallet: Wallet):
        super().__init__(wallet)

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def aptos_send(self, amount: float, address: str) -> bool:
        try:
            logger.info(f"[CLIENT] Try to send {amount} APT to address {address}")

            self.client_config.max_gas_amount = self.custom_randint(1000, 2000, 100)

            address = AccountAddress.from_hex(address)
            amount_wei = APT_TOKEN.to_wei(amount)

            payload = EntryFunction.natural(
                APTOS_SEND["script"],
                APTOS_SEND["function"],
                [],
                [
                    TransactionArgument(address, Serializer.struct),
                    TransactionArgument(amount_wei, Serializer.u64),
                ]
            )

            tx_hash = self.send_tx(payload=payload)
            if self.verify_tx(tx_hash):
                self.client_config.max_gas_amount = self.custom_randint(7000, 9000, 100)
                return True

        except Exception as e:
            error = str(e)
            if "EINSUFFICIENT_BALANCE" in error:
                logger.error(f"[CLIENT] Send {amount} aptos to address {address} error: not enough balance")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            elif "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[CLIENT] Problem with sequence number, retrying...")
            else:
                logger.error(f"[CLIENT] Error: {str(e)}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def claim_bridged_tokens(self, token: Token) -> bool:
        try:
            logger.info(f"[BRIDGE] Try to claim bridged {token.symbol} by layerzero bridge")

            token = TypeTag(StructTag.from_str(token.contract_address))

            payload = EntryFunction.natural(
                LAYERZERO_BRIDGE["script"],
                LAYERZERO_BRIDGE["function"],
                [token],
                []
            )

            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            logger.error(f"[BRIDGE] Claim bridged {token.symbol} by layerzero bridge error: {str(e)}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def liquidswap_swap(self, token_from: Token, token_to: Token, amount_from: float, new_token_slippage=None) -> bool:
        try:
            logger.info(f"[LIQUIDSWAP] Try to swap {amount_from} {token_from.symbol} to {token_to.symbol}")

            if token_from in LIQUIDSWAP_V1_TOKENS or token_to in LIQUIDSWAP_V1_TOKENS:
                liquidswap_data = LIQUIDSWAP_V1
            else:
                liquidswap_data = LIQUIDSWAP_V2

            reserve_value_ratio = self._get_liquidswap_reserve_value_ratio(
                resource_account=AccountAddress.from_hex(liquidswap_data["resource_account"]),
                token_from=token_from,
                token_to=token_to
            )

            slippage = TOKENS_SLIPPAGES[token_to] if token_from == APT_TOKEN else TOKENS_SLIPPAGES[token_from]
            if new_token_slippage is not None:
                slippage = new_token_slippage

            amount_to = token_to.to_wei(amount_from * reserve_value_ratio * slippage)
            amount_from = token_from.to_wei(amount_from)

            payload = EntryFunction.natural(
                liquidswap_data["script"],
                liquidswap_data["function"],
                get_liquidswap_type_args(token_from=token_from, token_to=token_to),
                [
                    TransactionArgument(amount_from, Serializer.u64),
                    TransactionArgument(amount_to, Serializer.u64),
                ],
            )

            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "ERR_COIN_OUT_NUM_LESS_THAN_EXPECTED_MINIMUM" in error:
                logger.warning(
                    f"[LIQUIDSWAP] High loss coefficient while swap from {token_from.symbol} to {token_to.symbol}"
                )
                if AUTODECREASE_SLIPPAGE:
                    new_slippage = slippage - AUTODECREASE_SLIPPAGE_STEP
                    logger.warning(f"Decreasing slippage from {slippage * 100}% to {new_slippage * 100}%")
                    return self.liquidswap_swap(
                        token_from=token_from,
                        token_to=token_to,
                        amount_from=token_from.from_wei(amount_from),
                        new_token_slippage=new_slippage
                    )
            elif "list index out of range" in error:
                logger.warning("[LIQUIDSWAP] Problem with simulate tx")
            elif "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[LIQUIDSWAP] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[LIQUIDSWAP] Error: {str(e)}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def pancakeswap_swap(self, token_from: Token, token_to: Token, amount_from: float, new_token_slippage=None) -> bool:
        try:
            logger.info(f"[PANCAKESWAP] Try to swap {amount_from} {token_from.symbol} to {token_to.symbol}")

            amount_from = token_from.to_wei(amount_from)

            simulation_payload = EntryFunction.natural(
                PANCAKESWAP["script"],
                PANCAKESWAP["function"],
                get_simple_swap_type_args(token_from=token_from, token_to=token_to),
                [
                    TransactionArgument(amount_from, Serializer.u64),
                    TransactionArgument(0, Serializer.u64),
                ]
            )

            tx = self.create_bcs_transaction(self.signer, TransactionPayload(simulation_payload))
            simulation = self.simulate_transaction(tx, self.signer)

            slippage = TOKENS_SLIPPAGES[token_to] if token_from == APT_TOKEN else TOKENS_SLIPPAGES[token_from]
            if new_token_slippage is not None:
                slippage = new_token_slippage

            amount_out = int(extract_amount_y_out_value(simulation_data=simulation) * slippage)

            payload = EntryFunction.natural(
                PANCAKESWAP["script"],
                PANCAKESWAP["function"],
                get_simple_swap_type_args(token_from=token_from, token_to=token_to),
                [
                    TransactionArgument(amount_from, Serializer.u64),
                    TransactionArgument(amount_out, Serializer.u64),
                ]
            )
            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "ERR_COIN_OUT_NUM_LESS_THAN_EXPECTED_MINIMUM" in error:
                logger.warning(
                    f"[PANCAKESWAP] High loss coefficient while swap from {token_from.symbol} to {token_to.symbol}"
                )
                if AUTODECREASE_SLIPPAGE:
                    new_slippage = slippage - AUTODECREASE_SLIPPAGE_STEP
                    logger.warning(f"Decreasing slippage from {slippage * 100}% to {new_slippage * 100}%")
                    return self.pancakeswap_swap(
                        token_from=token_from,
                        token_to=token_to,
                        amount_from=token_from.from_wei(amount_from),
                        new_token_slippage=new_slippage
                    )
            elif "list index out of range" in error:
                logger.warning("[PANCAKESWAP] Problem with simulate tx")
            elif "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[PANCAKESWAP] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[PANCAKESWAP] Error: {str(e)}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def sushiswap_swap(self, token_from: Token, token_to: Token, amount_from: float, new_token_slippage=None) -> bool:
        try:
            logger.info(f"[SUSHISWAP] Try to swap {amount_from} {token_from.symbol} to {token_to.symbol}")

            amount_from = token_from.to_wei(amount_from)

            simulation_payload = EntryFunction.natural(
                SUSHISWAP["script"],
                SUSHISWAP["function"],
                get_simple_swap_type_args(token_from=token_from, token_to=token_to),
                [
                    TransactionArgument(amount_from, Serializer.u64),
                    TransactionArgument(0, Serializer.u64),
                ]
            )

            tx = self.create_bcs_transaction(self.signer, TransactionPayload(simulation_payload))
            simulation = self.simulate_transaction(tx, self.signer)

            slippage = TOKENS_SLIPPAGES[token_to] if token_from == APT_TOKEN else TOKENS_SLIPPAGES[token_from]
            if new_token_slippage is not None:
                slippage = new_token_slippage

            amount_out = int(extract_amount_y_out_value(simulation_data=simulation) * slippage)

            payload = EntryFunction.natural(
                SUSHISWAP["script"],
                SUSHISWAP["function"],
                get_simple_swap_type_args(token_from=token_from, token_to=token_to),
                [
                    TransactionArgument(amount_from, Serializer.u64),
                    TransactionArgument(amount_out, Serializer.u64),
                ]
            )
            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "ERR_COIN_OUT_NUM_LESS_THAN_EXPECTED_MINIMUM" in error:
                logger.warning(
                    f"[SUSHISWAP] High loss coefficient while swap from {token_from.symbol} to {token_to.symbol}"
                )
                if AUTODECREASE_SLIPPAGE:
                    new_slippage = slippage - AUTODECREASE_SLIPPAGE_STEP
                    logger.warning(f"Decreasing slippage from {slippage * 100}% to {new_slippage * 100}%")
                    return self.sushiswap_swap(
                        token_from=token_from,
                        token_to=token_to,
                        amount_from=token_from.from_wei(amount_from),
                        new_token_slippage=new_slippage
                    )
            elif "list index out of range" in error:
                logger.warning("[SUSHISWAP] Problem with simulate tx")
            elif "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[SUSHISWAP] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.warning(f"[SUSHISWAP] Error while swap: {error}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def thala_swap(self, token_from: Token, token_to: Token, amount_from: float, new_token_slippage=None) -> bool:
        try:
            logger.info(f"[THALASWAP] Try to swap {amount_from} {token_from.symbol} to {token_to.symbol}")

            amount_from = token_from.to_wei(amount_from)

            simulation_payload = EntryFunction.natural(
                THALASWAP["script"],
                THALASWAP["function"],
                get_thala_swap_type_args(token_from=token_from, token_to=token_to),
                [
                    TransactionArgument(amount_from, Serializer.u64),
                    TransactionArgument(0, Serializer.u64),
                ]
            )

            tx = self.create_bcs_transaction(self.signer, TransactionPayload(simulation_payload))
            simulation = self.simulate_transaction(tx, self.signer)

            slippage = TOKENS_SLIPPAGES[token_to] if token_from == APT_TOKEN else TOKENS_SLIPPAGES[token_from]
            if new_token_slippage is not None:
                slippage = new_token_slippage

            amount_out = int(extract_amount_out_value(simulation_data=simulation) * slippage)

            payload = EntryFunction.natural(
                THALASWAP["script"],
                THALASWAP["function"],
                get_thala_swap_type_args(token_from=token_from, token_to=token_to),
                [
                    TransactionArgument(amount_from, Serializer.u64),
                    TransactionArgument(amount_out, Serializer.u64),
                ]
            )
            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "ERR_COIN_OUT_NUM_LESS_THAN_EXPECTED_MINIMUM" in error:
                logger.warning(
                    f"[THALASWAP] High loss coefficient while swap from {token_from.symbol} to {token_to.symbol}"
                )
                if AUTODECREASE_SLIPPAGE:
                    new_slippage = slippage - AUTODECREASE_SLIPPAGE_STEP
                    logger.warning(f"Decreasing slippage from {slippage * 100}% to {new_slippage * 100}%")
                    return self.thala_swap(
                        token_from=token_from,
                        token_to=token_to,
                        amount_from=token_from.from_wei(amount_from),
                        new_token_slippage=new_slippage
                    )
            elif "list index out of range" in error:
                logger.warning("[THALASWAP] Problem with simulate tx")
            elif "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[THALASWAP] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.warning(f"[THALASWAP] Error while swap: {e}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def gator_deposit(self, amount: float) -> bool:
        try:
            logger.info(f"[GATOR] Try to deposit {amount} zUSDC")

            amount_wei = USDC_TOKEN.to_wei(amount)

            self.econia_enter_market()

            payload = EntryFunction.natural(
                GATOR["script_user"],
                GATOR["function_deposit"],
                [
                    TypeTag(StructTag.from_str(USDC_TOKEN.contract_address))
                ],
                [
                    TransactionArgument(7, Serializer.u64),
                    TransactionArgument(0, Serializer.u64),
                    TransactionArgument(amount_wei, Serializer.u64)
                ],
            )

            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[GATOR] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[GATOR] Error while deposit: {e}")
            return False

    def sleep(self) -> None:
        try:
            for _ in tqdm(range(random.randint(*SLEEP_TIME)), colour="green"):
                time.sleep(1)

        except Exception as e:
            logger.error(f"Sleep error: {str(e)}")

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def econia_enter_market(self) -> bool:
        try:
            url = PONTEM_URL
            proxy = None if self.proxy is None else {"https": f"http://{self.proxy}"}
            response = requests.post(url=url, json={
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user::has_market_account_by_market_id",
                "type_arguments": [],
                "arguments": [str(self.address), "7"]
            }, proxies=proxy)
            data = response.json()

            if not data[0]:
                logger.info(f"[CLIENT] Try to enter markets")

                payload = EntryFunction.natural(
                    GATOR["script_user"],
                    GATOR["function_register"],
                    [
                        TypeTag(StructTag.from_str(APT_TOKEN.contract_address)),
                        TypeTag(StructTag.from_str(USDC_TOKEN.contract_address))
                    ],
                    [
                        TransactionArgument(7, Serializer.u64),
                        TransactionArgument(0, Serializer.u64)
                    ],
                )
                tx_hash = self.send_tx(payload=payload)
                self.verify_tx(tx_hash)
                self.sleep()
            return True

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[GATOR_REGISTER] Problem with sequence number, retrying...")
            else:
                logger.warning(f"[GATOR_REGISTER] Error while register: {e}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def gator_place_order(self) -> bool:
        try:
            logger.info(f"[GATOR] Try to place order")

            payload = {
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::market::place_market_order_user_entry",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
                ],
                "arguments": [
                    "7",
                    "0x63e39817ec41fad2e8d0713cc906a5f792e4cd2cf704f8b5fab6b2961281fa11",
                    False,
                    "10000",
                    3
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[GATOR_ORDER] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.warning(f"[GATOR_ORDER] Error while placing order: {error}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def gator_withdraw_apt(self) -> bool:
        try:
            logger.info(f"[GATOR] Try to withdraw APT")

            url = PONTEM_URL
            proxy = None if self.proxy is None else {"https": f"http://{self.proxy}"}
            response = requests.post(url=url, json=self.get_gator_balance_payload(), proxies=proxy)
            data = response.json()

            payload = EntryFunction.natural(
                GATOR["script_user"],
                GATOR["function_withdraw"],
                [
                    TypeTag(StructTag.from_str(APT_TOKEN.contract_address))
                ],
                [
                    TransactionArgument(7, Serializer.u64),
                    TransactionArgument(int(data[0]["base_available"]), Serializer.u64)
                ],
            )

            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[GATOR_WITHDRAW] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.warning(f"[GATOR_WITHDRAW] Error while withdraw: {error}")
            return False

    def get_gator_balance_payload(self):
        return {
            "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user::get_market_account",
            "type_arguments": [],
            "arguments": [
                self.address,
                "7",
                "0"
            ]
        }

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def swapgpt_deposit(self, amount: float) -> bool:
        try:
            self.econia_enter_market()
            logger.info(f"[SWAPGPT] Try to deposit {amount} APT")

            amount_wei = APT_TOKEN.to_wei(amount)

            payload = {
                "function": "0x1c3206329806286fd2223647c9f9b130e66baeb6d7224a18c1f642ffe48f3b4c::SwapGPT_Econia_Wrapper::register_market_and_deposit_coins_entry",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
                ],
                "arguments": [
                    "7",
                    False,
                    "0",
                    True,
                    str(amount_wei),
                    False,
                    "0"
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[SWAPGPT] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[SWAPGPT] Error while deposit: {str(e)}")
            return False

    def get_swapgpt_deposited_balance(self):
        url = APTOSLABS_URL
        proxy = None if self.proxy is None else {"https": f"http://{self.proxy}"}
        response = requests.post(url=url, json=self.get_econia_balance_payload(), proxies=proxy)
        data = response.json()

        apt_deposited_balance = data[0]

        return apt_deposited_balance

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def swapgpt_buy_usdc(self) -> bool:
        try:
            amount = APT_TOKEN.from_wei(float(self.get_swapgpt_deposited_balance()["base_available"]))
            logger.info(f"[SWAPGPT] Try to sell {amount} APT")

            payload = {
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::market::place_market_order_user_entry",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
                ],
                "arguments": [
                    "7",
                    "0xd0b17bea776bb87b70b2fb2ca631014f0ca94fc1acde4b8ff1a763f4172aa6c4",
                    True,
                    str(int(amount * 1000)),
                    0
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[SWAPGPT] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[SWAPGPT] Error while deposit: {e}")
            return False


    @retry_on_error(tries=ATTEMPTS_COUNT)
    def swapgpt_buy_apt(self) -> bool:
        try:
            amount = USDC_TOKEN.from_wei(int(self.get_swapgpt_deposited_balance()["quote_available"]))
            logger.info(f"[SWAPGPT] Try to sell {amount} USDC")

            usdc_price, apt_price = self.get_econia_prices()

            amount = round((amount * usdc_price / apt_price), 3)

            if amount < 0.5:
                logger.error("Amount of USDC to buy APT is less, than 0.5 APT")
                return False

            payload = {
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::market::place_market_order_user_entry",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC",
                ],
                "arguments": [
                    "7",
                    "0xd0b17bea776bb87b70b2fb2ca631014f0ca94fc1acde4b8ff1a763f4172aa6c4",
                    False,
                    str(int(amount * 1000)),
                    0
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[SWAPGPT] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[SWAPGPT] Error while deposit: {e}")
            return False

    def get_econia_prices(self):
        url = ECONIA_PRICES_URL

        payload = {
            "types":
                [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
                ]
        }

        proxy = None if self.proxy is None else {"https": f"http://{self.proxy}"}
        response = requests.post(url=url, json=payload, proxies=proxy)
        data = response.json()

        return float(data[1]["price"]), float(data[0]["price"])

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def swapgpt_withdraw(self) -> bool:
        try:
            logger.info(f"[SWAPGPT] Try to withdraw APT")

            url = APTOSLABS_URL
            proxy = None if self.proxy is None else {"https": f"http://{self.proxy}"}
            response = requests.post(url=url, json=self.get_econia_balance_payload(), proxies=proxy)
            data = response.json()

            apt_balance = data[0]["base_available"]

            payload = {
                "function": "0x1c3206329806286fd2223647c9f9b130e66baeb6d7224a18c1f642ffe48f3b4c::SwapGPT_Econia_Wrapper::withdraw_coins_entry",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
                ],
                "arguments": [
                    "7",
                    True,
                    apt_balance,
                    False,
                    "0"
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[SWAPGPT] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[SWAPGPT] Error while deposit: {e}")
            return False

    def get_econia_balance_payload(self):
        return {
            "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user::get_market_account",
            "type_arguments": [],
            "arguments": [self.address, "7", "0"],
            "type": "entry_function_payload"
        }

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def kanalabs_deposit(self, amount: float) -> bool:
        try:
            self.econia_enter_market()
            logger.info(f"[KANALABS] Try to deposit {amount} APT")

            amount_wei = APT_TOKEN.to_wei(amount)

            payload = {
                "function": "0x9538c839fe490ccfaf32ad9f7491b5e84e610ff6edc110ff883f06ebde82463d::wrapper::deposit_and_register_base",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
                ],
                "arguments": [
                    str(amount_wei),
                    "7"
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[KANALABS] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[KANALABS] Error while deposit: {e}")
            return False

    def get_kanalabs_deposited_balance(self):
        url = KANALABS_URL
        proxy = None if self.proxy is None else {"https": f"http://{self.proxy}"}
        response = requests.post(url=url, json=self.get_econia_balance_payload(), proxies=proxy, headers={
            'Origin': "https://tradebook.kanalabs.io"
        })
        data = response.json()
        apt_deposited_balance = data[0]

        return apt_deposited_balance

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def kanalabs_buy_usdc(self) -> bool:
        try:
            amount = APT_TOKEN.from_wei(float(self.get_kanalabs_deposited_balance()["base_available"]))
            logger.info(f"[KANALABS] Try to sell {amount} APT")

            payload = {
                "function": "0x9538c839fe490ccfaf32ad9f7491b5e84e610ff6edc110ff883f06ebde82463d::wrapper::place_market_order_user_entry_without_deposit",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
                ],
                "arguments": [
                    str(int(amount * 1000)),
                    "7",
                    "0xd718181a753f5b759518d9b896018dd7eb3d77d80bf90ba77fffaf678f781929",
                    True,
                    3
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[KANALABS] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[KANALABS] Error while sell APT: {e}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def kanalabs_buy_apt(self) -> bool:
        try:
            amount = USDC_TOKEN.from_wei(float(self.get_kanalabs_deposited_balance()["quote_available"]))
            logger.info(f"[KANALABS] Try to sell {amount} USDC")

            usdc_price, apt_price = self.get_econia_prices()

            amount = round((amount * usdc_price / apt_price), 3)

            if amount < 0.5:
                logger.error("Amount of USDC to buy APT is less, than 0.5 APT")
                return False

            payload = {
                "function": "0x9538c839fe490ccfaf32ad9f7491b5e84e610ff6edc110ff883f06ebde82463d::wrapper::place_market_order_user_entry_without_deposit",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC",
                ],
                "arguments": [
                    str(int(amount * 1000)),
                    "7",
                    "0xd718181a753f5b759518d9b896018dd7eb3d77d80bf90ba77fffaf678f781929",
                    False,
                    3
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[KANALABS] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[KANALABS] Error while deposit: {e}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def kanalabs_withdraw(self) -> bool:
        try:
            logger.info(f"[KANALABS] Try to withdraw APT")

            apt_balance = self.get_kanalabs_deposited_balance()["base_available"]

            payload = {
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user::withdraw_to_coinstore",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin"
                ],
                "arguments": [
                    "7",
                    apt_balance
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[KANALABS] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[KANALABS] Error while withdraw: {e}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def aries_deposit(self, amount: float) -> bool:
        try:
            self.econia_enter_market()
            logger.info(f"[ARIES] Try to deposit {amount} APT")

            amount_wei = APT_TOKEN.to_wei(amount)

            payload = {
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user::deposit_from_coinstore",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin"
                ],
                "arguments": [
                    "7",
                    "0",
                    str(amount_wei)
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[ARIES] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[ARIES] Error while deposit: {e}")
            return False

    def get_aries_deposited_balance(self):
        proxy = None if self.proxy is None else {"https": f"http://{self.proxy}"}

        url_to_get_address = (
                "https://fullnode.mainnet.aptoslabs.com/v1/accounts/" + self.address + "/resource/"
                "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user::MarketAccounts"
        )

        response = requests.get(url=url_to_get_address).json()
        aries_address = response["data"]["map"]["handle"]

        url = ARIES_URL + aries_address + "/item"

        response = requests.post(url=url, json={
            "key": "129127208515966861312",
            "key_type": "u128",
            "value_type": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user::MarketAccount"
        }, proxies=proxy)
        data = response.json()

        return data

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def aries_buy_usdc(self) -> bool:
        try:
            amount = APT_TOKEN.from_wei(float(self.get_aries_deposited_balance()["base_available"]))

            logger.info(f"[ARIES] Try to sell {amount} APT")

            payload = {
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::market::place_market_order_user_entry",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
                ],
                "arguments": [
                    "7",
                    "0x2e51979739db25dc987bd24e1a968e45cca0e0daea7cae9121f68af93e8884c9",
                    True,
                    str(int(amount * 1000)),
                    3
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[ARIES] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[ARIES] Error while sell APT: {e}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def aries_buy_apt(self) -> bool:
        try:
            amount = USDC_TOKEN.from_wei(float(self.get_aries_deposited_balance()["quote_available"]))
            logger.info(f"[ARIES] Try to sell {amount} USDC")

            usdc_price, apt_price = self.get_econia_prices()

            amount = round((amount * usdc_price / apt_price), 3)

            if amount < 0.5:
                logger.error("Amount of USDC to buy APT is less, than 0.5 APT")
                return False

            payload = {
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::market::place_market_order_user_entry",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC",
                ],
                "arguments": [
                    "7",
                    "0x2e51979739db25dc987bd24e1a968e45cca0e0daea7cae9121f68af93e8884c9",
                    False,
                    str(int(amount * 1000)),
                    3
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[ARIES] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[ARIES] Error while deposit: {e}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def aries_withdraw(self) -> bool:
        try:
            logger.info(f"[ARIES] Try to withdraw APT")

            apt_balance = self.get_aries_deposited_balance()["base_available"]

            payload = {
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user::withdraw_to_coinstore",
                "type_arguments": [
                    APT_TOKEN.contract_address
                ],
                "arguments": [
                    "7",
                    apt_balance
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[ARIES] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[ARIES] Error while withdraw: {e}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def econia_full_withdraw(self) -> bool:
        try:
            logger.info(f"[ECONIA WITHDRAW] Try to withdraw zUSDC")

            data = self.get_kanalabs_deposited_balance()

            usdc_balance = data["quote_available"]
            apt_balance = data["base_available"]

            payload = {
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user::withdraw_to_coinstore",
                "type_arguments": [
                    USDC_TOKEN.contract_address
                ],
                "arguments": [
                    "7",
                    usdc_balance
                ],
                "type": "entry_function_payload"
            }

            if int(usdc_balance) > 0:
                tx_hash = self.send_json_tx(payload=payload)
                self.verify_tx(tx_hash)

                self.sleep()
            else:
                logger.info("zUSDC balance = 0")

            logger.info(f"[ECONIA WITHDRAW] Try to withdraw APT")

            payload = {
                "function": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user::withdraw_to_coinstore",
                "type_arguments": [
                    APT_TOKEN.contract_address
                ],
                "arguments": [
                    "7",
                    apt_balance
                ],
                "type": "entry_function_payload"
            }

            if int(apt_balance) > 0:
                tx_hash = self.send_json_tx(payload=payload)
                return self.verify_tx(tx_hash)
            else:
                logger.info("APT balance = 0")
                return True

        except Exception as e:
            error = str(e)
            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[ARIES] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[ARIES] Error while withdraw: {e}")
            return False

    def autoswap_to_usdc_if_required(self, deposit_amount, usdc_balance, balance) -> bool:
        try:
            apt_price = self.get_coingecko_token_prices_in_usd()
            apt_price = apt_price[APT_TOKEN]

            apt_to_swap = (deposit_amount - usdc_balance) / apt_price * 1.01

            if apt_to_swap < APT_TOKEN.from_wei(balance):
                self.liquidswap_swap(
                    token_from=APT_TOKEN,
                    token_to=USDC_TOKEN,
                    amount_from=apt_to_swap
                )

                self.sleep()
                return True
            elif apt_to_swap < self.get_all_tokens_balance_in_apt():
                for token in TOKENS.values():
                    token_balance = token.from_wei(self.get_token_balance(token))

                    if token_balance > 0 and token != APT_TOKEN:
                        if token == THAPT_TOKEN:
                            self.thala_swap(
                                token_from=token,
                                token_to=APT_TOKEN,
                                amount_from=token_balance
                            )
                        else:
                            self.liquidswap_swap(
                                token_from=token,
                                token_to=APT_TOKEN,
                                amount_from=token_balance
                            )
                        self.sleep()

                self.liquidswap_swap(
                    token_from=APT_TOKEN,
                    token_to=USDC_TOKEN,
                    amount_from=apt_to_swap
                )

                self.sleep()
                return True
            else:
                logger.error(
                    f"APT {APT_TOKEN.from_wei(balance)} balance is less, than required ({apt_to_swap})")
                raise Exception("Insufficient balance for activity")
        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[AUTOSWAP] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            elif "Insufficient balance for activity" in str(e):
                raise Exception(e)
            else:
                logger.warning(f"[AUTOSWAP] Error while swap: {error}")
            return False

    def autoswap_to_apt_if_required(self, aptos_to_deposit, balance) -> bool:
        try:
            balance = APT_TOKEN.from_wei(balance)
            apt_to_swap = aptos_to_deposit - (balance - 0.01)

            if apt_to_swap < self.get_all_tokens_balance_in_apt():
                for token in TOKENS.values():
                    token_balance = token.from_wei(self.get_token_balance(token))

                    if token_balance > 0 and token != APT_TOKEN:
                        if token == THAPT_TOKEN:
                            self.thala_swap(
                                token_from=token,
                                token_to=APT_TOKEN,
                                amount_from=token_balance
                            )
                        else:
                            self.liquidswap_swap(
                                token_from=token,
                                token_to=APT_TOKEN,
                                amount_from=token_balance
                            )
                        self.sleep()
                return True
            else:
                logger.error(f"APT {balance} balance is less, than required ({apt_to_swap})")
                raise Exception("Insufficient balance for activity")

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[AUTOSWAP] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            elif "Insufficient balance for activity" in str(e):
                raise Exception(e)
            else:
                logger.warning(f"[AUTOSWAP] Error while withdraw: {error}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def amnis_stake(self, amount: float) -> bool:
        try:
            logger.info(f"[AMNIS] Try to stake {amount} APT")

            self.client_config.max_gas_amount = self.custom_randint(17000, 20000, 100)

            amount = APT_TOKEN.to_wei(amount)

            payload = {
                "function": "0x111ae3e5bc816a5e63c2da97d0aa3886519e0cd5e4b046659fa35796bd11542a::router::deposit_and_stake_entry",
                "type_arguments": [],
                "arguments": [
                    str(amount),
                    self.address
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            if self.verify_tx(tx_hash):
                self.client_config.max_gas_amount = self.custom_randint(7000, 9000, 100)
                return True

        except Exception as e:
            error = str(e)
            if "Out of gas" in error:
                logger.warning("[AMNIS] Gas less than minimum, try with more gas")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            elif "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[AMNIS] Problem with sequence number, retrying...")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def merkle_order(self, amount: float) -> bool:
        try:
            logger.info(f"[MERKLE] Try to make order on {amount} zUSDC")

            amount_wei = USDC_TOKEN.to_wei(amount)

            leverage = 130
            position_size = leverage * amount_wei

            apt = self.get_coingecko_token_prices_in_usd()
            apt = APT_TOKEN.to_wei(apt[APT_TOKEN])
            apt_wei = APT_TOKEN.to_wei(apt)
            margin_requirement = 1 / leverage

            liquidation_price = int(apt_wei * (1 - margin_requirement))
            stop_loss = int(apt_wei * (1 - 0.10 / leverage))
            take_profit = int(apt_wei * (1 + 0.20 / leverage))

            payload = {
                "function": "0x5ae6789dd2fec1a9ec9cccfb3acaf12e93d432f0a3a42c92fe1a9d490b7bbc06::managed_trading::place_order_with_referrer",
                "type_arguments": [
                    "0x5ae6789dd2fec1a9ec9cccfb3acaf12e93d432f0a3a42c92fe1a9d490b7bbc06::pair_types::APT_USD",
                    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
                ],
                "arguments": [
                    str(position_size),
                    str(amount_wei),
                    str(self.digits_to_integer(liquidation_price, 10)),
                    True,
                    True,
                    True,
                    str(self.digits_to_integer(stop_loss, 59)),
                    str(self.digits_to_integer(take_profit, 60)),
                    False,
                    "0x0"
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[MERKLE] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.warning(f"[MERKLE] Error while place order: {e}")
            return False

    @staticmethod
    def digits_to_integer(integer, digits):
        int_string = str(integer) + str(digits)
        new_integer = int(int_string)
        return new_integer

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def bluemove_bid(self, amount: float) -> bool:
        try:
            logger.info(f"[BLUEMOVE] Try to make bid on NFT Collection")

            payload = {
                "function": "0xd520d8669b0a3de23119898dcdff3e0a27910db247663646ad18cf16e44c6f5::collection_offer::init_for_tokenv2_entry",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin"
                ],
                "arguments": [
                    "0x3d94d2eb4aea99cdf051a817c1e9f31d2166c79ed301578c75c31e38d4be747e",
                    "0xb3e77042cc302994d7ae913d04286f61ecd2dbc4a73f6c7dbcb4333f3524b9d7",
                    str(APT_TOKEN.to_wei(amount)),
                    "1",
                    "86400000"
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[BLUEMOVE] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[BLUEMOVE] Error: {str(e)}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def topaz_bid(self, amount: float) -> bool:
        try:
            logger.info(f"[TOPAZ] Try to make bid on NFT Collection")

            deadline = int(datetime.now(timezone.utc).timestamp()) + 86400

            payload = {
                "function": "0x2c7bccf7b31baf770fdbcc768d9e9cb3d87805e255355df5db32ac9a669010a2::collection_marketplace::bid",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin"
                ],
                "arguments": [
                    str(APT_TOKEN.to_wei(amount)),
                    "1",
                    str(deadline),
                    "0x16ad31fef7f4e14a6f06ec9410950fb063f041f0ece9b2c9c1986106a17657bc",
                    "GoblinAPT"
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[TOPAZ] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[TOPAZ] Error: {str(e)}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def wapal_bid(self, amount: float) -> bool:
        try:
            logger.info(f"[WAPAL] Try to make bid on NFT Collection")

            deadline = int(datetime.now(timezone.utc).timestamp()) + 86400

            payload = {
                "function": "0x584b50b999c78ade62f8359c91b5165ff390338d45f8e55969a04e65d76258c9::collection_offer::init_for_tokenv1_entry",
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin"
                ],
                "arguments": [
                    "0x92d2f7ad00630e4dfffcca01bee12c84edf004720347fb1fd57016d2cc8d3f8",
                    "Galxe OAT",
                    "0x71f7c94805c33d32a7f9560c95f02e9d3b5bc49884a883916f03abe6da11ac08",
                    str(APT_TOKEN.to_wei(amount)),
                    "1",
                    str(deadline)
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[WAPAL] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[WAPAL] Error: {str(e)}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def merkato_bid(self, amount: float) -> bool:
        try:
            logger.info(f"[MERKATO] Try to make bid on NFT Collection")

            payload = {
                "function": "0xe11c12ec495f3989c35e1c6a0af414451223305b579291fc8f3d9d0575a23c26::biddings_v2::collection_bids",
                "type_arguments": [],
                "arguments": [
                    "0xa3d9ad08adf8af8dc3bd6a4bdd910d2a1cc88bd5fbedae0ddaa3e89b260a785f",
                    str(APT_TOKEN.to_wei(amount)),
                    "1"
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[MERKATO] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[MERKATO] Error: {str(e)}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def wapal_mint(self) -> bool:
        try:
            logger.info(f"[WAPAL] Try to mint 'Make Every Move Count' NFT")

            payload = {
                "function": "0x6547d9f1d481fdc21cd38c730c07974f2f61adb7063e76f9d9522ab91f090dac::candymachine::mint_script",
                "type_arguments": [],
                "arguments": [
                    "0xa79267255727285e55bc42d34134ffa2133b6983391846810d39f094fb5f1c87"
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[WAPAL] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(f"[WAPAL] Error: {str(e)}")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def mercato_buy(self) -> (bool, str):
        try:
            logger.info(f"[MERKATO] Try to buy NFT")

            url = GRAPHQL_URL
            proxy = None if self.proxy is None else {"https": f"http://{self.proxy}"}

            with open(os.path.abspath("core/clients/payloads/merkato_nfts_payload.json")) as file:
                json_payload = json.load(file)

            response = requests.post(url=url, json=json_payload, proxies=proxy, headers={
                'X-Api-Key': "WNQvjQy.1a4d0d1046098f8db1d4a529f7f44dd1",
                "X-Api-User": "mercato.xyz"
            })

            data = response.json()
            nft_to_buy = data["data"]["aptos"]["listings"][0]

            payload = {
                "function": "0xe11c12ec495f3989c35e1c6a0af414451223305b579291fc8f3d9d0575a23c26::markets_v2::buy_tokens_v2",
                "type_arguments": [],
                "arguments": [
                    ["2"],
                    ["TradePort"],
                    [nft_to_buy["seller"]],
                    [nft_to_buy["price_str"]],
                    ["0x39b61bdc5088c71bc496103af399ff79be45b9974cfd234a69beb726dd720df3"],
                    ["Make Every M🌐ve Count."],
                    [nft_to_buy["nft"]["token_id"]],
                    ["0"],
                    ["0"],
                    [nft_to_buy["nonce"]]
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash), nft_to_buy["nft"]["token_id"]

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[MERKATO] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(e)
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def merkato_sell(self, purchased_nft_address: str) -> bool:
        try:
            logger.info(f"[MERKATO] Try to sell NFT")

            payload = {
                "function": "0xe11c12ec495f3989c35e1c6a0af414451223305b579291fc8f3d9d0575a23c26::markets_v2::list_tokens_v2",
                "type_arguments": [],
                "arguments": [
                    ["2"],
                    [""],
                    ["0x39b61bdc5088c71bc496103af399ff79be45b9974cfd234a69beb726dd720df3"],
                    ["Make Every M🌐ve Count."],
                    [purchased_nft_address],
                    ["0"],
                    ["100000"],
                    ["0"],
                    ["0x0"],
                    [purchased_nft_address]
                ],
                "type": "entry_function_payload"
            }

            tx_hash = self.send_json_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            error = str(e)

            if "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[MERKATO] Problem with sequence number, retrying...")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            else:
                logger.error(e)
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def tortuga_stake(self, amount: float) -> bool:
        try:
            logger.info(f"[TORTUGA] Try to stake {amount} APT")

            self.client_config.max_gas_amount = self.custom_randint(8000, 12000, 100)

            amount = APT_TOKEN.to_wei(amount)

            payload = EntryFunction.natural(
                TORTUGA["script"],
                TORTUGA["function"],
                [],
                [TransactionArgument(amount, Serializer.u64)],
            )

            tx_hash = self.send_tx(payload=payload)
            if self.verify_tx(tx_hash):
                self.client_config.max_gas_amount = self.custom_randint(7000, 9000, 100)
                return True

        except Exception as e:
            error = str(e)
            if "Out of gas" in error:
                logger.warning("[TORTUGA] Gas less than minimum, try with more gas")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            elif "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[TORTUGA] Problem with sequence number, retrying...")
            return False

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def ditto_stake(self, amount: float) -> bool:
        try:
            logger.info(f"[DITTO] Try to stake {amount} APT")

            self.client_config.max_gas_amount = self.custom_randint(8000, 12000, 100)

            amount = APT_TOKEN.to_wei(amount)

            payload = EntryFunction.natural(
                DITTO["script"],
                DITTO["function"],
                [],
                [TransactionArgument(amount, Serializer.u64)],
            )

            tx_hash = self.send_tx(payload=payload)
            if self.verify_tx(tx_hash):
                self.client_config.max_gas_amount = self.custom_randint(7000, 9000, 100)
                return True

        except Exception as e:
            error = str(e)
            if "Out of gas" in error:
                logger.warning("[DITTO] Gas less than minimum, try with more gas")
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                raise Exception(e)
            elif "SEQUENCE_NUMBER_TOO_OLD" in error:
                logger.warning("[DITTO] Problem with sequence number, retrying...")
            return False

    def aptos_name_mint(self, domain_name: str) -> bool:
        try:
            logger.info(f"[APTOSNAME] Try to mint {domain_name} domain")

            registration_duration_timestamp = 31536000

            payload = EntryFunction.natural(
                APTOS_NAMES["script"],
                APTOS_NAMES["function_mint_domain"],
                [],
                [
                    TransactionArgument(domain_name, Serializer.str),
                    TransactionArgument(registration_duration_timestamp, Serializer.u64),
                    TransactionArgument(b'', Serializer.to_bytes),
                    TransactionArgument(b'', Serializer.to_bytes),
                ]
            )

            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            logger.error(f"[APTOSNAME] Mint {domain_name} domain error: {str(e)}")
            return False

    def sub_aptos_name_mint(self, sub_domain_name: str) -> bool:
        try:
            logger.info(f"[APTOSNAME] Try to mint {sub_domain_name} sub domain")

            domain_name, domain_timestamp = get_old_aptos_name_data(wallet_address=self.address)

            payload = EntryFunction.natural(
                APTOS_NAMES["script"],
                APTOS_NAMES["function_mint_sub_domain"],
                [],
                [
                    TransactionArgument(domain_name, Serializer.str),
                    TransactionArgument(sub_domain_name, Serializer.str),
                    TransactionArgument(domain_timestamp, Serializer.u64),
                    TransactionArgument(1, Serializer.u8),
                    TransactionArgument(True, Serializer.bool),
                    TransactionArgument(b'', Serializer.to_bytes),
                    TransactionArgument(b'', Serializer.to_bytes)
                ],
            )

            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            logger.error(f"[APTOSNAME] Mint {sub_domain_name} sub domain error: {str(e)}")
            return False

    def aptos_name_v2_update(self) -> bool:
        try:
            logger.info(f"[APTOSNAME] Try to update domain to v2")

            domain_name = get_old_aptos_name_wia_wapal(wallet_address=self.address, proxy=self.proxy)

            if domain_name is None:
                logger.warning("[APTOSNAME] No v1 aptos names on account")
                return False

            payload = EntryFunction.natural(
                APTOS_NAMES["script"],
                APTOS_NAMES["function_migrate_name"],
                [],
                [
                    TransactionArgument(domain_name, Serializer.str),
                    TransactionArgument(b'', Serializer.to_bytes)
                ],
            )

            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            logger.error(f"[APTOSNAME] Update domain to v2 error: {str(e)}")
            return False

    def _get_liquidswap_reserve_value_ratio(
            self,
            resource_account: AccountAddress,
            token_from: Token,
            token_to: Token
    ) -> float:
        try:
            resource_type = get_liquidswap_resource_type(token_from=token_from, token_to=token_to)
            data = self.account_resource(resource_account, resource_type)["data"]
            token_from_reserve_value = int(data["coin_x_reserve"]["value"])
            token_to_reserve_value = int(data["coin_y_reserve"]["value"])

        except:
            resource_type = get_liquidswap_resource_type(token_from=token_to, token_to=token_from)
            data = self.account_resource(resource_account, resource_type)["data"]
            token_to_reserve_value = int(data["coin_x_reserve"]["value"])
            token_from_reserve_value = int(data["coin_y_reserve"]["value"])

        token_from_reserve_value = token_from.from_wei(token_from_reserve_value)
        token_to_reserve_value = token_to.from_wei(token_to_reserve_value)
        reserve_value_ratio = token_to_reserve_value / token_from_reserve_value

        return reserve_value_ratio
