#!/bin/bash
########################################################################
# Version: 0.5
# License: AGPL-3.0 (https://choosealicense.com/licenses/agpl-3.0/)
########################################################################
## OC 2 UPlanet
########################################################################
## Regularly make OpenCollective GraphQL API calls
## to fill-up members ZenCard with their donation 1€=1Ẑ (-OC%)
########################################################################
## INIT
ASTROPORT="${HOME}/.zen/Astroport.ONE"
EMISSION_LOG="./data/emission.log"
MY_PATH="$(cd "$(dirname "$0")" && pwd)"
mkdir -p ./data
touch "$EMISSION_LOG"

# NOTE: .env is NO LONGER loaded locally. We rely on NOSTR/DID or explicit exports.

#######################################################################
## UPLANET SECRETS & ORIGIN DETECTION
#######################################################################
export UPLANETNAME="$(cat ~/.ipfs/swarm.key 2>/dev/null | tail -n 1)"

##############################################################################
## FALLBACK : DID NOSTR coopératif (kind 30800, chiffré avec $UPLANETNAME)
##############################################################################
COOP_CONFIG="${ASTROPORT}/tools/cooperative_config.sh"
JSON_OUTPUT=false
# Preliminary check for --json to silence init messages
for arg in "$@"; do [[ "$arg" == "--json" ]] && JSON_OUTPUT=true; done

if [[ -z "${OCAPIKEY}" && -f "${COOP_CONFIG}" ]]; then
    source "${COOP_CONFIG}" 2>/dev/null
    _coop_ocapikey=$(coop_config_get "OCAPIKEY" 2>/dev/null)
    [[ -n "${_coop_ocapikey}" ]] && export OCAPIKEY="${_coop_ocapikey}"
    [[ "$JSON_OUTPUT" == "false" && -n "${OCAPIKEY}" ]] && echo "✅ OCAPIKEY chargé depuis le DID NOSTR coopératif"
    _coop_ocslug=$(coop_config_get "OCSLUG" 2>/dev/null)
    [[ -n "${_coop_ocslug}" && -z "${OCSLUG}" ]] && export OCSLUG="${_coop_ocslug}"
    _coop_oc_api=$(coop_config_get "OC_API" 2>/dev/null)
    [[ -n "${_coop_oc_api}" && -z "${OC_API}" ]] && export OC_API="${_coop_oc_api}"
fi
[[ -z "${OC_API}" ]] && OC_API="https://api.opencollective.com/graphql/v2"

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --manual    Interactive mode to validate/edit transactions"
    echo "  --scan      List all backers and their contributions"
    echo "  --ranking   Rank backers by total contribution + active status"
    echo "  --alerts    Identify stopped or changed subscriptions"
    echo "  --status    Show current month summary"
    echo "  --history   Show the last processed transactions"
    echo "  --json      Modify output format to JSON"
    echo "  --help      Show this help message"
    echo ""
}

show_history() {
    if [[ -f "$EMISSION_LOG" ]]; then
        echo "=== Emission History (last 20) ==="
        tail -n 20 "$EMISSION_LOG" | awk -F: '{printf "Date: %s | Email: %s | Amount: %s | Tier: %s | Status: %s\n", strftime("%Y-%m-%d %H:%M:%S", $4), $1, $2, $3, $5}'
    else
        echo "No history found."
    fi
}

show_status() {
    local total_backers=$(jq -r ".data.account.members.totalCount // 0" data/backers.json 2>/dev/null)
    local count=$(jq -s "length" data/current_month.credit.json 2>/dev/null)
    local total_amount=$(jq -s "[.[] | .amount.value] | add // 0" data/current_month.credit.json 2>/dev/null)
    local processed=$(grep -c ":OK$" "$EMISSION_LOG" 2>/dev/null)

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        jq -n --arg tb "$total_backers" --arg cnt "$count" --arg ta "$total_amount" --arg pr "$processed" \
            '{total_backers: $tb, current_month_tx: $cnt, current_month_total: $ta, processed_ok: $pr}'
    else
        echo "=== Current Status ==="
        echo "Total Backers: $total_backers"
        echo "Current Month Transactions: $count"
        echo "Current Month Total: $total_amount EUR"
        echo "Total Transactions Processed (OK): $processed"
    fi
}

