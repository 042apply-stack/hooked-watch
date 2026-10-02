#!/usr/bin/env python3
import json,os,time,urllib.request
from collections import defaultdict
TARGET="HhmZp65YmWSddyumkFcHDzaykYKCDeLMTSwJqnw9sbtH"
EXEC="7iVCXQn4u6tiTEfNVqbWSEsRdEi69E9oYsSMiepuECwi"
MINT="7GUnr7krtQhJwd6ASY2VUprd9t4c64zcgCsjdmZepump"
SIGS=[
"5gMtqmvLNkRfNHN3V1egE33HRkE2ejzmhpzR67SvxEQ4mY5ejtj9TmTAKdfYFSfr3ZAcM1nYdAMLD8JN64rF3Qjy",
"3362BYzqAG5YZH2x8Lho7KvCT7BALavusBPNKZFAeE2qxM29cuJjxbBy2yMqqJYnUkGMkiTLXCNjpMudWhixpRk8",
"3GdURUDfNSJsZiyCNRRrm3dYbuaG4wuT9bgdrJqF6JxUV5jSfBdMUAFbDaZvmqtF92kNd4EpoqnU6gCSGtA4gFgG",
"3ztLqfPM8Y9YtkcW7pphDv3Jbie6utgoYAWJEkJzYcAryW4n7ecv8PwMEhdKbPd3z9mK2oqh9DvyHmu1kBbmfCr",
"ib8DPEgJuY3yE6H8Bgv8foB8RaSLspy9UBZQEhko4EAcbPsBCuSYjpR3BVbbALCKxh7SVsLkq8PX2sqW3KkRywu",
"V7rgsxR1cmFDVN7N3GieEwrNCAN6MedXk5XMVTRXTcksiNgERbKmhx8KWC28vNViacwZBqv7wZqv1eEQxjcbweN",
"2PXXLLjcmmN3d35tUxuz9rMABTPajAgezFDs6C922q8WDMmo91fLNRrjnzJCzspmhES63HE1V8AZADdFz2SVmtpy",
"5CWrWDzT5m7qQze6Dvcg9RVnkjrpvjwjvyLzdk9n6w2e95szzFiCThQYsMhvu81H9tHHR4cNwJcRctiR6TpFYETq",
"6vYbtJjvEMvgNKuQmiw8mpfropRL5zpGshF1jnpVkY3174ier2Z6YmaE4SRjbqy853JxztG1HrGbm7PrXSVdny7",
"2voLRRfBmW7y6rC39H519MdM7KpY1ejZvU1dBBHd5PJMduStEe2A3P9Mq8WjUyFXZ7bXSkcDqApfJWonFYV1y3bH",
"5EmwAj3on6sQdxwSq6U1TPwL9sCzyHo36d8F9kApSjdoFt588gxFzAN2n9NmPg6yd5uk2DG57VS7ESRqdpt8LKsW",
"3npeZV3remAfnXJUhub3Hi7eskunJkdm65BAfTkxP871Z6eGPfC7VHrai7f2qahm2p1WWNHKcUowyv8mzpvFGakJ"
]
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"];seq=0
def rpc(m,p):
 global seq
 for a in range(7):
  seq+=1;u=urls[(seq+a)%len(urls)]
  try:
   req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":seq,"method":m,"params":p}).encode(),headers={"content-type":"application/json"})
   with urllib.request.urlopen(req,timeout=25)as r:d=json.loads(r.read().decode())
   if"error"not in d:return d.get("result")
  except:pass
  time.sleep(1+a)
 raise RuntimeError(m)
def rows(tx):
 m=tx.get("meta")or{};pre={};post={}
 for b in m.get("preTokenBalances")or[]:
  pre[b["accountIndex"]]={"owner":b.get("owner"),"mint":b.get("mint"),"raw":int(b["uiTokenAmount"]["amount"]),"dec":b["uiTokenAmount"]["decimals"]}
 for b in m.get("postTokenBalances")or[]:
  post[b["accountIndex"]]={"owner":b.get("owner"),"mint":b.get("mint"),"raw":int(b["uiTokenAmount"]["amount"]),"dec":b["uiTokenAmount"]["decimals"]}
 agg=defaultdict(int);decs={}
 for i in set(pre)|set(post):
  a=post.get(i)or pre.get(i);key=(a["owner"],a["mint"]);agg[key]+=post.get(i,{"raw":0})["raw"]-pre.get(i,{"raw":0})["raw"];decs[key]=a["dec"]
 return [{"owner":o,"mint":mint,"delta":v/(10**decs[(o,mint)])}for(o,mint),v in agg.items()if v]
out=[]
for sig in SIGS:
 tx=rpc("getTransaction",[sig,{"encoding":"jsonParsed","maxSupportedTransactionVersion":1,"commitment":"confirmed"}])
 if not tx:continue
 rr=rows(tx)
 out.append({"signature":sig,"blockTime":tx.get("blockTime"),
  "targetNPC":next((x["delta"]for x in rr if x["owner"]==TARGET and x["mint"]==MINT),0),
  "execUSDC":next((x["delta"]for x in rr if x["owner"]==EXEC and x["mint"]=="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),0),
  "execWSOL":next((x["delta"]for x in rr if x["owner"]==EXEC and x["mint"]=="So11111111111111111111111111111111111111112"),0),
  "ownerMintDeltas":rr})
print(json.dumps(out,indent=2))
