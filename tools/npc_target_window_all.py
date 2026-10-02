#!/usr/bin/env python3
import json,os,time,urllib.request,datetime
TARGET="HhmZp65YmWSddyumkFcHDzaykYKCDeLMTSwJqnw9sbtH"
START=int(datetime.datetime(2026,9,28,18,0,tzinfo=datetime.timezone.utc).timestamp())
END=int(datetime.datetime(2026,9,29,1,30,tzinfo=datetime.timezone.utc).timestamp())
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"]
seq=0
def rpc(m,p,tries=7):
 global seq
 last=None
 for a in range(tries):
  seq+=1;u=urls[(seq+a)%len(urls)]
  req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":seq,"method":m,"params":p}).encode(),headers={"content-type":"application/json"})
  try:
   with urllib.request.urlopen(req,timeout=20)as r:d=json.loads(r.read().decode())
   if"error"not in d:return d.get("result")
   last=d["error"]
  except Exception as e:last=str(e)
  time.sleep(1+a)
 raise RuntimeError(str(last))
def iso(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()if t else None
ss=rpc("getSignaturesForAddress",[TARGET,{"limit":1000}])or[]
sel=[s for s in ss if s.get("blockTime")and START<=s["blockTime"]<=END]
rows=[]
for s in sorted(sel,key=lambda x:x["blockTime"]):
 t=rpc("getTransaction",[s["signature"],{"encoding":"jsonParsed","maxSupportedTransactionVersion":1,"commitment":"confirmed"}])
 if not t:continue
 keys=[k if isinstance(k,dict)else{"pubkey":k,"signer":False}for k in t["transaction"]["message"].get("accountKeys",[])]
 rows.append({"time":iso(s["blockTime"]),"signature":s["signature"],"signers":[k["pubkey"]for k in keys if k.get("signer")],
 "programs":[i.get("programId")or i.get("program")for i in t["transaction"]["message"].get("instructions",[])if isinstance(i,dict)]})
print(json.dumps({"count":len(rows),"rows":rows},indent=2))
