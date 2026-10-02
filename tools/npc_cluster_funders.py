#!/usr/bin/env python3
import json,os,time,urllib.request,datetime
ADDRS=[
"HhmZp65YmWSddyumkFcHDzaykYKCDeLMTSwJqnw9sbtH",
"4aVR9rGRVt9q5jAVfxHPnE75bN6uW6bBFM2mwkjz7hbi",
"BZBPNij3AaVsk2zogTKYFnAHmRjw9ZEYJoWzakgQbRN9",
"94v857jGb4z4nWEKqGizrNM9gD68n2Wnfot6dbbtLVnk",
"542RqmbGmMHxvw5bLtbiGyVu4pBuKLw3dBkZ4AcB5Kix",
"8eEWHgnSmx48ZYo8czQLY1xznBLCJfdRQEq5vURJYi6P"]
KNOWN=set(ADDRS+["7iVCXQn4u6tiTEfNVqbWSEsRdEi69E9oYsSMiepuECwi"])
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"]
seq=0
def rpc(method,params,tries=7):
 global seq
 last=None
 for a in range(tries):
  seq+=1;u=urls[(seq+a)%len(urls)]
  req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":seq,"method":method,"params":params}).encode(),headers={"content-type":"application/json","user-agent":"npc-funders"})
  try:
   with urllib.request.urlopen(req,timeout=22)as r:d=json.loads(r.read().decode())
   if "error"not in d:return d.get("result")
   last=d["error"]
  except Exception as e:last=str(e)
  time.sleep(1+a)
 raise RuntimeError(str(last))
def iso(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()if t else None
def sigs(addr,maxpages=10):
 out=[];before=None
 for p in range(maxpages):
  cfg={"limit":1000}
  if before:cfg["before"]=before
  b=rpc("getSignaturesForAddress",[addr,cfg])or[]
  out+=b
  if not b or len(b)<1000:break
  before=b[-1]["signature"]
  time.sleep(.05)
 return out
def tx(sig):
 try:return rpc("getTransaction",[sig,{"encoding":"jsonParsed","maxSupportedTransactionVersion":1,"commitment":"confirmed"}])
 except:return None
def system_transfers(t):
 out=[]
 groups=[t["transaction"]["message"].get("instructions",[])]+[g.get("instructions",[])for g in(t.get("meta")or{}).get("innerInstructions")or[]]
 for grp in groups:
  for ins in grp:
   p=ins.get("parsed")if isinstance(ins,dict)else None
   if isinstance(p,dict)and p.get("type")=="transfer":
    q=p.get("info")or{}
    if"lamports"in q:out.append({"source":q.get("source"),"destination":q.get("destination"),"sol":int(q["lamports"])/1e9})
 return out
report={}
for a in ADDRS:
 ss=sigs(a)
 entry={"signatureCountFetched":len(ss),"newest":iso(ss[0].get("blockTime"))if ss else None,"oldest":iso(ss[-1].get("blockTime"))if ss else None}
 # inspect oldest 25 and newest 25 plus all signatures if <=300
 inspect=ss if len(ss)<=300 else ss[:25]+ss[-25:]
 transfers=[]
 for s in inspect:
  t=tx(s["signature"])
  if not t:continue
  for x in system_transfers(t):
   if x.get("source")==a or x.get("destination")==a:
    transfers.append({"time":iso(s.get("blockTime")),"signature":s["signature"],**x,
     "counterpartyKnown":(x.get("source")in KNOWN or x.get("destination")in KNOWN)})
  time.sleep(.03)
 entry["sampledNativeTransfers"]=sorted(transfers,key=lambda x:x.get("time")or"")
 # balance/info
 try:
  inf=rpc("getAccountInfo",[a,{"encoding":"base64","commitment":"confirmed"}])["value"]
  entry["solBalance"]=inf["lamports"]/1e9 if inf else 0
  entry["accountProgramOwner"]=inf["owner"] if inf else None
 except Exception as e:entry["infoError"]=str(e)
 report[a]=entry
 print(a,json.dumps(entry),flush=True)
os.makedirs("trace",exist_ok=True)
open("trace/npc_cluster_funders.json","w").write(json.dumps(report,indent=2))
