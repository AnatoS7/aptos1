from core.models.token import Token

PRIVATE_KEYS_PATH = "data/private_keys.txt"
PROXIES_PATH = "data/proxies.txt"
DOMAINS_PATH = "data/domains.txt"
OKX_ADDRESSES_PATH = "data/okx_deposit_addresses.txt"
DATABASE_PATH = "data/database.json"

COIN_INFO = "0x1::coin::CoinInfo"
COIN_STORE = "0x1::coin::CoinStore"

COINGECKO_API_TOKEN_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price?ids={}&vs_currencies=usd"
APTOS_EXPLORER_URL = "https://explorer.aptoslabs.com/txn/{}?network=mainnet"
PONTEM_URL = "https://aptos-mainnet.pontem.network/v1/view"
GRAPHQL_URL = "https://api.indexer.xyz/graphql"
APTOSLABS_URL = "https://fullnode.mainnet.aptoslabs.com/v1/view"
ECONIA_PRICES_URL = "https://app.panora.exchange/api/shared/getUsdValue"
KANALABS_URL = "https://aptos-mainnet.nodereal.io/v1/8cc38039f305423e91e3f0d856b992f7/v1/view"
ARIES_URL = "https://aptos-mainnet.nodereal.io/v1/dbe3294d24374cad9d0886ca12d0aeb7/v1/tables/"

PANCAKESWAP = {
    "module_account": "0xc7efb4076dbe143cbcd98cfaaa929ecfc8f299203dfff63b95ccb6bfe19850fa",
    "resource_account": "0xc7efb4076dbe143cbcd98cfaaa929ecfc8f299203dfff63b95ccb6bfe19850fa",
    "resource_type": "0xc7efb4076dbe143cbcd98cfaaa929ecfc8f299203dfff63b95ccb6bfe19850fa::swap::TokenPairReserve",
    "script": "0xc7efb4076dbe143cbcd98cfaaa929ecfc8f299203dfff63b95ccb6bfe19850fa::router",
    "function": "swap_exact_input"
}

SUSHISWAP = {
    "script": "0x31a6675cbe84365bf2b0cbce617ece6c47023ef70826533bde5203d32171dc3c::router",
    "function": "swap_exact_input"
}

THALASWAP = {
    "base_pool": "0x48271d39d0b05bd6efca2278f22277d6fcc375504f9839fd73f74ace240861af::base_pool::Null",
    "script": "0x48271d39d0b05bd6efca2278f22277d6fcc375504f9839fd73f74ace240861af::stable_pool_scripts",
    "function": "swap_exact_in"
}

GATOR = {
    "script_user": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::user",
    "script_market": "0xc0deb00c405f84c85dc13442e305df75d1288100cdd82675695f6148c7ece51c::market",
    "function_deposit": "deposit_from_coinstore",
    "function_register": "register_market_account",
    "function_order": "place_market_order_user_entry",
    "function_withdraw": "withdraw_to_coinstore",
}

LIQUIDSWAP_V2 = {
    "module_account": "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12",
    "resource_account": "0x05a97986a9d031c4567e15b797be516910cfcb4156312482efc6a19c0a30c948",
    "resource_type": "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::liquidity_pool::LiquidityPool",
    "script": "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::scripts_v2",
    "function": "swap",
    "curve_uncorrelated": "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::curves::Uncorrelated"
}

LIQUIDSWAP_V1 = {
    "module_account": "0x163df34fccbf003ce219d3f1d9e70d140b60622cb9dd47599c25fb2f797ba6e",
    "resource_account": "0x61d2c22a6cb7831bee0f48363b0eec92369357aece0d1142062f7d5d85c7bef8",
    "resource_type": "0x163df34fccbf003ce219d3f1d9e70d140b60622cb9dd47599c25fb2f797ba6e::liquidity_pool::LiquidityPool",
    "script": "0x163df34fccbf003ce219d3f1d9e70d140b60622cb9dd47599c25fb2f797ba6e::scripts",
    "function": "swap",
    "curve_uncorrelated": "0x163df34fccbf003ce219d3f1d9e70d140b60622cb9dd47599c25fb2f797ba6e::curves::Uncorrelated"
}

