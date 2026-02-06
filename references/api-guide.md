# Beaconcha.in API Reference Guide

## Authentication

All endpoints require an API key obtained from https://beaconcha.in/user/api-key-management

**V2 API (POST endpoints):**
```
Authorization: Bearer <YOUR_API_KEY>
Content-Type: application/json
```

**V1 API (GET endpoints):**
```
https://beaconcha.in/api/v1/{endpoint}?apikey=<YOUR_API_KEY>
```

A single API key works for both V1 and V2.

## Network Base URLs

| Network  | Base URL                          |
|----------|-----------------------------------|
| Mainnet  | https://beaconcha.in              |
| Holesky  | https://holesky.beaconcha.in      |
| Gnosis   | https://gnosis.beaconcha.in       |

## Rate Limits

| Plan       | Price (annual, ex-VAT) | Limit/sec | Limit/month |
|------------|----------------------|-----------|-------------|
| Free       | 0€                   | 1         | 1,000       |
| Hobbyist   | 59€/mo               | 1         | — (none)    |
| Business   | 99€/mo               | 2         | — (none)    |
| Scale      | 399€/mo              | 5         | — (none)    |
| Enterprise | Contact              | Custom    | Custom      |

Scale and Enterprise plans unlock **Pro 💎 features**: premium validator selectors (`withdrawal` address, `deposit_address`).

### Rate Limit Headers

Every response includes these headers — use them to monitor usage:
- `ratelimit-remaining` — requests left in current window
- `ratelimit-reset` — seconds until window resets (use for 429 backoff)
- `ratelimit-bucket` — which bucket this request counted against (`default`, `app`, `machine`, `oldsubnewapi`)
- `x-ratelimit-remaining-second`, `-minute`, `-hour`, `-day`, `-month` — per-window remaining counts

### Rate Limit Buckets

- **Current plans** (Hobbyist/Business/Scale): V1 and V2 share **one combined bucket** with per-second limits only.
- **Legacy plans** (Sapphire/Emerald/Diamond): V1 and V2 use **separate buckets**. V2 endpoints get free-tier limits (1/sec, 1000/month). V1 gets your legacy plan limits.
- The `ratelimit-bucket` header tells you which bucket was used.

### Handling 429 Errors

When rate-limited:
1. Read the `ratelimit-reset` header for seconds to wait
2. Pause all outgoing requests for that duration
3. For repeated 429s, implement exponential backoff
4. For bulk operations, check `x-ratelimit-remaining-*` headers proactively before each batch

### Best Practices

- Use `dashboard_id` to batch-query many validators in one request
- Check `x-ratelimit-remaining-month` on free tier before multi-call workflows
- For large date ranges, estimate API calls needed: epochs ÷ page_size = calls

## V2 API Endpoints (POST, JSON body)

### Validators

**POST /api/v2/ethereum/validators**
Returns basic info (status, balance, lifecycle epochs) for validators at the current epoch.

Body:
```json
{
  "validator": {
    "validator_identifiers": [1, "0xpubkey..."]
  },
  "chain": "mainnet",
  "page_size": 10,
  "cursor": ""
}
```

Identifier types: validator index (int), public key (0x hex string), withdrawal address, deposit address.

Validator statuses: `pending_initialized`, `pending_queued`, `active_online`, `active_offline`, `exiting_online`, `exiting_offline`, `slashing_online`, `slashing_offline`, `exited`, `withdrawal`

---

**POST /api/v2/ethereum/validators/rewards-list**
Returns per-epoch reward breakdown (CL + EL).

Body:
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

Omit `epoch` for latest. Response includes attestation (head/source/target), sync_committee, and proposal rewards with sub-breakdowns.

All reward/penalty values are in **wei** (divide by 1e18 for ETH).

---

**POST /api/v2/ethereum/validators/beacon-score**
Returns BeaconScore (efficiency) for validators.

---

**POST /api/v2/ethereum/validators/rewards-aggregate**
Returns pre-computed reward summaries for rolling periods (24h, 7d, 30d, 90d). Faster and cheaper than iterating `rewards-list` for standard periods.

Body:
```json
{
  "validator": {
    "validator_identifiers": [1, 2, 3]
  },
  "chain": "mainnet"
}
```

---

**POST /api/v2/ethereum/validators/apy-roi**
Returns annualized return metrics with CL/EL breakdown.

---

**POST /api/v2/ethereum/validators/performance-aggregate**
Returns aggregated BeaconScore/performance metrics across validator groups. Useful for comparing group performance.

---

**POST /api/v2/ethereum/validators/balance-list**
Returns historical balance snapshots.

---

### Network

**POST /api/v2/ethereum/network**
Returns network-wide metrics: active validators, pending queue, participation rate.

---

**POST /api/v2/ethereum/queues**
Returns activation, exit, and withdrawal queue depths with estimated wait times. Use for planning validator operations.

---

### Validator Selectors

V2 endpoints accept multiple selector types in the `validator` object:

