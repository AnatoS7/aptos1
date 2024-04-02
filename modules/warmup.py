import random

from config import (
    TORTUGA_STAKE_AMOUNT,
    DITTO_STAKE_AMOUNT,
    TOKENS,
    ROUND_TO,
    SWAP_DEVIATION,
    MIN_GAS_BALANCE,
    OKX_WITHDRAW_DEVIATION,
    VOLUME_MODE_TX_COUNT,
    GATOR_DEPOSIT_AMOUNT,
    AUTOSWAP,
    AMNIS_STAKE_AMOUNT,
    MERKLE_ORDER_AMOUNT,
    SWAPGPT_DEPOSIT_AMOUNT,
    KANALABS_DEPOSIT_AMOUNT,
    ARIES_DEPOSIT_AMOUNT,
    WAPAL_BID_AMOUNT,
    TOPAZ_BID_AMOUNT,
    BLUEMOVE_BID_AMOUNT,
    MERKATO_BID_AMOUNT,
    BALANCE_KEEP_AMOUNT_AFTER_TRIM,
    USE_BACKSWAP,
)
from core.clients.client import Client
from core.constants import APT_TOKEN, THAPT_TOKEN, USDC_TOKEN, AMNIS_TOKEN, TAPT_TOKEN, DITTO_TOKEN
from core.models.action import Action
from core.models.data_item import DataItem
from core.models.token import Token
from core.models.wallet import Wallet
from core.okx import volume_mode_withdraw
from logger import logger
from modules.collector import process_collector
from modules.database import Database
from utils import (
    change_mobile_ip,
    sleep,
    check_min_native_balance,
    warmup_gas_withdraw,
    get_transfer_amount
)


def batch_warmup():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}. "
                        f"Database tx count: {Database.get_database_tx_count(database['data'])}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            check_min_native_balance(client=client, min_amount=MIN_GAS_BALANCE)

            tx_status, data_item = run_warmup_action(client=client, data_item=data_item)

            if tx_status:
                database = Database.update_database(database, data_item, data_item_index)
            else:
                logger.error("Move account to errors")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)

            Database.save_database(database)

            sleep()

        except Exception as e:
            if "Native balance less than min amount" in str(e):
                logger.warning("Native balance less than min amount")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)
            elif "Invalid URL" in str(e):
                logger.error("Incorrect RPC")
                exit()
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                logger.error("Native balance very low, move wallet to errors")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)
            elif "Insufficient balance for activity" in str(e):
                logger.error("Insufficient balance for activity, move wallet to errors")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)
            else:
                logger.error(f"Error while execute batch warmup module: {str(e)}")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)

    logger.debug("All accounts are finished. Run exit()")
    exit()


def batch_warmup_with_gas():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}. "
                        f"Database tx count: {Database.get_database_tx_count(database['data'])}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            warmup_gas_withdraw(
                client=client,
                min_amount=MIN_GAS_BALANCE,
                amount_to_withdraw=random.uniform(*OKX_WITHDRAW_DEVIATION)
            )

            tx_status, data_item = run_warmup_action(client=client, data_item=data_item)

            if tx_status:
                database = Database.update_database(database, data_item, data_item_index)
            else:
                logger.error("Move account to errors")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)

            Database.save_database(database)

            sleep()

        except Exception as e:
            if "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                logger.warning("Native balance very low")
                warmup_gas_withdraw(
                    client=client,
                    min_amount=MIN_GAS_BALANCE,
                    amount_to_withdraw=random.uniform(*OKX_WITHDRAW_DEVIATION)
                )
            elif "Insufficient balance for activity" in str(e):
                logger.warning("Native balance very low")
                warmup_gas_withdraw(
                    client=client,
                    min_amount=MIN_GAS_BALANCE,
                    amount_to_withdraw=random.uniform(*OKX_WITHDRAW_DEVIATION)
                )
            else:
                logger.error(f"Error while execute batch warmup with gas module: {str(e)}")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)

    logger.debug("All accounts are finished. Run exit()")
    exit()


