from __future__ import annotations


class Token:
    def __init__(
            self,
            contract_address: str,
            decimals: int,
            symbol: str,
            coingecko_id: str
    ):
        self.contract_address = contract_address
        self.decimals = decimals
        self.symbol = symbol
        self.coingecko_id = coingecko_id

    def to_wei(self, value: float) -> int:
        return int(value * 10 ** self.decimals)

    def from_wei(self, value: int) -> int:
        return value / 10 ** self.decimals
