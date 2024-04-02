import re
from datetime import datetime

import requests
from aptos_sdk.type_tag import TypeTag, StructTag
from moralis.aptos_api import aptos_api

from config import MORALIS_API_KEY
from core.constants import (
    APTOS_EXPLORER_URL,
    PANCAKESWAP,
    LIQUIDSWAP_V2,
    LIQUIDSWAP_V1,
    THAPT_TOKEN,
    APT_TOKEN,
    THALASWAP,
    LIQUIDSWAP_V1_TOKENS,
    WAPAL_NFT_DATA
)
from core.models.token import Token


def get_link_to_explorer(tx_hash: str) -> str:
    try:
        return APTOS_EXPLORER_URL.format(tx_hash)

    except Exception as e:
        raise Exception(f"Get explorer link by tx hash error: {str(e)}")

def get_pancakeswap_resource_type(token_from: Token, token_to: Token) -> str:
    try:
        account_resource_type = PANCAKESWAP["resource_type"]

        resource_type = (
            f"{account_resource_type}"
            f"<{token_from.contract_address},"
            f" {token_to.contract_address}>"
        )

        return resource_type

    except Exception as e:
        raise Exception(f"Get pancakeswap resource type error: {str(e)}")


def get_liquidswap_resource_type(token_from: Token, token_to: Token) -> str:
    try:
        if token_from in LIQUIDSWAP_V1_TOKENS or token_to in LIQUIDSWAP_V1_TOKENS:
            liquidswap_dict = LIQUIDSWAP_V1
        else:
            liquidswap_dict = LIQUIDSWAP_V2

        account_resource_type = liquidswap_dict["resource_type"]
        curve_uncorrelated = liquidswap_dict["curve_uncorrelated"]

        resource_type = (
            f"{account_resource_type}"
            f"<{token_from.contract_address},"
            f" {token_to.contract_address},"
            f" {curve_uncorrelated}>"
        )

        return resource_type

    except Exception as e:
        raise Exception(f"Get liquidswap resource type error: {str(e)}")


def get_simple_swap_type_args(token_from: Token, token_to: Token) -> list[TypeTag]:
    try:
        return [
            TypeTag(StructTag.from_str(token_from.contract_address)),
            TypeTag(StructTag.from_str(token_to.contract_address))
        ]

    except Exception as e:
        raise Exception(f"Get simple swap type args error: {str(e)}")


def get_thala_swap_type_args(token_from: Token, token_to: Token) -> list[TypeTag]:
    try:
        return [
            TypeTag(StructTag.from_str(THAPT_TOKEN.contract_address)),
            TypeTag(StructTag.from_str(APT_TOKEN.contract_address)),
            TypeTag(StructTag.from_str(THALASWAP["base_pool"])),
            TypeTag(StructTag.from_str(THALASWAP["base_pool"])),
            TypeTag(StructTag.from_str(token_from.contract_address)),
            TypeTag(StructTag.from_str(token_to.contract_address))
        ]

    except Exception as e:
        raise Exception(f"Get thala swap type args error: {str(e)}")


def get_liquidswap_type_args(token_from: Token, token_to: Token) -> list[TypeTag]:
    try:
        if token_from in LIQUIDSWAP_V1_TOKENS or token_to in LIQUIDSWAP_V1_TOKENS:
            liquidswap_data = LIQUIDSWAP_V1
        else:
            liquidswap_data = LIQUIDSWAP_V2

        return [
            TypeTag(StructTag.from_str(token_from.contract_address)),
            TypeTag(StructTag.from_str(token_to.contract_address)),
            TypeTag(StructTag.from_str(liquidswap_data["curve_uncorrelated"]))
        ]

    except Exception as e:
        raise Exception(f"Get liquidswap type args error: {str(e)}")


def extract_amount_y_out_value(simulation_data: dict) -> float:
    try:
        simulation_data = str(simulation_data)
        pattern = r"'amount_y_out': '([^']+)'"
        match = re.search(pattern, simulation_data)

        if match:
            number = int(match.group(1))

            return number
        else:
            raise Exception("No amount_y_out extracted")

    except Exception as e:
        raise Exception(f"Extract amount_y_out value error: {str(e)}")


def extract_amount_out_value(simulation_data: dict) -> float:
    try:
        simulation_data = str(simulation_data)
        pattern = r"'amount_out': '([^']+)'"
        match = re.search(pattern, simulation_data)

        if match:
            number = int(match.group(1))

            return number
        else:
            raise Exception("No amount_out extracted")

    except Exception as e:
        raise Exception(f"Extract amount_out value error: {str(e)}")


def get_old_aptos_name_data(wallet_address: str) -> tuple[str, int]:
    try:
        params = {
            "limit": 100,
            "owner_addresses": [wallet_address],
            "network": "mainnet"
        }

        domain_item = None
        data = aptos_api.wallets.get_nft_by_owners(api_key=MORALIS_API_KEY, params=params)
        pattern = re.compile(r'^[^.]*\.apt$')

        for item in data["result"]:
            if item["collection_name"] == "Aptos Names V1" and pattern.match(item["name"]):
                domain_item = item
                break

        if domain_item is None:
            raise Exception("Aptos name not focund")

        try:
            domain_name = domain_item["name"][:-4]
        except Exception:
            raise Exception("Name is None")

        try:
            domain_mint_timestamp = domain_item["last_transaction_timestamp"]
        except Exception:
            raise Exception("Last transaction timestamp is None")

        domain_mint_datetime = datetime.strptime(domain_mint_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        domain_mint_timestamp = int(domain_mint_datetime.timestamp())

        one_year_timestamp = 31470526
        domain_expiration_timestamp = domain_mint_timestamp + one_year_timestamp

        return domain_name, domain_expiration_timestamp

    except Exception as e:
        raise Exception(f"Get old aptos name data error: {str(e)}")


def get_old_aptos_name_wia_wapal(wallet_address: str, proxy: str) -> str:
    url = WAPAL_NFT_DATA.format(address=wallet_address)
    proxy = None if proxy is None else {"https": f"http://{proxy}"}
    response = requests.get(url=url, proxies=proxy)
    data = response.json()

    pattern = re.compile(r'^[^.]*\.apt$')

    domain_item = None
    for item in data:
        if item["collectionName"] == "Aptos Names V1" and pattern.match(item["tokenName"]):
            domain_item = item["tokenName"][:-4]
            break

    return domain_item
