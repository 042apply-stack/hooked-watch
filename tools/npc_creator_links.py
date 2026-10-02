#!/usr/bin/env python3
import json,os,time,urllib.request,datetime
CREATOR="Hufy2kTe3sji5mbcttVhmkbWFyyKbHuHd9V8qQpWT4dw"
MINT="7GUnr7krtQhJwd6ASY2VUprd9t4c64zcgCsjdmZepump"
KNOWN=[
"HhmZp65YmWSddyumkFcHDzaykYKCDeLMTSwJqnw9sbtH",
"7iVCXQn4u6tiTEfNVqbWSEsRdEi69E9oYsSMiepuECwi",
"4aVR9rGRVt9q5jAVfxHPnE75bN6uW6bBFM2mwkjz7hbi",
"BZBPNij3AaVsk2zogTKYFnAHmRjw9ZEYJoWzakgQbRN9",
"94v857jGb4z4nWEKqGizrNM9gD68n2Wnfot6dbbtLVnk",
"542RqmbGmMHxvw5bLtbiGyVu4pBuKLw3dBkZ4AcB5Kix",
"8eEWHgnSmx48ZYo8czQLY1xznBLCJfdRQEq5vURJYi6P"]
urls=[]
if os.getenv("SOLANA_RPC_URL","").strip():urls.append(os.getenv("SOLANA_RPC_URL").strip())
urls+=["https://solana-rpc.publicnode.com","https://api.mainnet-beta.solana.com","https://solana.drpc.org"]
seq=0
def rpc(m,p,tries=7):
 global seq
 last=None
 for a in range(tries):
  seq+=1;u=urls[(seq+a)%len(urls)]
  req=urllib.request.Request(u,data=json.dumps({"jsonrpc":"2.0","id":seq,"method":m,"params":p}).encode(),headers={"content-type":"application/json","user-agent":"npc-creator-links"})
  try:
   with urllib.request.urlopen(req,timeout=22)as r:d=json.loads(r.read().decode())
   if"error"not in d:return d.get("result")
   last=d["error"]
  except Exception as e:last=str(e)
  time.sleep(1+a)
 raise RuntimeError(str(last))
def iso(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()if t else None
def systrans(t):
 out=[]
 groups=[t["transaction"]["message"].get("instructions",[])]+[g.get("instructions",[])for g in(t.get("meta")or{}).get("innerInstructions")or[]]
 for grp in groups:
  for ins in grp:
   p=ins.get("parsed")if isinstance(ins,dict)else None
   if isinstance(p,dict)and p.get("type")=="transfer":
    q=p.get("info")or{}
    if"lamports"in q:out.append({"source":q.get("source"),"destination":q.get("destination"),"sol":int(q["lamports"])/1e9})
 return out
ss=[];before=None
for page in range(5):
 cfg={"limit":1000}
 if before:cfg["before"]=before
 b=rpc("getSignaturesForAddress",[CREATOR,cfg])or[];ss+=b
 if not b or len(b)<1000:break
 before=b[-1]["signature"]
links=[];allnative=[]
inspect=ss if len(ss)<=500 else ss[:100]+ss[-100:]
for s in inspect:
 try:t=rpc("getTransaction",[s["signature"],{"encoding":"jsonParsed","maxSupportedTransactionVersion":1,"commitment":"confirmed"}])
 except:continue
 if not t:continue
 for x in systrans(t):
  if x["source"]==CREATOR or x["destination"]==CREATOR:
   rec={"time":iso(s.get("blockTime")),"signature":s["signature"],**x}
   allnative.append(rec)
   if x["source"]in KNOWN or x["destination"]in KNOWN:links.append(rec)
 time.sleep(.03)
tas=rpc("getTokenAccountsByOwner",[CREATOR,{"mint":MINT},{"encoding":"jsonParsed","commitment":"confirmed"}])
npc=[]
for x in (tas or{}).get("value",[]):
 inf=x["account"]["data"]["parsed"]["info"];npc.append({"account":x["pubkey"],"amount":inf["tokenAmount"].get("uiAmountString")})
info=rpc("getAccountInfo",[CREATOR,{"encoding":"base64","commitment":"confirmed"}])["value"]
report={"creator":CREATOR,"signatureCountFetched":len(ss),"newest":iso(ss[0].get("blockTime"))if ss else None,"oldest":iso(ss[-1].get("blockTime"))if ss else None,
"solBalance":info["lamports"]/1e9 if info else None,"npcAccounts":npc,"directKnownLinks":links,"sampleNativeTransfers":sorted(allnative,key=lambda x:x["time"]or"")}
os.makedirs("trace",exist_ok=True);open("trace/npc_creator_links.json","w").write(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
