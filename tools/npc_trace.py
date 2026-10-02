#!/usr/bin/env python3
import json, os, time, urllib.request, urllib.error, datetime, sys
from collections import defaultdict

TARGET = "HhmZp65YmWSddyumkFcHDzaykYKCDeLMTSwJqnw9sbtH"
MINT = "7GUnr7krtQhJwd6ASY2VUprd9t4c64zcgCsjdmZepump"
TOKEN_ACCOUNT = "oQJpC9tRecH2Yn7sNF4REeK6xtNEzftLxTPpD2eAK6F"
DECIMALS = 6
START_TS = int(datetime.datetime(2026,9,23,tzinfo=datetime.timezone.utc).timestamp())

urls = []
secret = os.getenv("SOLANA_RPC_URL","").strip()
if secret:
    urls.append(secret)
urls += [
    "https://solana-rpc.publicnode.com",
    "https://api.mainnet-beta.solana.com",
    "https://solana.drpc.org",
    "https://rpc.ankr.com/solana",
]
# dedup while preserving order
RPC_URLS=[]
for u in urls:
    if u and u not in RPC_URLS: RPC_URLS.append(u)

rid=0
def rpc(method, params, tries=10):
    global rid
    last=None
    for attempt in range(tries):
        u=RPC_URLS[(rid+attempt)%len(RPC_URLS)]
        rid += 1
        body=json.dumps({"jsonrpc":"2.0","id":rid,"method":method,"params":params}).encode()
        req=urllib.request.Request(u,data=body,headers={"content-type":"application/json","user-agent":"npc-trace/1.0"})
        try:
            with urllib.request.urlopen(req,timeout=35) as r:
                data=json.loads(r.read().decode())
            if "error" in data:
                last=f"{u}: {data['error']}"
                time.sleep(min(2+attempt,8)); continue
            return data.get("result")
        except Exception as e:
            last=f"{u}: {e}"
            time.sleep(min(2+attempt,8))
    raise RuntimeError(f"RPC failed {method}: {last}")

def sigs_for(addr, stop_ts=START_TS, max_pages=20):
    out=[]; before=None
    for _ in range(max_pages):
        cfg={"limit":1000}
        if before: cfg["before"]=before
        batch=rpc("getSignaturesForAddress",[addr,cfg])
        if not batch: break
        out.extend(batch)
        # stop once oldest is before start
        times=[x.get("blockTime") for x in batch if x.get("blockTime")]
        if times and min(times) < stop_ts: break
        if len(batch)<1000: break
        before=batch[-1]["signature"]
        time.sleep(.15)
    # keep slightly older records too for wallet funding; caller can filter
    return out

def get_tx(sig):
    return rpc("getTransaction",[sig,{"encoding":"jsonParsed","maxSupportedTransactionVersion":0,"commitment":"confirmed"}])

def account_keys(tx):
    ks=tx["transaction"]["message"].get("accountKeys",[])
    arr=[]
    for k in ks:
        if isinstance(k,str): arr.append({"pubkey":k,"signer":False})
        else: arr.append(k)
    # Loaded addresses are reflected in token balance accountIndex but not always in jsonParsed accountKeys.
    meta=tx.get("meta") or {}
    loaded=meta.get("loadedAddresses") or {}
    for k in loaded.get("writable",[]) + loaded.get("readonly",[]):
        arr.append({"pubkey":k,"signer":False})
    return arr

def token_owner_deltas(tx, mint=MINT):
    meta=tx.get("meta") or {}
    pre={}; post={}
    for b in meta.get("preTokenBalances") or []:
        if b.get("mint")==mint:
            pre[b["accountIndex"]]={"owner":b.get("owner"),"amount":int(b["uiTokenAmount"]["amount"])}
    for b in meta.get("postTokenBalances") or []:
        if b.get("mint")==mint:
            post[b["accountIndex"]]={"owner":b.get("owner"),"amount":int(b["uiTokenAmount"]["amount"])}
    idxs=set(pre)|set(post)
    by_owner=defaultdict(int)
    by_idx=[]
    for i in idxs:
        a0=pre.get(i,{}).get("amount",0); a1=post.get(i,{}).get("amount",0)
        owner=post.get(i,{}).get("owner") or pre.get(i,{}).get("owner")
        d=a1-a0
        if d:
            by_owner[owner]+=d
            by_idx.append({"accountIndex":i,"owner":owner,"deltaRaw":d})
    return dict(by_owner),by_idx