def batch_volume_warmup():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}. "
                        f"Database tx count: {Database.get_database_tx_count(database['data'])}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            volume_mode_withdraw(
                client=client,
                withdrawal_address=client.address,
                amount_to_withdraw=random.uniform(*OKX_WITHDRAW_DEVIATION)
            )

            circle_tx_index = 0
            volume_mode_tx_count = random.randint(*VOLUME_MODE_TX_COUNT)
            data_item_tx_count = Database.get_data_item_tx_count(data_item)

            if volume_mode_tx_count > data_item_tx_count:
                volume_mode_tx_count = data_item_tx_count

            while circle_tx_index < volume_mode_tx_count:
                logger.info(f"Tx number in circle: {circle_tx_index + 1}/{volume_mode_tx_count}")
                tx_status, data_item = run_warmup_action(client=client, data_item=data_item)
                circle_tx_index += 1

                if tx_status:
                    database = Database.update_database(database, data_item, data_item_index)
                else:
                    logger.error("Move account to errors")
                    database = Database.move_data_item_to_errors(database, data_item, data_item_index)

                Database.save_database(database)
                sleep()

            logger.info("Start collector")

            process_collector(client=client)

            transfer_amount = get_transfer_amount(client=client)
            client.aptos_send(amount=transfer_amount, address=data_item.okx_deposit_address)

            sleep()

        except Exception as e:
            if "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                logger.error("Native balance very low, move wallet to errors")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)
            elif "Insufficient balance for activity" in str(e):
                logger.error("Insufficient balance for activity, move wallet to errors")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)
            else:
                logger.error(f"Error while execute batch volume warmup module: {str(e)}")
                logger.info("Start collector")

                process_collector(client=client)

                transfer_amount = get_transfer_amount(client=client)
                client.aptos_send(amount=transfer_amount, address=data_item.okx_deposit_address)

                sleep()

                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)

    logger.debug("All accounts are finished. Run exit()")
    exit()


def batch_trim_balance():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}. ", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            apt_balance = APT_TOKEN.from_wei(client.get_token_balance(APT_TOKEN))
            apt_to_send = apt_balance - random.uniform(*BALANCE_KEEP_AMOUNT_AFTER_TRIM) - 0.000006

            if apt_to_send > 0:
                if data_item.okx_deposit_address:
                    client.aptos_send(amount=apt_to_send, address=data_item.okx_deposit_address)
                else:
                    logger.error("OKX deposit address not available for this wallet")

            database = Database.delete_data_item_from_data(database, data_item_index)
            Database.save_database(database)

            sleep()

        except Exception as e:
            if "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                logger.error("Native balance very low, move wallet to errors")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)
            else:
                logger.error(f"Error while execute batch trim balance module: {str(e)}")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)

    logger.debug("All accounts are finished. Run exit()")
    exit()

def batch_econia_withdraw():
    database = Database.read_database()

    while Database.not_empty(database):
        try:
            change_mobile_ip()

            data_item, data_item_index = Database.get_data_item(database["data"], is_random_item=True)

            client = Client(wallet=Wallet(private_key=data_item.private_key, proxy=data_item.proxy))

            logger.info(f"Accounts remaining count: {database['accounts_remaining']}", send_to_tg=False)
            logger.debug(f"Wallet address: {client.address}")

            check_min_native_balance(client=client, min_amount=MIN_GAS_BALANCE)

            if client.econia_full_withdraw():
                database = Database.delete_data_item_from_data(database, data_item_index)
                Database.save_database(database)
                sleep()

        except Exception as e:
            if "Native balance less than min amount" in str(e):
                logger.warning("Native balance less than min amount")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)
            elif "Invalid URL" in str(e):
                logger.error("Incorrect RPC")
                exit()
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                logger.error("Native balance very low, move wallet to errors")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)
            else:
                logger.error(f"Error while execute batch econia withdraw module: {str(e)}")
                database = Database.move_data_item_to_errors(database, data_item, data_item_index)
                Database.save_database(database)

    logger.debug("All accounts are finished. Run exit()")
    exit()


