from core.models.wallet import Wallet


class DataItem:
    def __init__(
            self,
            wallet: Wallet,
            okx_deposit_address: str,
            pancakeswap_tx_count: int,
            liquidswap_tx_count: int,
            sushiswap_tx_count: int,
            thalaswap_tx_count: int,
            gator_deposit_tx_count: int,
            gator_order_tx_count: int,
            gator_withdraw_tx_count: int,
            tortuga_tx_count: int,
            merkle_tx_count: int,
            amnis_tx_count: int,
            ditto_tx_count: int,
            wapal_bid_tx_count: int,
            wapal_mint_tx_count: int,
            topaz_bid_tx_count: int,
            bluemove_bid_tx_count: int,
            merkato_bid_tx_count: int,
            merkato_buy_tx_count: int,
            merkato_purchased_nft_address: str,
            merkato_sell_tx_count: int,
            swapgpt_deposit_tx_count: int,
            swapgpt_buy_tx_count: int,
            swapgpt_withdraw_tx_count: int,
            kanalabs_deposit_tx_count: int,
            kanalabs_buy_tx_count: int,
            kanalabs_withdraw_tx_count: int,
            aries_deposit_tx_count: int,
            aries_buy_tx_count: int,
            aries_withdraw_tx_count: int,
            aptos_names_tx_count: int,
            sub_aptos_names_tx_count: int
    ):
        self.private_key = wallet.private_key
        self.address = wallet.address
        self.proxy = wallet.proxy
        self.okx_deposit_address = okx_deposit_address
        self.pancakeswap_tx_count = pancakeswap_tx_count
        self.liquidswap_tx_count = liquidswap_tx_count
        self.sushiswap_tx_count = sushiswap_tx_count
        self.thalaswap_tx_count = thalaswap_tx_count
        self.gator_deposit_tx_count = gator_deposit_tx_count
        self.gator_order_tx_count = gator_order_tx_count
        self.gator_withdraw_tx_count = gator_withdraw_tx_count
        self.tortuga_tx_count = tortuga_tx_count
        self.merkle_tx_count = merkle_tx_count
        self.amnis_tx_count = amnis_tx_count
        self.ditto_tx_count = ditto_tx_count
        self.wapal_bid_tx_count = wapal_bid_tx_count
        self.wapal_mint_tx_count = wapal_mint_tx_count
        self.topaz_bid_tx_count = topaz_bid_tx_count
        self.bluemove_bid_tx_count = bluemove_bid_tx_count
        self.merkato_bid_tx_count = merkato_bid_tx_count
        self.merkato_buy_tx_count = merkato_buy_tx_count
        self.merkato_purchased_nft_address = merkato_purchased_nft_address
        self.merkato_sell_tx_count = merkato_sell_tx_count
        self.swapgpt_deposit_tx_count = swapgpt_deposit_tx_count
        self.swapgpt_buy_tx_count = swapgpt_buy_tx_count
        self.swapgpt_withdraw_tx_count = swapgpt_withdraw_tx_count
        self.kanalabs_deposit_tx_count = kanalabs_deposit_tx_count
        self.kanalabs_buy_tx_count = kanalabs_buy_tx_count
        self.kanalabs_withdraw_tx_count = kanalabs_withdraw_tx_count
        self.aries_deposit_tx_count = aries_deposit_tx_count
        self.aries_buy_tx_count = aries_buy_tx_count
        self.aries_withdraw_tx_count = aries_withdraw_tx_count
        self.aptos_names_tx_count = aptos_names_tx_count
        self.sub_aptos_names_tx_count = sub_aptos_names_tx_count
