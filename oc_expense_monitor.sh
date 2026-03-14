#!/bin/bash
########################################################################
# oc_expense_monitor.sh — Monitor OC expense statuses and refund
#                         rejected restitutions back to MULTIPASS
########################################################################
# Scans OC expenses matching RESTITUTION:INDEMNISATION transactions.
# If an expense is REJECTED, sends the ẐEN back to the MULTIPASS holder.
# If PAID, marks the restitution as finalized.
#
# Called by: 20h12.process.sh (daily cron) or manually
# Depends on: .env (OCAPIKEY, OCSLUG), Astroport.ONE tools
########################################################################
set -euo pipefail

MY_PATH="$(cd "$(dirname "$0")" && pwd)"

## Load OC credentials from cooperative-config (NOSTR DID) or .env fallback
COOP_CONFIG="$HOME/.zen/Astroport.ONE/tools/cooperative_config.sh"
if [[ -f "$COOP_CONFIG" ]]; then
    source "$COOP_CONFIG"
    coop_load_env_vars 2>/dev/null || true
fi
if [[ -z "${OCSLUG:-}" || -z "${OCAPIKEY:-}" ]]; then
    if [[ -s "$MY_PATH/.env" ]]; then
        export $(grep -v '^#' "$MY_PATH/.env" | xargs)
    else
        echo "ERROR: No OC credentials found (cooperative-config or .env)"
        exit 1
    fi
fi

ASTROPORT="$HOME/.zen/Astroport.ONE"
DATA_DIR="$MY_PATH/data"
RESTITUTION_LOG="$DATA_DIR/restitution.log"
REFUND_LOG="$DATA_DIR/refund.log"
mkdir -p "$DATA_DIR"
touch "$RESTITUTION_LOG" "$REFUND_LOG"

########################################################################
## UPLANET SECRETS & API MODE
########################################################################
UPLANETNAME="$(cat ~/.ipfs/swarm.key 2>/dev/null | tail -n 1)"
ORIGIN_KEY="0000000000000000000000000000000000000000000000000000000000000000"

if [[ "$UPLANETNAME" == "$ORIGIN_KEY" || -z "$UPLANETNAME" ]]; then
    OC_API="https://api-staging.opencollective.com/graphql/v2"
else
    OC_API="${OC_API:-https://api.opencollective.com/graphql/v2}"
fi

########################################################################
## uplanet.G1.dunikey — Cooperative central wallet (source for refunds)
########################################################################
UPLANET_G1_DUNIKEY="$HOME/.zen/game/uplanet.G1.dunikey"
if [[ ! -s "$UPLANET_G1_DUNIKEY" ]]; then
    echo "ERROR: uplanet.G1.dunikey not found — cannot process refunds"
    exit 1
fi
UPLANET_G1PUB=$(grep "pub:" "$UPLANET_G1_DUNIKEY" | cut -d ' ' -f 2)

########################################################################
## Step 1: Fetch pending/rejected expenses from OC
########################################################################
echo "=== Monitoring OC expenses for restitution status ==="

## Query expenses with status PENDING, REJECTED, or PAID
## We look for expenses whose description contains RESTITUTION
curl -sX POST \
    -H "Content-Type: application/json" \
    -H "Personal-Token: ${OCAPIKEY}" \
    -d '{
    "query": "query ($slug: String) { account(slug: $slug) { expenses(limit: 50, status: [PENDING, REJECTED, APPROVED, PAID]) { totalCount nodes { id status description amount { value currency } createdBy { name slug emails } createdAt } } } }",
    "variables": {
      "slug": "'"${OCSLUG}"'"
    }
  }' "$OC_API" > "$DATA_DIR/expenses.json"

echo "Fetched expenses: $DATA_DIR/expenses.json"

########################################################################
## Step 2: Scan blockchain for RESTITUTION transactions
########################################################################
## Find recent incoming TX to uplanet.G1.dunikey with comment RESTITUTION
## These are the ẐEN credits returned by MULTIPASS holders

RESTITUTION_TX_FILE="$DATA_DIR/restitution_pending.json"

## Use G1history to get recent incoming transactions
if [[ -x "$ASTROPORT/tools/G1history.sh" ]]; then
    "$ASTROPORT/tools/G1history.sh" "$UPLANET_G1PUB" 50 2>/dev/null \
        | jq -c '[.[] | select(.comment | test("RESTITUTION"; "i"))]' \
        > "$RESTITUTION_TX_FILE" 2>/dev/null || echo "[]" > "$RESTITUTION_TX_FILE"
else
    echo "[]" > "$RESTITUTION_TX_FILE"
fi

echo "Restitution TX found: $(jq 'length' "$RESTITUTION_TX_FILE" 2>/dev/null || echo 0)"

########################################################################
## Step 3: Match REJECTED expenses → refund ẐEN to MULTIPASS
########################################################################
echo "=== Checking for REJECTED expenses ==="

