#!/usr/bin/env python3
import json,os,time,urllib.request,datetime
from collections import defaultdict
TARGET="HhmZp65YmWSddyumkFcHDzaykYKCDeLMTSwJqnw9sbtH"
MINT="7GUnr7krtQhJwd6ASY2VUprd9t4c64zcgCsjdmZepump"
DEC=6
FROM=int(datetime.datetime(2026,9,23,tzinfo=datetime.timezone.utc).timestamp())
TO=int(datetime.datetime(2026,10,1,tzinfo=datetime.timezone.utc).timestamp())
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"]
seq=0
def rpc(method,params,tries=8):
 global seq
 last=None
 for a in range(tries):
  u=urls[(seq+a)%len(urls)];seq+=1
  req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":seq,"method":method,"params":params}).encode(),headers={"content-type":"application/json","user-agent":"npc-origin"})
  try:
   with urllib.request.urlopen(req,timeout=22) as r:d=json.loads(r.read().decode())
   if "error" not in d:return d.get("result")
   last=d["error"]
  except Exception as e:last=str(e)
  time.sleep(1+a)
 raise RuntimeError(f"{method}: {last}")
def iso(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat() if t else None
def sigs():
 out=[];before=None
 for page in range(8):
  cfg={"limit":1000}
  if before:cfg["before"]=before
  b=rpc("getSignaturesForAddress",[TARGET,cfg])or[]
  print("page",page,"n",len(b),"newest",iso(b[0].get("blockTime"))if b else None,"oldest",iso(b[-1].get("blockTime"))if b else None,flush=True)
  out+=b
  if not b or (b[-1].get("blockTime") and b[-1]["blockTime"]<FROM):break
  before=b[-1]["signature"]
 return out
def keys(tx):return[k if isinstance(k,dict)else{"pubkey":k,"signer":False}for k in tx["transaction"]["message"].get("accountKeys",[])]
def deltas(tx):
 m=tx.get("meta")or{};pre={};post={}
 for b in m.get("preTokenBalances")or[]:
  if b.get("mint")==MINT:pre[b["accountIndex"]]=(b.get("owner"),int(b["uiTokenAmount"]["amount"]))
 for b in m.get("postTokenBalances")or[]:
  if b.get("mint")==MINT:post[b["accountIndex"]]=(b.get("owner"),int(b["uiTokenAmount"]["amount"]))
 out=defaultdict(int)
 for i in set(pre)|set(post):
  owner=(post.get(i)or pre.get(i))[0];out[owner]+=post.get(i,(None,0))[1]-pre.get(i,(None,0))[1]
 return {o:v for o,v in out.items()if o and v}
def progs(tx):
 s=set()
 groups=[tx["transaction"]["message"].get("instructions",[])]+[g.get("instructions",[])for g in(tx.get("meta")or{}).get("innerInstructions")or[]]
 for grp in groups:
  for x in grp:
   if isinstance(x,dict):s.add(x.get("programId")or x.get("program")or"")
 return sorted(y for y in s if y)
def systems(tx):
 out=[]
 groups=[tx["transaction"]["message"].get("instructions",[])]+[g.get("instructions",[])for g in(tx.get("meta")or{}).get("innerInstructions")or[]]
 for grp in groups:
  for ins in grp:
   p=ins.get("parsed")if isinstance(ins,dict)else None
   if isinstance(p,dict)and p.get("type")=="transfer":
    q=p.get("info")or{}
    if "lamports"in q:out.append({"source":q.get("source"),"destination":q.get("destination"),"sol":int(q["lamports"])/1e9})
 return out
all_s=sigs()
sel=[s for s in all_s if s.get("blockTime") and FROM<=s["blockTime"]<TO]
print("selected",len(sel),flush=True)
rows=[]
for i,s in enumerate(sorted(sel,key=lambda x:x["blockTime"])):
 tx=rpc("getTransaction",[s["signature"],{"encoding":"jsonParsed","maxSupportedTransactionVersion":0,"commitment":"confirmed"}])
 if not tx:continue
 ds=deltas(tx)
 if TARGET not in ds:continue
 ks=keys(tx);meta=tx.get("meta")or{};pre=meta.get("preBalances")or[];post=meta.get("postBalances")or[]
 sol=None
 for ix,k in enumerate(ks[:len(pre)]):
  if k["pubkey"]==TARGET:sol=(post[ix]-pre[ix])/1e9;break
 rows.append({"time":iso(s["blockTime"]),"signature":s["signature"],"npcDelta":ds[TARGET]/10**DEC,
  "otherNpcOwnerDeltas":{o:v/10**DEC for o,v in ds.items()if o!=TARGET},"targetSolDelta":sol,
  "signers":[k["pubkey"]for k in ks if k.get("signer")],"programs":progs(tx),"systemTransfers":systems(tx)})
 print("hit",rows[-1],flush=True)
 time.sleep(.04)
report={"target":TARGET,"mint":MINT,"signatureCount":len(all_s),"windowSignatureCount":len(sel),"rows":rows}
os.makedirs("trace",exist_ok=True)
open("trace/npc_origin.json","w").write(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
