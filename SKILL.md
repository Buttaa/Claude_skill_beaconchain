---
name: beaconchain-explorer
description: Ethereum Beacon Chain explorer workflows using the beaconcha.in API (V1 and V2). Use when the user mentions "validator", "beacon chain", "staking rewards", "attestation", "epoch", "slot", "beaconcha.in", "BeaconScore", "validator efficiency", "staking performance", "consensus layer", "CL rewards", "execution layer rewards", "validator balance", "validator status", "block proposal", "sync committee", "slashing", "validator queue", "activation queue", "exit queue", "withdrawal", "ETH staking", "validator dashboard", "validator monitoring", or asks to look up, monitor, analyze, or report on Ethereum validators or network health. Also use when the user provides a validator index, public key, or withdrawal address and wants data about it. Do NOT use for general Ethereum execution layer queries unrelated to staking or the beacon chain.
---

# Beaconcha.in Explorer Skill

Workflows for querying the beaconcha.in API to look up validators, analyze staking rewards, explore blocks/epochs/slots, and monitor Ethereum network health.

## Prerequisites

- A beaconcha.in MCP server connection OR a valid API key (Bearer token)
- **API key is required for all endpoints.** Free keys at https://beaconcha.in/user/api-key-management
- If a request returns 401, ask the user to verify their API key. If they don't have one, direct them to the URL above.
- Base URL: `https://beaconcha.in` (mainnet), `https://holesky.beaconcha.in` (Holesky), `https://gnosis.beaconcha.in` (Gnosis)
- Auth: V2 header `Authorization: Bearer <API_KEY>`, V1 query param `?apikey=<API_KEY>`
- **Always prefer V2 endpoints over V1.** V1 endpoints are listed as fallbacks only for features not yet available in V2.
- Rate limits by plan:

| Plan | Price (annual billing, ex-VAT) | Limit/sec | Limit/month | Pro 💎 |
|------|-------------------------------|-----------|-------------|--------|
| Free | 0€ | 1 | 1,000 | No |
| Hobbyist | 59€/mo | 1 | — (per-second only) | No |
| Business | 99€/mo | 2 | — (per-second only) | No |
| Scale | 399€/mo | 5 | — (per-second only) | Yes |
| Enterprise | Contact | Custom | Custom | Yes |

**Pro 💎 features** (Scale/Enterprise only): premium validator selectors including `withdrawal` address and `deposit_address`. Other plans can only query by validator index or public key.

**Rate limit buckets:**
- Current plans (Hobbyist/Business/Scale): V1 and V2 share **one combined bucket**.
- Legacy plans (Sapphire/Emerald/Diamond): V1 and V2 use **separate buckets** — V2 gets free-tier limits (1/sec, 1000/month).

**Monitoring rate limits:** Every API response includes `ratelimit-remaining`, `ratelimit-reset`, and `x-ratelimit-remaining-*` headers. Check these before bulk operations.

**Handling 429 errors:** When rate-limited, pause and wait for the duration in the `ratelimit-reset` header before retrying. Implement exponential backoff for repeated 429s.

**Batching:** Use `dashboard_id` to query many validators in one request instead of individual calls — this is the most effective way to stay within limits.