fetch_oc_data() {
    [[ -z "${OCAPIKEY}" ]] && echo "ERROR 0 : OCAPIKEY manquant" && return 1
    [[ "$JSON_OUTPUT" == "false" ]] && echo "Fetching data from OpenCollective for slug: ${OCSLUG}..."
    
    # Backers list
    curl -sX POST -H "Content-Type: application/json" -H "Personal-Token: ${OCAPIKEY}" \
        -d "{\"query\": \"query account(\$slug: String) { account(slug: \$slug) { name slug members(role: BACKER, limit: 200) { totalCount nodes { account { name slug emails } } } } }\", \"variables\": {\"slug\": \"${OCSLUG}\"}}" \
        "${OC_API}" > data/backers.json

    # Slug email map
    jq -r '.data.account.members.nodes[] | "\(.account.slug):\(.account.emails[0])"' data/backers.json > data/slugemail.list
    cat data/slugemail.list | awk -F: '{print "{\"" $1 "\": \"" $2 "\"}"}' | jq -s 'add' > data/slug_email_map.json

    # Transactions (last 100)
    curl -sX POST -H "Content-Type: application/json" -H "Personal-Token: ${OCAPIKEY}" \
        -d "{\"query\": \"query (\$slug: String) { account(slug: \$slug) { name slug transactions(limit: 100, type: CREDIT) { totalCount nodes { type fromAccount { name slug emails } amount { value currency } order { tier { slug name } } createdAt } } } }\", \"variables\": {\"slug\": \"${OCSLUG}\"}}" \
        "${OC_API}" > data/tx.json

    # Time splits
    local start_of_month=$(date -d "$(date +%Y-%m-01)" +"%Y-%m-%d")
    local start_of_last_month=$(date -d "$(date +%Y-%m-01) -1 month" +"%Y-%m-%d")
    local end_of_last_month=$(date -d "$(date +%Y-%m-01) -1 day" +"%Y-%m-%d")

    jq -c --arg som "$start_of_month" '.data.account.transactions.nodes[] | select(.type == "CREDIT" and .createdAt >= $som)' data/tx.json > data/current_month.credit.json
    jq -c --arg solm "$start_of_last_month" --arg eolm "$end_of_last_month" '.data.account.transactions.nodes[] | select(.type == "CREDIT" and (.createdAt >= $solm and .createdAt <= $eolm))' data/tx.json > data/last_month.credit.json
}