def run_warmup_action(client: Client, data_item: DataItem):
    try:
        action = get_random_warmup_action(data_item=data_item)
        balance = client.get_token_balance(token=APT_TOKEN)

        if action == Action.THALASWAP:
            thapt_balance = THAPT_TOKEN.from_wei(client.get_token_balance(THAPT_TOKEN))
            aptos_balance = APT_TOKEN.from_wei(client.get_token_balance(APT_TOKEN))

            aptos_amount_from = round(aptos_balance * random.uniform(*SWAP_DEVIATION), ROUND_TO)

            if thapt_balance > aptos_balance:
                tx_status = client.thala_swap(
                    token_from=THAPT_TOKEN,
                    token_to=APT_TOKEN,
                    amount_from=thapt_balance
                )
            else:
                tx_status = client.thala_swap(
                    token_from=APT_TOKEN,
                    token_to=THAPT_TOKEN,
                    amount_from=aptos_amount_from
                )

                if USE_BACKSWAP:
                    sleep()
                    token_from = THAPT_TOKEN
                    token_to = APT_TOKEN
                    amount = token_from.from_wei(client.get_token_balance(token_from))

                    tx_status = client.thala_swap(
                        token_from=token_from,
                        token_to=token_to,
                        amount_from=amount
                    )

        elif action == Action.LIQUIDSWAP:
            swap_data = get_warmup_swap_data(client=client)

            tx_status = client.liquidswap_swap(
                token_from=swap_data["token_from"],
                token_to=swap_data["token_to"],
                amount_from=swap_data["amount_from"]
            )

            if USE_BACKSWAP:
                sleep()
                token_from = swap_data["token_to"]
                token_to = swap_data["token_from"]
                amount = token_from.from_wei(client.get_token_balance(token_from))
                if token_to == APT_TOKEN:
                    tx_status = client.liquidswap_swap(
                        token_from=token_from,
                        token_to=APT_TOKEN,
                        amount_from=amount
                    )

        elif action == Action.PANCAKESWAP:
            swap_data = get_warmup_swap_data(client=client)

            tx_status = client.pancakeswap_swap(
                token_from=swap_data["token_from"],
                token_to=swap_data["token_to"],
                amount_from=swap_data["amount_from"]
            )

            if USE_BACKSWAP:
                sleep()
                token_from = swap_data["token_to"]
                token_to = swap_data["token_from"]
                amount = token_from.from_wei(client.get_token_balance(token_from))
                if token_to == APT_TOKEN:
                    tx_status = client.pancakeswap_swap(
                        token_from=token_from,
                        token_to=APT_TOKEN,
                        amount_from=amount
                    )

        elif action == Action.SUSHISWAP:
            usdc_balance = USDC_TOKEN.from_wei(client.get_token_balance(USDC_TOKEN))
            aptos_balance = APT_TOKEN.from_wei(client.get_token_balance(APT_TOKEN))

            aptos_amount_from = round(aptos_balance * random.uniform(*SWAP_DEVIATION), ROUND_TO)

            if usdc_balance > aptos_balance:
                tx_status = client.sushiswap_swap(
                    token_from=USDC_TOKEN,
                    token_to=APT_TOKEN,
                    amount_from=usdc_balance
                )
            else:
                tx_status = client.sushiswap_swap(
                    token_from=APT_TOKEN,
                    token_to=USDC_TOKEN,
                    amount_from=aptos_amount_from
                )

                if USE_BACKSWAP:
                    sleep()
                    token_from = USDC_TOKEN
                    token_to = APT_TOKEN
                    amount = token_from.from_wei(client.get_token_balance(token_from))

                    tx_status = client.sushiswap_swap(
                        token_from=token_from,
                        token_to=token_to,
                        amount_from=amount
                    )

        elif action == Action.AMNIS:
            stake_amount = random.uniform(*AMNIS_STAKE_AMOUNT)

            if balance < stake_amount:
                raise Exception(f"Amnis stake amount more than native wallet balance: {balance} < {stake_amount}")

            tx_status = client.amnis_stake(amount=stake_amount)

            if USE_BACKSWAP:
                sleep()
                token_from = AMNIS_TOKEN
                token_to = APT_TOKEN
                amount = token_from.from_wei(client.get_token_balance(token_from))

                tx_status = client.liquidswap_swap(
                    token_from=token_from,
                    token_to=token_to,
                    amount_from=amount
                )

        elif action == Action.GATOR_DEPOSIT:
            deposit_amount = random.uniform(*GATOR_DEPOSIT_AMOUNT)
            usdc_balance = client.get_token_balance(token=USDC_TOKEN)
            usdc_balance = USDC_TOKEN.from_wei(usdc_balance)

            if usdc_balance < deposit_amount:
                logger.warning(f"Gator deposit amount more than zUSDC balance: {usdc_balance} < {deposit_amount}")

                if AUTOSWAP:
                    if not client.autoswap_to_usdc_if_required(
                            deposit_amount=deposit_amount,
                            usdc_balance=usdc_balance,
                            balance=balance
                    ):
                        return False, data_item
                else:
                    return False, data_item

            tx_status = client.gator_deposit(amount=deposit_amount)

        elif action == Action.MERKLE:
            deposit_amount = random.uniform(*MERKLE_ORDER_AMOUNT)
            usdc_balance = client.get_token_balance(token=USDC_TOKEN)
            usdc_balance = USDC_TOKEN.from_wei(usdc_balance)

            if usdc_balance < deposit_amount:
                logger.warning(f"Merkle order amount more than zUSDC balance: {usdc_balance} < {deposit_amount}")

                if AUTOSWAP:
                    if not client.autoswap_to_usdc_if_required(
                            deposit_amount=deposit_amount,
                            usdc_balance=usdc_balance,
                            balance=balance
                    ):
                        return False, data_item
                else:
                    return False, data_item

            tx_status = client.merkle_order(amount=deposit_amount)

        elif action == Action.GATOR_ORDER:
            tx_status = client.gator_place_order()

        elif action == Action.GATOR_WITHDRAW:
            tx_status = client.gator_withdraw_apt()

        elif action == Action.WAPAL:
            bid_amount = random.uniform(*WAPAL_BID_AMOUNT)

            tx_status = client.wapal_bid(bid_amount)

        elif action == Action.WAPAL_MINT:
            tx_status = client.wapal_mint()

        elif action == Action.TOPAZ:
            bid_amount = random.uniform(*TOPAZ_BID_AMOUNT)

            tx_status = client.topaz_bid(bid_amount)

        elif action == Action.BLUEMOVE:
            bid_amount = random.uniform(*BLUEMOVE_BID_AMOUNT)

            tx_status = client.bluemove_bid(bid_amount)

        elif action == Action.MERKATO:
            bid_amount = random.uniform(*MERKATO_BID_AMOUNT)

            tx_status = client.merkato_bid(bid_amount)

        elif action == Action.MERKATO_BUY:
            tx_status, buyed_nft_address = client.mercato_buy()
            if tx_status:
                data_item.merkato_purchased_nft_address = buyed_nft_address

        elif action == Action.MERKATO_SELL:
            tx_status = client.merkato_sell(data_item.merkato_purchased_nft_address)
            if tx_status:
                data_item.merkato_purchased_nft_address = ""

        elif action == Action.TORTUGA:
            stake_amount = random.uniform(*TORTUGA_STAKE_AMOUNT)

            if APT_TOKEN.from_wei(balance) < stake_amount:
                raise Exception(f"Tortuga stake amount more than native wallet balance: {APT_TOKEN.from_wei(balance)} < {stake_amount}")

            tx_status = client.tortuga_stake(amount=stake_amount)

            if USE_BACKSWAP:
                sleep()
                token_from = TAPT_TOKEN
                token_to = APT_TOKEN
                amount = token_from.from_wei(client.get_token_balance(token_from))

                tx_status = client.liquidswap_swap(
                    token_from=token_from,
                    token_to=token_to,
                    amount_from=amount
                )

        elif action == Action.DITTO:
            stake_amount = random.uniform(*DITTO_STAKE_AMOUNT)

            if APT_TOKEN.from_wei(balance) < stake_amount:
                raise Exception(f"Ditto stake amount more than native wallet balance: {APT_TOKEN.from_wei(balance)} < {stake_amount}")

            tx_status = client.ditto_stake(amount=stake_amount)

            if USE_BACKSWAP:
                sleep()
                token_from = DITTO_TOKEN
                token_to = APT_TOKEN
                amount = token_from.from_wei(client.get_token_balance(token_from))

                tx_status = client.liquidswap_swap(
                    token_from=token_from,
                    token_to=token_to,
                    amount_from=amount
                )

        elif action == Action.SWAPGPT_DEPOSIT:
            apt_dep = random.uniform(*SWAPGPT_DEPOSIT_AMOUNT)

            if apt_dep > APT_TOKEN.from_wei(balance):
                logger.warning(f"SWAPGPT deposit amount more than APT balance: {APT_TOKEN.from_wei(balance)} < {apt_dep}")

                if AUTOSWAP:
                    if not client.autoswap_to_apt_if_required(
                            aptos_to_deposit=apt_dep,
                            balance=balance
                    ):
                        return False, data_item
                else:
                    return False, data_item

            tx_status = client.swapgpt_deposit(apt_dep)


        elif action == Action.SWAPGPT_BUY:
            client.swapgpt_buy_usdc()
            sleep()
            tx_status = client.swapgpt_buy_apt()

        elif action == Action.SWAPGPT_WITHDRAW:
            tx_status = client.swapgpt_withdraw()

        elif action == Action.KANALABS_DEPOSIT:
            apt_dep = random.uniform(*KANALABS_DEPOSIT_AMOUNT)

            if apt_dep > APT_TOKEN.from_wei(balance):
                logger.warning(f"KANALABS deposit amount more than APT balance: {APT_TOKEN.from_wei(balance)} < {apt_dep}")

                if AUTOSWAP:
                    if not client.autoswap_to_apt_if_required(
                            aptos_to_deposit=apt_dep,
                            balance=balance
                    ):
                        return False, data_item
                else:
                    return False, data_item

            tx_status = client.kanalabs_deposit(apt_dep)


        elif action == Action.KANALABS_BUY:
            client.kanalabs_buy_usdc()
            sleep()
            tx_status = client.kanalabs_buy_apt()

        elif action == Action.KANALABS_WITHDRAW:
            tx_status = client.kanalabs_withdraw()

        elif action == Action.ARIES_DEPOSIT:
            apt_dep = random.uniform(*ARIES_DEPOSIT_AMOUNT)

            if apt_dep > APT_TOKEN.from_wei(balance):
                logger.warning(f"ARIES deposit amount more than APT balance: {APT_TOKEN.from_wei(balance)} < {apt_dep}")

                if AUTOSWAP:
                    if not client.autoswap_to_apt_if_required(
                            aptos_to_deposit=apt_dep,
                            balance=balance
                    ):
                        return False, data_item
                else:
                    return False, data_item

            tx_status = client.aries_deposit(apt_dep)


        elif action == Action.ARIES_BUY:
            client.aries_buy_usdc()
            sleep()
            tx_status = client.aries_buy_apt()

        elif action == Action.ARIES_WITHDRAW:
            tx_status = client.aries_withdraw()

        else:
            raise Exception("Action choice error: zero tx in data item")

        data_item = warmup_data_item_update(action=action, data_item=data_item) if tx_status else data_item

        return tx_status, data_item

    except Exception as e:
        raise Exception(f"Run warmup action error: {str(e)}")