For multi-call workflows (#9 Custom Range, #10 Tax Year), estimate API calls needed and warn the user if it may exceed their plan limits.

## Important Concepts

- **Epoch**: 32 slots (~6.4 minutes). Validators are reshuffled each epoch.
- **Slot**: 12-second window for a block proposal.
- **BeaconScore**: Validator efficiency metric (target ≥99%, exceptional ≥99.5%).
- **Effective balance**: Used for reward/penalty calculations. Max 32 ETH (or 2048 ETH post-Pectra for compounding validators).
- **Finality**: Requires 2/3+ of validators agreeing on two consecutive epochs.
- Rewards are returned in wei (divide by 1e18 for ETH).

## Core Workflows

### 1. Validator Lookup & Status

Fetch current status, balance, and lifecycle info for one or more validators.

**V2 Endpoint:** `POST /api/v2/ethereum/validators`

```json
{
  "validator": {
    "validator_identifiers": [1, 2, 3]
  },
  "chain": "mainnet",
  "page_size": 10
}
```

Identifiers can be: validator index (integer), public key (0x-prefixed), withdrawal address (Pro 💎 Scale/Enterprise only), or deposit address (Pro 💎 Scale/Enterprise only).

**Response fields to highlight:**
- `status`: pending_initialized, pending_queued, active_online, active_offline, exiting_online, exiting_offline, slashing_online, slashing_offline, exited, withdrawal
- `balances.current` / `balances.effective`: Current and effective balance in wei
- `online`: Whether the validator is currently attesting
- `life_cycle_epochs`: activation_eligibility, activation, exit, withdrawable epochs

**When presenting results:** Convert wei to ETH, flag offline validators, note if slashed. If checking many validators, summarize: count by status, total balance, average balance.

### 2. Staking Rewards & Income

Fetch detailed reward breakdowns (CL + EL) per validator per epoch.

**V2 Endpoint:** `POST /api/v2/ethereum/validators/rewards-list`

```json
{
  "validator": {
    "validator_identifiers": [1]
  },
  "chain": "mainnet",
  "page_size": 10,
  "epoch": 347566
}
```

Omit `epoch` to get the most recent rewards.

**Response fields to highlight:**
- `total_reward`: Combined CL+EL rewards in wei
- `total_penalty` and `total_missed`: Penalties and missed opportunity cost
- `attestation`: Breakdown by head/source/target votes with reward, penalty, and missed amounts
- `sync_committee`: Rewards from sync committee participation
- `proposal`: Block proposal rewards including `execution_layer_reward` (tips/MEV) and `attestation_inclusion_reward`
- `finality`: Whether the epoch is finalized

**When presenting results:**
- Convert all values from wei to ETH (÷ 1e18)
- Calculate attestation efficiency: actual_reward / (actual_reward + missed_reward + penalty)
- Highlight any penalties or missed rewards
- For multiple epochs: aggregate totals, compute daily/weekly APR
- **CL-only rewards:** If the user asks for "consensus layer" or "CL" rewards specifically, sum only `attestation.total` + `sync_committee.reward` + `proposal.attestation_inclusion_reward` + `proposal.sync_inclusion_reward`. Exclude `proposal.execution_layer_reward` (that's EL/MEV).
- **EL-only rewards:** If the user asks for "execution layer" or "EL" rewards, use `proposal.execution_layer_reward` only.

### 3. Validator Performance / BeaconScore

**V2 Endpoint:** `POST /api/v2/ethereum/validators/beacon-score`

Use to fetch the BeaconScore (efficiency metric) for validators.

Interpretation:
- ≥99.5%: Exceptional performance
- ≥99.0%: Good, meets target
- <99.0%: Investigate — check for missed attestations, offline periods, or poor inclusion delays

Use `scripts/format_beaconscore.py` to format the response with threshold indicators and component breakdown.

When displaying BeaconScore data publicly, attribution via the official badge is required (see `references/api-guide.md`).

### 4. Validator Balances Over Time

**V2 Endpoint:** `POST /api/v2/ethereum/validators/balance-list`

Fetch historical balance snapshots for trend analysis. Use `scripts/format_balances.py` to format the response with trend indicators and anomaly detection.

**When presenting results:**
- Plot or tabulate balance over time
- Identify balance drops (penalties, slashing) or jumps (proposals, sync committee)
- Calculate net change over period

### 5. Block / Slot / Epoch Exploration

Look up what happened at a specific slot or epoch.

**V2 Endpoint (preferred):** Use `rewards-list` with a specific epoch to see per-validator duty results for that epoch. Combine with `balance-list` to detect balance changes.

**V1 Fallback Endpoints (GET, only if V2 lacks the needed data):**
- `/api/v1/slot/{slot}` — Block details for a specific slot (proposer, attestations, status)
- `/api/v1/epoch/{epoch}` — Epoch summary (participation rate, finalization)
- `/api/v1/epoch/{epoch}/slots` — All slots in an epoch
- `/api/v1/validator/{index}/attestations` — Attestation history for a validator
- `/api/v1/validator/{index}/proposals` — Block proposal history

Add `?apikey=<KEY>` as query parameter for V1 auth.

**When presenting results:**
- Note if slot was proposed, missed, or orphaned
- Show proposer validator index
- For epochs: show participation rate, finalization status, total rewards

### 6. Network Overview

**V2 Endpoint:** `POST /api/v2/ethereum/network`

Fetch network-wide metrics: active validator count, pending queue, participation rate, average balance. Use `scripts/format_network.py` to format the response with health indicators and queue wait estimates.

**V1 Fallback Endpoints (only if V2 network endpoint is unavailable):**
- `/api/v1/epoch/latest` — Latest epoch stats
- `/api/v1/validators/queue` — Entry/exit queue lengths

**When presenting results:**
- Show active vs total validators, pending in entry/exit queues
- Note participation rate (healthy ≥99%, concerning <95%)
- If queue is long, estimate wait time: queue_length / validators_per_epoch × 6.4 minutes

### 7. Validator Dashboard Management

For users who manage validator dashboards on beaconcha.in:

**V2 Endpoints:**
- `POST /api/v2/validator-dashboards` — Create a new dashboard
- `POST /api/v2/validator-dashboards/{id}/validators` — Add validators to dashboard
- `DELETE /api/v2/validator-dashboards/{id}/validators` — Remove validators
- `POST /api/v2/validator-dashboards/{id}/validators/bulk-deletions` — Bulk remove

### 8. Rewards Aggregate (Rolling Periods)

Get pre-computed reward summaries for standard rolling windows without iterating epochs.

**V2 Endpoint:** `POST /api/v2/ethereum/validators/rewards-aggregate`

```json
{
  "validator": {
    "validator_identifiers": [1, 2, 3]
  },
  "chain": "mainnet"
}
```

Returns aggregated rewards for rolling periods: 24h, 7d, 30d, 90d. Use this instead of `rewards-list` when the user wants a quick summary like "how much did I earn this week?" Format with `scripts/format_aggregate.py` for multi-period comparison with trend indicators.

**When to use `rewards-aggregate` vs `rewards-list`:**
- Aggregate: Quick summaries for standard periods. Fewer API calls, pre-computed.
- List: Per-epoch granularity needed (tax reporting, custom date ranges, debugging specific epochs).

### 9. Custom Date Range Rewards

When the user needs rewards for a specific date range (not a standard rolling period):

**Step 1:** Convert date range to epoch range using the epoch conversion formulas in `references/api-guide.md`:
```
epoch = floor((unix_timestamp - 1606824023) / 384)
```
Where 1606824023 is the genesis timestamp and 384 = 32 slots × 12 seconds.

**Step 2:** Iterate `rewards-list` with pagination across the epoch range:
```json
{
  "validator": { "validator_identifiers": [1] },
  "chain": "mainnet",
  "epoch_start": 340000,
  "epoch_end": 341575,
  "page_size": 100
}
```

**Step 3:** Aggregate the results using `scripts/format_rewards.py` or custom summation.

**Rate limit awareness:** For large ranges, estimate API calls needed. At 100 epochs per page, a 30-day range (~6,750 epochs) requires ~68 calls. Warn the user about rate limits on free tier.

### 10. Tax Year Calculations

For users preparing tax reports on staking income:

**Step 1:** Determine the tax year epoch range (e.g., Jan 1 – Dec 31 UTC).

**Step 2:** Fetch per-epoch rewards via `rewards-list` with full pagination.

**Step 3:** For each epoch's reward, note the timestamp for fiat conversion:
```
epoch_timestamp = 1606824023 + (epoch × 384)
```

**Step 4:** Use `scripts/format_tax_export.py` to generate a tax-ready table. Supports `--csv output.csv` for spreadsheet export and `--timezone UTC+1` for local time conversion.

**Important:** Advise users that this is raw data — they should consult a tax professional for jurisdiction-specific reporting requirements. Claude should not provide tax advice.

### 11. Dashboard Private Sets

For users who organize validators into groups on beaconcha.in dashboards:

Query rewards or performance by `dashboard_id` and optional `group_id` instead of listing individual validator indices. This is useful for staking providers managing thousands of validators across client groups.

**V2 Endpoints accept dashboard selectors:**
```json
{
  "validator": {
    "dashboard_id": "your-dashboard-id",
    "group_id": 0
  },
  "chain": "mainnet"
}
```

Prerequisite: Dashboard and groups must be created in the beaconcha.in UI first. Requires an active Orca subscription for API dashboard management.

### 12. Epoch & Time Zone Conversion

**Epoch → Unix timestamp:**
```
timestamp = 1606824023 + (epoch × 384)
```

**Unix timestamp → Epoch:**
```
epoch = floor((timestamp - 1606824023) / 384)
```

**Slot → Epoch:**
```
epoch = floor(slot / 32)
```

**Constants:**
- Genesis timestamp: `1606824023` (Dec 1, 2020, 12:00:23 UTC)
- Seconds per slot: `12`
- Slots per epoch: `32`
- Seconds per epoch: `384`

Use `scripts/epoch_converter.py` for conversions. Always present times in the user's local timezone when known, defaulting to UTC.

### 13. Missed Rewards Analysis

Identify where a validator is losing rewards and quantify the cost.

**Step 1:** Fetch `rewards-list` for the period of interest.

**Step 2:** For each epoch, check:
- `attestation.head.missed_reward` — missed head votes (often from high latency)
- `attestation.source.missed_reward` — missed source votes
- `attestation.target.missed_reward` — missed target votes (most costly)
- `sync_committee.missed_reward` — missed sync duties
- `proposal.missed_cl_reward` / `proposal.missed_el_reward` — missed block proposals

**Step 3:** Aggregate missed rewards by duty type. Present a breakdown:
- Total missed vs total earned → "You captured X% of available rewards"
- Which duty type had the most missed rewards
- Identify patterns (e.g., consistently missing target votes → possible attestation timing issue)

**Actionable advice based on patterns:**
- Missed head votes → check network latency, peer count
- Missed target votes → check if node is staying synced
- Missed proposals → check if node was online for assigned slot, MEV relay config
- Missed sync duties → check uptime during sync committee period

### 14. APY & ROI Metrics

**V2 Endpoint:** `POST /api/v2/ethereum/validators/apy-roi`

Returns annualized return metrics with CL/EL breakdown. Use `scripts/calc_apr.py` to calculate APR/APY from rewards data with CL/EL split and extrapolated earnings.

**Manual APR calculation from rewards data:**
```
APR = (RewardsInPeriod / BalanceAtPeriodStart) × (EpochsPerYear / EpochsInPeriod) × 100
```

Where:
- `EpochsPerYear ≈ 82,125` (365.25 days × 225 epochs/day)
- Note: beaconcha.in's dashboard uses ~51,480 for the "All time" 90-day APR display

**When presenting APY/ROI:**
- Distinguish CL rewards (attestation + sync) from EL rewards (proposals/MEV)
- Note that proposal rewards are luck-based and highly variable
- For short periods, warn that APR extrapolation may be misleading
- Compare against network average if available

### 15. Queue Tracking

**V2 Endpoint:** `POST /api/v2/ethereum/queues`

Monitor activation, exit, and withdrawal queues with estimated wait times. Use `scripts/format_queues.py` to format with wait estimates and planning advice.

**V1 Fallback:** `GET /api/v1/validators/queue`

**Key metrics to present:**
- **Activation queue:** Number of validators waiting to enter. Wait time depends on churn limit.
- **Exit queue:** Number of validators waiting to leave. Same churn limit.
- **Withdrawal queue:** Validators waiting for balance sweep.

**Churn limit calculation:**
```
churn_limit = max(4, active_validator_count / 65536)
```

**Estimated wait time:**
```
wait_epochs = queue_length / churn_limit
wait_hours = wait_epochs × 6.4 / 60
```

**When presenting queue data:**
- Show current queue depth for each type
- Calculate estimated wait in human-readable format (hours/days)
- Note if queues are unusually long vs. historical norms
- For users planning to stake: "At current queue depth, activation would take approximately X days"

### 16. Embed BeaconScore

For users integrating BeaconScore into their own products/dashboards:

**Step 1:** Fetch BeaconScore via `POST /api/v2/ethereum/validators/beacon-score`

**Step 2:** Display with required attribution:
- Include the official BeaconScore badge (SVG/PNG from https://docs.beaconcha.in/legal/license-materials)
- Enterprise plan users are exempt from attribution

**BeaconScore components (for context):**
- **Attester efficiency** (84.4% weight): head + source + target vote accuracy
- **Proposer efficiency** (12.5% weight): CL rewards from proposals vs median of surrounding 32 proposals
- **Sync committee efficiency** (3.1% weight): sync participation rate

Target: ≥99% good, ≥99.5% exceptional. Below 99% warrants investigation.

### 17. Validator Incident Investigation

When a user asks "what happened to my validator at [time]?" or "why did my balance drop on [date]?" — a time-based forensic workflow.

**Step 1:** Convert the user's time to an epoch range using `scripts/epoch_converter.py`:
```bash
python scripts/epoch_converter.py --date "2025-06-15T18:00:00"
```
If the user says "around 6pm" without a date, ask for the date. If they say "yesterday at 6pm", calculate accordingly. Expand the range by ±10 epochs (~1 hour) to catch surrounding context.

**Step 2:** Fetch rewards-list (#2) for the validator across that epoch range to check for:
- Missed attestation rewards (head/source/target) → validator was offline or slow
- Missed proposal rewards → validator was assigned to propose but missed it
- Penalties → validator was actively penalized
- Zero rewards for consecutive epochs → validator was likely offline

**Step 3:** Fetch balance-list (#4) for the same range to detect:
- Sudden balance drops → slashing or accumulated penalties
- Flat balance (no growth) → validator was offline and not earning

**Step 4:** If a missed proposal is detected, use slot exploration (#5) to check the specific slot:
- Was the slot missed entirely or was the block orphaned?
- What was the proposer index?

**Step 5:** Run `scripts/analyze_missed.py` on the rewards data to generate a diagnostic report.

**Present findings as a timeline:** "At epoch X (6:02 PM UTC), your validator missed a target attestation. At epoch X+1, it resumed normal operation. Total missed rewards: Y ETH."

## Pagination

V2 API uses cursor-based pagination:
- Send `page_size` (1-100, default 10) and optional `cursor`
- Response includes `paging.next_cursor` — pass it in the next request
- When `next_cursor` is absent/empty, all data has been fetched
- Keep all filters identical across pages

## Error Handling

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| 401 Unauthorized | Missing or invalid API key | Verify Bearer token in header |
| 429 Too Many Requests | Rate limit exceeded | Read `ratelimit-reset` header, wait that many seconds, then retry. For repeated 429s, use exponential backoff. |
| 400 Bad Request | Malformed body or invalid identifier | Verify JSON structure and identifier format |
| Empty `data` array | Validator/epoch doesn't exist | Verify the identifier is correct |

If MCP connection fails:
1. Verify MCP server is connected in Settings
2. Test a simple call: fetch validator index 1
3. If that fails, the issue is MCP connectivity, not this skill

## Common Scenarios

**"How is my validator doing?"**
→ Fetch validator status (#1) + recent rewards (#2) + BeaconScore (#3). Summarize: online/offline, current balance, recent reward trend, efficiency score.

**"What did I earn this week?"**
→ Use rewards-aggregate (#8) for a quick 7d summary. If the user needs per-epoch detail, fall back to rewards-list (#2).

**"What did I earn between March 1 and March 15?"**
→ Custom date range (#9): convert dates to epochs via `scripts/epoch_converter.py`, then iterate rewards-list with pagination.

**"I need my staking rewards for tax reporting"**
→ Tax year workflow (#10): fetch per-epoch rewards for the tax year, output with timestamps for fiat conversion. Remind user to consult a tax professional.

**"Is the network healthy?"**
→ Fetch network overview (#6). Report: participation rate, finalization status, queue lengths, active validator count.

**"How long until my validator activates?"**
→ Queue tracking (#15): fetch queue depths, calculate estimated wait from churn limit.

**"Where am I losing rewards?"**
→ Missed rewards analysis (#13): fetch rewards-list, pipe through `scripts/analyze_missed.py`. Show breakdown by duty type with diagnostics.

**"What's my APR?"**
→ APY/ROI metrics (#14): use apy-roi endpoint or calculate from rewards-aggregate data.

**"What happened at slot X / epoch Y?"**
→ Use block/epoch exploration (#5). Report: proposer, attestation count, whether slot was missed, any slashings.

**"Show me my dashboard group performance"**
→ Dashboard private sets (#11): query by dashboard_id/group_id instead of listing individual validators.

**"Set up monitoring for my validators"**
→ Guide through dashboard management (#7) or direct to the mobile app node monitoring setup at `references/api-guide.md`.

**"What happened to my validator at 6pm yesterday?"**
→ Incident investigation (#17): convert time to epoch range, fetch rewards-list + balance-list for surrounding epochs, run missed analysis, present as timeline.

**"Show me just the CL rewards for my validators"**
→ Staking rewards (#2) with CL-only filtering: sum attestation + sync committee + proposal CL components, exclude execution_layer_reward.

**"I want to embed BeaconScore in my app"**
→ Embed BeaconScore (#16): fetch scores via API, explain attribution requirements, link to badge assets.

## Attribution

When displaying beaconcha.in data publicly, include "Powered by beaconcha.in" attribution. When displaying BeaconScore metrics, use the official BeaconScore badge. Enterprise plan users are exempt. See `references/api-guide.md` for badge download links.
