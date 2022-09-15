import base64
import hashlib
import hmac
import json
import time
import requests
import urllib.parse
import os
from shutil import copyfile
from decimal import Decimal
from datetime import datetime


def create_user_json():
    """
        Check if the user.json exists. If not, copy the base.json as the initial user.json

        No Return
    """
    if os.path.exists(GLOBAL_USER_JSON_PATH) == False:
        copyfile(GLOBAL_BASE_JSON_PATH, GLOBAL_USER_JSON_PATH)


def get_user_json():
    """
        Get the user info from the user.json.

        Returns the user info. (E.g. api key, secret key, etc.)
    """
    create_user_json()

    user_json = json.load(open(GLOBAL_USER_JSON_PATH))
    return user_json['api_key'], user_json['secret_key']


def get_kraken_signature(urlpath, data):
    """
        Get the encoded payload with signature.

        Parameter uri_path: uri path of the api.
        Precondition: uri_path is a string uri.

        Parameter data: Payload data ready to encode.
        Precondition: data is payload datas in string.

        Returns the encoded payload with signature.
    """
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(GLOBAL_SECRET_KEY),
                   message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()


def kraken_request(uri_path, data):
    """
        Send private requests and get the response. 
        Require two parts: the api path and the payload data. 
        Data needs to be encoded. 

        Parameter uri_path: uri path of the api.
        Precondition: uri_path is a string uri.

        Parameter data: Payload data ready to encode.
        Precondition: data is payload datas in string.

        Returns the request result.
    """
    headers = {}
    headers['API-Key'] = GLOBAL_API_KEY

    headers['API-Sign'] = get_kraken_signature(uri_path, data)
    req = requests.post((GLOBAL_API_URI + uri_path),
                        headers=headers, data=data)
    return req


def get_nonce():
    """
        Get nonce for signature verification.
        Nonce is the Post Date in string.

        Returns the string nonce.
    """
    return str(int(1000*time.time()))


def get_account_assets():
    """
        Get asset balance of the account.

        Returns the asset balance of the account in json. (E.g. asset name, asset qunantity, etc.)
    """
    resp = kraken_request('/0/private/Balance', {"nonce": get_nonce()})
    return resp.json()


def get_asset_info(assets=[]):
    """
        Get the list of information of given assets. Get all possible assets if not specified.

        Parameter assets: List of asset name of the target assets.
        Precondition: assets is a list of string asset names.

        Returns the basic asset informations in json. (E.g. asset name, asset type, etc.)
    """
    req_uri = GLOBAL_API_URI + '/0/public/Assets'
    if len(assets) > 0:
        req_uri += '?asset='
        for asset in assets:
            req_uri += asset + ','
        req_uri = req_uri[:-1]
    resp = requests.get(req_uri)
    return resp.json()


def get_pairs(pairs=[]):
    """
        Get the list of information of given pairs. Get all possible pairs if not specified.

        Parameter pairs: List of pair name of the target pairs.
        Precondition: pairs is a list of string pair names.

        Returns the basic pair informations in json. (E.g. pair name, pair unit, pair base and quote, etc.)
    """
    req_uri = GLOBAL_API_URI + '/0/public/AssetPairs'
    if len(pairs) > 0:
        req_uri += '?pair='
        for pair in pairs:
            req_uri += pair + ','
        req_uri = req_uri[:-1]
    resp = requests.get(req_uri)
    return resp.json()


def get_order_book(pair):
    """
        Get the list of orders in the order book.

        Parameter pair: Pair name of the target pair.
        Precondition: pair is a string.

        Returns the asks and bids orders of the pair in json. (E.g. order price, order depth, etc.)
    """
    resp = requests.get(GLOBAL_API_URI + '/0/public/Depth?pair=' + pair)
    return resp.json()


def get_account_balance():
    """
        Get the asset information in account.
        Base on the json from API, calculate the actual value and percent of each assets in USD.

        Returns the account balance in dictionary with the amount, value and percent of each assets in decimal.
    """
    balance = get_account_assets()['result']
    account_balance = 0
    for asset in balance:
        if asset != 'ZUSD':
            order_book = get_order_book(asset + 'ZUSD')['result']
            asset_price = Decimal(order_book[asset + 'ZUSD']['asks'][0][0])
            balance[asset] = {'amount': Decimal(balance[asset]),
                              'value': Decimal(balance[asset]) * asset_price,
                              'price': asset_price}
            account_balance += balance[asset]['value']
        else:
            balance[asset] = {'amount': Decimal(balance[asset]),
                              'value': Decimal(balance[asset]),
                              'price': 1}
            account_balance += balance[asset]['value']
    for asset in balance:
        balance[asset]['percent'] = balance[asset]['value'] / account_balance
    return balance