def get_random_warmup_action(data_item: DataItem):
    try:
        actions = []

        if data_item.liquidswap_tx_count > 0:
            actions.append(Action.LIQUIDSWAP)

        if data_item.pancakeswap_tx_count > 0:
            actions.append(Action.PANCAKESWAP)

        if data_item.sushiswap_tx_count > 0:
            actions.append(Action.SUSHISWAP)

        if data_item.thalaswap_tx_count > 0:
            actions.append(Action.THALASWAP)

        if data_item.gator_deposit_tx_count > 0:
            if data_item.gator_deposit_tx_count == data_item.gator_withdraw_tx_count:
                actions.append(Action.GATOR_DEPOSIT)

        if data_item.gator_withdraw_tx_count > 0:
            if data_item.gator_withdraw_tx_count - data_item.gator_order_tx_count == 1:
                actions.append(Action.GATOR_WITHDRAW)

        if data_item.gator_order_tx_count > 0:
            if data_item.gator_order_tx_count - data_item.gator_deposit_tx_count == 1:
                actions.append(Action.GATOR_ORDER)

        if data_item.swapgpt_deposit_tx_count > 0:
            if data_item.gator_withdraw_tx_count == 0:
                if data_item.swapgpt_withdraw_tx_count == data_item.swapgpt_deposit_tx_count:
                    actions.append(Action.SWAPGPT_DEPOSIT)

        if data_item.swapgpt_buy_tx_count > 0:
            if data_item.swapgpt_buy_tx_count - data_item.swapgpt_deposit_tx_count == 1:
                actions.append(Action.SWAPGPT_BUY)

        if data_item.swapgpt_withdraw_tx_count > 0:
            if data_item.swapgpt_withdraw_tx_count - data_item.swapgpt_buy_tx_count == 1:
                actions.append(Action.SWAPGPT_WITHDRAW)

        if data_item.kanalabs_deposit_tx_count > 0:
            if data_item.gator_withdraw_tx_count == 0:
                if data_item.swapgpt_withdraw_tx_count == 0:
                    if data_item.kanalabs_withdraw_tx_count == data_item.kanalabs_deposit_tx_count:
                        actions.append(Action.KANALABS_DEPOSIT)

        if data_item.kanalabs_buy_tx_count > 0:
            if data_item.kanalabs_buy_tx_count - data_item.kanalabs_deposit_tx_count == 1:
                if data_item.swapgpt_withdraw_tx_count == 0:
                    actions.append(Action.KANALABS_BUY)

        if data_item.kanalabs_withdraw_tx_count > 0:
            if data_item.kanalabs_withdraw_tx_count - data_item.kanalabs_buy_tx_count == 1:
                actions.append(Action.KANALABS_WITHDRAW)

        if data_item.aries_deposit_tx_count > 0:
            if data_item.gator_withdraw_tx_count == 0:
                if data_item.swapgpt_withdraw_tx_count == 0:
                    if data_item.kanalabs_withdraw_tx_count == 0:
                        if data_item.aries_withdraw_tx_count == data_item.aries_deposit_tx_count:
                            actions.append(Action.ARIES_DEPOSIT)

        if data_item.aries_buy_tx_count > 0:
            if data_item.aries_buy_tx_count - data_item.aries_deposit_tx_count == 1:
                actions.append(Action.ARIES_BUY)

        if data_item.aries_withdraw_tx_count > 0:
            if data_item.aries_withdraw_tx_count - data_item.aries_buy_tx_count == 1:
                actions.append(Action.ARIES_WITHDRAW)

        if data_item.tortuga_tx_count > 0:
            actions.append(Action.TORTUGA)

        if data_item.merkle_tx_count > 0:
            actions.append(Action.MERKLE)

        if data_item.amnis_tx_count > 0:
            actions.append(Action.AMNIS)

        if data_item.wapal_bid_tx_count > 0:
            actions.append(Action.WAPAL)

        if data_item.wapal_mint_tx_count > 0:
            actions.append(Action.WAPAL_MINT)

        if data_item.topaz_bid_tx_count > 0:
            actions.append(Action.TOPAZ)

        if data_item.bluemove_bid_tx_count > 0:
            actions.append(Action.BLUEMOVE)

        if data_item.merkato_bid_tx_count > 0:
            actions.append(Action.MERKATO)

        if data_item.merkato_buy_tx_count > 0:
            if data_item.merkato_buy_tx_count == data_item.merkato_sell_tx_count:
                actions.append(Action.MERKATO_BUY)

        if data_item.merkato_sell_tx_count > data_item.merkato_buy_tx_count:
            actions.append(Action.MERKATO_SELL)

        if data_item.ditto_tx_count > 0:
            actions.append(Action.DITTO)

        random_action = random.choice(actions) if len(actions) > 0 else None
        return random_action

    except Exception as e:
        raise Exception(f"Get random warmup action error: {str(e)}")


