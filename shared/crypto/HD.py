import os
import hashlib
from hashlib import sha256
from ecdsa import SECP256k1
from eth_utils import keccak
from hdwallet import HDWallet
from hdwallet.hds import BIP32HD
from hdwallet.mnemonics import BIP39Mnemonic, BIP39_MNEMONIC_LANGUAGES
from hdwallet.cryptocurrencies import (
    Bitcoin, Ethereum, Tron, BitcoinCash, GroestlCoin, Litecoin, Ripple, 
    Binance, Polygon, Optimism, Solana
)
from hdwallet.derivations import BIP44Derivation, CustomDerivation
from hdwallet.entropies import BIP39Entropy, BIP39_ENTROPY_STRENGTHS
from hdwallet.seeds import BIP39Seed
from hdwallet.consts import PUBLIC_KEY_TYPES
from typing import Optional

SECP256k1_GEN = SECP256k1.generator
SECP256k1_ORD = SECP256k1.order


class HD():
    def __init__(self, entropy_bit_size: int = 128):
        self.entropy_bit_size = entropy_bit_size
        self.dirname = os.path.dirname(__file__)

    def mnemonic(self, language: str = "english"):
        entropy = BIP39Entropy.generate(strength=BIP39_ENTROPY_STRENGTHS.ONE_HUNDRED_TWENTY_EIGHT)
        mnemonic_obj = BIP39Mnemonic.from_entropy(entropy=entropy, language=language)
        return str(mnemonic_obj)

    def make_seed(self, mnemonic: str, passphrase: str = ""):
        salt = "mnemonic" + passphrase
        seed = hashlib.pbkdf2_hmac(
            "sha512",
            mnemonic.encode("utf-8"),
            salt.encode("utf-8"),
            2048
        )
        return seed.hex()


class BTC(HD):
    def __init__(self, testnet: bool = True):
        self.cryptocurrency = Bitcoin
        self.network = Bitcoin.NETWORKS.TESTNET if testnet else Bitcoin.NETWORKS.MAINNET
        self.wallet: HDWallet = None
        super().__init__()

    def from_mnemonic(self, mnemonic: str, language: Optional[str] = "english", passphrase: Optional[str] = None):
        # Create entropy directly using the working pattern
        entropy = BIP39Entropy(
            entropy=BIP39Entropy.generate(
                strength=BIP39_ENTROPY_STRENGTHS.ONE_HUNDRED_TWENTY_EIGHT
            )
        )
        
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            language=language or "english",
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED,
            passphrase=passphrase or ""
        ).from_entropy(entropy=entropy)
        return self

    def from_seed(self, seed: str):
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED
        ).from_seed(seed=seed)
        return self

    def clean_derivation(self):
        if self.wallet:
            self.wallet.clean_derivation()
        return self

    def new_address(self, change: Optional[bool] = False, index: Optional[int] = 0, account: Optional[int] = 0):
        if not self.wallet:
            raise ValueError("Wallet not initialized. Call from_mnemonic() or from_seed() first.")
            
        self.clean_derivation()
        # Use CustomDerivation with BIP44 path format
        change_val = 1 if change else 0
        path = f"m/44'/{self.cryptocurrency.COIN_TYPE}'/{account}'/{change_val}/{index}"
        derivation = CustomDerivation(path=path)
        self.wallet.from_derivation(derivation=derivation)

        address = self.wallet.address()
        priv_key = self.wallet.private_key()
        pub_key = self.wallet.public_key()

        self.clean_derivation()

        return address, priv_key, pub_key


class EVMBase(HD):
    """Base class for EVM-compatible chains that generate identical addresses for testnet/mainnet"""
    
    def __init__(self, cryptocurrency, testnet: bool = False):
        self.cryptocurrency = cryptocurrency
        # EVM chains generate same addresses for testnet/mainnet, always use MAINNET
        self.network = cryptocurrency.NETWORKS.MAINNET
        self.wallet: HDWallet = None
        super().__init__()

    def from_mnemonic(self, mnemonic: str, language: Optional[str] = "english", passphrase: Optional[str] = None):
        # Create BIP39Mnemonic object for deterministic wallet generation
        mnemonic_obj = BIP39Mnemonic(mnemonic=mnemonic)
        
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            language=language or "english",
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED,
            passphrase=passphrase or ""
        ).from_mnemonic(mnemonic=mnemonic_obj)
        return self

    def from_seed(self, seed: str):
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED
        ).from_seed(seed=seed)
        return self

    def clean_derivation(self):
        if self.wallet:
            self.wallet.clean_derivation()
        return self

    def new_address(self, change: Optional[bool] = False, index: Optional[int] = 0, account: Optional[int] = 0):
        if not self.wallet:
            raise ValueError("Wallet not initialized. Call from_mnemonic() or from_seed() first.")
            
        self.clean_derivation()
        # Use CustomDerivation with BIP44 path format
        change_val = 1 if change else 0
        path = f"m/44'/{self.cryptocurrency.COIN_TYPE}'/{account}'/{change_val}/{index}"
        derivation = CustomDerivation(path=path)
        self.wallet.from_derivation(derivation=derivation)

        address = self.wallet.address()
        priv_key = self.wallet.private_key()
        pub_key = self.wallet.public_key()

        self.clean_derivation()

        # Normalize EVM addresses to lowercase for consistent database storage
        address = address.lower()

        return address, priv_key, pub_key


