#!/usr/bin/env python3
import json,os,time,urllib.request,datetime
from collections import defaultdict,deque

MINT="7GUnr7krtQhJwd6ASY2VUprd9t4c64zcgCsjdmZepump"
DEC=6
TARGET="HhmZp65YmWSddyumkFcHDzaykYKCDeLMTSwJqnw9sbtH"
KNOWN_POOL="BRjMA8UALNp3diTKHfdeAn5riQrYPoaYez7KhYWD4oEs"
SEEDS=[
 TARGET,
 "4aVR9rGRVt9q5jAVfxHPnE75bN6uW6bBFM2mwkjz7hbi",
 "BZBPNij3AaVsk2zogTKYFnAHmRjw9ZEYJoWzakgQbRN9",
]
AUX=[
 "94v857jGb4z4nWEKqGizrNM9gD68n2Wnfot6dbbtLVnk",
 "542RqmbGmMHxvw5bLtbiGyVu4pBuKLw3dBkZ4AcB5Kix",
 "8eEWHgnSmx48ZYo8czQLY1xznBLCJfdRQEq5vURJYi6P",
 "7iVCXQn4u6tiTEfNVqbWSEsRdEi69E9oYsSMiepuECwi",
]
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"]
seq=0
def rpc(method,params,tries=8):
 global seq
 last=None
 for a in range(tries):
  u=urls[(seq+a)%len(urls)];seq+=1
  req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":seq,"method":method,"params":params}).encode(),headers={"content-type":"application/json","user-agent":"npc-graph"})
  try:
   with urllib.request.urlopen(req,timeout=22) as r:d=json.loads(r.read().decode())
   if "error" not in d:return d.get("result")
   last=d["error"]
  except Exception as e:last=str(e)
  time.sleep(1+a)
 raise RuntimeError(f"{method}: {last}")
def iso(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat() if t else None
def acct_info(addr):
 try:
  r=rpc("getAccountInfo",[addr,{"encoding":"base64","commitment":"confirmed"}])
  v=(r or {}).get("value")
  if not v:return {"exists":False}
  return {"exists":True,"programOwner":v.get("owner"),"lamports":v.get("lamports"),"executable":v.get("executable")}
 except Exception as e:return {"error":str(e)}
def token_accounts(owner):
 try:
  r=rpc("getTokenAccountsByOwner",[owner,{"mint":MINT},{"encoding":"jsonParsed","commitment":"confirmed"}])
  out=[]
  for x in (r or {}).get("value",[]):
   inf=x["account"]["data"]["parsed"]["info"]
   out.append({"tokenAccount":x["pubkey"],"amountRaw":inf["tokenAmount"]["amount"],"amount":float(inf["tokenAmount"].get("uiAmountString") or 0)})
  return out
 except Exception as e:return [{"error":str(e)}]
def keys(tx):
 return [k if isinstance(k,dict) else {"pubkey":k,"signer":False} for k in tx["transaction"]["message"].get("accountKeys",[])]
def deltas(tx):
 m=tx.get("meta")or{};pre={};post={}
 for b in m.get("preTokenBalances")or[]:
  if b.get("mint")==MINT:pre[b["accountIndex"]]=(b.get("owner"),int(b["uiTokenAmount"]["amount"]))
 for b in m.get("postTokenBalances")or[]:
  if b.get("mint")==MINT:post[b["accountIndex"]]=(b.get("owner"),int(b["uiTokenAmount"]["amount"]))
 o=defaultdict(int)
 for i in set(pre)|set(post):
  owner=(post.get(i)or pre.get(i))[0];o[owner]+=post.get(i,(None,0))[1]-pre.get(i,(None,0))[1]
 return {k:v for k,v in o.items() if k and v}
def systems(tx):
 out=[]
 groups=[tx["transaction"]["message"].get("instructions",[])]+[g.get("instructions",[])for g in (tx.get("meta")or{}).get("innerInstructions")or[]]
 for grp in groups:
  for ins in grp:
   p=ins.get("parsed")if isinstance(ins,dict)else None
   if isinstance(p,dict)and p.get("type")=="transfer":
    q=p.get("info")or{}
    if "lamports" in q:out.append({"source":q.get("source"),"destination":q.get("destination"),"sol":int(q["lamports"])/1e9})
 return out

owners={}
edges=[]
txseen=set()
queue=deque((x,0) for x in SEEDS)
queued=set(SEEDS)
MAX_OWNERS=25
while queue and len(owners)<MAX_OWNERS:
 owner,depth=queue.popleft()
 ai=acct_info(owner);tas=token_accounts(owner)
 owners[owner]={"depth":depth,"accountInfo":ai,"tokenAccounts":tas}
 print("owner",owner,"depth",depth,"tas",tas,flush=True)
 for ta in tas:
  if "tokenAccount" not in ta:continue
  sigs=rpc("getSignaturesForAddress",[ta["tokenAccount"],{"limit":200}])or[]
  owners[owner].setdefault("signatureCounts",{})[ta["tokenAccount"]]=len(sigs)
  for si in sigs:
   sig=si["signature"]
   if sig in txseen:continue
   txseen.add(sig)
   tx=rpc("getTransaction",[sig,{"encoding":"jsonParsed","maxSupportedTransactionVersion":0,"commitment":"confirmed"}])
   if not tx:continue
   ds=deltas(tx)
   neg=[(o,-v/10**DEC)for o,v in ds.items()if v<0]
   pos=[(o,v/10**DEC)for o,v in ds.items()if v>0]
   if not neg or not pos:continue
   signers=[k["pubkey"]for k in keys(tx)if k.get("signer")]
   # pair each side proportionally; normally one-to-one for transfers/swaps
   for f,fa in neg:
    for t,taamt in pos:
     amt=min(fa,taamt)
     edges.append({"time":iso(si.get("blockTime")),"signature":sig,"from":f,"to":t,"npc":amt,"allDeltas":{o:v/10**DEC for o,v in ds.items()},"signers":signers,"systemTransfers":systems(tx)})
   if depth<2:
    for cp in list(ds):
     if cp not in (owner,KNOWN_POOL) and cp not in queued and len(queued)<MAX_OWNERS:
      queue.append((cp,depth+1));queued.add(cp)
   time.sleep(.04)

# Auxiliary account info and direct relationship/funding txs if discoverable
aux={}
for a in AUX:
 aux[a]={"accountInfo":acct_info(a),"npcTokenAccounts":token_accounts(a)}

# aggregate edges
agg=defaultdict(float)
for e in edges:agg[(e["from"],e["to"])]+=e["npc"]
aggregated=[{"from":f,"to":t,"npc":v}for(f,t),v in sorted(agg.items(),key=lambda kv:-kv[1])]

report={"generatedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"mint":MINT,"target":TARGET,"knownPool":KNOWN_POOL,"owners":owners,"auxiliary":aux,"edges":edges,"aggregatedEdges":aggregated}
os.makedirs("trace",exist_ok=True)
open("trace/npc_graph.json","w").write(json.dumps(report,indent=2))
print(json.dumps({"owners":owners,"auxiliary":aux,"aggregatedEdges":aggregated},indent=2))