def warmup_data_item_update(action: Action, data_item: DataItem):
    try:
        if action == Action.LIQUIDSWAP:
            data_item.liquidswap_tx_count -= 1

        elif action == Action.PANCAKESWAP:
            data_item.pancakeswap_tx_count -= 1

        elif action == Action.SUSHISWAP:
            data_item.sushiswap_tx_count -= 1

        elif action == Action.THALASWAP:
            data_item.thalaswap_tx_count -= 1

        elif action == Action.GATOR_DEPOSIT:
            data_item.gator_deposit_tx_count -= 1

        elif action == Action.GATOR_ORDER:
            data_item.gator_order_tx_count -= 1

        elif action == Action.GATOR_WITHDRAW:
            data_item.gator_withdraw_tx_count -= 1

        elif action == Action.SWAPGPT_DEPOSIT:
            data_item.swapgpt_deposit_tx_count -= 1

        elif action == Action.SWAPGPT_BUY:
            data_item.swapgpt_buy_tx_count -= 1

        elif action == Action.SWAPGPT_WITHDRAW:
            data_item.swapgpt_withdraw_tx_count -= 1

        elif action == Action.KANALABS_DEPOSIT:
            data_item.kanalabs_deposit_tx_count -= 1

        elif action == Action.KANALABS_BUY:
            data_item.kanalabs_buy_tx_count -= 1

        elif action == Action.KANALABS_WITHDRAW:
            data_item.kanalabs_withdraw_tx_count -= 1

        elif action == Action.ARIES_DEPOSIT:
            data_item.aries_deposit_tx_count -= 1

        elif action == Action.ARIES_BUY:
            data_item.aries_buy_tx_count -= 1

        elif action == Action.ARIES_WITHDRAW:
            data_item.aries_withdraw_tx_count -= 1

        elif action == Action.TORTUGA:
            data_item.tortuga_tx_count -= 1

        elif action == Action.MERKLE:
            data_item.merkle_tx_count -= 1

        elif action == Action.AMNIS:
            data_item.amnis_tx_count -= 1

        elif action == Action.WAPAL:
            data_item.wapal_bid_tx_count -= 1

        elif action == Action.WAPAL_MINT:
            data_item.wapal_mint_tx_count -= 1

        elif action == Action.TOPAZ:
            data_item.topaz_bid_tx_count -= 1

        elif action == Action.BLUEMOVE:
            data_item.bluemove_bid_tx_count -= 1

        elif action == Action.MERKATO:
            data_item.merkato_bid_tx_count -= 1

        elif action == Action.MERKATO_BUY:
            data_item.merkato_buy_tx_count -= 1

        elif action == Action.MERKATO_SELL:
            data_item.merkato_sell_tx_count -= 1

        elif action == Action.DITTO:
            data_item.ditto_tx_count -= 1

        return data_item

    except Exception as e:
        raise Exception(f"Warmup data item update error: {str(e)}")


def get_random_token_to(token_from: Token) -> Token:
    try:
        random_token = random.choice(list(TOKENS.values()))

        if random_token == token_from or random_token == THAPT_TOKEN:
            return get_random_token_to(token_from=token_from)

        return random_token

    except Exception as e:
        raise Exception(f"Get random token_to error: {str(e)}")


def get_warmup_swap_data(client: Client) -> dict:
    try:
        token_from = client.get_max_balance_token()
        token_to = get_random_token_to(token_from=token_from)
        token_from_balance = token_from.from_wei(client.get_token_balance(token=token_from))
        amount_from = round(token_from_balance * random.uniform(*SWAP_DEVIATION), ROUND_TO)

        return {
            "token_from": token_from,
            "token_to": token_to,
            "amount_from": amount_from
        }

    except Exception as e:
        raise Exception(f"Get warmup swap data error: {str(e)}")