def add_order(ordertype, type, volume, pair, price=-1):
    data = {"nonce": get_nonce(), "ordertype": ordertype, "type": type,
            "volume": volume, "pair": pair}

    log_string = "Placing {} {} {} order for {}".format(
        volume, ordertype, type, pair)

    if ordertype in ['limit', 'stop-loss', 'stop-loss-limit', 'take-profit', 'take-profit-limit']:
        data["price"] = price
        log_string += " at {}".format(price)

    write_log(log_string)
    resp = kraken_request('/0/private/AddOrder', data)
    return resp.json()


def balance_assets(balance, percent_per_asset):
    orders = []
    for asset in balance:
        if asset != 'ZUSD':
            volume = balance[asset]['amount'] * \
                abs((percent_per_asset[asset] / balance[asset]['percent']) - 1)

            if (percent_per_asset[asset] + Decimal(0.03) < balance[asset]['percent']):
                type = 'sell'
            elif (percent_per_asset[asset] > balance[asset]['percent'] + Decimal(0.03)):
                type = 'buy'
            else:
                continue

            orders.append({'ordertype': 'market', 'type': type,
                          'volume': volume, 'pair': asset + 'ZUSD'})

    for order in orders:
        add_order(order['ordertype'], order['type'],
                  order['volume'], order['pair'])


def get_fear_greed_json():
    req_uri = GLOBAL_FNG_URI
    resp = requests.get(req_uri)
    return resp.json()


def get_fear_greed_index(fng_json):
    return Decimal(1) - ((Decimal(fng_json['data'][0]['value']) - Decimal(GLOBAL_FNG_DEADZONE)) / Decimal(100 - (2 * GLOBAL_FNG_DEADZONE)))


def get_fng_sleep_span(fng_json):
    until_update = int(fng_json['data'][0]
                       ['time_until_update']) + GLOBAL_SLEEP_MIN
    return until_update


def get_target_percent(balance, fng_json):
    percent = get_fear_greed_index(fng_json)
    total_assets_count = sum(map(lambda k: k != 'ZUSD', balance.keys()))
    ret = {}
    for asset in balance:
        if asset != 'ZUSD':
            ret[asset] = percent / total_assets_count
    return ret


def write_log(log_string):
    split_path = os.path.split(GLOBAL_LOG_FILE_PATH)
    if os.path.exists(split_path[0]) == False:
        os.makedirs(split_path[0])

    dt_string = "[{}] ".format(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    with open(GLOBAL_LOG_FILE_PATH, 'a') as f:
        f.write(dt_string + log_string + '\n')

    print(dt_string + log_string)


def main():
    while True:
        balance = get_account_balance()
        fng_json = get_fear_greed_json()
        percent_per_asset = get_target_percent(balance, fng_json)
        balance_assets(balance, percent_per_asset)

        sec_to_sleep = get_fng_sleep_span(fng_json)
        write_log("Sleeping for {}s".format(sec_to_sleep))
        time.sleep(sec_to_sleep)


if __name__ == "__main__":
    # All asset codes https://support.kraken.com/hc/en-us/articles/360001185506-How-to-interpret-asset-codes

    GLOBAL_BASE_JSON_PATH = 'usr/base.json'
    GLOBAL_USER_JSON_PATH = 'usr/user.json'
    GLOBAL_LOG_FILE_PATH = 'log/log.txt'
    GLOBAL_API_URI = "https://api.kraken.com"
    GLOBAL_FNG_URI = "https://api.alternative.me/fng/"  # Fear and Greed Index api uri
    GLOBAL_API_KEY, GLOBAL_SECRET_KEY = get_user_json()
    GLOBAL_FNG_DEADZONE = 10
    GLOBAL_SLEEP_MIN = 300  # 300 sec, 5 min
    GLOBAL_SLEEP_MAX = 47800  # 47800 sec, 13hr

    main()
