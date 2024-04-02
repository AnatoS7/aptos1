from config import MIN_GAS_BALANCE
from core.clients.client import Client
from core.clients.utils import get_old_aptos_name_data
from core.constants import DOMAINS_PATH
from core.models.wallet import Wallet
from logger import logger
from modules.database import Database
from utils import (
    change_mobile_ip,
    sleep,
    get_available_name,
    check_min_native_balance
)


def batch_mint_domains():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            domain_min_gas_balance = 1.003 if MIN_GAS_BALANCE < 1.003 else MIN_GAS_BALANCE
            check_min_native_balance(client=client, min_amount=domain_min_gas_balance)

            domain_name = get_available_name(proxy=client.proxy)

            if client.aptos_name_mint(domain_name=domain_name):
                database = Database.delete_data_item_from_data(database=database, data_item_index=data_item_index)
                Database.save_database(database)

                sleep()

        except Exception as e:
            if "Native balance less than min amount" in str(e):
                logger.warning("Native balance less than min amount")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                logger.warning("Native balance very low")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
            else:
                logger.error(f"Error while execute warmup module: {str(e)}")

    logger.debug("All accounts are finished. Run exit()")
    exit()


def batch_mint_sub_domains():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            check_min_native_balance(client=client, min_amount=MIN_GAS_BALANCE)

            sub_domain_name = get_available_name(proxy=client.proxy)

            client.sub_aptos_name_mint(sub_domain_name=sub_domain_name)

            data_item.sub_aptos_names_tx_count -= 1
            data_item = delete_all_tx_except_sub_domains(data_item)

            database = Database.update_database(database, data_item, data_item_index)
            Database.save_database(database)

            sleep()

        except Exception as e:
            if "Native balance less than min amount" in str(e):
                logger.warning("Native balance less than min amount")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                logger.warning("Native balance very low")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
            else:
                logger.error(f"Error while execute warmup module: {str(e)}")

    logger.debug("All accounts are finished. Run exit()")
    exit()


def batch_domains_v2_update():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            check_min_native_balance(client=client, min_amount=MIN_GAS_BALANCE)

            client.aptos_name_v2_update()

            database = Database.delete_data_item_from_data(database, data_item_index)
            Database.save_database(database)

            sleep()

        except Exception as e:
            if "Native balance less than min amount" in str(e):
                logger.warning("Native balance less than min amount")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                logger.warning("Native balance very low")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
            else:
                logger.error(f"Error while execute warmup module: {str(e)}")

    logger.debug("All accounts are finished. Run exit()")
    exit()


def batch_check_domains():
    database = Database.read_database()
    domain_names = []

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=False)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            domain_name, domain_timestamp = get_old_aptos_name_data(wallet_address=client.address)
            logger.info(f"{client.address} - {domain_name}")
            domain_names.append(domain_name)

            database = Database.delete_data_item_from_data(database, data_item_index)
            Database.save_database(database)

            sleep()

        except Exception as e:
            if "Native balance less than min amount" in str(e):
                logger.warning("Native balance less than min amount")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                logger.warning("Native balance very low")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
            else:
                logger.error(f"Error while execute warmup module: {str(e)}")

        Database.write_to_txt(file_path=DOMAINS_PATH, data=domain_names)

    logger.debug("All accounts are finished. Run exit()")
    exit()


def delete_all_tx_except_sub_domains(data_item):
    data_item.liquidswap_tx_count = 0
    data_item.pancakeswap_tx_count = 0
    data_item.sushiswap_tx_count = 0
    data_item.thalaswap_tx_count = 0
    data_item.gator_deposit_tx_count = 0
    data_item.gator_order_tx_count = 0
    data_item.gator_withdraw_tx_count = 0
    data_item.tortuga_tx_count = 0
    data_item.merkle_tx_count = 0
    data_item.amnis_tx_count = 0
    data_item.ditto_tx_count = 0
    data_item.wapal_bid_tx_count = 0
    data_item.wapal_mint_tx_count = 0
    data_item.topaz_bid_tx_count = 0
    data_item.bluemove_bid_tx_count = 0
    data_item.merkato_bid_tx_count = 0
    data_item.merkato_buy_tx_count = 0
    data_item.merkato_sell_tx_count = 0
    data_item.aptos_names_tx_count = 0

    return data_item

def delete_all_tx_except_domains(data_item):
    data_item.liquidswap_tx_count = 0
    data_item.pancakeswap_tx_count = 0
    data_item.sushiswap_tx_count = 0
    data_item.thalaswap_tx_count = 0
    data_item.gator_deposit_tx_count = 0
    data_item.gator_order_tx_count = 0
    data_item.gator_withdraw_tx_count = 0
    data_item.tortuga_tx_count = 0
    data_item.merkle_tx_count = 0
    data_item.amnis_tx_count = 0
    data_item.ditto_tx_count = 0
    data_item.wapal_bid_tx_count = 0
    data_item.wapal_mint_tx_count = 0
    data_item.topaz_bid_tx_count = 0
    data_item.bluemove_bid_tx_count = 0
    data_item.merkato_bid_tx_count = 0
    data_item.merkato_buy_tx_count = 0
    data_item.merkato_sell_tx_count = 0
    data_item.sub_aptos_names_tx_count = 0

    return data_item