class ETH(EVMBase):
    def __init__(self, testnet: bool = False):
        super().__init__(Ethereum, testnet)


class TRX(HD):
    def __init__(self, testnet: bool = False):
        self.cryptocurrency = Tron
        # Tron only has MAINNET in hdwallet 3.6.1
        self.network = Tron.NETWORKS.MAINNET
        self.wallet: HDWallet = None
        super().__init__()

    def from_mnemonic(self, mnemonic: str, language: Optional[str] = "english", passphrase: Optional[str] = None):
        # Create entropy directly using the working pattern
        entropy = BIP39Entropy(
            entropy=BIP39Entropy.generate(
                strength=BIP39_ENTROPY_STRENGTHS.ONE_HUNDRED_TWENTY_EIGHT
            )
        )
        
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            language=language or "english",
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED,
            passphrase=passphrase or ""
        ).from_entropy(entropy=entropy)
        return self

    def from_seed(self, seed: str):
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED
        ).from_seed(seed=seed)
        return self

    def clean_derivation(self):
        if self.wallet:
            self.wallet.clean_derivation()
        return self

    def new_address(self, change: Optional[bool] = False, index: Optional[int] = 0, account: Optional[int] = 0):
        if not self.wallet:
            raise ValueError("Wallet not initialized. Call from_mnemonic() or from_seed() first.")
            
        self.clean_derivation()
        # Use CustomDerivation with BIP44 path format
        change_val = 1 if change else 0
        path = f"m/44'/{self.cryptocurrency.COIN_TYPE}'/{account}'/{change_val}/{index}"
        derivation = CustomDerivation(path=path)
        self.wallet.from_derivation(derivation=derivation)

        address = self.wallet.address()
        priv_key = self.wallet.private_key()
        pub_key = self.wallet.public_key()

        self.clean_derivation()

        return address, priv_key, pub_key


# EVM-based cryptocurrencies (BNB, MATIC, WORLD, OPTIMISM) use Ethereum structure
class BNB(EVMBase):
    def __init__(self, testnet: bool = False):
        super().__init__(Binance, testnet)
    
    def new_address(self, change: Optional[bool] = False, index: Optional[int] = 0, account: Optional[int] = 0):
        if not self.wallet:
            raise ValueError("Wallet not initialized. Call from_mnemonic() or from_seed() first.")
            
        self.clean_derivation()
        # Use CustomDerivation with BIP44 path format
        change_val = 1 if change else 0
        path = f"m/44'/{self.cryptocurrency.COIN_TYPE}'/{account}'/{change_val}/{index}"
        derivation = CustomDerivation(path=path)
        self.wallet.from_derivation(derivation=derivation)

        # Get the private key to derive hex address
        priv_key = self.wallet.private_key()
        pub_key = self.wallet.public_key()
        
        # Convert BNB address from bech32 to hex format
        from ecdsa import SigningKey, SECP256k1
        
        # Create signing key from private key and derive hex address
        sk = SigningKey.from_string(bytes.fromhex(priv_key), curve=SECP256k1)
        vk = sk.get_verifying_key()
        
        # Get uncompressed public key
        uncompressed_key = b'\x04' + vk.to_string()
        
        # Convert to Ethereum-style hex address
        pk_bytes = uncompressed_key[1:]  # Remove '04' prefix
        address_bytes = keccak(pk_bytes)[-20:]  # Last 20 bytes of keccak hash
        address = '0x' + address_bytes.hex().lower()

        self.clean_derivation()

        return address, priv_key, pub_key


class MATIC(EVMBase):
    def __init__(self, testnet: bool = False):
        super().__init__(Polygon, testnet)


class WORLD(EVMBase):
    def __init__(self, testnet: bool = False):
        # World Chain uses Ethereum as base
        super().__init__(Ethereum, testnet)


class OPTIMISM(EVMBase):
    def __init__(self, testnet: bool = False):
        super().__init__(Optimism, testnet)

