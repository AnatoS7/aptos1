from __future__ import annotations

import random
import time
from typing import Any

import requests
from aptos_sdk import ed25519
from aptos_sdk.account import Account
from aptos_sdk.authenticator import Authenticator, Ed25519Authenticator
from aptos_sdk.client import RestClient, ApiError, ResourceNotFound
from aptos_sdk.transactions import (
    EntryFunction,
    TransactionPayload,
    SignedTransaction,
    RawTransaction
)
from aptos_sdk.type_tag import TypeTag, StructTag

from config import RPC, TOKENS, ATTEMPTS_COUNT, ROUND_TO
from core.decorators import retry_on_error
from logger import logger
from core.clients.utils import get_link_to_explorer
from core.constants import COIN_STORE, TOKEN_REGISTRATION, APT_TOKEN, THAPT_TOKEN, COINGECKO_API_TOKEN_PRICE_URL
from core.models.token import Token
from core.models.wallet import Wallet


class BaseClient(RestClient):
    def __init__(self, wallet: Wallet):
        super().__init__(RPC)

        self.signer = Account.load_key(wallet.private_key)
        self.proxy = wallet.proxy
        self.address = wallet.address
        self.client_config.max_gas_amount = self.custom_randint(7000, 9000, 100)
        self.client_config.transaction_wait_in_seconds = 60

    def send_tx(self, payload: EntryFunction) -> str:
        signed_tx = self.create_bcs_signed_transaction(self.signer, TransactionPayload(payload))
        tx_hash = self.submit_bcs_transaction(signed_tx)

        return tx_hash

    def send_json_tx(self, payload: dict) -> str:
        tx_hash = self.submit_transaction(self.signer, payload)
        return tx_hash

    def custom_randint(self, low, high, multiple):
        return random.randint(low // multiple, high // multiple) * multiple

    def verify_tx(self, tx_hash) -> bool:
        try:
            self.wait_for_transaction(tx_hash)
            logger.success(f"Transaction was successful: {get_link_to_explorer(tx_hash)}")
            return True

        except Exception as e:
            logger.error(f"Transaction failed: {get_link_to_explorer(tx_hash)}")
            raise Exception(str(e))

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def get_coingecko_token_prices_in_usd(self) -> dict[Token, float] | bool:
        try:
            coingecko_ids = [token.coingecko_id for token in TOKENS.values()]
            coingecko_ids_string = ",".join(coingecko_ids)

            url = COINGECKO_API_TOKEN_PRICE_URL.format(coingecko_ids_string)
            proxy = None if self.proxy is None else {"https": f"http://{self.proxy}"}
            response = requests.get(url=url, proxies=proxy)

            if response.status_code == 200:
                data = response.json()
            else:
                logger.error(f"Error on request for getting coingecko prices")
                return False

            token_prices = {}

            for token in TOKENS.values():
                coingecko_id = token.coingecko_id

                if coingecko_id in data and "usd" in data[coingecko_id]:
                    token_prices[token] = float(data[coingecko_id]["usd"])

            return token_prices

        except Exception as e:
            logger.error(f"Get token prices in usd from coingecko error: {str(e)}")
            return False

    def get_token_balance_in_usd(self, token_balance: int, token: Token, token_price: float) -> float:
        try:
            token_balance = token.from_wei(token_balance)
            token_balance_in_usd = round(token_balance * token_price, ROUND_TO)

            return token_balance_in_usd

        except Exception as e:
            raise Exception(f"Get token balance in usd error: {str(e)}")

    def token_registration(self, token: Token) -> bool:
        try:
            logger.info(f"[CLIENT] Trying to register {token.symbol} token")

            payload = EntryFunction.natural(
                TOKEN_REGISTRATION["script"],
                TOKEN_REGISTRATION["function"],
                [TypeTag(StructTag.from_str(token.contract_address))],
                [],
            )

            tx_hash = self.send_tx(payload=payload)
            return self.verify_tx(tx_hash)

        except Exception as e:
            raise Exception(f"[CLIENT] Token registration error: {str(e)}")

    @retry_on_error(tries=ATTEMPTS_COUNT)
    def get_token_balance(self, token: Token, **kwargs) -> int | None:
        try:
            store_address = f"{COIN_STORE}<{token.contract_address}>"
            account_resource = self.account_resource(self.signer.address(), store_address)
            value = int(account_resource.get("data", {}).get("coin", {}).get("value"))

            return value

        except Exception as e:
            if token.contract_address in str(e):
                if token == APT_TOKEN:
                    return 0
                else:
                    self.token_registration(token)
                    return False
            logger.error(f"Get coin data error: {str(e)}")

    def get_all_tokens_balance_in_apt(self) -> int | None:
        try:
            token_prices = self.get_coingecko_token_prices_in_usd()
            apt_balance = 0

            for token in TOKENS.values():
                token_balance_usd = self.get_token_balance_in_usd(
                    self.get_token_balance(token),
                    token,
                    token_prices[token]
                )
                if token_balance_usd > 0:
                    apt_balance += token_balance_usd / token_prices[APT_TOKEN]

            return round(apt_balance, 6)
        except Exception as e:
            logger.error(f"Get all tokens balance in apt error: {str(e)}")

    def get_max_balance_token(self) -> Token:
        try:
            max_balance = 0.0
            max_balance_token = None

            token_prices = self.get_coingecko_token_prices_in_usd()

            for token in TOKENS.values():
                if token == THAPT_TOKEN:
                    continue

                token_balance = self.get_token_balance(token=token)

                if token not in token_prices:
                    raise Exception("Token not in token prices while getting max balance token")

                token_price = token_prices[token]
                token_balance_in_usd = self.get_token_balance_in_usd(
                    token_balance=token_balance,
                    token=token,
                    token_price=token_price
                )

                if token_balance_in_usd > max_balance:
                    max_balance = token_balance_in_usd
                    max_balance_token = token

            return max_balance_token

        except Exception as e:
            logger.error(f"Get max balance token error: {str(e)}")

    def submit_bcs_transaction(self, signed_transaction: SignedTransaction) -> str:
        headers = {"Content-Type": "application/x.aptos.signed_transaction+bcs"}

        if self.proxy is None:
            response = self.client.post(
                f"{self.base_url}/transactions",
                headers=headers,
                data=signed_transaction.bytes(),
            )
        else:
            response = self.client.post(
                f"{self.base_url}/transactions",
                headers=headers,
                data=signed_transaction.bytes(),
                proxies={"https": f"http://{self.proxy}"}
            )

        if response.status_code >= 400:
            if "hash" not in response.json():
                raise ApiError(response.text, response.status_code)

        return response.json()["hash"]

    def wait_for_transaction(self, txn_hash: str) -> None:
        time.sleep(3)
        count = 0

        while self.transaction_pending(txn_hash):
            assert (count < self.client_config.transaction_wait_in_seconds), f"transaction {txn_hash} timed out"
            time.sleep(1)
            count += 1

        if self.proxy is None:
            response = self.client.get(f"{self.base_url}/transactions/by_hash/{txn_hash}")
        else:
            response = self.client.get(
                f"{self.base_url}/transactions/by_hash/{txn_hash}",
                proxies={"https": f"http://{self.proxy}"}
            )

        assert ("success" in response.json() and response.json()["success"]), f"{response.text} - {txn_hash}"

    def transaction_pending(self, txn_hash: str) -> bool:
        if self.proxy is None:
            response = self.client.get(f"{self.base_url}/transactions/by_hash/{txn_hash}")
        else:
            response = self.client.get(
                f"{self.base_url}/transactions/by_hash/{txn_hash}",
                proxies={"https": f"http://{self.proxy}"}
            )

        if response.status_code == 404:
            return True

        if response.status_code >= 400:
            raise ApiError(response.text, response.status_code)

        return response.json()["type"] == "pending_transaction"

    def simulate_transaction(self, transaction: RawTransaction, sender: Account) -> dict[str, Any]:
        authenticator = Authenticator(Ed25519Authenticator(sender.public_key(), ed25519.Signature(b"\x00" * 64)))
        signed_transaction = SignedTransaction(transaction, authenticator)

        headers = {"Content-Type": "application/x.aptos.signed_transaction+bcs"}

        if self.proxy is None:
            response = self.client.post(
                f"{self.base_url}/transactions/simulate",
                headers=headers,
                data=signed_transaction.bytes()
            )
        else:
            response = self.client.post(
                f"{self.base_url}/transactions/simulate",
                headers=headers,
                data=signed_transaction.bytes(),
                proxies={"https": f"http://{self.proxy}"}
            )
        if response.status_code >= 400:
            raise ApiError(response.text, response.status_code)

        return response.json()

    def account_resource(self, account_address, resource_type, ledger_version=None):
        if not ledger_version:
            request = f"{self.base_url}/accounts/{account_address}/resource/{resource_type}"
        else:
            request = f"{self.base_url}/accounts/{account_address}/resource/{resource_type}" \
                      f"?ledger_version={ledger_version}"

        if self.proxy is None:
            response = self.client.get(url=request)
        else:
            response = self.client.get(url=request, proxies={"https": f"http://{self.proxy}"})

        if response.status_code == 404:
            raise ResourceNotFound(resource_type, resource_type)

        if response.status_code >= 400:
            raise ApiError(f"{response.text} - {account_address}", response.status_code)

        return response.json()