def programs(tx):
    ps=set()
    msg=tx["transaction"]["message"]
    def walk(ins):
        for x in ins or []:
            if isinstance(x,dict):
                if x.get("programId"): ps.add(x["programId"])
                elif x.get("program"): ps.add(x["program"])
    walk(msg.get("instructions"))
    for g in (tx.get("meta") or {}).get("innerInstructions") or []: walk(g.get("instructions"))
    return sorted(ps)

def system_transfers(tx):
    out=[]
    groups=[tx["transaction"]["message"].get("instructions") or []]
    groups += [g.get("instructions") or [] for g in (tx.get("meta") or {}).get("innerInstructions") or []]
    for grp in groups:
        for ins in grp:
            if not isinstance(ins,dict): continue
            p=ins.get("parsed")
            if not isinstance(p,dict): continue
            if p.get("type")=="transfer":
                info=p.get("info") or {}
                if "lamports" in info and info.get("source") and info.get("destination"):
                    out.append({"source":info["source"],"destination":info["destination"],"lamports":int(info["lamports"])})
    return out

def iso(ts):
    return datetime.datetime.fromtimestamp(ts,datetime.timezone.utc).isoformat() if ts else None

def tx_record(siginfo, tx):
    keys=account_keys(tx)
    owner_deltas, idx_deltas=token_owner_deltas(tx)
    td=owner_deltas.get(TARGET,0)
    signers=[k["pubkey"] for k in keys if k.get("signer")]
    prebal=(tx.get("meta") or {}).get("preBalances") or []
    postbal=(tx.get("meta") or {}).get("postBalances") or []
    sol_delta=None
    for i,k in enumerate(keys[:len(prebal)]):
        if k["pubkey"]==TARGET:
            sol_delta=postbal[i]-prebal[i]
            break
    others={o:d for o,d in owner_deltas.items() if o and o!=TARGET and d}
    return {
        "signature":siginfo["signature"],
        "blockTime":siginfo.get("blockTime"),
        "time":iso(siginfo.get("blockTime")),
        "targetNpcDeltaRaw":td,
        "targetNpcDelta":td/(10**DECIMALS),
        "counterpartyOwnerDeltas":{o:d/(10**DECIMALS) for o,d in others.items()},
        "targetSigned":TARGET in signers,
        "signers":signers,
        "targetSolDelta": None if sol_delta is None else sol_delta/1e9,
        "programs":programs(tx),
        "systemTransfers":[{**x,"sol":x["lamports"]/1e9} for x in system_transfers(tx)],
        "fee":(tx.get("meta") or {}).get("fee"),
        "err":(tx.get("meta") or {}).get("err"),
    }

print("Collecting token-account signatures...", flush=True)
tsigs=sigs_for(TOKEN_ACCOUNT, START_TS, max_pages=10)
# de-dupe, filter from start
uniq={x["signature"]:x for x in tsigs if (x.get("blockTime") or 0)>=START_TS}
print("token sigs",len(uniq), flush=True)

records=[]
for i,s in enumerate(sorted(uniq.values(),key=lambda x:x.get("blockTime") or 0)):
    try:
        tx=get_tx(s["signature"])
        if not tx: continue
        rec=tx_record(s,tx)
        if rec["targetNpcDeltaRaw"]!=0:
            records.append(rec)
    except Exception as e:
        records.append({"signature":s["signature"],"blockTime":s.get("blockTime"),"time":iso(s.get("blockTime")),"error":str(e)})
    if i%10==0: print("tx",i,"of",len(uniq), flush=True)
    time.sleep(.12)

# wallet signatures for SOL funding and potentially NPC tx not captured on ATA
print("Collecting wallet signatures...", flush=True)
wsigs=sigs_for(TARGET, START_TS-7*86400, max_pages=10)
wallet_records=[]
for i,s in enumerate(sorted({x["signature"]:x for x in wsigs}.values(),key=lambda x:x.get("blockTime") or 0)):
    try:
        tx=get_tx(s["signature"])
        if not tx: continue
        st=system_transfers(tx)
        hit=[x for x in st if x["source"]==TARGET or x["destination"]==TARGET]
        if hit:
            keys=account_keys(tx)
            wallet_records.append({
              "signature":s["signature"],"blockTime":s.get("blockTime"),"time":iso(s.get("blockTime")),
              "systemTransfers":[{**x,"sol":x["lamports"]/1e9} for x in hit],
              "signers":[k["pubkey"] for k in keys if k.get("signer")],
              "programs":programs(tx)
            })
    except Exception as e:
        pass
    time.sleep(.08)

