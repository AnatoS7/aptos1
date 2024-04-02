from __future__ import annotations

import json
import random

from loguru import logger

from config import (
    USE_PROXY,
    PANCAKESWAP_TX_COUNT,
    LIQUIDSWAP_TX_COUNT,
    SUSHISWAP_TX_COUNT,
    TORTUGA_TX_COUNT,
    DITTO_TX_COUNT,
    APTOS_NAMES_TX_COUNT,
    SUB_APTOS_NAMES_TX_COUNT,
    THALASWAP_TX_COUNT,
    GATOR_DEPOSIT_TX_COUNT,
    AMNIS_TX_COUNT,
    MERKLE_TX_COUNT,
    MERKATO_BID_TX_COUNT,
    BLUEMOVE_BID_TX_COUNT,
    TOPAZ_BID_TX_COUNT,
    WAPAL_BID_TX_COUNT,
    WAPAL_MINT_TX_COUNT,
    MERKATO_BUY_SELL_TX_COUNT,
    SWAPGPT_TX_COUNT,
    KANALABS_TX_COUNT,
    ARIES_TX_COUNT
)
from core.constants import (
    DATABASE_PATH,
    PRIVATE_KEYS_PATH,
    PROXIES_PATH,
    OKX_ADDRESSES_PATH
)
from core.models.data_item import DataItem
from core.models.wallet import Wallet