class SOL(HD):
    def __init__(self, testnet: bool = False):
        self.cryptocurrency = Solana
        # Solana only has MAINNET in hdwallet 3.6.1
        self.network = Solana.NETWORKS.MAINNET
        self.wallet: HDWallet = None
        super().__init__()

    def from_mnemonic(self, mnemonic: str, language: Optional[str] = "english", passphrase: Optional[str] = None):
        # Create entropy directly using the working pattern
        entropy = BIP39Entropy(
            entropy=BIP39Entropy.generate(
                strength=BIP39_ENTROPY_STRENGTHS.ONE_HUNDRED_TWENTY_EIGHT
            )
        )
        
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            language=language or "english",
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED,
            passphrase=passphrase or ""
        ).from_entropy(entropy=entropy)
        return self

    def from_seed(self, seed: str):
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED
        ).from_seed(seed=seed)
        return self

    def clean_derivation(self):
        if self.wallet:
            self.wallet.clean_derivation()
        return self

    def new_address(self, change: Optional[bool] = False, index: Optional[int] = 0, account: Optional[int] = 0):
        if not self.wallet:
            raise ValueError("Wallet not initialized. Call from_mnemonic() or from_seed() first.")
            
        self.clean_derivation()
        # Use CustomDerivation with BIP44 path format
        change_val = 1 if change else 0
        path = f"m/44'/{self.cryptocurrency.COIN_TYPE}'/{account}'/{change_val}/{index}"
        derivation = CustomDerivation(path=path)
        self.wallet.from_derivation(derivation=derivation)

        address = self.wallet.address()
        priv_key = self.wallet.private_key()
        pub_key = self.wallet.public_key()

        self.clean_derivation()

        return address, priv_key, pub_key

class XRP(HD):
    def __init__(self, testnet: bool = False):
        self.cryptocurrency = Ripple
        # Ripple only has MAINNET in hdwallet 3.6.1
        self.network = Ripple.NETWORKS.MAINNET
        self.wallet: HDWallet = None
        super().__init__()

    def from_mnemonic(self, mnemonic: str, language: Optional[str] = "english", passphrase: Optional[str] = None):
        # Create entropy directly using the working pattern
        entropy = BIP39Entropy(
            entropy=BIP39Entropy.generate(
                strength=BIP39_ENTROPY_STRENGTHS.ONE_HUNDRED_TWENTY_EIGHT
            )
        )
        
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            language=language or "english",
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED,
            passphrase=passphrase or ""
        ).from_entropy(entropy=entropy)
        return self

    def from_seed(self, seed: str):
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED
        ).from_seed(seed=seed)
        return self

    def clean_derivation(self):
        if self.wallet:
            self.wallet.clean_derivation()
        return self

    def new_address(self, change: Optional[bool] = False, index: Optional[int] = 0, account: Optional[int] = 0):
        if not self.wallet:
            raise ValueError("Wallet not initialized. Call from_mnemonic() or from_seed() first.")
            
        self.clean_derivation()
        # Use CustomDerivation with BIP44 path format
        change_val = 1 if change else 0
        path = f"m/44'/{self.cryptocurrency.COIN_TYPE}'/{account}'/{change_val}/{index}"
        derivation = CustomDerivation(path=path)
        self.wallet.from_derivation(derivation=derivation)

        address = self.wallet.address()
        priv_key = self.wallet.private_key()
        pub_key = self.wallet.public_key()

        self.clean_derivation()

        return address, priv_key, pub_key


class LTC(HD):
    def __init__(self, testnet: bool = True):
        self.cryptocurrency = Litecoin
        self.network = Litecoin.NETWORKS.TESTNET if testnet else Litecoin.NETWORKS.MAINNET
        self.wallet: HDWallet = None
        super().__init__()

    def from_mnemonic(self, mnemonic: str, language: Optional[str] = "english", passphrase: Optional[str] = None):
        # Create entropy directly using the working pattern
        entropy = BIP39Entropy(
            entropy=BIP39Entropy.generate(
                strength=BIP39_ENTROPY_STRENGTHS.ONE_HUNDRED_TWENTY_EIGHT
            )
        )
        
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            language=language or "english",
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED,
            passphrase=passphrase or ""
        ).from_entropy(entropy=entropy)
        return self

    def from_seed(self, seed: str):
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED
        ).from_seed(seed=seed)
        return self

    def clean_derivation(self):
        if self.wallet:
            self.wallet.clean_derivation()
        return self

    def new_address(self, change: Optional[bool] = False, index: Optional[int] = 0, account: Optional[int] = 0):
        if not self.wallet:
            raise ValueError("Wallet not initialized. Call from_mnemonic() or from_seed() first.")
            
        self.clean_derivation()
        # Use CustomDerivation with BIP44 path format
        change_val = 1 if change else 0
        path = f"m/44'/{self.cryptocurrency.COIN_TYPE}'/{account}'/{change_val}/{index}"
        derivation = CustomDerivation(path=path)
        self.wallet.from_derivation(derivation=derivation)

        address = self.wallet.address()
        priv_key = self.wallet.private_key()
        pub_key = self.wallet.public_key()

        self.clean_derivation()

        return address, priv_key, pub_key


