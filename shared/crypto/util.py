import asyncio
from decimal import Decimal
from http.client import HTTPException
from decouple import config
from bitcart import COINS as cns
from bitcart import APIManager, TRX
from shared.crypto.constants import MAX_CONTRACT_DIVISIBILITY
from ..moneyformat import currency_table

SEND_ALL = Decimal("-1")


def coin_info(coin: str):
    if coin in cns:
        coin_obj = cns[coin.upper()]
    else:
        return None
    if (coin_obj):
        default_url = coin_obj.RPC_URL
        default_user = coin_obj.RPC_USER
        default_password = coin_obj.RPC_PASS
        _, default_host, default_port = default_url.split(":")
        default_host = default_host[2:]
        default_port = int(default_port)
        rpc_host = config(f"{coin.upper()}_HOST", default_host)
        rpc_port = config(f"{coin.upper()}_PORT", default_port)
        rpc_url = f"http://{rpc_host}:{rpc_port}"
        rpc_user = config(f"{coin.upper()}_USER", default_user)
        rpc_password = config(
            f"{coin.upper()}_PASSWORD", default_password)
        crypto_network = config(f"{coin.upper()}_NETWORK", "testnet")
        crypto_lightning = config(
            f"{coin.upper()}_LIGHTNING", "False")

        crypto_lightning = False if crypto_lightning == "False" else crypto_lightning

        info = {
            "credentials": {"rpc_url": rpc_url, "rpc_user": rpc_user, "rpc_pass": rpc_password},
            "network": crypto_network,
            "lightning": crypto_lightning,
        }

        print(f"[COIN_INFO] {coin}: default_url={default_url}, default_host={default_host}, default_port={default_port}")
        print(f"[COIN_INFO] {coin}: rpc_host={rpc_host}, rpc_port={rpc_port}, rpc_url={rpc_url}")

        return info


async def prepare_tx(coin, wallet, destination, amount, divisibility, fee=None):
    contract = wallet.get('contract') or None
    if not coin.is_eth_based:
        if amount == SEND_ALL:
            amount = "!"
        raw_tx = coin.pay_to(destination, amount, broadcast=False)
    else:
        if contract:
            if amount == SEND_ALL:
                address = await coin.server.getaddress()
                amount = Decimal(coin.server.readcontract(contract, "balanceOf", address)) / Decimal(
                    10**divisibility
                )
            raw_tx = await coin.server.transfer(contract, destination, amount, unsigned=True)
        else:
            if amount == SEND_ALL:
                amount = Decimal((await coin.balance())["confirmed"])
                estimated_fee = Decimal(
                    await coin.server.get_default_fee(await coin.server.payto(destination, amount, unsigned=True))
                )
                amount -= estimated_fee
            raw_tx = await coin.server.payto(destination, amount, unsigned=True)
    return raw_tx


async def broadcast_tx_flow(coin, wallet, raw_tx, max_fee, divisibility, rate):
    try:
        predicted_fee = Decimal(await coin.server.get_default_fee(raw_tx))
        if max_fee is not None:
            max_fee_amount = currency_table.normalize(
                wallet.currency, max_fee / rate, divisibility=divisibility)
            if predicted_fee > max_fee_amount:
                return
        if coin.is_eth_based:
            raw_tx = await coin.server.signtransaction(raw_tx)
        else:
            await coin.server.addtransaction(raw_tx)
        tx_hash = await coin.server.broadcast(raw_tx)
        return tx_hash, predicted_fee
    finally:
        await coin.server.close_wallet()


def broadcast_tx_flow_sync(coin, wallet, raw_tx, max_fee, divisibility, rate):
    async def wrapper():
        return await broadcast_tx_flow(coin, wallet, raw_tx, max_fee, divisibility, rate)
    return asyncio.run(wrapper())


def get_coin(coin, xpub=None):
    coin = coin.upper()
    cryptos = ["BTC"]
    crypto_settings = {}
    nodes = {}
    for crypto in cryptos:
        crypto_settings[crypto] = coin_info(crypto)
        env_name = crypto.upper()
        cn = cns[env_name]
        nodes[crypto] = cn(**crypto_settings[crypto]["credentials"])
    if coin not in nodes:
        raise HTTPException(422, f"Unsupported currency: {coin}")
    if not xpub:
        return nodes[coin]
    obj = None
    if coin.upper() in cns:
        obj = cns[coin.upper()](
            xpub=xpub, **crypto_settings[coin]["credentials"])
    return obj


async def get_divisibility(wallet, coin):
    currency = wallet.get("currency") or None
    contract = wallet.get("contract") or None

    divisibility = currency_table.get_currency_data(currency)["divisibility"]
    if contract:  # pragma: no cover
        divis = await coin.server.readcontract(contract, "decimals")
        divisibility = min(MAX_CONTRACT_DIVISIBILITY, divis)
    return divisibility
