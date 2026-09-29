#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

MINT="C1mBfBoDkwWfd6uTFZp62ARHLjeVp3bDpCDMfMZtPngE"
CREATOR="Dpmutmc4ZLqvJwHbwabvKYeFJ9zkQ86nutUAUviRrXG2"
FLYWHEEL="2oXT6oMgNPfToahWG48QTBPWS9UJ8a7TSSeEoeoSLMGt"
UPGRADE="8D71hCD9xnQbxEjUedH4dHHVXrJowG4bDVVjCtdDwFGz"
SITE="https://www.hookedpad.com/"
LAUNCHES=SITE+"launches"
X_HANDLE="Hoookedpad"
ENTRY_MC=950000.0
POSITION_USD=1000.0
INITIAL_SUPPLY=1000000000.0
STATE=Path("state/latest.json")
REPORT=Path("reports/latest.md")
ALERT=Path("state/alert.json")
UA="hooked-watch/1.0"
TIMEOUT=20

PROGRAMS={
 "combined":"C3vEdPepTPRrJdQ4nQ3ZmhdXCmpKdGRKVUqxduHZWbdR",
 "anti_bundle":"AsqN4BA2cGmzbajL5rdg8rmfAsWs2K4TBS7Eqa8eLaY8",
 "core_1":"3uxoNzXjn6hKxuFqi5sZjnSoFauSXjnq6i9vWPJf99Zs",
 "core_2":"4Tabcoy1niosiNAGHMruLBFscgJWXZsVF3pfij3FqMB5",
}
RPCS=[x for x in [
 os.getenv("SOLANA_RPC_URL","").strip(),
 "https://api.mainnet-beta.solana.com",
 "https://solana-rpc.publicnode.com"
] if x]

def now():
 return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

def request(url,method="GET",data=None,headers=None):
 h={"User-Agent":UA,"Accept":"*/*"}
 if headers:h.update(headers)
 q=urllib.request.Request(url,data=data,method=method,headers=h)
 with urllib.request.urlopen(q,timeout=TIMEOUT) as r:return r.read()

def jget(url):return json.loads(request(url,headers={"Accept":"application/json"}).decode())
def tget(url):return request(url,headers={"Accept":"text/html,text/plain;q=0.9,*/*;q=0.8"}).decode("utf-8","replace")

def rpc(method,params):
 body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
 last=None
 for ep in RPCS:
  try:
   out=json.loads(request(ep,"POST",body,{"Content-Type":"application/json"}))
   if "error" in out:raise RuntimeError(str(out["error"]))
   return out.get("result")
  except Exception as e:last=e
 raise RuntimeError("all RPC endpoints failed: "+str(last))

def safe(fn,default=None):
 try:return fn(),None
 except Exception as e:return default,type(e).__name__+": "+str(e)

def sha(s):return hashlib.sha256(s.encode("utf-8","replace")).hexdigest()
def clean(s):return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s))).strip()
def pct(a,b):return None if not a else (b-a)/a*100.0

def load():
 if not STATE.exists():return {}
 try:return json.loads(STATE.read_text())
 except Exception:return {}

