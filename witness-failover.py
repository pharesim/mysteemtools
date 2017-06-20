# config
account = "pharesim"
wif = "5..."
backupkey = "STM..."
fee = 0.1
rpcnode = "wss://steemd.steemit.com"
SMTPserver = "" # your smtp server
SMTPuser = "" # smtp user
SMTPpass = "" # smtp password
sender =     "" # sending address
destination = [] # recipient addresses


from piston import Steem
from piston.witness import Witness
from pistonbase import transactions
from pistonapi.steemnoderpc import SteemNodeRPC

from smtplib import SMTP_SSL as SMTP
from email.mime.text import MIMEText

import json
import time
import sys


text_subtype = "plain"
client = Steem()
rpc = SteemNodeRPC(rpcnode)

def sendmail(content,subject):
  try:
    msg = MIMEText(content, text_subtype)
    msg['Subject']= subject
    msg['From']   = sender

    conn = SMTP(SMTPserver)
    conn.set_debuglevel(False)
    conn.login(SMTPuser, SMTPpass)
    try:
        conn.sendmail(sender, destination, msg.as_string())
    finally:
        conn.quit()
  except Exception:
    print('Sending mail failed')

def proceed(op):
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


if __name__ == '__main__':
  oldmissed = 0
  misscount = 0
  checkcount = 0
  while True:
    witness = Witness(account)
    missed = witness['total_missed']
    if oldmissed == 0:
      oldmissed = missed
      print('Starting at '+str(missed)+' missed blocks')
    else:
      if missed > oldmissed or misscount > 0:
        checkcount = checkcount + 1

        if missed > oldmissed:
         misscount = misscount + 1
          oldmissed = missed
          print('Missed '+str(misscount)+' block(s) in '+str(checkcount)+' minutes. Total missed: '+str(missed))
          message = "Your node missed "+str(misscount)+" blocks, "+str(missed)+" total."
          sendmail(message,"Missed blocks...")

        if checkcount > 1 and misscount > 1:
          expiration = transactions.formatTimeFromNow(60)
          op = transactions.Witness_update(
            **{"owner": account,
             "url": witness['url'],
             "block_signing_key": backupkey,
             "props": witness['props'],
             "fee": str(fee)+' STEEM'}
          )
          proceed(op)
          print('Failover activated because of too many missed blocks')
          sendmail("Failover activated","Witness failover activated")
          sys.exit()

        if checkcount > 5:
            checkcount = 0
            misscount = 0
            print('Cleared log, everything seems fine')

    time.sleep(60)
