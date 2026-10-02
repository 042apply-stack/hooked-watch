#!/usr/bin/env python3
import json,os,time,urllib.request,datetime
MINT="7GUnr7krtQhJwd6ASY2VUprd9t4c64zcgCsjdmZepump"
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"]
seq=0
def rpc(method,params,tries=7):
 global seq
 last=None
 for a in range(tries):
  seq+=1;u=urls[(seq+a)%len(urls)]
  req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":seq,"method":method,"params":params}).encode(),headers={"content-type":"application/json","user-agent":"npc-launch"})
  try:
   with urllib.request.urlopen(req,timeout=25)as r:d=json.loads(r.read().decode())
   if"error"not in d:return d.get("result")
   last=d["error"]
  except Exception as e:last=str(e)
  time.sleep(1+a)
 raise RuntimeError(str(last))
def iso(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()if t else None
ss=rpc("getSignaturesForAddress",[MINT,{"limit":1000}])or[]
# fetch oldest 20 signatures from available history
rows=[]
for s in list(reversed(ss[-20:])):
 t=rpc("getTransaction",[s["signature"],{"encoding":"jsonParsed","maxSupportedTransactionVersion":1,"commitment":"confirmed"}])
 if not t:continue
 keys=[k if isinstance(k,dict)else{"pubkey":k,"signer":False,"writable":False}for k in t["transaction"]["message"].get("accountKeys",[])]
 meta=t.get("meta")or{};pre=meta.get("preBalances")or[];post=meta.get("postBalances")or[]
 kd=[]
 for i,k in enumerate(keys[:len(pre)]):
  kd.append({"pubkey":k["pubkey"],"signer":k.get("signer",False),"writable":k.get("writable",False),"solDelta":(post[i]-pre[i])/1e9})
 progs=[]
 for ins in t["transaction"]["message"].get("instructions",[]):
  if isinstance(ins,dict):progs.append(ins.get("programId")or ins.get("program"))
 rows.append({"time":iso(s.get("blockTime")),"signature":s["signature"],"keys":kd,"programs":progs,"feeSol":meta.get("fee",0)/1e9})
report={"mint":MINT,"signatureCount":len(ss),"newest":iso(ss[0].get("blockTime"))if ss else None,"oldest":iso(ss[-1].get("blockTime"))if ss else None,"oldestRows":rows}
os.makedirs("trace",exist_ok=True);open("trace/npc_launch.json","w").write(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