class BCH(HD):
    def __init__(self, testnet: bool = False):
        self.cryptocurrency = BitcoinCash
        self.network = BitcoinCash.NETWORKS.TESTNET if testnet else BitcoinCash.NETWORKS.MAINNET
        self.wallet: HDWallet = None
        super().__init__()

    def from_mnemonic(self, mnemonic: str, language: Optional[str] = "english", passphrase: Optional[str] = None):
        # Create entropy directly using the working pattern
        entropy = BIP39Entropy(
            entropy=BIP39Entropy.generate(
                strength=BIP39_ENTROPY_STRENGTHS.ONE_HUNDRED_TWENTY_EIGHT
            )
        )
        
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            language=language or "english",
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED,
            passphrase=passphrase or ""
        ).from_entropy(entropy=entropy)
        return self

    def from_seed(self, seed: str):
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED
        ).from_seed(seed=seed)
        return self

    def clean_derivation(self):
        if self.wallet:
            self.wallet.clean_derivation()
        return self

    def new_address(self, change: Optional[bool] = False, index: Optional[int] = 0, account: Optional[int] = 0):
        if not self.wallet:
            raise ValueError("Wallet not initialized. Call from_mnemonic() or from_seed() first.")
            
        self.clean_derivation()
        # Use CustomDerivation with BIP44 path format
        change_val = 1 if change else 0
        path = f"m/44'/{self.cryptocurrency.COIN_TYPE}'/{account}'/{change_val}/{index}"
        derivation = CustomDerivation(path=path)
        self.wallet.from_derivation(derivation=derivation)

        address = self.wallet.address()
        priv_key = self.wallet.private_key()
        pub_key = self.wallet.public_key()

        self.clean_derivation()

        return address, priv_key, pub_key


class GRS(HD):
    def __init__(self, testnet: bool = False):
        self.cryptocurrency = GroestlCoin
        self.network = GroestlCoin.NETWORKS.TESTNET if testnet else GroestlCoin.NETWORKS.MAINNET
        self.wallet: HDWallet = None
        super().__init__()

    def from_mnemonic(self, mnemonic: str, language: Optional[str] = "english", passphrase: Optional[str] = None):
        # Create entropy directly using the working pattern
        entropy = BIP39Entropy(
            entropy=BIP39Entropy.generate(
                strength=BIP39_ENTROPY_STRENGTHS.ONE_HUNDRED_TWENTY_EIGHT
            )
        )
        
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            language=language or "english",
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED,
            passphrase=passphrase or ""
        ).from_entropy(entropy=entropy)
        return self

    def from_seed(self, seed: str):
        self.wallet = HDWallet(
            cryptocurrency=self.cryptocurrency,
            hd=BIP32HD,
            network=self.network,
            public_key_type=PUBLIC_KEY_TYPES.COMPRESSED
        ).from_seed(seed=seed)
        return self

    def clean_derivation(self):
        if self.wallet:
            self.wallet.clean_derivation()
        return self

    def new_address(self, change: Optional[bool] = False, index: Optional[int] = 0, account: Optional[int] = 0):
        if not self.wallet:
            raise ValueError("Wallet not initialized. Call from_mnemonic() or from_seed() first.")
            
        self.clean_derivation()
        # Use CustomDerivation with BIP44 path format
        change_val = 1 if change else 0
        path = f"m/44'/{self.cryptocurrency.COIN_TYPE}'/{account}'/{change_val}/{index}"
        derivation = CustomDerivation(path=path)
        self.wallet.from_derivation(derivation=derivation)

        address = self.wallet.address()
        priv_key = self.wallet.private_key()
        pub_key = self.wallet.public_key()

        self.clean_derivation()

        return address, priv_key, pub_key


def wallets():
    return {
        "BTC": BTC,
        "ETH": ETH,
        "TRX": TRX,
        "BNB": BNB,
        "MATIC": MATIC,
        "WORLD": WORLD,
        "OPTIMISM": OPTIMISM,
        "XRP": XRP,
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
        case "XRP":
            return XRP
        case "GRS":
            return GRS
        case "LTC":
            return LTC
