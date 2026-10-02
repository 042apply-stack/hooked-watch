#!/usr/bin/env python3
import json,os,time,urllib.request
from collections import defaultdict
SIG="5EmwAj3on6sQdxwSq6U1TPwL9sCzyHo36d8F9kApSjdoFt588gxFzAN2n9NmPg6yd5uk2DG57VS7ESRqdpt8LKsW"
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"]
tx=None
for u in urls:
 try:
  req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":1,"method":"getTransaction","params":[SIG,{"encoding":"jsonParsed","maxSupportedTransactionVersion":1,"commitment":"confirmed"}]}).encode(),headers={"content-type":"application/json"})
  with urllib.request.urlopen(req,timeout=25)as r:d=json.loads(r.read().decode())
  if"error"not in d:tx=d["result"];break
 except:pass
m=tx["meta"];pre={};post={}
for b in m.get("preTokenBalances")or[]:
 pre[b["accountIndex"]]={"owner":b.get("owner"),"mint":b.get("mint"),"raw":int(b["uiTokenAmount"]["amount"]),"dec":b["uiTokenAmount"]["decimals"]}
for b in m.get("postTokenBalances")or[]:
 post[b["accountIndex"]]={"owner":b.get("owner"),"mint":b.get("mint"),"raw":int(b["uiTokenAmount"]["amount"]),"dec":b["uiTokenAmount"]["decimals"]}
agg=defaultdict(int);decs={}
for i in set(pre)|set(post):
 a=post.get(i)or pre.get(i);key=(a["owner"],a["mint"]);agg[key]+=post.get(i,{"raw":0})["raw"]-pre.get(i,{"raw":0})["raw"];decs[key]=a["dec"]
rows=[]
for (owner,mint),raw in agg.items():
 if raw:
  rows.append({"owner":owner,"mint":mint,"delta":raw/(10**decs[(owner,mint)])})
rows.sort(key=lambda x:(x["mint"],-abs(x["delta"])))
print(json.dumps({"signature":SIG,"ownerMintDeltas":rows},indent=2))