# Aggregate direct NPC counterparties
inbound=defaultdict(float); outbound=defaultdict(float)
for r in records:
    if "targetNpcDelta" not in r: continue
    d=r["targetNpcDelta"]
    cps=r.get("counterpartyOwnerDeltas") or {}
    if d>0:
        for o,v in cps.items():
            if v<0: inbound[o]+=(-v)
    elif d<0:
        for o,v in cps.items():
            if v>0: outbound[o]+=v

# Classify likely mode
for r in records:
    if "targetNpcDelta" not in r: continue
    d=r["targetNpcDelta"]
    if d>0:
        r["direction"]="IN"
        r["classification"]="likely_buy_or_self_initiated_inbound" if r.get("targetSigned") else "direct_inbound_or_airdrop"
    elif d<0:
        r["direction"]="OUT"
        r["classification"]="self_initiated_outbound_or_sell" if r.get("targetSigned") else "authority_or_program_outbound"
    else: r["direction"]="ZERO"

# earliest native SOL funding into target
funding=[]
for r in wallet_records:
    for x in r["systemTransfers"]:
        if x["destination"]==TARGET and x["source"]!=TARGET:
            funding.append({"time":r["time"],"signature":r["signature"],"source":x["source"],"sol":x["sol"],"targetSigned":TARGET in r["signers"]})
funding.sort(key=lambda x:x["time"] or "")

summary={
 "target":TARGET,
 "mint":MINT,
 "tokenAccount":TOKEN_ACCOUNT,
 "generatedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "tokenTransferCount":len([r for r in records if "targetNpcDelta" in r]),
 "inboundTotalNpc":sum(max(0,r.get("targetNpcDelta",0)) for r in records),
 "outboundTotalNpc":sum(max(0,-r.get("targetNpcDelta",0)) for r in records),
 "currentDerivedNpc":sum(r.get("targetNpcDelta",0) for r in records),
 "directInboundCounterparties":[{"owner":o,"npc":v} for o,v in sorted(inbound.items(), key=lambda kv:-kv[1])],
 "directOutboundCounterparties":[{"owner":o,"npc":v} for o,v in sorted(outbound.items(), key=lambda kv:-kv[1])],
 "firstNativeFunding":funding[:20],
 "npcTransactions":records,
 "nativeTransferTransactions":wallet_records,
}

os.makedirs("trace",exist_ok=True)
with open("trace/npc_hhmz_trace.json","w") as f: json.dump(summary,f,indent=2)

# compact markdown
lines=[]
lines.append("# NPC whale trace")
lines.append("")
lines.append(f"- Target: `{TARGET}`")
lines.append(f"- NPC mint: `{MINT}`")
lines.append(f"- Token account: `{TOKEN_ACCOUNT}`")
lines.append(f"- Generated: {summary['generatedAt']}")
lines.append(f"- NPC transfer txs found: {summary['tokenTransferCount']}")
lines.append(f"- Total inbound: {summary['inboundTotalNpc']:,.6f} NPC")
lines.append(f"- Total outbound: {summary['outboundTotalNpc']:,.6f} NPC")
lines.append(f"- Net from traced txs: {summary['currentDerivedNpc']:,.6f} NPC")
lines.append("")
lines.append("## Direct inbound counterparties")
for x in summary["directInboundCounterparties"]:
    lines.append(f"- `{x['owner']}`: {x['npc']:,.6f} NPC")
lines.append("")
lines.append("## Direct outbound counterparties")
for x in summary["directOutboundCounterparties"]:
    lines.append(f"- `{x['owner']}`: {x['npc']:,.6f} NPC")
lines.append("")
lines.append("## First native SOL funding")
for x in summary["firstNativeFunding"][:10]:
    lines.append(f"- {x['time']} — {x['sol']:.9f} SOL from `{x['source']}` — tx `{x['signature']}`")
lines.append("")
lines.append("## NPC transactions")
for r in records:
    if "targetNpcDelta" not in r: 
        lines.append(f"- {r.get('time')} ERROR {r.get('signature')}: {r.get('error')}")
        continue
    cps=", ".join([f"{o} ({v:+,.6f})" for o,v in (r.get("counterpartyOwnerDeltas") or {}).items()])
    lines.append(f"- {r['time']} {r['direction']} {r['targetNpcDelta']:+,.6f} NPC; signed={r['targetSigned']}; SOLΔ={r.get('targetSolDelta')}; cps={cps}; tx=`{r['signature']}`")
with open("trace/npc_hhmz_trace.md","w") as f: f.write("\n".join(lines)+"\n")
print(json.dumps({"summary":{k:v for k,v in summary.items() if k not in ("npcTransactions","nativeTransferTransactions")}},indent=2))