```json
// By index or pubkey
{ "validator_identifiers": [1, 2, "0xpubkey..."] }

// By dashboard (requires Orca subscription)
{ "dashboard_id": "your-dashboard-id" }

// By dashboard + group
{ "dashboard_id": "your-dashboard-id", "group_id": 0 }
```

Dashboard selectors are useful for staking providers managing thousands of validators across client groups.

---

### Validator Dashboard Management

**POST /api/v2/validator-dashboards**
Create a new validator dashboard.

**POST /api/v2/validator-dashboards/{dashboard_id}/validators**
Add validators to a dashboard.

Body:
```json
{
  "deposit_address": "text",
  "graffiti": "text",
  "group_id": 1,
  "validators": [{}],
  "withdrawal_credential": "text"
}
```

**DELETE /api/v2/validator-dashboards/{dashboard_id}/groups/{group_id}/validators**
Remove validators from a group.

**POST /api/v2/validator-dashboards/{dashboard_id}/validators/bulk-deletions**
Bulk remove validators.

## V1 API Endpoints (GET, query params)

### Consensus Layer

- `GET /api/v1/validator/{indexOrPubkey}` — Single validator info
- `GET /api/v1/validator/{indexOrPubkey}/balancehistory` — Balance history
- `GET /api/v1/validator/{indexOrPubkey}/performance` — Performance metrics
- `GET /api/v1/validator/{indexOrPubkey}/attestations` — Attestation history
- `GET /api/v1/validator/{indexOrPubkey}/proposals` — Block proposals
- `GET /api/v1/validator/{indexOrPubkey}/deposits` — Deposit info
- `GET /api/v1/validator/{indexOrPubkey}/withdrawals` — Withdrawal history
- `GET /api/v1/validators/queue` — Entry and exit queue lengths

### Blocks and Epochs

- `GET /api/v1/slot/{slot}` — Block data for a slot
- `GET /api/v1/slot/{slot}/attestations` — Attestations in a slot
- `GET /api/v1/epoch/{epoch}` — Epoch summary
- `GET /api/v1/epoch/{epoch}/slots` — All slots in an epoch
- `GET /api/v1/epoch/latest` — Latest finalized epoch

### Execution Layer

- `GET /api/v1/execution/block/{blockNumber}` — Execution block
- `GET /api/v1/execution/{address}/produced` — Blocks produced by address

### Misc

- `GET /api/v1/ethstore/{day}` — Network-wide staking stats for a day
- `GET /api/v1/sync_committee/{period}` — Sync committee members

## Pagination (V2)

Cursor-based. Send `page_size` (1-100) and `cursor` from `paging.next_cursor`. When `next_cursor` is absent, all data is fetched. Keep filters identical across pages.

## Attribution Requirements

When using beaconcha.in API data publicly:
- Display "Powered by beaconcha.in" badge
- When showing BeaconScore metrics, use the official BeaconScore badge
- Enterprise plan users are exempt

Badge downloads: https://docs.beaconcha.in/legal/license-materials

## Mobile App Node Monitoring

Solo stakers can push metrics from their CL node to beaconcha.in for mobile app monitoring.

Add to your beacon node startup flags:
```
--monitoring.endpoint 'https://beaconcha.in/api/v1/client/metrics?apikey=YOUR_API_KEY'
```

Compatible clients: Lighthouse, Lodestar, Teku, Nimbus (partial). Prysm not supported.

## MCP Server

beaconcha.in offers an MCP server for AI assistant integration:
- Server URL: `https://docs.beaconcha.in/mcp`
- Provides access to: API documentation, validator dashboard guides, FAQs, notification setup guides

## Useful Formulas

**Beacon Chain Constants:**
- Genesis timestamp: `1606824023` (Dec 1, 2020, 12:00:23 UTC)
- Seconds per slot: `12`
- Slots per epoch: `32`
- Seconds per epoch: `384`

**Epoch/Time Conversions:**
```
epoch → timestamp:   ts = 1606824023 + (epoch × 384)
timestamp → epoch:   epoch = floor((ts - 1606824023) / 384)
slot → epoch:        epoch = floor(slot / 32)
epoch → slot range:  start = epoch × 32, end = start + 31
slot → timestamp:    ts = 1606824023 + (slot × 12)
```

Use `scripts/epoch_converter.py` for quick conversions:
```bash
python scripts/epoch_converter.py --epoch 347566
python scripts/epoch_converter.py --date "2025-01-01"
python scripts/epoch_converter.py --range "2025-01-01" "2025-12-31"
```

**Epochs per day:** 225 (24h × 60min ÷ 6.4min)
**Epochs per week:** 1,575
**Epochs per year:** ~82,125

**Estimated queue wait time:**
```
wait_minutes = (queue_length / activations_per_epoch) × 6.4
```
Activations per epoch = max(4, active_validator_count / 65536)

**APR calculation:**
```
APR = (RewardsInPeriod / BalanceAtPeriodStart) × (EpochsPerYear / EpochsInPeriod) × 100
```

**Attester efficiency:**
```
efficiency = actual_reward / (actual_reward + missed_reward + penalty)
```
