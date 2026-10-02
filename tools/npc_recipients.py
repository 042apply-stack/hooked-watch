#!/usr/bin/env python3
import json,os,time,urllib.request,datetime
from collections import defaultdict
MINT="7GUnr7krtQhJwd6ASY2VUprd9t4c64zcgCsjdmZepump";DEC=6
RECIPS=["4aVR9rGRVt9q5jAVfxHPnE75bN6uW6bBFM2mwkjz7hbi","BZBPNij3AaVsk2zogTKYFnAHmRjw9ZEYJoWzakgQbRN9"]
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"];seq=0
def rpc(m,p):
 global seq
 for a in range(7):
  seq+=1;u=urls[(seq+a)%len(urls)]
  try:
   req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":seq,"method":m,"params":p}).encode(),headers={"content-type":"application/json"})
   with urllib.request.urlopen(req,timeout=20)as r:d=json.loads(r.read().decode())
   if"error"not in d:return d.get("result")
  except:pass
  time.sleep(1+a)
 raise RuntimeError(m)
def iso(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()if t else None
def deltas(t):
 meta=t.get("meta")or{};pre={};post={}
 for b in meta.get("preTokenBalances")or[]:
  if b.get("mint")==MINT:pre[b["accountIndex"]]=(b.get("owner"),int(b["uiTokenAmount"]["amount"]))
 for b in meta.get("postTokenBalances")or[]:
  if b.get("mint")==MINT:post[b["accountIndex"]]=(b.get("owner"),int(b["uiTokenAmount"]["amount"]))
 o=defaultdict(int)
 for i in set(pre)|set(post):
  own=(post.get(i)or pre.get(i))[0];o[own]+=post.get(i,(None,0))[1]-pre.get(i,(None,0))[1]
 return{o:v/10**DEC for o,v in o.items()if o and v}
out={}
for owner in RECIPS:
 tas=rpc("getTokenAccountsByOwner",[owner,{"mint":MINT},{"encoding":"jsonParsed","commitment":"confirmed"}])
 x=[]
 for ta in(tas or{}).get("value",[]):
  inf=ta["account"]["data"]["parsed"]["info"];ata=ta["pubkey"]
  ss=rpc("getSignaturesForAddress",[ata,{"limit":100}])or[]
  txs=[]
  for s in reversed(ss):
   t=rpc("getTransaction",[s["signature"],{"encoding":"jsonParsed","maxSupportedTransactionVersion":1,"commitment":"confirmed"}])
   if t:
    ds=deltas(t)
    if owner in ds:txs.append({"time":iso(s.get("blockTime")),"signature":s["signature"],"delta":ds[owner],"all":ds})
  x.append({"tokenAccount":ata,"current":inf["tokenAmount"].get("uiAmountString"),"sigCount":len(ss),"txs":txs})
 out[owner]=x
print(json.dumps(out,indent=2))
