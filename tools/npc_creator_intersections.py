#!/usr/bin/env python3
import json,os,time,urllib.request
ADDRS={
"creator":"Hufy2kTe3sji5mbcttVhmkbWFyyKbHuHd9V8qQpWT4dw",
"hhmz":"HhmZp65YmWSddyumkFcHDzaykYKCDeLMTSwJqnw9sbtH",
"recv1":"4aVR9rGRVt9q5jAVfxHPnE75bN6uW6bBFM2mwkjz7hbi",
"recv2":"BZBPNij3AaVsk2zogTKYFnAHmRjw9ZEYJoWzakgQbRN9",
"funder":"94v857jGb4z4nWEKqGizrNM9gD68n2Wnfot6dbbtLVnk"}
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
def sigs(addr,pages):
 out=[];before=None
 for _ in range(pages):
  cfg={"limit":1000}
  if before:cfg["before"]=before
  b=rpc("getSignaturesForAddress",[addr,cfg])or[];out+=b
  if len(b)<1000:break
  before=b[-1]["signature"]
 return out
sets={}
raw={}
for k,a in ADDRS.items():
 pages=6 if k=="creator" else (1 if k in("hhmz","recv1","recv2") else 2)
 x=sigs(a,pages);raw[k]=x;sets[k]=set(i["signature"]for i in x)
out={"counts":{k:len(v)for k,v in raw.items()},"creatorRange":{"newest":raw["creator"][0].get("blockTime")if raw["creator"]else None,"oldest":raw["creator"][-1].get("blockTime")if raw["creator"]else None},"intersections":{}}
for k in ADDRS:
 if k=="creator":continue
 inter=sets["creator"]&sets[k]
 out["intersections"][f"creator_{k}"]=list(inter)
print(json.dumps(out,indent=2))
