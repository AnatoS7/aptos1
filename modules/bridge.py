from config import CLAIM_TOKEN, MIN_GAS_BALANCE
from core.clients.client import Client
from core.models.wallet import Wallet
from logger import logger
from modules.database import Database
from utils import change_mobile_ip, sleep, check_min_native_balance


def batch_claim_layerzero_bridged_tokens():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=False)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            check_min_native_balance(client=client, min_amount=MIN_GAS_BALANCE)

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            tx_status = client.claim_bridged_tokens(token=CLAIM_TOKEN)

            if tx_status:
                database = Database.delete_data_item_from_data(database, data_item_index)
            else:
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)

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
