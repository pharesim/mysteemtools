# Config
witness = ""    # Your witness name
wif = ""
minchange = 0.02 # Minimum change of price to trigger an update
minchange_bias = 0.01 # Minimum change of bias to trigger an update
numberoftrades = 25 # Number of trades to analyse
offset = 0 # Percentage to modify the price with

rpcnode = 'wss://steemd.steemit.com'


from piston import Steem
from pistonbase import transactions
from piston.transactionbuilder import TransactionBuilder
from pistonapi.steemnoderpc import SteemNodeRPC
from piston.witness import Witness

import json
import time
import dateutil.parser
import requests


def btc_usd():
  prices = {}
  exchanges = {
    'bitfinex': {
      'url': 'https://api.bitfinex.com/v1/pubticker/BTCUSD',
      'price': 'last_price',
      'volume': 'volume'
    },
    'coinbase': {
      'url': 'https://api.exchange.coinbase.com/products/BTC-USD/ticker',
      'price': 'price',
      'volume': 'volume'
    },
    'okcoin': {
      'url': 'https://www.okcoin.com/api/v1/ticker.do?symbol=btc_usd',
      'price': 'last',
      'volume': 'vol'
    },
    'bitstamp': {
      'url': 'https://www.bitstamp.net/api/v2/ticker/btcusd/',
      'price': 'price',
      'volume': 'volume'
    }
  }
  for key, value in exchanges.items():
    try:
      r = json.loads(requests.request("GET",value['url']).text)
      prices[key] = {'price': float(r[value['price']]), 'volume': float(r[value['volume']])};
    except:
      pass

  if not prices:
    raise Exception("All BTC price feeds failed.")
  avg_price    = 0
  total_volume = 0
  for p in prices.values():
    avg_price    += p['price'] * p['volume']
    total_volume += p['volume']
  avg_price = avg_price / total_volume
  return avg_price


def proceed(op):
  rpc = SteemNodeRPC(rpcnode)
  expiration = transactions.formatTimeFromNow(60)
  ops    = [transactions.Operation(op)]
  ref_block_num, ref_block_prefix = transactions.getBlockParams(rpc)
  tx     = transactions.Signed_Transaction(ref_block_num=ref_block_num,
                                         ref_block_prefix=ref_block_prefix,
                                         expiration=expiration,
                                         operations=ops)
  tx = tx.sign([wif])

  # Broadcast JSON to network
  rpc.broadcast_transaction(tx.json(), api="network_broadcast")


def publish_feed(base,quote):
  op = transactions.Feed_publish(
    **{"publisher": witness,
       "exchange_rate": {"base": base+" SBD", "quote": quote+" STEEM"}}
  )

  proceed(op)



if __name__ == '__main__':
  quantities = {'steem':0,'steembtc':0,'sbd':0,'sbdbtc':0}
  try:
    hist = json.loads(requests.request("GET","https://bittrex.com/api/v1.1/public/getmarkethistory?market=BTC-STEEM").text)
    for i in range(numberoftrades):
      quantities['steem'] += hist["result"][i]["Quantity"]
      quantities['steembtc'] += hist["result"][i]["Total"]
  except:
    a = 1

  try:
    hist = json.loads(requests.request("GET","https://poloniex.com/public?command=returnTradeHistory&currencyPair=BTC_STEEM").text)
    for i in range(numberoftrades):
      quantities['steem'] += float(hist[i]['amount'])
      quantities['steembtc'] += float(hist[i]['total'])
  except:
    a = 1

  try:
    hist = json.loads(requests.request("GET","https://bittrex.com/api/v1.1/public/getmarkethistory?market=BTC-SBD").text)
    for i in range(numberoftrades):
      quantities['sbd'] += hist["result"][i]["Quantity"]
      quantities['sbdbtc'] += hist["result"][i]["Total"]
  except:
    a = 1

  try:
    hist = json.loads(requests.request("GET","https://poloniex.com/public?command=returnTradeHistory&currencyPair=BTC_SBD").text)
    for i in range(numberoftrades):
      quantities['sbd'] += float(hist[i]['amount'])
      quantities['sbdbtc'] += float(hist[i]['total'])
  except:
    a = 1

  if quantities['steem'] > 0 and quantities['sbd'] > 0:
    price = round((quantities['steembtc']/quantities['steem']*btc_usd())*(1+offset),3)
    bias = 1 / (quantities['sbdbtc']/quantities['sbd']*btc_usd())
    current = Witness(witness)
    curr = float(current['sbd_exchange_rate']['base'][:5])
    curr_bias = float(current['sbd_exchange_rate']['quote'][:5])
    if price > (curr * (1 + minchange)) or price < (curr * (1 - minchange)) or bias > (curr_bias * (1 + minchange_bias)) or bias < (curr_bias * (1 - minchange_bias)):
      price = format(price, ".3f")
      bias = format(bias, ".3f")
      publish_feed(price,bias)
      print("Published price feed: " + price + " USD/STEEM with a bias of " + bias + " at " + time.ctime())
  
