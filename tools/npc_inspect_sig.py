#!/usr/bin/env python3
import json,os,time,urllib.request
SIG="5EmwAj3on6sQdxwSq6U1TPwL9sCzyHo36d8F9kApSjdoFt588gxFzAN2n9NmPg6yd5uk2DG57VS7ESRqdpt8LKsW"
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"]
for u in urls:
 try:
  body=json.dumps({"jsonrpc":"2.0","id":1,"method":"getTransaction","params":[SIG,{"encoding":"jsonParsed","maxSupportedTransactionVersion":1,"commitment":"confirmed"}]}).encode()
  req=urllib.request.Request(u,data=body,headers={"content-type":"application/json"})
  with urllib.request.urlopen(req,timeout=30) as r:d=json.loads(r.read().decode())
  if"d" not in locals()or"error"in d:continue
  tx=d["result"];break
 except Exception as e:continue
meta=tx.get("meta")or{}
keys=[k if isinstance(k,dict)else{"pubkey":k,"signer":False}for k in tx["transaction"]["message"].get("accountKeys",[])]
# include loaded addresses so accountIndex resolves
loaded=meta.get("loadedAddresses")or{}
for k in loaded.get("writable",[])+loaded.get("readonly",[]):keys.append({"pubkey":k,"signer":False,"loaded":True})
def balrows(which):
 out=[]
 for b in meta.get(which)or[]:
  i=b["accountIndex"]
  out.append({"accountIndex":i,"account":keys[i]["pubkey"]if i<len(keys)else None,"mint":b.get("mint"),"owner":b.get("owner"),"raw":b["uiTokenAmount"]["amount"],"ui":b["uiTokenAmount"].get("uiAmountString")})
 return out
report={"signature":SIG,"blockTime":tx.get("blockTime"),"accountKeys":keys,"preTokenBalances":balrows("preTokenBalances"),"postTokenBalances":balrows("postTokenBalances"),
"messageInstructions":tx["transaction"]["message"].get("instructions",[]),"innerInstructions":meta.get("innerInstructions"),"preBalances":meta.get("preBalances"),"postBalances":meta.get("postBalances"),"fee":meta.get("fee")}
print(json.dumps(report,indent=2))