show_scan() {
    fetch_oc_data || return 1
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        # Join with email map in JSON
        jq --slurpfile map data/slug_email_map.json '
            .data.account.transactions.nodes | map(. + {email: ($map[0][.fromAccount.slug] // .fromAccount.emails[0] // "-")})
        ' data/tx.json
    else
        echo ""
        echo "=== OpenCollective Scan : ${OCSLUG} ==="
        printf "%-20s | %-15s | %-25s | %-10s | %-15s | %s\n" "Name" "Slug" "Email" "Amount" "Tier" "Date"
        echo "----------------------------------------------------------------------------------------------------------------------------"
        jq -r '.data.account.transactions.nodes[] | "\(.fromAccount.name // "-"):\(.fromAccount.slug):\(.fromAccount.emails[0] // "-"):\(.amount.value) \(.amount.currency):\(.order.tier.name // "-"):\(.createdAt)"' data/tx.json | while IFS=: read -r name slug email amount tier date; do
            [[ "$email" == "-" ]] && email=$(jq -r --arg s "$slug" '.[$s] // "-"' data/slug_email_map.json 2>/dev/null)
            printf "%-20.20s | %-15.15s | %-25.25s | %-10s | %-15.15s | %s\n" "$name" "$slug" "$email" "$amount" "$tier" "$date"
        done
    fi
}

show_ranking() {
    fetch_oc_data || return 1
    # Identify slugs that paid this month
    local active_slugs=$(jq -r '.fromAccount.slug' data/current_month.credit.json | sort -u)
    
    local rank_cmd='
        .data.account.transactions.nodes 
        | group_by(.fromAccount.slug) 
        | map({
            slug: .[0].fromAccount.slug, 
            name: (.[0].fromAccount.name // .[0].fromAccount.slug), 
            total: (map(.amount.value) | add), 
            count: length, 
            currency: .[0].amount.currency,
            email: ""
          }) 
        | sort_by(-.total)'

    local result_json=$(jq "$rank_cmd" data/tx.json)
    
    # Enrich with email and active status
    local enriched=$(echo "$result_json" | jq --argjson active "$(echo "$active_slugs" | jq -R . | jq -s .)" --slurpfile map data/slug_email_map.json '
        map(. + {
            email: ($map[0][.slug] // "-"),
            status: (if (.slug as $s | $active | index($s)) then "ACTIVE" else "INACTIVE" end)
        })
    ')

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo "$enriched"
    else
        echo "=== Backers Ranking (based on last 100 transactions) ==="
        printf "%-25s | %-25s | %-10s | %-8s | %-8s\n" "Backer Name" "Email" "Total" "Status" "Count"
        echo "---------------------------------------------------------------------------------------------------"
        echo "$enriched" | jq -r '.[] | "\(.name):\(.email):\(.total) \(.currency):\(.status):\(.count)"' | while IFS=: read -r name email total status count; do
            printf "%-25.25s | %-25.25s | %-10s | %-8s | %-8s\n" "$name" "$email" "$total" "$status" "$count"
        done
    fi
}

show_alerts() {
    fetch_oc_data || return 1
    local slugs_last=$(jq -r '.fromAccount.slug' data/last_month.credit.json | sort -u)
    local slugs_curr=$(jq -r '.fromAccount.slug' data/current_month.credit.json | sort -u)
    
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        local stopped=$(comm -23 <(echo "$slugs_last") <(echo "$slugs_curr") | while read s; do
            jq -n --arg slug "$s" --arg email "$(jq -r --arg s "$s" '.[$s] // "-"' data/slug_email_map.json)" \
                  --arg name "$(jq -r --arg s "$s" 'select(.fromAccount.slug == $s).fromAccount.name' data/last_month.credit.json | head -1)" \
                  '{slug: $slug, name: $name, email: $email, status: "STOPPED"}'
        done | jq -s .)
        
        local common=$(comm -12 <(echo "$slugs_last") <(echo "$slugs_curr"))
        local changed="[]"
        for s in $common; do
            local val_last=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" data/last_month.credit.json)
            local val_curr=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" data/current_month.credit.json)
            if (( $(echo "$val_last != $val_curr" | bc -l) )); then
                changed=$(echo "$changed" | jq --arg slug "$s" --arg last "$val_last" --arg curr "$val_curr" \
                    --arg email "$(jq -r --arg s "$s" '.[$s] // "-"' data/slug_email_map.json)" \
                    '. += [{slug: $slug, email: $email, last_month: $last, current_month: $curr, status: "CHANGED"}]')
            fi
        done
        jq -n --argjson s "$stopped" --argjson c "$changed" '{stopped: $s, changed: $c}'
    else
        echo "=== Subscription Alerts (Current Month vs Last Month) ==="
        echo "--- STOPPED (Paid last month, not yet this month) ---"
        comm -23 <(echo "$slugs_last") <(echo "$slugs_curr") | while read s; do
            local name=$(jq -r --arg s "$s" 'select(.fromAccount.slug == $s).fromAccount.name' data/last_month.credit.json | head -1)
            local email=$(jq -r --arg s "$s" '.[$s] // "-"' data/slug_email_map.json)
            echo "❌ $s ($name) - Email: $email"
        done
        echo ""
        echo "--- CHANGED (Amount differs from last month) ---"
        local common=$(comm -12 <(echo "$slugs_last") <(echo "$slugs_curr"))
        for s in $common; do
            local val_last=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" data/last_month.credit.json)
            local val_curr=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" data/current_month.credit.json)
            if (( $(echo "$val_last != $val_curr" | bc -l) )); then
                local name=$(jq -r --arg s "$s" 'select(.fromAccount.slug == $s).fromAccount.name' data/current_month.credit.json | head -1)
                local email=$(jq -r --arg s "$s" '.[$s] // "-"' data/slug_email_map.json)
                echo "⚠️  $s ($name): ${val_last}€ -> ${val_curr}€ - Email: $email"
            fi
        done
    fi
}

## Argument parsing
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --manual) MANUAL_MODE=true ;;
        --scan) show_scan; exit 0 ;;
        --ranking) show_ranking; exit 0 ;;
        --alerts) show_alerts; exit 0 ;;
        --status) show_status; exit 0 ;;
        --history) show_history; exit 0 ;;
        --json) JSON_OUTPUT=true ;;
        --help) show_help; exit 0 ;;
        *) [[ "$JSON_OUTPUT" == "false" ]] && echo "Unknown parameter: $1" && show_help; exit 1 ;;
    esac
    shift
done

