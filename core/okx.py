import time

from ccxt import okx

from config import (
    OKX_API_KEY,
    OKX_API_SECRET,
    OKX_API_PASSWORD,
    OKX_WAIT_FOR_WITHDRAWAL_FINAL_STATUS_ATTEMPTS,
    OKX_WAIT_FOR_WITHDRAWAL_FINAL_STATUS_TIME,
    OKX_WAIT_FOR_WITHDRAWAL_RECEIVED_ATTEMPTS,
    OKX_WAIT_FOR_WITHDRAWAL_RECEIVED_TIME,
    OKX_APTOS_CURRENCY,
    OKX_APTOS_CHAIN,
    OKX_APTOS_WITHDRAWAL_FEE,
    OKX_TOTAL_TRIES,
    OKX_SLEEP_TIME_AFTER_ERROR_SEC,
    OKX_WAIT_DEPOSIT_TIME
)
from core.clients.client import Client
from core.constants import APT_TOKEN
from logger import logger


def get_okx_config():
    default_config = {
        'apiKey': OKX_API_KEY,
        'secret': OKX_API_SECRET,
        'password': OKX_API_PASSWORD,
        'enableRateLimit': True,
    }

    return default_config


def wait_for_withdrawal_final_status(exchange: okx, withdrawal_id: str):
    try:
        attempt = 1
        while True:
            if attempt > OKX_WAIT_FOR_WITHDRAWAL_FINAL_STATUS_ATTEMPTS:
                raise (Exception('[OKX] Wait for withdrawal final status attempts limit exceeded.'))

            status = exchange.private_get_asset_deposit_withdraw_status(params={'wdId': withdrawal_id})

            if 'Cancellation complete' in status['data'][0]['state']:
                raise Exception('f[OKX] Withdrawal cancelled')

            if 'Withdrawal complete' not in status['data'][0]['state']:
                attempt = attempt + 1
                time.sleep(OKX_WAIT_FOR_WITHDRAWAL_FINAL_STATUS_TIME)
            else:
                logger.info('[OKX] Withdraw by OKX side was completed')
                return True

    except Exception as e:
        raise Exception(f'[OKX] Wait for withdrawal final status error: {e}')


def wait_for_withdraw_received(client: Client, initial_balance: float):
    okx_attempt = 0
    while True:
        if okx_attempt > OKX_WAIT_FOR_WITHDRAWAL_RECEIVED_ATTEMPTS:
            raise Exception('[OKX] Wait for withdraw attempts limit exceeded')

        final_balance = client.get_token_balance(APT_TOKEN)

        if final_balance > initial_balance:
            return True

        okx_attempt = okx_attempt + 1
        time.sleep(OKX_WAIT_FOR_WITHDRAWAL_RECEIVED_TIME)


def okx_watch_for_delivery(
        client: Client,
        exchange: okx,
        withdrawal_id: str,
        initial_client_balance: float
):
    withdrawal_completed_status = wait_for_withdrawal_final_status(exchange, withdrawal_id)
    if not withdrawal_completed_status:
        raise Exception('[OKX] Failed to wait for withdrawal completed status')

    withdrawal_received_status = wait_for_withdraw_received(client=client, initial_balance=initial_client_balance)

    if not withdrawal_received_status:
        raise Exception('[OKX] Failed to wait for withdrawal received status')

    return withdrawal_completed_status and withdrawal_received_status