jq -c '.data.account.expenses.nodes[] | select(.status == "REJECTED")' \
    "$DATA_DIR/expenses.json" 2>/dev/null | while IFS= read -r expense; do

    expense_id=$(echo "$expense" | jq -r '.id')
    expense_amount=$(echo "$expense" | jq -r '.amount.value')
    expense_email=$(echo "$expense" | jq -r '.createdBy.emails[0] // empty')
    expense_slug=$(echo "$expense" | jq -r '.createdBy.slug // empty')
    expense_desc=$(echo "$expense" | jq -r '.description // empty')
    created_at=$(echo "$expense" | jq -r '.createdAt // empty')

    ## Only process expenses that look like restitution claims
    ## (submitted after a RESTITUTION:INDEMNISATION blockchain TX)
    if ! echo "$expense_desc" | grep -qiE "restitution|indemnisation|hébergement|maintenance|hosting"; then
        continue
    fi

    ## Idempotency: skip already processed refunds
    refund_key="${expense_id}:REJECTED"
    if grep -qF "$refund_key" "$REFUND_LOG" 2>/dev/null; then
        echo "  ⏭ Already refunded: $refund_key"
        continue
    fi

    ## Resolve email from slug if not directly available
    if [[ -z "$expense_email" || "$expense_email" == "null" ]]; then
        expense_email=$(jq -r --arg s "$expense_slug" '.[$s] // empty' \
            "$DATA_DIR/slug_email_map.json" 2>/dev/null)
    fi

    if [[ -z "$expense_email" || "$expense_email" == "null" ]]; then
        echo "  ⚠ REJECTED expense $expense_id — no email found for slug=$expense_slug"
        continue
    fi

    ## Find the MULTIPASS G1 pubkey for this email
    MULTIPASS_G1PUB_FILE="$HOME/.zen/game/nostr/${expense_email}/G1PUBNOSTR"
    if [[ ! -s "$MULTIPASS_G1PUB_FILE" ]]; then
        echo "  ⚠ REJECTED expense $expense_id — no MULTIPASS for ${expense_email}"
        continue
    fi
    MULTIPASS_G1PUB=$(cat "$MULTIPASS_G1PUB_FILE")

    ## Calculate refund amount in G1 (1 ẐEN = 0.1 Ğ1)
    ## expense_amount is in EUR = ẐEN, so G1 = amount / 10
    refund_g1=$(echo "scale=2; $expense_amount / 10" | bc)

    echo "  ↩ REFUND: ${expense_email} — ${expense_amount} ẐEN (${refund_g1} Ğ1)"
    echo "    Expense #${expense_id} REJECTED — returning credits to MULTIPASS ${MULTIPASS_G1PUB:0:8}..."

    ## Execute refund: uplanet.G1.dunikey → MULTIPASS holder
    if [[ -x "$ASTROPORT/tools/PAYforSURE.sh" ]]; then
        "$ASTROPORT/tools/PAYforSURE.sh" \
            "$UPLANET_G1_DUNIKEY" \
            "${refund_g1}" \
            "$MULTIPASS_G1PUB" \
            "REFUND:REJECTED:${expense_id}" \
            2>&1 | tail -1

        RESULT=$?
        if [[ $RESULT -eq 0 ]]; then
            echo "    ✅ Refund sent"
            echo "${refund_key}:${expense_email}:${expense_amount}:$(date +%s):OK" >> "$REFUND_LOG"
        else
            echo "    ❌ Refund FAILED (exit $RESULT)"
            echo "${refund_key}:${expense_email}:${expense_amount}:$(date +%s):FAIL" >> "$REFUND_LOG"
        fi
    else
        echo "    ❌ PAYforSURE.sh not found"
    fi

done

########################################################################
## Step 4: Mark PAID expenses as finalized in restitution log
########################################################################
echo "=== Checking for PAID expenses ==="

jq -c '.data.account.expenses.nodes[] | select(.status == "PAID")' \
    "$DATA_DIR/expenses.json" 2>/dev/null | while IFS= read -r expense; do

    expense_id=$(echo "$expense" | jq -r '.id')
    expense_amount=$(echo "$expense" | jq -r '.amount.value')
    expense_email=$(echo "$expense" | jq -r '.createdBy.emails[0] // empty')
    expense_desc=$(echo "$expense" | jq -r '.description // empty')

    if ! echo "$expense_desc" | grep -qiE "restitution|indemnisation|hébergement|maintenance|hosting"; then
        continue
    fi

    finalized_key="${expense_id}:PAID"
    if grep -qF "$finalized_key" "$RESTITUTION_LOG" 2>/dev/null; then
        continue
    fi

    echo "  ✅ PAID: ${expense_email:-unknown} — ${expense_amount} EUR (expense #${expense_id})"
    echo "${finalized_key}:${expense_email}:${expense_amount}:$(date +%s)" >> "$RESTITUTION_LOG"

done

########################################################################
## Summary
########################################################################
echo "=== Expense monitor complete ==="
echo "Refund log: $REFUND_LOG"
echo "Restitution log: $RESTITUTION_LOG"
REJECTED_COUNT=$(grep -c ":OK$" "$REFUND_LOG" 2>/dev/null || echo 0)
PAID_COUNT=$(wc -l < "$RESTITUTION_LOG" 2>/dev/null || echo 0)
echo "Total refunded: $REJECTED_COUNT | Total finalized: $PAID_COUNT"
