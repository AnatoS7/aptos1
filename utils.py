import random
import time

import requests
from tqdm import tqdm

from config import (
    USE_MOBILE_PROXY,
    CHANGE_IP_URL,
    SLEEP_TIME,
    USE_PROXY,
    WALLET_KEEP_AMOUNT
)
from core.clients.client import Client
from core.constants import APT_TOKEN
from core.okx import volume_mode_withdraw
from logger import logger


def change_mobile_ip() -> None:
    try:
        if USE_MOBILE_PROXY:
            res = requests.get(CHANGE_IP_URL)

            if res.status_code == 200:
                logger.info("IP address changed successfully", send_to_tg=False)
            else:
                raise Exception("Failed to change IP address")

    except Exception as e:
        raise Exception(f"Encountered an error when changing ip address, check your proxy provider: {e}")


def sleep() -> None:
    try:
        for _ in tqdm(range(random.randint(*SLEEP_TIME)), colour="green"):
            time.sleep(1)

    except Exception as e:
        logger.error(f"Sleep error: {str(e)}")


def get_random_domain_name():
    try:
        url = 'https://spinxo.com/services/NameService.asmx/GetNames'
        payload = {
            "snr": {
                "category": 0,
                "UserName": "",
                "Hobbies": "",
                "ThingsILike": "",
                "Numbers": "",
                "WhatAreYouLike": "",
                "Words": "",
                "Stub": "username",
                "LanguageCode": "en",
                "NamesLanguageID": "45",
                "Rhyming": False,
                "OneWord": False,
                "UseExactWords": False,
                "ScreenNameStyleString": "Any",
                "GenderAny": False,
                "GenderMale": False,
                "GenderFemale": False
            }
        }
        res = requests.post(url, json=payload)
        names = res.json()['d']['Names']

        return names

    except Exception as e:
        raise Exception(f"Get random domain name error: {str(e)}")


def get_available_name(proxy):
    try:
        names = get_random_domain_name()

        while True:
            if len(names) == 0:
                return get_available_name(proxy)

            name = names.pop(random.randint(0, len(names) - 1)).lower()

            if len(name) < 6:
                continue

            url = f'https://www.aptosnames.com/api/mainnet/v1/address/{name}'

            if USE_PROXY:
                res = requests.get(url, proxies={"https": f"http://{proxy}"})
            else:
                res = requests.get(url)

            if res.text == "{}":
                return name

    except Exception as e:
        raise Exception(f"Get available name error: {str(e)}")


def check_min_native_balance(client: Client, min_amount: float):
    try:
        balance = APT_TOKEN.from_wei(client.get_token_balance(APT_TOKEN))

        if balance < min_amount:
            raise Exception("Native balance less than min amount")

    except Exception as e:
        raise Exception(f"Check min native balance error: {str(e)}")


def get_transfer_amount(client: Client):
    wallet_balance_ether = APT_TOKEN.from_wei(client.get_token_balance(token=APT_TOKEN))
    wallet_keep_amount = random.uniform(*WALLET_KEEP_AMOUNT)
    amount = wallet_balance_ether - wallet_keep_amount

    if amount < 0:
        raise Exception("Transfer amount less than wallet keep amount")

    return amount


def warmup_gas_withdraw(client: Client, min_amount: float, amount_to_withdraw: float) -> None:
    balance = APT_TOKEN.from_wei(client.get_token_balance(APT_TOKEN))

    if balance < min_amount:
        volume_mode_withdraw(
            client=client,
            withdrawal_address=client.address,
            amount_to_withdraw=amount_to_withdraw
        )


start_message = r'''

                                  ^Y                  
                                 ~&@7                
                      75~:.     !@&~&:       , .      
                      .&&PYY7^.7@@# J#   .^7JPB^      
                       ^@&Y:^?Y&@@P  GBB&@@GP&~       
                        7@@&?  :&@J  G@@&Y.~#^        
                     .:~?&#&@&? !@! B@G~  !&:         
                :75PPY?!^. .:?GG~P!5P~^!YG@@GJ~.      
                .~YG#&&##B#BGPJ?J??J?J5GBBBB##&#B5!.  
                    .^?P&@BJ!^^5G~G^5GJ^. .:!?Y5P57:\  
                       .#?  ^P@#.:@J !&@@#&J~^.       
                      :#7.J&@@#. !@@~  !&@@5          
                     ^&GP@@&BG#. J@@@5?~:?&@7         
                    :BGJ7^..  GG P@@J.:!JY5&@:        
                    .         .&7B@?      .~YJ        
                              ^&@7                   
                                ?!                  

               __    _ __                        __                  
   _______  __/ /_  (_) /  _   __   ____  ____ _/ /______  ____  ___ 
  / ___/ / / / __ \/ / /  | | / /  /_  / / __ `/ //_/ __ \/ __ \/ _ \
 (__  ) /_/ / /_/ / / /   | |/ /    / /_/ /_/ / ,< / /_/ / / / /  __/   
/____/\__, /_.___/_/_/    |___/    /___/\__,_/_/|_|\____/_/ /_/\___/ 
     /____/                                                          

Modules v2.0:
1: create_database                        | создать базу данных
2: batch_warmup                           | обычный прогрев кошельков
3: batch_warmup_with_gas                  | прогрев кошельков с выводом газа
4: batch_volume_warmup                    | прогрев через okx для лоубанков
5: batch_collector                        | сбор всех монет на аккаунте в apt токен
6: batch_mint_domains                     | регистрирует на аккаунт домен (aptosname)
7: batch_mint_sub_domains                 | регистрирует на аккаунт субдомен (sub aptosname)
8: batch_claim_layerzero_bridged_tokens   | клеймит токены отправленные из evm (юзать только там, где они есть)
9: batch_transfer_aptos                   | отправка apt токенов на указанные кошельки
10: batch_domains_v2_update               | обновление доменов v2
11: batch_check_domains                   | вывод через moralis всех aptos имен
12: restore_failed_accounts               | восстановить ошибочные кошельки
13: batch_trim_balance                    | оставить на балансе только указанное число APT, остальное отправить на ОКХ
14: batch_econia_withdraw                 | вывод apt и usdc с econia
'''