def save(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")

def dex():
 raw=jget("https://api.dexscreener.com/latest/dex/tokens/"+MINT)
 pairs=[p for p in (raw.get("pairs") or []) if MINT in (p.get("baseToken",{}).get("address"),p.get("quoteToken",{}).get("address"))]
 pairs.sort(key=lambda p:float((p.get("liquidity") or {}).get("usd") or 0),reverse=True)
 top=pairs[0] if pairs else {}
 mc=top.get("marketCap") or top.get("fdv") or 0
 return {
  "price":float(top.get("priceUsd") or 0),
  "mc":float(mc),
  "liq":sum(float((p.get("liquidity") or {}).get("usd") or 0) for p in pairs),
  "vol24":sum(float((p.get("volume") or {}).get("h24") or 0) for p in pairs),
  "pair":top.get("pairAddress"),
  "dex":top.get("dexId"),
  "b1":int(((top.get("txns") or {}).get("h1") or {}).get("buys") or 0),
  "s1":int(((top.get("txns") or {}).get("h1") or {}).get("sells") or 0),
  "b24":int(((top.get("txns") or {}).get("h24") or {}).get("buys") or 0),
  "s24":int(((top.get("txns") or {}).get("h24") or {}).get("sells") or 0),
  "c1":float((top.get("priceChange") or {}).get("h1") or 0),
  "c24":float((top.get("priceChange") or {}).get("h24") or 0),
  "pairs":len(pairs),
 }

def rug():
 r=jget("https://api.rugcheck.xyz/v1/tokens/"+MINT+"/report")
 graph,ge=safe(lambda:jget("https://api.rugcheck.xyz/v1/tokens/"+MINT+"/insiders/graph"),{})
 tok=r.get("token") or {}
 dec=int(tok.get("decimals") or 0)
 supply=float(tok.get("supply") or 0)/(10**dec)
 hs=r.get("topHolders") or []
 markets=[]
 for m in (r.get("markets") or []):
  lp=m.get("lp") or {}
  markets.append({"pubkey":m.get("pubkey"),"type":m.get("marketType"),"locked_pct":lp.get("lpLockedPct"),"locked_usd":lp.get("lpLockedUSD"),"base_usd":lp.get("baseUSD"),"quote_usd":lp.get("quoteUSD")})
 return {
  "creator":r.get("creator"),"creator_balance":r.get("creatorBalance"),
  "mint_authority":tok.get("mintAuthority"),"freeze_authority":tok.get("freezeAuthority"),
  "supply":supply,"burned":max(0,INITIAL_SUPPLY-supply),
  "mutable":(r.get("tokenMeta") or {}).get("mutable"),
  "update_authority":(r.get("tokenMeta") or {}).get("updateAuthority"),
  "graph_insiders":r.get("graphInsidersDetected"),
  "insider_networks":r.get("insiderNetworks"),
  "graph_hash":sha(json.dumps(graph,sort_keys=True)) if graph else None,
  "graph_error":ge,
  "top10":sum(float(h.get("pct") or 0) for h in hs[:10]),
  "top20":[{"owner":h.get("owner"),"pct":h.get("pct"),"amount":h.get("uiAmount"),"insider":h.get("insider")} for h in hs[:20]],
  "risks":r.get("risks") or [],
  "liq":r.get("totalMarketLiquidity"),
  "markets":markets[:20],
 }

def supply_rpc():
 r=rpc("getTokenSupply",[MINT,{"commitment":"finalized"}]) or {}
 v=r.get("value") or {}
 return {"supply":float(v.get("uiAmountString") or v.get("uiAmount") or 0),"decimals":v.get("decimals")}

def sigs(addr,n=15):
 return rpc("getSignaturesForAddress",[addr,{"limit":n,"commitment":"finalized"}]) or []

def balance(addr):
 r=rpc("getBalance",[addr,{"commitment":"finalized"}]) or {}
 return float(r.get("value") or 0)/1e9

def activity(addr):
 ss=sigs(addr,10)
 return {"sol":balance(addr),"latest":ss[0].get("signature") if ss else None,"time":ss[0].get("blockTime") if ss else None}

def creator_funded():
 out={}
 for s in sigs(CREATOR,35)[:20]:
  sg=s.get("signature")
  if not sg:continue
  tx,e=safe(lambda sg=sg:rpc("getTransaction",[sg,{"encoding":"jsonParsed","maxSupportedTransactionVersion":0,"commitment":"finalized"}]))
  if e or not tx:continue
  msg=((tx.get("transaction") or {}).get("message") or {})
  for ix in msg.get("instructions") or []:
   p=ix.get("parsed") if isinstance(ix,dict) else None
   if not isinstance(p,dict) or p.get("type")!="transfer":continue
   inf=p.get("info") or {}
   if inf.get("source")!=CREATOR or inf.get("lamports") is None:continue
   d=inf.get("destination")
   if not d:continue
   z=out.setdefault(d,{"sol":0.0,"count":0,"hooked":0.0})
   z["sol"]+=float(inf["lamports"])/1e9;z["count"]+=1
 for owner,z in out.items():
  x,e=safe(lambda owner=owner:rpc("getTokenAccountsByOwner",[owner,{"mint":MINT},{"encoding":"jsonParsed","commitment":"finalized"}]),{})
  total=0.0
  if isinstance(x,dict):
   for v in x.get("value") or []:
    try:total+=float(v["account"]["data"]["parsed"]["info"]["tokenAmount"].get("uiAmountString") or 0)
    except Exception:pass
  z["hooked"]=total
 return out

def burns(addr):
 found=[]
 ss=sigs(addr,12)
 for s in ss:
  sg=s.get("signature")
  if not sg:continue
  tx,e=safe(lambda sg=sg:rpc("getTransaction",[sg,{"encoding":"jsonParsed","maxSupportedTransactionVersion":0,"commitment":"finalized"}]))
  if e or not tx:continue
  amount=0.0
  msg=((tx.get("transaction") or {}).get("message") or {})
  for ix in msg.get("instructions") or []:
   p=ix.get("parsed") if isinstance(ix,dict) else None
   if not isinstance(p,dict) or p.get("type") not in ("burn","burnChecked"):continue
   inf=p.get("info") or {}
   if inf.get("mint")!=MINT:continue
   ta=inf.get("tokenAmount") or {}
   val=ta.get("uiAmountString") or ta.get("uiAmount") or 0
   try:amount+=float(val)
   except Exception:pass
  if amount:found.append({"sig":sg,"amount":amount,"time":tx.get("blockTime")})
 return found

def site():
 h=tget(SITE);l=tget(LAUNCHES);p=clean(l)
 cnt=len(re.findall(r"\bLaunched\s+\d{1,2}\s+\w+\s+20\d{2}\b",p,re.I))
 if not cnt:cnt=p.count(" Market cap ")
 addrs=sorted(set(re.findall(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b",h+"\n"+l)))
 return {"home_hash":sha(clean(h)),"launch_hash":sha(p),"launch_count":cnt,"addresses":addrs[:100]}

def xstate():
 urls=["https://syndication.twitter.com/srv/timeline-profile/screen-name/"+X_HANDLE,"https://r.jina.ai/https://x.com/"+X_HANDLE]
 err=None
 for u in urls:
  try:
   t=tget(u);p=clean(t)
   ids=re.findall(r"(?:status/|status%2F)(\d{12,24})",t)
   addrs=sorted(set(re.findall(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b",t)))
   return {"source":u,"hash":sha(p),"ids":ids[:20],"addresses":addrs[:50],"excerpt":p[:700],"error":None}
  except Exception as e:err=type(e).__name__+": "+str(e)
 return {"source":None,"hash":None,"ids":[],"addresses":[],"excerpt":"","error":err}

def program(pid):
 r=rpc("getAccountInfo",[pid,{"encoding":"base64","commitment":"finalized"}]) or {}
 v=r.get("value")
 if not v:return {"exists":False}
 ss=sigs(pid,4)
 return {"exists":True,"exec":bool(v.get("executable")),"owner":v.get("owner"),"data_hash":sha(json.dumps(v.get("data"),sort_keys=True)),"latest":ss[0].get("signature") if ss else None,"time":ss[0].get("blockTime") if ss else None}

def collect():
 d={"checked_at":now(),"mint":MINT,"errors":{}}
 jobs={
  "dex":dex,"rug":rug,"supply_rpc":supply_rpc,
  "creator":lambda:activity(CREATOR),"flywheel":lambda:activity(FLYWHEEL),"upgrade":lambda:activity(UPGRADE),
  "creator_funded":creator_funded,"flywheel_burns":lambda:burns(FLYWHEEL),"creator_burns":lambda:burns(CREATOR),
  "site":site,"x":xstate
 }
 for k,fn in jobs.items():
  v,e=safe(fn,{})
  d[k]=v
  if e:d["errors"][k]=e
 progs=dict(PROGRAMS)
 surfaced=set((d.get("site") or {}).get("addresses") or [])|set((d.get("x") or {}).get("addresses") or [])
 for a in (MINT,CREATOR,FLYWHEEL,UPGRADE):surfaced.discard(a)
 for i,a in enumerate(sorted(surfaced)[:10]):progs["surfaced_"+str(i+1)]=a
 d["programs"]={}
 for n,pid in progs.items():
  v,e=safe(lambda pid=pid:program(pid),{})
  d["programs"][n]={"address":pid,**(v or {})}
  if e:d["errors"]["program:"+n]=e
 return d

def event(out,sev,key,title,detail,action):
 out.append({"severity":sev,"key":key,"title":title,"detail":detail,"action":action})

def risks(x):
 return {str(r.get("name") or r.get("description") or r) for r in (x or [])}

def evaluate(prev,cur):
 out=[];d=cur.get("dex") or {};od=prev.get("dex") or {}
 mc=float(d.get("mc") or 0);omc=float(od.get("mc") or 0)
 if mc and omc:
  c=pct(omc,mc)
  if abs(c)>=15:event(out,"HIGH" if abs(c)>=25 else "MEDIUM","mc_move","Market cap moved "+format(c,"+.1f")+"%",format(omc,",.0f")+" USD -> "+format(mc,",.0f")+" USD","REVIEW PROFIT / RISK")
 li=float(d.get("liq") or 0);oli=float(od.get("liq") or 0)
 if li and oli:
  c=pct(oli,li)
  if c<=-15:event(out,"CRITICAL" if c<=-30 else "HIGH","liq_drop","Liquidity dropped "+format(c,".1f")+"%",format(oli,",.0f")+" USD -> "+format(li,",.0f")+" USD","REDUCE RISK / VERIFY LP")

 r=cur.get("rug") or {};o=prev.get("rug") or {}
 s=float(r.get("supply") or (cur.get("supply_rpc") or {}).get("supply") or 0)
 osup=float(o.get("supply") or (prev.get("supply_rpc") or {}).get("supply") or 0)
 if s and osup and osup-s>=100000:
  delta=osup-s
  event(out,"HIGH" if delta>=1000000 else "MEDIUM","burn","Supply fell by "+format(delta,",.0f")+" HOOKED","Current supply "+format(s,",.0f")+"; cumulative burn ~"+format(INITIAL_SUPPLY-s,",.0f"),"THESIS STRENGTHENED")
 for f,label in (("mint_authority","Mint authority"),("freeze_authority","Freeze authority")):
  if prev and o.get(f) is None and r.get(f):
   event(out,"CRITICAL",f+"_active",label+" became active",str(r.get(f)),"EXIT / VERIFY IMMEDIATELY")
 if o.get("update_authority") and r.get("update_authority")!=o.get("update_authority"):
  event(out,"HIGH","metadata_auth","Metadata authority changed",str(o.get("update_authority"))+" -> "+str(r.get("update_authority")),"REVIEW RISK")
 if o.get("graph_insiders") is not None and r.get("graph_insiders") is not None and int(r.get("graph_insiders"))>int(o.get("graph_insiders")):
  event(out,"HIGH","insider_growth","Insider graph expanded",str(o.get("graph_insiders"))+" -> "+str(r.get("graph_insiders")),"REVIEW LINKED WALLETS")
 nr=risks(r.get("risks"))-risks(o.get("risks"))
 if prev and nr:event(out,"HIGH","new_risk","New RugCheck risk flag","; ".join(sorted(nr)),"DO NOT ADD UNTIL VERIFIED")

 of=prev.get("creator_funded") or {};nf=cur.get("creator_funded") or {}
 for w,z in nf.items():
  if w not in of:event(out,"MEDIUM","funded:"+w,"New creator-funded wallet",w+" funded with "+format(z.get("sol",0),".5f")+" SOL; holds "+format(z.get("hooked",0),",.0f")+" HOOKED","INVESTIGATE")
  elif float(z.get("hooked") or 0)>=1000000 and float((of.get(w) or {}).get("hooked") or 0)<1000000:
   event(out,"HIGH","linked_holder:"+w,"Creator-funded wallet crossed 1M HOOKED",w+" holds "+format(z.get("hooked",0),",.0f"),"REVIEW INSIDER RISK")

 for k,label in (("creator","Creator/deployer"),("upgrade","Upgrade authority")):
  old=(prev.get(k) or {}).get("latest");new=(cur.get(k) or {}).get("latest")
  if old and new and old!=new:event(out,"HIGH",k+"_activity",label+" wallet has new activity","Latest tx "+new,"REVIEW TRANSACTION")

 oldburn={x.get("sig") for x in (prev.get("flywheel_burns") or [])}
 for b in cur.get("flywheel_burns") or []:
  if b.get("sig") not in oldburn and float(b.get("amount") or 0)>=50000:
   event(out,"MEDIUM","burn:"+str(b.get("sig")),"New flywheel burn",format(float(b.get("amount") or 0),",.0f")+" HOOKED burned","THESIS STRENGTHENED")

 sc=(cur.get("site") or {}).get("launch_count");osc=(prev.get("site") or {}).get("launch_count")
 if isinstance(sc,int) and isinstance(osc,int) and sc>osc:
  n=sc-osc;event(out,"MEDIUM" if n>=3 else "INFO","launches","New Hooked launches",str(osc)+" -> "+str(sc),"USAGE SIGNAL")

 for name,p in (cur.get("programs") or {}).items():
  op=(prev.get("programs") or {}).get(name) or {}
  if not op and p.get("exists") and p.get("exec"):event(out,"MEDIUM","newprog:"+p.get("address",""),"New executable related program",name+" "+p.get("address",""),"REVIEW DEPLOYMENT")
  elif op.get("data_hash") and p.get("data_hash") and op.get("data_hash")!=p.get("data_hash"):
   event(out,"HIGH","progchg:"+p.get("address",""),"Program account data changed",name+" "+p.get("address",""),"REVIEW UPGRADE")

 xx=cur.get("x") or {};ox=prev.get("x") or {}
 if xx.get("ids") and ox.get("ids"):
  fresh=[i for i in xx["ids"] if i not in set(ox["ids"])]
  if fresh:event(out,"MEDIUM","x_posts","New official X post detected",", ".join(fresh[:5]),"REVIEW ANNOUNCEMENT")
 return out

def report(cur,ev):
 d=cur.get("dex") or {};r=cur.get("rug") or {};s=float(r.get("supply") or (cur.get("supply_rpc") or {}).get("supply") or 0);mc=float(d.get("mc") or 0)
 rel=pct(ENTRY_MC,mc) if mc else None;value=POSITION_USD*(mc/ENTRY_MC) if mc else None
 L=["# HOOKED Watch - Latest","","Checked: **"+str(cur.get("checked_at"))+"**","",
 "## Position","- Entry reference: **1,000 USD at ~950,000 USD MC**","- Current MC: **"+format(mc,",.0f")+" USD**",
 "- MC vs entry: **"+(format(rel,"+.1f")+"%" if rel is not None else "n/a")+"**",
 "- Rough value if token amount unchanged: **"+(format(value,",.0f")+" USD" if value else "n/a")+"**","",
 "## Market","- Price: **"+format(float(d.get("price") or 0),".8f")+" USD**","- Liquidity: **"+format(float(d.get("liq") or 0),",.0f")+" USD**",
 "- 24h volume: **"+format(float(d.get("vol24") or 0),",.0f")+" USD**","- Top pair 1h buys/sells: **"+str(d.get("b1",0))+" / "+str(d.get("s1",0))+"**","",
 "## Token / security","- Supply: **"+format(s,",.0f")+" HOOKED**","- Burned from 1B ref: **"+format(max(0,INITIAL_SUPPLY-s),",.0f")+" HOOKED**",
 "- Mint authority: **"+str(r.get("mint_authority"))+"**","- Freeze authority: **"+str(r.get("freeze_authority"))+"**",
 "- Creator direct balance: **"+str(r.get("creator_balance"))+"**","- RugCheck graph insiders: **"+str(r.get("graph_insiders"))+"**","",
 "## Product","- Launches detected: **"+str((cur.get("site") or {}).get("launch_count","?"))+"**","",
 "## Alerts this run"]
 if ev:
  for e in ev:L.append("- **["+e["severity"]+"] "+e["title"]+"** - "+e["detail"]+" - Action: **"+e["action"]+"**")
 else:L.append("- No material new thesis event.")
 if cur.get("errors"):
  L+=["","## Source errors"]+["- "+k+": "+v for k,v in cur["errors"].items()]
 L+=["","_Monitor only. No automatic trading._",""]
 return "\n".join(L)

def issue(ev,cur):
 if not ev:return None
 tok=os.getenv("GITHUB_TOKEN");repo=os.getenv("GITHUB_REPOSITORY")
 if not tok or not repo:return {"error":"missing GitHub context"}
 rank={"INFO":0,"MEDIUM":1,"HIGH":2,"CRITICAL":3};top=max(ev,key=lambda e:rank.get(e["severity"],0))
 title="[HOOKED "+top["severity"]+"] "+top["title"]
 body=["Automated HOOKED alert at **"+str(cur.get("checked_at"))+"**.","","Token: `"+MINT+"`","Entry reference: **1,000 USD near 950k MC**",""]
 for e in ev:body+=["### ["+e["severity"]+"] "+e["title"],e["detail"],"","**Action view:** "+e["action"],""]
 payload=json.dumps({"title":title[:250],"body":"\n".join(body)}).encode()
 try:
  out=json.loads(request("https://api.github.com/repos/"+repo+"/issues","POST",payload,{"Authorization":"Bearer "+tok,"Accept":"application/vnd.github+json","Content-Type":"application/json","X-GitHub-Api-Version":"2022-11-28"}))
  return {"number":out.get("number"),"url":out.get("html_url")}
 except Exception as e:return {"error":type(e).__name__+": "+str(e)}

def main():
 prev=load();cur=collect();ev=evaluate(prev,cur) if prev else []
 cur["events_this_run"]=ev;cur["baseline_initialized"]=not bool(prev)
 REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(report(cur,ev))
 cur["issue_created"]=issue(ev,cur) if prev else None
 save(STATE,cur);save(ALERT,{"checked_at":cur["checked_at"],"events":ev,"issue":cur["issue_created"]})
 print(json.dumps({"events":ev,"errors":cur.get("errors"),"issue":cur.get("issue_created")},indent=2))
 return 0

if __name__=="__main__":raise SystemExit(main())
