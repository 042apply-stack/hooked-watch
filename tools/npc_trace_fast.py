#!/usr/bin/env python3
import json, os, time, urllib.request, datetime
from collections import defaultdict
TARGET="HhmZp65YmWSddyumkFcHDzaykYKCDeLMTSwJqnw9sbtH"
MINT="7GUnr7krtQhJwd6ASY2VUprd9t4c64zcgCsjdmZepump"
ATA="oQJpC9tRecH2Yn7sNF4REeK6xtNEzftLxTPpD2eAK6F"
DEC=6
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip(): urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls += ["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"]
seq=0
def rpc(method,params):
 global seq
 last=None
 for attempt in range(8):
  u=urls[(seq+attempt)%len(urls)]; seq+=1
  req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":seq,"method":method,"params":params}).encode(),headers={"content-type":"application/json","user-agent":"npc-fast-trace"})
  try:
   with urllib.request.urlopen(req,timeout=20) as r: d=json.loads(r.read().decode())
   if "error" not in d: return d.get("result")
   last=d["error"]
  except Exception as e: last=str(e)
  time.sleep(1+attempt)
 raise RuntimeError(f"{method}: {last}")
def iso(ts): return datetime.datetime.fromtimestamp(ts,datetime.timezone.utc).isoformat() if ts else None
def owner_deltas(tx):
 m=tx.get("meta") or {}; pre={}; post={}
 for b in m.get("preTokenBalances") or []:
  if b.get("mint")==MINT: pre[b["accountIndex"]]=(b.get("owner"),int(b["uiTokenAmount"]["amount"]))
 for b in m.get("postTokenBalances") or []:
  if b.get("mint")==MINT: post[b["accountIndex"]]=(b.get("owner"),int(b["uiTokenAmount"]["amount"]))
 out=defaultdict(int)
 for i in set(pre)|set(post):
  owner=(post.get(i) or pre.get(i))[0]
  out[owner]+=(post.get(i,(None,0))[1]-pre.get(i,(None,0))[1])
 return dict(out)
def keys(tx):
 a=[]
 for k in tx["transaction"]["message"].get("accountKeys",[]):
  a.append(k if isinstance(k,dict) else {"pubkey":k,"signer":False})
 return a
def progs(tx):
 s=set()
 for ins in tx["transaction"]["message"].get("instructions",[]):
  if isinstance(ins,dict): s.add(ins.get("programId") or ins.get("program") or "")
 for g in (tx.get("meta") or {}).get("innerInstructions") or []:
  for ins in g.get("instructions",[]):
   if isinstance(ins,dict): s.add(ins.get("programId") or ins.get("program") or "")
 return sorted(x for x in s if x)
def systems(tx):
 out=[]
 groups=[tx["transaction"]["message"].get("instructions",[])] + [g.get("instructions",[]) for g in (tx.get("meta") or {}).get("innerInstructions") or []]
 for grp in groups:
  for ins in grp:
   p=ins.get("parsed") if isinstance(ins,dict) else None
   if isinstance(p,dict) and p.get("type")=="transfer":
    inf=p.get("info") or {}
    if "lamports" in inf:
     out.append({"source":inf.get("source"),"destination":inf.get("destination"),"sol":int(inf["lamports"])/1e9})
 return out
sigs=rpc("getSignaturesForAddress",[ATA,{"limit":1000}]) or []
print("signatures",len(sigs),flush=True)
rows=[]
for n,s in enumerate(sigs):
 tx=rpc("getTransaction",[s["signature"],{"encoding":"jsonParsed","maxSupportedTransactionVersion":0,"commitment":"confirmed"}])
 if not tx: continue
 ds=owner_deltas(tx); d=ds.get(TARGET,0)
 if d:
  ks=keys(tx); signers=[x["pubkey"] for x in ks if x.get("signer")]
  meta=tx.get("meta") or {}; pre=meta.get("preBalances") or []; post=meta.get("postBalances") or []
  sol=None
  for i,x in enumerate(ks[:len(pre)]):
   if x["pubkey"]==TARGET: sol=(post[i]-pre[i])/1e9; break
  rows.append({"time":iso(s.get("blockTime")),"blockTime":s.get("blockTime"),"signature":s["signature"],
   "npcDelta":d/10**DEC,"targetSigned":TARGET in signers,"targetSolDelta":sol,
   "otherNpcOwnerDeltas":{o:v/10**DEC for o,v in ds.items() if o and o!=TARGET and v},
   "signers":signers,"programs":progs(tx),"systemTransfers":systems(tx),"feeSol":meta.get("fee",0)/1e9})
 print(n+1,"/",len(sigs),flush=True)
 time.sleep(.05)
rows.sort(key=lambda x:x.get("blockTime") or 0)
report={"target":TARGET,"mint":MINT,"tokenAccount":ATA,"signatureCount":len(sigs),"npcTxCount":len(rows),"rows":rows}
os.makedirs("trace",exist_ok=True)
open("trace/npc_hhmz_fast.json","w").write(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
