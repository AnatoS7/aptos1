from config import TOKENS
from core.clients.client import Client
from core.constants import APT_TOKEN, THAPT_TOKEN
from core.models.wallet import Wallet
from logger import logger
from modules.database import Database
from utils import change_mobile_ip, sleep


def batch_collector():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            process_collector(client=client)

            database = Database.delete_data_item_from_data(database, data_item_index)
            Database.save_database(database)

        except Exception as e:
            if "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                logger.error("Native balance very low, move wallet to errors")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)
            else:
                logger.error(f"Error while execute batch collector module: {str(e)}")

    logger.debug("All accounts are finished. Run exit()")
    exit()


def process_collector(client):
    for token in TOKENS.values():
        token_balance = token.from_wei(client.get_token_balance(token))

        if token_balance > 0 and token != APT_TOKEN:
            if token == THAPT_TOKEN:
                client.thala_swap(
                    token_from=token,
                    token_to=APT_TOKEN,
                    amount_from=token_balance
                )
            else:
                client.liquidswap_swap(
                    token_from=token,
                    token_to=APT_TOKEN,
                    amount_from=token_balance
                )
            sleep()