[[ "$JSON_OUTPUT" == "false" ]] && echo "MONITORING ${OCSLUG} | Station: ${UPLANETNAME:0:8}..."

#######################################################################
## CHECKS
#######################################################################
[[ -z $UPLANETNAME ]] && echo "MISSING PRIVATE SWARM ACTIVATED ASTROPORT STATION" && exit 1
find ./data -mtime +1 -type f -exec rm '{}' \; 2>/dev/null
[[ ! -s data/current_month.credit.json ]] && fetch_oc_data

########################################################################
## EMISSION ẐEN
########################################################################
if [[ -f "$EMISSION_LOG" ]]; then
    tail -n 10000 "$EMISSION_LOG" > "${EMISSION_LOG}.tmp" && mv "${EMISSION_LOG}.tmp" "$EMISSION_LOG"
fi

dispatch_zen_emission() {
    local email="$1" amount="$2" tier_slug="$3"
    local zen_amount=$(echo "scale=2; $amount * 1" | bc)
    case "$tier_slug" in
        *parrainage*128-go*|*extension-128*|*satellite*|*love-box-le-claude*|*love-box*claude*)
            ${ASTROPORT}/UPLANET.official.sh -s "${email}" -t satellite -m "${zen_amount}"
            return $? ;;
        *parrainage*gpu*|*module-gpu*|*constellation*|*love-box-deluxe*|*love-box*gpu*)
            ${ASTROPORT}/UPLANET.official.sh -s "${email}" -t constellation -m "${zen_amount}"
            return $? ;;
        *)
            ${ASTROPORT}/UPLANET.official.sh -l "${email}" -m "${zen_amount}"
            return $? ;;
    esac
}

[[ "$JSON_OUTPUT" == "false" ]] && echo "=== Processing current month credits ==="
while IFS= read -r credit_json; do
    [[ -z "$credit_json" ]] && continue
    slug=$(echo "$credit_json" | jq -r '.fromAccount.slug // empty')
    email=$(echo "$credit_json" | jq -r '.fromAccount.emails[0] // empty')
    amount=$(echo "$credit_json" | jq -r '.amount.value // 0')
    created_at=$(echo "$credit_json" | jq -r '.createdAt // empty')
    tier_slug=$(echo "$credit_json" | jq -r '.order.tier.slug // empty')

    [[ -z "$email" || "$email" == "null" ]] && email=$(jq -r --arg s "$slug" '.[$s] // empty' data/slug_email_map.json 2>/dev/null)
    [[ -z "$email" || "$email" == "null" ]] && continue

    tx_id="${email}:${amount}:${created_at}"
    grep -qF "$tx_id" "$EMISSION_LOG" 2>/dev/null && continue
    [[ ! -f "$HOME/.zen/game/nostr/${email}/G1PUBNOSTR" ]] && continue

    if [[ "$MANUAL_MODE" == "true" ]]; then
        echo "------------------------------------------------"
        echo "Transaction: $email | Amount: $amount EUR"
        read -p "Process? [Y/n/edit/skip/exit]: " choice
        case "${choice,,}" in
            y|yes|"") dispatch_zen_emission "${email}" "${amount}" "${tier_slug}" ;;
            edit)
                read -p "Amount: " amount
                echo "Tier: 1) Satellite 2) Constellation 3) Cloud 4) Membre"
                read -p "Choice: " tc
                case $tc in 1) ts="satellite" ;; 2) ts="constellation" ;; 3) ts="cotisation" ;; 4) ts="membre-resident" ;; *) ts="$tier_slug" ;; esac
                dispatch_zen_emission "${email}" "${amount}" "$ts" ;;
            skip|n|no) continue ;;
            exit) exit 0 ;;
            *) continue ;;
        esac
    else
        dispatch_zen_emission "${email}" "${amount}" "${tier_slug}"
    fi
    [[ $? -eq 0 ]] && echo "${tx_id}:${amount}:${tier_slug}:$(date +%s):OK" >> "$EMISSION_LOG" || echo "${tx_id}:${amount}:${tier_slug}:$(date +%s):FAIL" >> "$EMISSION_LOG"
done < <(jq -c '.' data/current_month.credit.json 2>/dev/null)

[[ "$JSON_OUTPUT" == "false" ]] && echo "=== ẐEN emission complete ==="
[[ -x "$MY_PATH/oc_expense_monitor.sh" ]] && "$MY_PATH/oc_expense_monitor.sh" >/dev/null 2>&1 || true
