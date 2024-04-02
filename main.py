from logger import logger
from modules.bridge import batch_claim_layerzero_bridged_tokens
from modules.collector import batch_collector
from modules.database import Database
from modules.domains import (
    batch_mint_domains,
    batch_mint_sub_domains,
    batch_domains_v2_update,
    batch_check_domains
)
from modules.transfer import batch_transfer_aptos, batch_okx_bubble_withdraw
from modules.warmup import (
    batch_warmup,
    batch_warmup_with_gas,
    batch_volume_warmup,
    batch_trim_balance,
    batch_econia_withdraw
)
from utils import start_message

logger.debug(start_message, send_to_tg=False)
module = input("Start module: ")

if module == "1":
    Database.create_database()
elif module == "2":
    batch_warmup()
elif module == "3":
    batch_warmup_with_gas()
elif module == "4":
    batch_volume_warmup()
elif module == "5":
    batch_collector()
elif module == "6":
    batch_mint_domains()
elif module == "7":
    batch_mint_sub_domains()
elif module == "8":
    batch_claim_layerzero_bridged_tokens()
elif module == "9":
    batch_transfer_aptos()
elif module == "10":
    batch_domains_v2_update()
elif module == "11":
    batch_check_domains()
elif module == "12":
    Database.restore_error_accounts()
elif module == "13":
    batch_trim_balance()
elif module == "14":
    batch_econia_withdraw()
elif module == "15":
    batch_okx_bubble_withdraw()
else:
    logger.error(f"Invalid module number: {module}")