class Database:
    def __init__(self, data: list):
        self.data: list = data
        self.errors: list = []
        self.accounts_remaining: int = len(data)

    def to_json(self):
        try:
            return json.dumps(self, default=lambda o: o.__dict__, indent=4)

        except Exception as e:
            logger.error(f"Database to json object error: {str(e)}")

    @staticmethod
    def not_empty(database: dict) -> bool:
        return not database["accounts_remaining"] == 0

    @staticmethod
    def create_database() -> None:
        try:
            data = []
            private_keys = Database.read_from_txt(PRIVATE_KEYS_PATH)
            proxies = Database.read_from_txt(PROXIES_PATH)
            okx_deposit_addresses = Database.read_from_txt(OKX_ADDRESSES_PATH)

            if USE_PROXY and len(private_keys) != len(proxies):
                logger.error(f"Proxies length less than needed. Run exit()")
                exit()

            if len(okx_deposit_addresses) > 0 and len(okx_deposit_addresses) != len(private_keys):
                logger.error(f"Okx deposit addresses length less than needed. Run exit()")
                exit()

            for private_key in private_keys:
                private_key_index = private_keys.index(private_key)
                proxy = proxies[private_key_index] if USE_PROXY else None
                okx_deposit_address = okx_deposit_addresses[private_key_index] if len(
                    okx_deposit_addresses) > 0 else None

                wallet = Wallet(
                    private_key=private_key,
                    proxy=proxy
                )

                data_item = Database.generate_data_item(wallet=wallet, okx_deposit_address=okx_deposit_address)

                while Database.get_data_item_tx_count(data_item=data_item) <= 0:
                    data_item = Database.generate_data_item(wallet=wallet, okx_deposit_address=okx_deposit_address)

                data.append(data_item)

            Database.save_database(Database(data).to_json())
            logger.success(f"Database was been created", send_to_tg=False)

        except Exception as e:
            raise Exception(f"Database creation error: {str(e)}")

    @staticmethod
    def generate_data_item(wallet, okx_deposit_address):
        gator_tx_count = random.randint(*GATOR_DEPOSIT_TX_COUNT)
        merkato_buy_sell_tx_count = random.randint(*MERKATO_BUY_SELL_TX_COUNT)
        swapgpt_tx_count = random.randint(*SWAPGPT_TX_COUNT)
        kanalabs_tx_count = random.randint(*KANALABS_TX_COUNT)
        aries_tx_count = random.randint(*ARIES_TX_COUNT)

        data_item = DataItem(
            wallet=wallet,
            okx_deposit_address=okx_deposit_address,
            pancakeswap_tx_count=random.randint(*PANCAKESWAP_TX_COUNT),
            liquidswap_tx_count=random.randint(*LIQUIDSWAP_TX_COUNT),
            sushiswap_tx_count=random.randint(*SUSHISWAP_TX_COUNT),
            thalaswap_tx_count=random.randint(*THALASWAP_TX_COUNT),
            gator_deposit_tx_count=gator_tx_count,
            gator_order_tx_count=gator_tx_count,
            gator_withdraw_tx_count=gator_tx_count,
            tortuga_tx_count=random.randint(*TORTUGA_TX_COUNT),
            merkle_tx_count=random.randint(*MERKLE_TX_COUNT),
            amnis_tx_count=random.randint(*AMNIS_TX_COUNT),
            ditto_tx_count=random.randint(*DITTO_TX_COUNT),
            wapal_bid_tx_count=random.randint(*WAPAL_BID_TX_COUNT),
            wapal_mint_tx_count=random.randint(*WAPAL_MINT_TX_COUNT),
            topaz_bid_tx_count=random.randint(*TOPAZ_BID_TX_COUNT),
            bluemove_bid_tx_count=random.randint(*BLUEMOVE_BID_TX_COUNT),
            merkato_bid_tx_count=random.randint(*MERKATO_BID_TX_COUNT),
            merkato_buy_tx_count=merkato_buy_sell_tx_count,
            merkato_purchased_nft_address="",
            merkato_sell_tx_count=merkato_buy_sell_tx_count,
            swapgpt_deposit_tx_count=swapgpt_tx_count,
            swapgpt_buy_tx_count=swapgpt_tx_count,
            swapgpt_withdraw_tx_count=swapgpt_tx_count,
            kanalabs_deposit_tx_count=kanalabs_tx_count,
            kanalabs_buy_tx_count=kanalabs_tx_count,
            kanalabs_withdraw_tx_count=kanalabs_tx_count,
            aries_deposit_tx_count=aries_tx_count,
            aries_buy_tx_count=aries_tx_count,
            aries_withdraw_tx_count=aries_tx_count,
            aptos_names_tx_count=random.randint(*APTOS_NAMES_TX_COUNT),
            sub_aptos_names_tx_count=random.randint(*SUB_APTOS_NAMES_TX_COUNT)
        )

        return data_item

    @staticmethod
    def read_database() -> dict:
        try:
            with open(DATABASE_PATH) as json_file:
                return json.load(json_file)

        except Exception as e:
            raise Exception(f"Error while read database: {str(e)}")

    @staticmethod
    def save_database(database: dict | str) -> None:
        try:
            if type(database) is dict:
                database = json.dumps(database, indent=4)

            with open(DATABASE_PATH, 'w') as json_file:
                json_file.write(database)

        except Exception as e:
            raise Exception(f"Error while save database: {str(e)}")

    @staticmethod
    def update_database(database: dict, data_item: DataItem, data_item_index: int) -> dict:
        try:
            tx_count = Database.get_data_item_tx_count(data_item=data_item)

            if tx_count == 0:
                return Database.delete_data_item_from_data(database, data_item_index)

            database["data"][data_item_index]["private_key"] = data_item.private_key
            database["data"][data_item_index]["address"] = data_item.address
            database["data"][data_item_index]["proxy"] = data_item.proxy
            database["data"][data_item_index]["okx_deposit_address"] = data_item.okx_deposit_address
            database["data"][data_item_index]["pancakeswap_tx_count"] = data_item.pancakeswap_tx_count
            database["data"][data_item_index]["liquidswap_tx_count"] = data_item.liquidswap_tx_count
            database["data"][data_item_index]["sushiswap_tx_count"] = data_item.sushiswap_tx_count
            database["data"][data_item_index]["thalaswap_tx_count"] = data_item.thalaswap_tx_count
            database["data"][data_item_index]["gator_deposit_tx_count"] = data_item.gator_deposit_tx_count
            database["data"][data_item_index]["gator_withdraw_tx_count"] = data_item.gator_withdraw_tx_count
            database["data"][data_item_index]["gator_order_tx_count"] = data_item.gator_order_tx_count
            database["data"][data_item_index]["tortuga_tx_count"] = data_item.tortuga_tx_count
            database["data"][data_item_index]["merkle_tx_count"] = data_item.merkle_tx_count
            database["data"][data_item_index]["amnis_tx_count"] = data_item.amnis_tx_count
            database["data"][data_item_index]["ditto_tx_count"] = data_item.ditto_tx_count
            database["data"][data_item_index]["wapal_bid_tx_count"] = data_item.wapal_bid_tx_count
            database["data"][data_item_index]["wapal_mint_tx_count"] = data_item.wapal_mint_tx_count
            database["data"][data_item_index]["topaz_bid_tx_count"] = data_item.topaz_bid_tx_count
            database["data"][data_item_index]["bluemove_bid_tx_count"] = data_item.bluemove_bid_tx_count
            database["data"][data_item_index]["merkato_bid_tx_count"] = data_item.merkato_bid_tx_count
            database["data"][data_item_index]["merkato_buy_tx_count"] = data_item.merkato_buy_tx_count
            database["data"][data_item_index]["merkato_purchased_nft_address"] = data_item.merkato_purchased_nft_address
            database["data"][data_item_index]["merkato_sell_tx_count"] = data_item.merkato_sell_tx_count
            database["data"][data_item_index]["swapgpt_deposit_tx_count"] = data_item.swapgpt_deposit_tx_count
            database["data"][data_item_index]["swapgpt_buy_tx_count"] = data_item.swapgpt_buy_tx_count
            database["data"][data_item_index]["swapgpt_withdraw_tx_count"] = data_item.swapgpt_withdraw_tx_count
            database["data"][data_item_index]["kanalabs_deposit_tx_count"] = data_item.kanalabs_deposit_tx_count
            database["data"][data_item_index]["kanalabs_buy_tx_count"] = data_item.kanalabs_buy_tx_count
            database["data"][data_item_index]["kanalabs_withdraw_tx_count"] = data_item.kanalabs_withdraw_tx_count
            database["data"][data_item_index]["aries_deposit_tx_count"] = data_item.aries_deposit_tx_count
            database["data"][data_item_index]["aries_buy_tx_count"] = data_item.aries_buy_tx_count
            database["data"][data_item_index]["aries_withdraw_tx_count"] = data_item.aries_withdraw_tx_count
            database["data"][data_item_index]["aptos_names_tx_count"] = data_item.aptos_names_tx_count
            database["data"][data_item_index]["sub_aptos_names_tx_count"] = data_item.sub_aptos_names_tx_count

            return database

        except Exception as e:
            raise Exception(f"Update database error: {str(e)}")

    @staticmethod
    def read_from_txt(file_path: str) -> list[str]:
        try:
            with open(file_path, "r") as file:
                return [line.strip() for line in file]

        except Exception as e:
            raise Exception(f"Encountered an error while reading a txt file '{file_path}': {str(e)}")

    @staticmethod
    def write_to_txt(file_path: str, data: list):
        try:
            with open("domain.txt", "w") as file:
                for item in data:
                    file.write(f"{item}\n")

        except Exception as e:
            raise Exception(f"Encountered an error while write to txt file '{file_path}': {str(e)}")

    @staticmethod
    def delete_data_item_from_data(database: dict, data_item_index: int) -> dict:
        try:
            database["data"].pop(data_item_index)
            database["accounts_remaining"] -= 1

            return database

        except Exception as e:
            raise Exception(f"Delete data item from data error: {str(e)}")

    @staticmethod
    def move_data_item_to_errors(database: dict, data_item: DataItem, data_item_index: int) -> dict:
        try:
            if data_item is None or data_item_index is None:
                raise Exception("Data item or data_item_index is None")

            database["errors"].append(database["data"][data_item_index])
            database["data"].pop(data_item_index)
            database["accounts_remaining"] = database["accounts_remaining"] - 1

            return database

        except Exception as e:
            logger.error(f"Move data item error: {str(e)}")

    @staticmethod
    def get_data_item_tx_count(data_item: DataItem) -> int:
        try:
            total_tx_count = sum([
                data_item.liquidswap_tx_count,
                data_item.pancakeswap_tx_count,
                data_item.sushiswap_tx_count,
                data_item.thalaswap_tx_count,
                data_item.gator_deposit_tx_count,
                data_item.gator_order_tx_count,
                data_item.gator_withdraw_tx_count,
                data_item.tortuga_tx_count,
                data_item.merkle_tx_count,
                data_item.amnis_tx_count,
                data_item.ditto_tx_count,
                data_item.wapal_bid_tx_count,
                data_item.wapal_mint_tx_count,
                data_item.topaz_bid_tx_count,
                data_item.bluemove_bid_tx_count,
                data_item.merkato_bid_tx_count,
                data_item.merkato_buy_tx_count,
                data_item.merkato_sell_tx_count,
                data_item.swapgpt_deposit_tx_count,
                data_item.swapgpt_buy_tx_count,
                data_item.swapgpt_withdraw_tx_count,
                data_item.kanalabs_deposit_tx_count,
                data_item.kanalabs_buy_tx_count,
                data_item.kanalabs_withdraw_tx_count,
                data_item.aries_deposit_tx_count,
                data_item.aries_buy_tx_count,
                data_item.aries_withdraw_tx_count,
                data_item.aptos_names_tx_count,
                data_item.sub_aptos_names_tx_count
            ])

            return total_tx_count

        except Exception as e:
            raise Exception(f"Get data item tx count error: {str(e)}")

    @staticmethod
    def get_database_tx_count(data: dict) -> int:
        try:
            tx_count = 0

            for item in data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if key.endswith("_tx_count"):
                            tx_count += value

            return tx_count

        except Exception as e:
            raise Exception(f"Get database tx count error: {str(e)}")

    @staticmethod
    def get_data_item(data: dict, is_random_item=False) -> (DataItem, int):
        try:
            data_len = len(data)

            if data_len == 0:
                logger.debug("All accounts are finished. Run exit()")
                exit()
            elif data_len == 1 or not is_random_item:
                data_item_index = 0
            else:
                data_item_index = random.randint(0, data_len - 1)

            data_item_json = data[data_item_index]

            if data_len > 0:
                data_item = Database.create_data_item(data_item_json=data_item_json)
                return data_item, data_item_index
            else:
                raise Exception("Empty range for randrange")

        except Exception as e:
            if "Empty range for randrange" in str(e):
                logger.debug("All accounts are finished. Run exit()")
                exit()
            else:
                raise Exception(f"Get random data item from database error: {str(e)}")

    @staticmethod
    def create_data_item(data_item_json: dict) -> DataItem:
        try:
            wallet = Wallet(
                private_key=data_item_json["private_key"],
                proxy=data_item_json["proxy"]
            )

            data_item = DataItem(
                wallet,
                data_item_json["okx_deposit_address"],
                data_item_json["pancakeswap_tx_count"],
                data_item_json["liquidswap_tx_count"],
                data_item_json["sushiswap_tx_count"],
                data_item_json["thalaswap_tx_count"],
                data_item_json["gator_deposit_tx_count"],
                data_item_json["gator_order_tx_count"],
                data_item_json["gator_withdraw_tx_count"],
                data_item_json["tortuga_tx_count"],
                data_item_json["merkle_tx_count"],
                data_item_json["amnis_tx_count"],
                data_item_json["ditto_tx_count"],
                data_item_json["wapal_bid_tx_count"],
                data_item_json["wapal_mint_tx_count"],
                data_item_json["topaz_bid_tx_count"],
                data_item_json["bluemove_bid_tx_count"],
                data_item_json["merkato_bid_tx_count"],
                data_item_json["merkato_buy_tx_count"],
                data_item_json["merkato_purchased_nft_address"],
                data_item_json["merkato_sell_tx_count"],
                data_item_json["swapgpt_deposit_tx_count"],
                data_item_json["swapgpt_buy_tx_count"],
                data_item_json["swapgpt_withdraw_tx_count"],
                data_item_json["kanalabs_deposit_tx_count"],
                data_item_json["kanalabs_buy_tx_count"],
                data_item_json["kanalabs_withdraw_tx_count"],
                data_item_json["aries_deposit_tx_count"],
                data_item_json["aries_buy_tx_count"],
                data_item_json["aries_withdraw_tx_count"],
                data_item_json["aptos_names_tx_count"],
                data_item_json["sub_aptos_names_tx_count"],
            )

            return data_item

        except Exception as e:
            raise Exception(f"Create data item error: {str(e)}")

    @staticmethod
    def restore_error_accounts():
        data = Database.read_database()
        data["data"] = data["errors"]
        data["errors"] = []
        data["accounts_remaining"] = len(data["data"])
        Database.save_database(data)
