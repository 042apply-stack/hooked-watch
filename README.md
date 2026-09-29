# HOOKED Watch

Automated GitHub-only monitor for the Solana token **HOOKED**.

- Token: `C1mBfBoDkwWfd6uTFZp62ARHLjeVp3bDpCDMfMZtPngE`
- Position reference: **$1,000 entered around $950,000 market cap**
- Official site: https://www.hookedpad.com/
- Official X: https://x.com/Hoookedpad

The monitor is designed to watch the **investment thesis**, not just the chart.

## What it watches

- price, market cap, liquidity and volume
- market-cap movement relative to the $950k entry
- total token supply and continuing burns
- mint/freeze authority and metadata changes
- holder concentration and RugCheck insider graph changes
- creator/deployer activity
- wallets directly funded by the creator and their HOOKED balances
- flywheel wallet activity and on-chain burn instructions
- liquidity pools and LP-lock/control changes
- Hooked launchpad activity and launch-count changes
- Hooked website/docs changes
- best-effort monitoring of the official X timeline
- deployed transfer-hook programs and program-code changes
- upgrade-authority wallet activity
- source/API failures that could blind the monitor

## Alerts

Material events open GitHub Issues with severity:

- **CRITICAL** — thesis/security break, authority risk, large LP/liquidity event
- **HIGH** — major whale/creator activity, sharp market move, program upgrade, large supply event
- **MEDIUM** — meaningful burn, launchpad/product activity, concentration change
- **INFO** — notable but non-urgent change

No trade is executed. Action text is deliberately framed as portfolio review guidance such as HOLD / DO NOT ADD / REVIEW RISK / REVIEW PROFIT rather than automatic trading.

## Schedule

GitHub Actions runs every **15 minutes** (GitHub cron can occasionally be delayed).

State is saved under `state/latest.json` so old events are not repeatedly alerted.

Latest human-readable snapshot is written to `reports/latest.md`.

## Data sources

The watcher uses public endpoints only:

- DexScreener
- RugCheck
- Solana JSON-RPC
- hookedpad.com
- X public/syndication pages on a best-effort basis

No wallet private key or trading key is required.

## Safety

This repository never needs a seed phrase, wallet private key, or trading authority. Do not add those to GitHub Secrets or commit them.


## Optional secrets

The monitor works without private wallet keys.

For more reliable X monitoring, add this repository secret:

- `X_BEARER_TOKEN` — official X API bearer token. If absent, the monitor falls back to public profile endpoints, which X may rate-limit or block.

Optional Solana RPC override:

- `SOLANA_RPC_URL` — a preferred Solana RPC endpoint. If absent, the monitor uses public RPC fallbacks.

Never store wallet seed phrases or trading private keys in this repository.
