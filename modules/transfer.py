import random

from config import OKX_APTOS_CURRENCY, OKX_APTOS_WITHDRAWAL_FEE, OKX_APTOS_CHAIN
from core.clients.client import Client
from core.constants import APT_TOKEN
from core.models.wallet import Wallet
from core.okx import okx_withdraw
from logger import logger
from modules.database import Database
from utils import change_mobile_ip, get_transfer_amount, sleep


def batch_transfer_aptos():
    database = Database.read_database()

    while Database.not_empty(database):
        try:

            sleep()
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            transfer_amount = get_transfer_amount(client=client)
            client.aptos_send(amount=transfer_amount, address=data_item.okx_deposit_address)

            database = Database.delete_data_item_from_data(database, data_item_index)
            Database.save_database(database)

        except Exception as e:
            logger.error(f"Error while execute barch transfer aptos module: {str(e)}")
            exit()

    logger.debug("All accounts are finished. Run exit()")
    exit()


def batch_okx_bubble_withdraw():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            balance = APT_TOKEN.from_wei(client.get_token_balance(APT_TOKEN))
            finish_account_balance = random.uniform(1.003, 1.1)
            amount_to_withdraw = finish_account_balance - balance

            if amount_to_withdraw > 0:
                okx_withdraw(
                    client=client,
                    to_address=client.address,
                    amount_to_withdraw=amount_to_withdraw,
                    okx_currency=OKX_APTOS_CURRENCY,
                    okx_chain=OKX_APTOS_CHAIN,
                    okx_withdrawal_fee=OKX_APTOS_WITHDRAWAL_FEE,
                )

            database = Database.delete_data_item_from_data(database, data_item_index)
            Database.save_database(database)

            sleep()

        except Exception as e:
            logger.error(f"Error while execute batch transfer aptos module: {str(e)}")
            exit()

    logger.debug("All accounts are finished. Run exit()")
    exit()
