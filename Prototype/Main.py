import base64
import hashlib
import hmac
import json
import time
import urllib.parse
from os.path import exists
from shutil import copyfile

import requests

# All asset codes https://support.kraken.com/hc/en-us/articles/360001185506-How-to-interpret-asset-codes

GLOBAL_BASE_JSON_PATH = 'usr/base.json'
GLOBAL_USER_JSON_PATH = 'usr/user.json'
GLOBAL_API_URI = "https://api.kraken.com"
GLOBAL_API_KEY = "DO NOT PUT YOUR API KEY HERE!"
GLOBAL_SECRET_KEY = "DO NOT PUT YOUR API KEY HERE!"


def create_user_json():
    if exists(GLOBAL_USER_JSON_PATH) == False:
        copyfile(GLOBAL_BASE_JSON_PATH, GLOBAL_USER_JSON_PATH)


def get_user_json():
    global GLOBAL_API_KEY, GLOBAL_SECRET_KEY
    create_user_json()
    user_json = json.load(open(GLOBAL_USER_JSON_PATH))
    GLOBAL_API_KEY = user_json['api_key']
    GLOBAL_SECRET_KEY = user_json['secret_key']


def get_kraken_signature(urlpath, data, secret):
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()


def kraken_request(uri_path, data, api_key, api_sec):
    headers = {}
    headers['API-Key'] = GLOBAL_API_KEY
    # get_kraken_signature() as defined in the 'Authentication' section
    headers['API-Sign'] = get_kraken_signature(
        uri_path, data, GLOBAL_SECRET_KEY)
    req = requests.post((GLOBAL_API_URI + uri_path),
                        headers=headers, data=data)
    return req


def get_account_balance():
    resp = kraken_request(
        '/0/private/Balance', {"nonce": str(int(1000*time.time()))}, GLOBAL_API_KEY, GLOBAL_SECRET_KEY)
    return resp.json()


def get_asset_info(assets=[]):
    req_uri = GLOBAL_API_URI + '/0/public/Assets'
    if len(assets) > 0:
        req_uri += '?asset='
        for asset in assets:
            req_uri += asset + ','
        req_uri = req_uri[:-1]
    resp = requests.get(req_uri)
    return resp.json()


def get_pairs(pairs=[]):
    req_uri = GLOBAL_API_URI + '/0/public/AssetPairs'
    if len(pairs) > 0:
        req_uri += '?pair='
        for pair in pairs:
            req_uri += pair + ','
        req_uri = req_uri[:-1]
    resp = requests.get(req_uri)
    test = resp.json()
    return resp.json()

def main():
    get_user_json()
    get_account_balance()
    get_asset_info(['XBT', 'ETH'])
    print(get_pairs()['result']['XXBTZUSD'])


if __name__ == "__main__":
    main()
