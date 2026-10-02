#!/usr/bin/env python3
import json,os,time,urllib.request,datetime,concurrent.futures,threading
from collections import defaultdict

EXEC="7iVCXQn4u6tiTEfNVqbWSEsRdEi69E9oYsSMiepuECwi"
TARGET="HhmZp65YmWSddyumkFcHDzaykYKCDeLMTSwJqnw9sbtH"
MINT="7GUnr7krtQhJwd6ASY2VUprd9t4c64zcgCsjdmZepump"
DEC=6
START=int(datetime.datetime(2026,9,28,18,30,tzinfo=datetime.timezone.utc).timestamp())
END=int(datetime.datetime(2026,9,29,1,0,tzinfo=datetime.timezone.utc).timestamp())
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org","https://rpc.ankr.com/solana"]
lock=threading.Lock(); seq=0
def rpc(method,params,tries=7):
 global seq
 last=None
 for a in range(tries):
  with lock:
   seq+=1; i=seq
  u=urls[(i+a)%len(urls)]
  req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":i,"method":method,"params":params}).encode(),headers={"content-type":"application/json","user-agent":"npc-exec-window"})
  try:
   with urllib.request.urlopen(req,timeout=25) as r:d=json.loads(r.read().decode())
   if "error" not in d:return d.get("result")
   last=d["error"]
  except Exception as e:last=str(e)
  time.sleep(min(1+a,5))
 raise RuntimeError(f"{method}: {last}")
def iso(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat() if t else None
def get_window_sigs():
 out=[];before=None
 for page in range(60):
  cfg={"limit":1000}
  if before:cfg["before"]=before
  b=rpc("getSignaturesForAddress",[EXEC,cfg])or[]
  if not b:break
  newest=b[0].get("blockTime");oldest=b[-1].get("blockTime")
  print("page",page,"n",len(b),"newest",iso(newest),"oldest",iso(oldest),flush=True)
  for s in b:
   t=s.get("blockTime")
   if t and START<=t<=END:out.append(s)
  if oldest and oldest<START:break
  before=b[-1]["signature"]
  if len(b)<1000:break
  time.sleep(.08)
 return out
def deltas(tx):
 m=tx.get("meta")or{};pre={};post={}
 for b in m.get("preTokenBalances")or[]:
  if b.get("mint")==MINT:pre[b["accountIndex"]]=(b.get("owner"),int(b["uiTokenAmount"]["amount"]))
 for b in m.get("postTokenBalances")or[]:
  if b.get("mint")==MINT:post[b["accountIndex"]]=(b.get("owner"),int(b["uiTokenAmount"]["amount"]))
 out=defaultdict(int)
 for i in set(pre)|set(post):
  owner=(post.get(i)or pre.get(i))[0]
  out[owner]+=post.get(i,(None,0))[1]-pre.get(i,(None,0))[1]
 return {o:v for o,v in out.items() if o and v}
def one(si):
 try:
  tx=rpc("getTransaction",[si["signature"],{"encoding":"jsonParsed","maxSupportedTransactionVersion":1,"commitment":"confirmed"}])
  if not tx:return None
  ds=deltas(tx)
  if TARGET not in ds:return None
  keys=[k if isinstance(k,dict)else{"pubkey":k,"signer":False}for k in tx["transaction"]["message"].get("accountKeys",[])]
  return {"time":iso(si.get("blockTime")),"signature":si["signature"],"targetNpcDelta":ds[TARGET]/10**DEC,
   "allNpcOwnerDeltas":{o:v/10**DEC for o,v in ds.items()},"signers":[k["pubkey"] for k in keys if k.get("signer")],
   "feeSol":(tx.get("meta")or{}).get("fee",0)/1e9}
 except Exception as e:return {"signature":si["signature"],"error":str(e)}
sigs=get_window_sigs()
print("window signatures",len(sigs),flush=True)
hits=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
 for i,r in enumerate(ex.map(one,sigs)):
  if r:
   hits.append(r); print("HIT",json.dumps(r),flush=True)
  if i and i%100==0: print("processed",i,flush=True)
hits.sort(key=lambda x:x.get("time")or"")
report={"executor":EXEC,"target":TARGET,"mint":MINT,"start":iso(START),"end":iso(END),"windowSignatureCount":len(sigs),"hits":hits,
 "targetNetNpc":sum(x.get("targetNpcDelta",0) for x in hits)}
os.makedirs("trace",exist_ok=True)
open("trace/npc_7ivc_window.json","w").write(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
