import base64
import hashlib
import hmac
import json
import time
import urllib.parse
from os.path import exists
from shutil import copyfile

import requests


def create_user_json():
    """
        Check if the user.json exists. If not, copy the base.json as the initial user.json

        No Return
    """
    if exists(GLOBAL_USER_JSON_PATH) == False:
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


def get_account_balance():
    """
        Get asset balance of the account.

        Returns the asset balance of the account in json. (E.g. asset name, asset qunantity, etc.)
    """
    resp = kraken_request('/0/private/Balance', {"nonce": get_nonce()})
    return resp.json()


def get_asset_info(assets=[]):
    """
        Get the list of information of given pairs. Get all possible pairs if not specified.

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


def main():
    get_user_json()
    get_account_balance()
    get_asset_info(['XBT', 'ETH'])
    print(get_pairs()['result']['XXBTZUSD'])
    print(get_order_book('XBTUSD'))


if __name__ == "__main__":
    # All asset codes https://support.kraken.com/hc/en-us/articles/360001185506-How-to-interpret-asset-codes

    GLOBAL_BASE_JSON_PATH = 'usr/base.json'
    GLOBAL_USER_JSON_PATH = 'usr/user.json'
    GLOBAL_API_URI = "https://api.kraken.com"
    GLOBAL_API_KEY, GLOBAL_SECRET_KEY = get_user_json()

    main()