def okx_withdraw(
        client: Client,
        to_address: str,
        amount_to_withdraw: float,
        okx_currency=OKX_APTOS_CURRENCY,
        okx_chain=OKX_APTOS_CHAIN,
        okx_withdrawal_fee=OKX_APTOS_WITHDRAWAL_FEE,
        retry=0
) -> str:
    exchange = okx(get_okx_config())

    logger.info(f"[OKX] Try to withdraw {amount_to_withdraw} {OKX_APTOS_CURRENCY}")

    try:
        initial_client_balance = client.get_token_balance(APT_TOKEN)

        withdrawal_id = exchange.withdraw(
            okx_currency,
            amount_to_withdraw,
            to_address,
            params={
                "toAddress": to_address,
                "chainName": f"{okx_currency}-{okx_chain}",
                "dest": 4,
                "fee": okx_withdrawal_fee,
                "pwd": '-',
                "amt": amount_to_withdraw,
                "network": okx_chain
            })['info']['wdId']

    except Exception as e:
        logger.error(f"[OKX] Withdraw {amount_to_withdraw} {OKX_APTOS_CURRENCY} error: {str(e)}")

        if retry < OKX_TOTAL_TRIES:
            time.sleep(OKX_SLEEP_TIME_AFTER_ERROR_SEC)
            return okx_withdraw(
                client=client,
                to_address=to_address,
                retry=retry + 1,
                amount_to_withdraw=amount_to_withdraw
            )
        else:
            raise Exception(f"[OKX] Withdraw failed: {str(e)}")

    delivered_success_status = okx_watch_for_delivery(
        client=client,
        initial_client_balance=initial_client_balance,
        withdrawal_id=withdrawal_id,
        exchange=exchange
    )

    if delivered_success_status:
        logger.success(f"[OKX] Success withdraw {amount_to_withdraw} {OKX_APTOS_CURRENCY}")


def withdraw_from_sub_account(name, symbol: str) -> None:
    try:
        exchange = okx(get_okx_config())
        try:
            amount = exchange.private_get_asset_subaccount_balances(
                params={'subAcct': name, 'ccy': symbol}
            )['data'][0]['availBal']

        except Exception as e:
            raise Exception(f'[OKX] Failed to fetch sub account balances: {str(e)}')

        logger.info(f"[OKX]{name} sub account balance: {amount} {symbol}")

        if amount != "0":
            exchange.load_markets()
            currency = exchange.currency(symbol)
            request = {
                'ccy': currency['id'],
                'amt': exchange.currency_to_precision(symbol, amount),
                'from': '6',
                'to': '6',
                'type': '2',  # sub-acc to main using main api key
                'subAcct': name,
            }

            exchange.private_post_asset_transfer(request)
            logger.info(f"[OKX] Withdraw {symbol} from sub account with name: '{name}' to main account successful")

    except Exception as e:
        raise (Exception(f"[OKX] Withdraw {symbol} from {name} to main account error: {str(e)}"))


def withdraw_from_sub_accounts(symbol=OKX_APTOS_CURRENCY):
    try:
        exchange = okx(get_okx_config())

        sub_accounts = exchange.private_get_users_subaccount_list()['data']
        for sub_acc in sub_accounts:
            withdraw_from_sub_account(sub_acc['subAcct'], symbol)
            time.sleep(1)  # okx rate limit is 1 request per second

    except Exception as e:
        raise (Exception(f"[OKX] Withdraw from sub accounts error: {str(e)}"))


def volume_mode_withdraw(
        client: Client,
        withdrawal_address: str,
        amount_to_withdraw: float,
        okx_currency=OKX_APTOS_CURRENCY,
        okx_chain=OKX_APTOS_CHAIN,
        okx_withdrawal_fee=OKX_APTOS_WITHDRAWAL_FEE,
):
    exchange = okx(get_okx_config())
    okx_main_account_balance = get_main_account_balance(exchange)

    while okx_main_account_balance < amount_to_withdraw:
        logger.info(f"[OKX] Main balance: {okx_main_account_balance} {OKX_APTOS_CURRENCY}")

        withdraw_from_sub_accounts()
        okx_main_account_balance = get_main_account_balance(exchange)

        if okx_main_account_balance < amount_to_withdraw:
            time.sleep(OKX_WAIT_DEPOSIT_TIME)

    okx_withdraw(
        client=client,
        to_address=withdrawal_address,
        amount_to_withdraw=amount_to_withdraw,
        okx_currency=okx_currency,
        okx_chain=okx_chain,
        okx_withdrawal_fee=okx_withdrawal_fee,
    )


def get_main_account_balance(exchange):
    okx_main_account_balance = exchange.fetch_balance(
        params={'type': 'funding'}
    )['total'][OKX_APTOS_CURRENCY]

    return okx_main_account_balance
