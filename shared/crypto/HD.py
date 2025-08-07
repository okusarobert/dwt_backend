import os
import hashlib
from hashlib import sha256
from ecdsa import SECP256k1
from eth_utils import keccak
from hdwallet import BIP44HDWallet
from hdwallet.cryptocurrencies import EthereumMainnet, BitcoinMainnet, BitcoinTestnet, TronMainnet, BitcoinCashMainnet, GroestlCoinMainnet, LitecoinMainnet, LitecoinTestnet, BitcoinTestnet
from hdwallet.derivations import BIP44Derivation
from hdwallet.utils import generate_mnemonic
from typing import Optional

SECP256k1_GEN = SECP256k1.generator
SECP256k1_ORD = SECP256k1.order


class HD():
    def __init__(self, entropy_bit_size: int = 128):
        self.entropy_bit_size = entropy_bit_size
        self.dirname = os.path.dirname(__file__)

    def mnemonic(self, language: str = "english"):
        return generate_mnemonic(language=language, strength=128)

    def make_seed(self, mnemonic: str):
        passphrase = ""
        salt = "mnemonic" + passphrase
        seed = hashlib.pbkdf2_hmac(
            "sha512",
            mnemonic.encode("utf-8"),
            salt.encode("utf-8"),
            2048
        )
        return seed.hex()


class BTC(HD):
    coin = BitcoinTestnet

    def __init__(self):
        self.wallet: BIP44HDWallet = BIP44HDWallet(cryptocurrency=self.coin)
        super().__init__()

    def from_mnemonic(self, mnemonic: str, language: Optional[str] = "english", passphrase: Optional[str] = None):
        self.wallet.from_mnemonic(
            mnemonic=mnemonic, language=language, passphrase=passphrase
        )
        return self

    def from_seed(self, seed: str):
        self.wallet.from_seed(seed=seed)
        return self

    def clean_derivation(self):
        self.wallet.clean_derivation()
        return self

    def new_address(self, change: Optional[bool] = False, index: Optional[int] = 0, account: Optional[int] = 0):
        self.clean_derivation()
        derivation: BIP44Derivation = BIP44Derivation(
            cryptocurrency=self.coin, account=account, change=change, address=index
        )
        self.wallet.from_path(path=derivation)

        address = self.wallet.address()
        priv_key = self.wallet.private_key()
        pub_key = self. wallet.public_key()

        # print(json.dumps(self.wallet.dumps(), indent=4, ensure_ascii=False))

        self.clean_derivation()

        return address, priv_key, pub_key


class ETH(BTC):
    coin = EthereumMainnet


class TRX(BTC):
    coin = TronMainnet


class BNB(BTC):
    coin = EthereumMainnet


class MATIC(BTC):
    coin = EthereumMainnet


class WORLD(BTC):
    coin = EthereumMainnet


class OPTIMISM(BTC):
    coin = EthereumMainnet


class LTC(BTC):
    coin = LitecoinTestnet


class BCH(BTC):
    coin = BitcoinCashMainnet


class GRS(BTC):
    coin = GroestlCoinMainnet


def wallets():
    return {
        "BTC": BTC,
        "ETH": ETH,
        "TRX": TRX,
        "BNB": BNB,
        "MATIC": MATIC,
        "WORLD": WORLD,
        "OPTIMISM": OPTIMISM,
        "LTC": LTC,
        "BCH": BCH,
        "GRS": GRS
    }


def get_wallet(wallet):
    match wallet:
        case "TRX":
            return TRX
        case "BTC":
            return BTC
        case "BCH":
            return BCH
        case "ETH":
            return ETH
        case "BNB":
            return BNB
        case "MATIC":
            return MATIC
        case "WORLD":
            return WORLD
        case "OPTIMISM":
            return OPTIMISM
        case "GRS":
            return GRS
        case "LTC":
            return LTC