TORTUGA = {
    "module_account": "0x8f396e4246b2ba87b51c0739ef5ea4f26515a98375308c31ac2ec1e42142a57f",
    "script": "0x8f396e4246b2ba87b51c0739ef5ea4f26515a98375308c31ac2ec1e42142a57f::stake_router",
    "function": "stake"
}

DITTO = {
    "module_account": "0xd11107bdf0d6d7040c6c0bfbdecb6545191fdf13e8d8d259952f53e1713f61b5",
    "script": "0xd11107bdf0d6d7040c6c0bfbdecb6545191fdf13e8d8d259952f53e1713f61b5::ditto_staking",
    "function": "stake_aptos"
}

LAYERZERO_BRIDGE = {
    "module_account": "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa",
    "script": "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::coin_bridge",
    "function": "claim_coin"
}

APTOS_NAMES = {
    "script": "0x867ed1f6bf916171b1de3ee92849b8978b7d1b9e0a8cc982a3d19d535dfd9c0c::router",
    "function_mint_domain": "register_domain",
    "function_mint_sub_domain": "register_subdomain",
    "function_migrate_name": "migrate_name"
}

TOKEN_REGISTRATION = {
    "script": "0x1::managed_coin",
    "function": "register"
}

APTOS_SEND = {
    "script": "0x1::aptos_account",
    "function": "transfer"
}

WAPAL_NFT_DATA = "https://marketplace-api.wapal.io/user/tokens/{address}"

APT_TOKEN = Token(
    contract_address="0x1::aptos_coin::AptosCoin",
    decimals=8,
    symbol="APT",
    coingecko_id="aptos"
)

USDC_TOKEN = Token(
    contract_address="0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC",
    decimals=6,
    symbol="zUSDC",
    coingecko_id="usd-coin"
)

USDT_TOKEN = Token(
    contract_address="0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDT",
    decimals=6,
    symbol="zUSDT",
    coingecko_id="tether"
)

WETH_TOKEN = Token(
    contract_address="0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::WETH",
    decimals=6,
    symbol="zWETH",
    coingecko_id="ethereum"
)

TAPT_TOKEN = Token(
    contract_address="0x84d7aeef42d38a5ffc3ccef853e1b82e4958659d16a7de736a29c55fbbeb0114::staked_aptos_coin::StakedAptosCoin",
    decimals=8,
    symbol="tAPT",
    coingecko_id="aptos"
)

DITTO_TOKEN = Token(
    contract_address="0xd11107bdf0d6d7040c6c0bfbdecb6545191fdf13e8d8d259952f53e1713f61b5::staked_coin::StakedAptos",
    decimals=8,
    symbol="stAPT",
    coingecko_id="ditto-staked-aptos"
)

ALT_TOKEN = Token(
    contract_address="0xd0b4efb4be7c3508d9a26a9b5405cf9f860d0b9e5fe2f498b90e68b8d2cedd3e::aptos_launch_token::AptosLaunchToken",
    decimals=8,
    symbol="ALT",
    coingecko_id="aptos-launch-token"
)

THL_TOKEN = Token(
    contract_address="0x7fd500c11216f0fe3095d0c4b8aa4d64a4e2e04f83758462f2b127255643615::thl_coin::THL",
    decimals=8,
    symbol="THL",
    coingecko_id="thala"
)

THAPT_TOKEN = Token(
    contract_address="0xfaf4e633ae9eb31366c9ca24214231760926576c7b625313b3688b5e900731f6::staking::ThalaAPT",
    decimals=8,
    symbol="thAPT",
    coingecko_id="thala-apt"
)

SOL_TOKEN = Token(
    contract_address="0xdd89c0e695df0692205912fb69fc290418bed0dbe6e4573d744a6d5e6bab6c13::coin::T",
    decimals=8,
    symbol="SOL",
    coingecko_id="sol-wormhole"
)

AMNIS_TOKEN = Token(
    contract_address="0x111ae3e5bc816a5e63c2da97d0aa3886519e0cd5e4b046659fa35796bd11542a::stapt_token::StakedApt",
    decimals=8,
    symbol="stAPT",
    coingecko_id="amnis-staked-aptos-coin"
)

LIQUIDSWAP_V1_TOKENS = [
    AMNIS_TOKEN,
    THL_TOKEN
]
