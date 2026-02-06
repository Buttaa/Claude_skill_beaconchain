# Claude skill for beaconcha.in

A Claude skill for querying the [beaconcha.in](https://beaconcha.in) API to look up Ethereum validators, analyze staking rewards, explore blocks and epochs, and monitor network health.

## What it does

Give Claude natural-language requests about Ethereum staking and it will know which beaconcha.in API endpoints to call, how to interpret the responses, and how to present the results. Examples:

- "How is my validator 482903 doing?"
- "What did I earn this week?"
- "What happened to my validator yesterday at 6pm?"
- "Show me just the CL rewards for the last 30 days"
- "I need my staking income for 2025 tax reporting"
- "Is the Ethereum network healthy right now?"
- "How long until my validator activates?"
- "Where am I losing rewards?"

## Setup

1. Get a beaconcha.in API key (free tier available): https://beaconcha.in/user/api-key-management
2. Upload the skill to Claude via **Settings → Capabilities → Skills**
3. Connect a beaconcha.in MCP server, or provide your API key when Claude asks for it

## Structure

```
beaconchain-explorer/
├── SKILL.md                          # 17 workflows, trigger phrases, error handling
├── README.md
├── references/
│   └── api-guide.md                  # Full V1+V2 endpoint reference, auth, rate limits
└── scripts/
    ├── format_validators.py          # Validator status → report with emoji indicators
    ├── format_rewards.py             # Rewards → ETH conversion, efficiency, CL/EL split
    ├── format_beaconscore.py         # BeaconScore → threshold indicators, component tree
    ├── format_balances.py            # Balance history → trend analysis, anomaly detection
    ├── format_network.py             # Network metrics → health indicators, queue estimates
    ├── format_aggregate.py           # Rolling period comparison (24h/7d/30d/90d)
    ├── format_tax_export.py          # Tax-ready table with CSV export, timezone support
    ├── format_queues.py              # Queue status → wait estimates, planning advice
    ├── calc_apr.py                   # APR/APY calculation with CL/EL breakdown
    ├── epoch_converter.py            # Epoch ↔ timestamp ↔ slot conversion
    └── analyze_missed.py             # Missed rewards breakdown by duty type
```

## Workflows

| #  | Workflow | What it covers |
|----|---------|----------------|
| 1  | Validator Lookup & Status | Current status, balance, lifecycle for one or many validators |
| 2  | Staking Rewards & Income | Per-epoch reward breakdown (CL + EL), with CL-only and EL-only filtering |
| 3  | BeaconScore | Validator efficiency metric with component breakdown |
| 4  | Balance History | Historical balance snapshots with trend and anomaly analysis |
| 5  | Block / Slot / Epoch Exploration | What happened at a specific slot or epoch |
| 6  | Network Overview | Active validators, participation rate, finalization, queues |
| 7  | Dashboard Management | Create/manage validator dashboards via API |
| 8  | Rewards Aggregate | Pre-computed summaries for 24h, 7d, 30d, 90d rolling windows |
| 9  | Custom Date Range | Rewards for arbitrary date ranges via epoch conversion |
| 10 | Tax Year Calculations | Per-epoch rewards with timestamps, CSV export for tax prep |
| 11 | Dashboard Private Sets | Query by dashboard group instead of listing individual validators |
| 12 | Epoch & Time Zone Conversion | Epoch ↔ timestamp ↔ slot formulas and converter |
| 13 | Missed Rewards Analysis | Breakdown by duty type (head/source/target/sync/proposal) with diagnostics |
| 14 | APY & ROI Metrics | Annualized return calculation with CL/EL split |
| 15 | Queue Tracking | Activation, exit, withdrawal queues with wait time estimates |
| 16 | Embed BeaconScore | Integration guide with attribution requirements |
| 17 | Incident Investigation | Time-based forensic workflow ("what happened at 6pm?") |

## Rate limits

The beaconcha.in API enforces rate limits by plan. The skill includes guidance on monitoring rate limit headers, handling 429 errors, and estimating API call counts for bulk workflows. See the full breakdown in `SKILL.md` or `references/api-guide.md`.

| Plan | Limit/sec | Limit/month |
|------|-----------|-------------|
| Free | 1 | 1,000 |
| Hobbyist | 1 | — |
| Business | 2 | — |
| Scale | 5 | — |

## API coverage

The skill primarily uses V2 endpoints (POST with JSON body), falling back to V1 (GET) only for slot-level detail and validator attestation/proposal history which don't have V2 equivalents. All reward values are in wei and scripts convert to ETH automatically.

Supported networks: Mainnet, Hoodi (testnet).

## Scripts

All scripts accept piped JSON from API responses and output formatted reports. They require only Python 3 standard library (no pip dependencies).

```bash
# Example: format rewards with CL-only filter
cat rewards_response.json | python scripts/format_rewards.py - --cl-only

# Example: convert a date to epoch
python scripts/epoch_converter.py --date "2025-06-15T18:00:00"

# Example: export rewards for tax reporting as CSV
cat rewards_response.json | python scripts/format_tax_export.py - --timezone UTC+1 --csv rewards.csv
```
