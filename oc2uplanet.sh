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
MY_PATH="$(cd "$(dirname "$0")" && pwd)"
EMISSION_LOG="${MY_PATH}/data/emission.log"
mkdir -p "${MY_PATH}/data"
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

## Station variables (CAPTAINEMAIL, uSPOT, myDOMAIN, myIPFS…)
[[ -z "$myDOMAIN" && -f "${ASTROPORT}/tools/my.sh" ]] && source "${ASTROPORT}/tools/my.sh" 2>/dev/null

INVITATION_LOG="${MY_PATH}/data/invitation.log"
touch "$INVITATION_LOG"
## Email du capitaine (destinataire des tiers labo/R&D)
CAPTAIN_TARGET="${CAPTAINEMAIL:-$(cat ~/.zen/game/players/.current/.player 2>/dev/null)}"

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
    local total_backers=$(jq -r ".data.account.members.totalCount // 0" ${MY_PATH}/data/backers.json 2>/dev/null)
    local count=$(jq -s "length" ${MY_PATH}/data/current_month.credit.json 2>/dev/null)
    local total_amount=$(jq -s "[.[] | .amount.value] | add // 0" ${MY_PATH}/data/current_month.credit.json 2>/dev/null)
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
        "${OC_API}" > ${MY_PATH}/data/backers.json

    # Slug email map
    jq -r '.data.account.members.nodes[] | "\(.account.slug):\(.account.emails[0])"' ${MY_PATH}/data/backers.json > ${MY_PATH}/data/slugemail.list
    cat ${MY_PATH}/data/slugemail.list | awk -F: '{print "{\"" $1 "\": \"" $2 "\"}"}' | jq -s 'add' > ${MY_PATH}/data/slug_email_map.json

    # Transactions (last 100)
    curl -sX POST -H "Content-Type: application/json" -H "Personal-Token: ${OCAPIKEY}" \
        -d "{\"query\": \"query (\$slug: String) { account(slug: \$slug) { name slug transactions(limit: 100, type: CREDIT) { totalCount nodes { type fromAccount { name slug emails } amount { value currency } order { tier { slug name } } createdAt } } } }\", \"variables\": {\"slug\": \"${OCSLUG}\"}}" \
        "${OC_API}" > ${MY_PATH}/data/tx.json

    # Time splits
    local start_of_month=$(date -d "$(date +%Y-%m-01)" +"%Y-%m-%d")
    local start_of_last_month=$(date -d "$(date +%Y-%m-01) -1 month" +"%Y-%m-%d")
    local end_of_last_month=$(date -d "$(date +%Y-%m-01) -1 day" +"%Y-%m-%d")

    jq -c --arg som "$start_of_month" '.data.account.transactions.nodes[] | select(.type == "CREDIT" and .createdAt >= $som)' ${MY_PATH}/data/tx.json > ${MY_PATH}/data/current_month.credit.json
    jq -c --arg solm "$start_of_last_month" --arg eolm "$end_of_last_month" '.data.account.transactions.nodes[] | select(.type == "CREDIT" and (.createdAt >= $solm and .createdAt <= $eolm))' ${MY_PATH}/data/tx.json > ${MY_PATH}/data/last_month.credit.json
}

show_scan() {
    fetch_oc_data || return 1
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        # Join with email map in JSON
        jq --slurpfile map ${MY_PATH}/data/slug_email_map.json '
            .data.account.transactions.nodes | map(. + {email: ($map[0][.fromAccount.slug] // .fromAccount.emails[0] // "-")})
        ' ${MY_PATH}/data/tx.json
    else
        echo ""
        echo "=== OpenCollective Scan : ${OCSLUG} ==="
        printf "%-20s | %-15s | %-25s | %-10s | %-15s | %s\n" "Name" "Slug" "Email" "Amount" "Tier" "Date"
        echo "----------------------------------------------------------------------------------------------------------------------------"
        jq -r '.data.account.transactions.nodes[] | "\(.fromAccount.name // "-"):\(.fromAccount.slug):\(.fromAccount.emails[0] // "-"):\(.amount.value) \(.amount.currency):\(.order.tier.name // "-"):\(.createdAt)"' ${MY_PATH}/data/tx.json | while IFS=: read -r name slug email amount tier date; do
            [[ "$email" == "-" ]] && email=$(jq -r --arg s "$slug" '.[$s] // "-"' ${MY_PATH}/data/slug_email_map.json 2>/dev/null)
            printf "%-20.20s | %-15.15s | %-25.25s | %-10s | %-15.15s | %s\n" "$name" "$slug" "$email" "$amount" "$tier" "$date"
        done
    fi
}

show_ranking() {
    fetch_oc_data || return 1
    # Identify slugs that paid this month
    local active_slugs=$(jq -r '.fromAccount.slug' ${MY_PATH}/data/current_month.credit.json | sort -u)
    
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

    local result_json=$(jq "$rank_cmd" ${MY_PATH}/data/tx.json)
    
    # Enrich with email and active status
    local enriched=$(echo "$result_json" | jq --argjson active "$(echo "$active_slugs" | jq -R . | jq -s .)" --slurpfile map ${MY_PATH}/data/slug_email_map.json '
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
    local slugs_last=$(jq -r '.fromAccount.slug' ${MY_PATH}/data/last_month.credit.json | sort -u)
    local slugs_curr=$(jq -r '.fromAccount.slug' ${MY_PATH}/data/current_month.credit.json | sort -u)
    
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        local stopped=$(comm -23 <(echo "$slugs_last") <(echo "$slugs_curr") | while read s; do
            jq -n --arg slug "$s" --arg email "$(jq -r --arg s "$s" '.[$s] // "-"' ${MY_PATH}/data/slug_email_map.json)" \
                  --arg name "$(jq -r --arg s "$s" 'select(.fromAccount.slug == $s).fromAccount.name' ${MY_PATH}/data/last_month.credit.json | head -1)" \
                  '{slug: $slug, name: $name, email: $email, status: "STOPPED"}'
        done | jq -s .)
        
        local common=$(comm -12 <(echo "$slugs_last") <(echo "$slugs_curr"))
        local changed="[]"
        for s in $common; do
            local val_last=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" ${MY_PATH}/data/last_month.credit.json)
            local val_curr=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" ${MY_PATH}/data/current_month.credit.json)
            if (( $(echo "$val_last != $val_curr" | bc -l) )); then
                changed=$(echo "$changed" | jq --arg slug "$s" --arg last "$val_last" --arg curr "$val_curr" \
                    --arg email "$(jq -r --arg s "$s" '.[$s] // "-"' ${MY_PATH}/data/slug_email_map.json)" \
                    '. += [{slug: $slug, email: $email, last_month: $last, current_month: $curr, status: "CHANGED"}]')
            fi
        done
        jq -n --argjson s "$stopped" --argjson c "$changed" '{stopped: $s, changed: $c}'
    else
        echo "=== Subscription Alerts (Current Month vs Last Month) ==="
        echo "--- STOPPED (Paid last month, not yet this month) ---"
        comm -23 <(echo "$slugs_last") <(echo "$slugs_curr") | while read s; do
            local name=$(jq -r --arg s "$s" 'select(.fromAccount.slug == $s).fromAccount.name' ${MY_PATH}/data/last_month.credit.json | head -1)
            local email=$(jq -r --arg s "$s" '.[$s] // "-"' ${MY_PATH}/data/slug_email_map.json)
            echo "❌ $s ($name) - Email: $email"
        done
        echo ""
        echo "--- CHANGED (Amount differs from last month) ---"
        local common=$(comm -12 <(echo "$slugs_last") <(echo "$slugs_curr"))
        for s in $common; do
            local val_last=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" ${MY_PATH}/data/last_month.credit.json)
            local val_curr=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" ${MY_PATH}/data/current_month.credit.json)
            if (( $(echo "$val_last != $val_curr" | bc -l) )); then
                local name=$(jq -r --arg s "$s" 'select(.fromAccount.slug == $s).fromAccount.name' ${MY_PATH}/data/current_month.credit.json | head -1)
                local email=$(jq -r --arg s "$s" '.[$s] // "-"' ${MY_PATH}/data/slug_email_map.json)
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
[[ "${PAF}" == "0" ]] && echo "PAF=0 — station sandbox, émission ẐEN désactivée." && exit 0
find ./data -mtime +1 -type f -exec rm '{}' \; 2>/dev/null
[[ ! -s ${MY_PATH}/data/current_month.credit.json ]] && fetch_oc_data

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
        *infrastructure*|*labo*|*genereux-donateur*|*r-d*|*recherche*)
            ## Dons fléchés vers le MULTIPASS du Capitaine (labo / R&D qo-op)
            local cap="${CAPTAIN_TARGET:-support@qo-op.com}"
            [[ "$JSON_OUTPUT" == "false" ]] && echo "→ Tier labo/R&D : routage vers MULTIPASS capitaine ${cap}"
            ${ASTROPORT}/UPLANET.official.sh -l "${cap}" -m "${zen_amount}"
            return $? ;;
        *)
            ${ASTROPORT}/UPLANET.official.sh -l "${email}" -m "${zen_amount}"
            return $? ;;
    esac
}

_build_station_card_html() {
    ## Génère un bloc HTML présentant les capacités de cette station Astroport.
    ## Injecté dans les emails d'invitation via {{STATION_CARD}}.
    local _hb_json
    if [[ -n "$IPFSNODEID" ]]; then
        _hb_json="${HOME}/.zen/tmp/${IPFSNODEID}/heartbox_analysis.json"
    else
        _hb_json=$(find "${HOME}/.zen/tmp" -maxdepth 2 -name "heartbox_analysis.json" 2>/dev/null | head -1)
    fi
    [[ ! -s "$_hb_json" ]] && return 0

    local hostname cpu_model cpu_cores ram_gb
    local power_score provider_tier gpu_detected gpu_vram gpu_name
    local disk_write disk_read crypto_score crypto_ms
    local zencard_slots nostr_slots
    local ollama_active ollama_models nextcloud_active
    local ipfs_active ipfs_peers nostr_relay_active nostr_engine

    hostname=$(jq -r '.node_info.hostname // "Station UPlanet"' "$_hb_json" 2>/dev/null | sed 's/&/\&amp;/g; s/</\&lt;/g')
    cpu_model=$(jq -r '.system.cpu.model // "Unknown"' "$_hb_json" 2>/dev/null | sed 's/&/\&amp;/g; s/</\&lt;/g')
    cpu_cores=$(jq -r '.system.cpu.cores // 0' "$_hb_json" 2>/dev/null)
    ram_gb=$(jq -r '.system.memory.total_gb // 0' "$_hb_json" 2>/dev/null)
    power_score=$(jq -r '.capacities.power_score // 0' "$_hb_json" 2>/dev/null)
    provider_tier=$(jq -r '.capacities.provider_tier // "light"' "$_hb_json" 2>/dev/null)
    gpu_detected=$(jq -r '.capacities.gpu.detected // false' "$_hb_json" 2>/dev/null)
    gpu_vram=$(jq -r '.capacities.gpu.vram_gb // 0' "$_hb_json" 2>/dev/null)
    gpu_name=$(jq -r '.capacities.gpu.name // ""' "$_hb_json" 2>/dev/null | sed 's/&/\&amp;/g; s/</\&lt;/g')
    disk_write=$(jq -r '.capacities.disk_io.write_mbps // 0' "$_hb_json" 2>/dev/null)
    disk_read=$(jq -r '.capacities.disk_io.read_mbps // 0' "$_hb_json" 2>/dev/null)
    crypto_score=$(jq -r '.capacities.crypto_score // 0' "$_hb_json" 2>/dev/null)
    crypto_ms=$(jq -r '.capacities.crypto_ms // 0' "$_hb_json" 2>/dev/null)
    zencard_slots=$(jq -r '.capacities.zencard_slots // 0' "$_hb_json" 2>/dev/null)
    nostr_slots=$(jq -r '.capacities.nostr_slots // 0' "$_hb_json" 2>/dev/null)
    ollama_active=$(jq -r '.services.ai_company.ollama.active // false' "$_hb_json" 2>/dev/null)
    ollama_models=$(jq -r '(.services.ai_company.ollama.models // []) | map(split(":")[0]) | join(", ")' "$_hb_json" 2>/dev/null)
    nextcloud_active=$(jq -r '.services.nextcloud.cloud_apache.active // false' "$_hb_json" 2>/dev/null)
    ipfs_active=$(jq -r '.services.ipfs.active // false' "$_hb_json" 2>/dev/null)
    ipfs_peers=$(jq -r '.services.ipfs.peers_connected // 0' "$_hb_json" 2>/dev/null)
    nostr_relay_active=$(jq -r '.services.nostr_relay.active // false' "$_hb_json" 2>/dev/null)
    nostr_engine=$(jq -r '.services.nostr_relay.engine // "strfry"' "$_hb_json" 2>/dev/null)

    local tier_badge tier_color
    case "$provider_tier" in
        brain-gpu)  tier_badge="🔥 BRAIN-GPU"  ; tier_color="#ff6b35" ;;
        brain-cpu)  tier_badge="🔥 BRAIN-CPU"  ; tier_color="#ff9500" ;;
        standard)   tier_badge="⚡ STANDARD"   ; tier_color="#e8d44d" ;;
        *)          tier_badge="🌿 LIGHT"       ; tier_color="#00ff88" ;;
    esac

    local svc_badges=""
    [[ "$ipfs_active" == "true" ]] && \
        svc_badges+="<span style=\"display:inline-block;background:rgba(0,245,255,0.1);border:1px solid rgba(0,245,255,0.2);border-radius:3px;padding:2px 8px;font-size:0.72rem;color:#00f5ff;margin:2px 2px 2px 0;\">🌐&nbsp;IPFS&nbsp;(${ipfs_peers})</span>"
    [[ "$nostr_relay_active" == "true" ]] && \
        svc_badges+="<span style=\"display:inline-block;background:rgba(0,245,255,0.08);border:1px solid rgba(0,245,255,0.18);border-radius:3px;padding:2px 8px;font-size:0.72rem;color:#00f5ff;margin:2px 2px 2px 0;\">⚡&nbsp;NOSTR&nbsp;(${nostr_engine})</span>"
    [[ "$nextcloud_active" == "true" ]] && \
        svc_badges+="<span style=\"display:inline-block;background:rgba(0,255,136,0.08);border:1px solid rgba(0,255,136,0.2);border-radius:3px;padding:2px 8px;font-size:0.72rem;color:#00ff88;margin:2px 2px 2px 0;\">☁️&nbsp;NextCloud</span>"
    [[ "$ollama_active" == "true" ]] && \
        svc_badges+="<span style=\"display:inline-block;background:rgba(195,155,211,0.1);border:1px solid rgba(195,155,211,0.2);border-radius:3px;padding:2px 8px;font-size:0.72rem;color:#c39bd3;margin:2px 2px 2px 0;\">🤖&nbsp;Ollama&nbsp;LLM</span>"

    local gpu_row=""
    [[ "$gpu_detected" == "true" && "${gpu_vram:-0}" -gt 0 ]] && \
        gpu_row="<tr><td style=\"padding:3px 8px;color:rgba(255,255,255,0.45);\">GPU</td><td style=\"padding:3px 8px;color:#c39bd3;\">${gpu_name}&nbsp;·&nbsp;${gpu_vram}&nbsp;Go VRAM</td></tr>"

    local models_row=""
    [[ "$ollama_active" == "true" && -n "$ollama_models" && "$ollama_models" != "null" && "$ollama_models" != "" ]] && \
        models_row="<tr><td style=\"padding:3px 8px;color:rgba(255,255,255,0.45);\">Modèles&nbsp;IA</td><td style=\"padding:3px 8px;color:#c39bd3;font-size:0.78rem;\">${ollama_models}</td></tr>"

    local crypto_info="${crypto_score}/10"
    [[ "${crypto_ms:-0}" -gt 0 ]] && crypto_info="${crypto_score}/10&nbsp;(${crypto_ms}&nbsp;ms)"

    cat << STATION_HTML

  <!-- FICHE STATION ASTROPORT -->
  <div style="background:rgba(0,0,0,0.3);border:1px solid rgba(0,245,255,0.15);padding:18px 20px;margin-bottom:20px;border-radius:4px;">
    <div style="font-family:'Courier New',monospace;font-size:0.62rem;color:#00f5ff;letter-spacing:4px;margin-bottom:12px;">// STATION ASTROPORT · SOURCE DE CE MESSAGE</div>
    <table style="width:100%;margin-bottom:14px;"><tr>
      <td style="vertical-align:top;">
        <strong style="font-family:'Courier New',monospace;color:#00f5ff;font-size:0.95rem;">${hostname}</strong><br>
        <span style="font-family:'Courier New',monospace;font-size:0.68rem;color:rgba(255,255,255,0.3);">${UPLANETNAME:0:8}</span>
      </td>
      <td style="text-align:right;vertical-align:top;">
        <span style="display:inline-block;background:rgba(0,245,255,0.06);border:1px solid rgba(0,245,255,0.22);border-radius:3px;padding:4px 12px;font-family:'Courier New',monospace;font-size:0.75rem;color:${tier_color};">${tier_badge}&nbsp;·&nbsp;Score&nbsp;${power_score}</span>
      </td>
    </tr></table>
    <table style="width:100%;border-collapse:collapse;font-size:0.82rem;margin-bottom:14px;">
      <tr>
        <td style="padding:3px 8px;color:rgba(255,255,255,0.45);width:30%;">CPU</td>
        <td style="padding:3px 8px;color:#e0f0ff;">${cpu_model}&nbsp;·&nbsp;${cpu_cores}&nbsp;cœurs</td>
      </tr>
      <tr>
        <td style="padding:3px 8px;color:rgba(255,255,255,0.45);">RAM</td>
        <td style="padding:3px 8px;color:#e0f0ff;">${ram_gb}&nbsp;Go</td>
      </tr>
      ${gpu_row}
      <tr>
        <td style="padding:3px 8px;color:rgba(255,255,255,0.45);">Disque</td>
        <td style="padding:3px 8px;color:#e0f0ff;">✍&nbsp;${disk_write}&nbsp;MB/s&nbsp;·&nbsp;📖&nbsp;${disk_read}&nbsp;MB/s</td>
      </tr>
      <tr>
        <td style="padding:3px 8px;color:rgba(255,255,255,0.45);">Crypto</td>
        <td style="padding:3px 8px;color:#e0f0ff;">${crypto_info}</td>
      </tr>
      <tr>
        <td style="padding:3px 8px;color:rgba(255,255,255,0.45);">Capacités</td>
        <td style="padding:3px 8px;color:#00ff88;">${zencard_slots}&nbsp;ZenCard&nbsp;·&nbsp;${nostr_slots}&nbsp;slots&nbsp;NOSTR</td>
      </tr>
      ${models_row}
    </table>
    <div style="margin-bottom:12px;">${svc_badges}</div>
    <p style="margin:0;font-size:0.72rem;color:rgba(255,255,255,0.3);">Capitaine&nbsp;:&nbsp;<a href="mailto:${CAPTAIN_TARGET:-support@qo-op.com}" style="color:rgba(0,245,255,0.5);">${CAPTAIN_TARGET:-support@qo-op.com}</a>&nbsp;·&nbsp;<a href="${station_url:-https://u.copylaradio.com}" style="color:rgba(0,245,255,0.4);">Station →</a>&nbsp;·&nbsp;<a href="https://ipfs.copylaradio.com/ipns/${IPFSNODEID}/status.html" style="color:rgba(0,245,255,0.4);">📊&nbsp;Status →</a></p>
  </div>

STATION_HTML
}

_send_multipass_invitation() {
    local email="$1" amount="$2" tier_slug="$3" donor_email="${4:-$1}"

    ## Opt-out Mailjet : vérifier ~/.zen/game/nostr/$email/.mailjet
    local mailjet_optout="${HOME}/.zen/game/nostr/${email}/.mailjet"
    if [[ -f "$mailjet_optout" ]]; then
        local _ch
        _ch=$(jq -r '.channels[]?' "$mailjet_optout" 2>/dev/null)
        if echo "$_ch" | grep -qE '^(email|all)$'; then
            [[ "$JSON_OUTPUT" == "false" ]] && echo "⛔ ${email} a demandé l'opt-out (mailjet)"
            return 0
        fi
    fi

    ## Ne pas envoyer depuis une station publiquement routable (uSPOT + myIPFS)
    ## Une telle station est déjà visible — la compétition par email est pour les nœuds locaux
    _oc_pub() { [[ -n "$1" ]] && ! echo "$1" | grep -qE '(localhost|127\.|192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)'; }
    if _oc_pub "${uSPOT}" && _oc_pub "${myIPFS}"; then
        [[ "$JSON_OUTPUT" == "false" ]] && echo "ℹ️  Station publique (uSPOT+myIPFS routables) — invitation concurrentielle inactive"
        return 0
    fi

    ## Idempotence : renvoi toutes les 72h si MULTIPASS non détecté
    local now
    now=$(date +%s)
    local last_ts
    last_ts=$(grep -F "${email}:" "$INVITATION_LOG" | grep ":INVITED:" | grep -oE ':[0-9]{10}$' | tail -1 | tr -d ':')
    if [[ -n "$last_ts" ]] && (( now - last_ts < 86400 )); then
        return 0
    fi

    local captain_npub=""
    [[ -n "$CAPTAIN_TARGET" ]] && captain_npub=$(cat ~/.zen/game/nostr/${CAPTAIN_TARGET}/NPUB 2>/dev/null)

    ## URL publique de la station — domaine DNS > Yggdrasil > fallback coopératif
    local station_url
    if [[ -n "$myDOMAIN" ]]; then
        station_url="https://${myDOMAIN}"
    elif [[ -n "$uSPOT" ]]; then
        station_url="$uSPOT"
    else
        station_url="https://u.copylaradio.com"
    fi

    ## Profil NOSTR du capitaine (viewer public sur la station ou Coracle)
    local profile_url
    if [[ -n "$captain_npub" ]]; then
        profile_url="${station_url}/nostr_profile_viewer.html?npub=${captain_npub}"
    else
        profile_url="https://coracle.copylaradio.com"
    fi

    ## Sélection du template et objet selon le tier
    local template_file subject
    case "$tier_slug" in
        *parrainage*128*|*extension-128*|*satellite*|*love-box*claude*)
            template_file="${MY_PATH}/templates/invitation_satellite.html"
            subject="🌟 Bienvenue Parrain Satellite UPlanet — créez votre MULTIPASS" ;;
        *parrainage*gpu*|*module-gpu*|*constellation*|*love-box*deluxe*|*love-box*gpu*)
            template_file="${MY_PATH}/templates/invitation_constellation.html"
            subject="✨ Bienvenue Parrain Constellation UPlanet — accès GPU & #BRO" ;;
        *infrastructure*|*labo*|*genereux-donateur*|*r-d*|*recherche*)
            template_file="${MY_PATH}/templates/notification_labo.html"
            subject="🔬 Contribution Labo/R&D reçue — UPlanet" ;;
        *membre-resident*|*cloud-usage*|*adhesion*)
            template_file="${MY_PATH}/templates/invitation_locataire.html"
            subject="🎫 Votre adhésion UPlanet — créez votre MULTIPASS" ;;
        *)
            template_file="${MY_PATH}/templates/invitation_multipass.html"
            subject="Votre contribution UPlanet — créez votre MULTIPASS" ;;
    esac
    [[ ! -f "$template_file" ]] && template_file="${MY_PATH}/templates/invitation_multipass.html"

    local tmp_html
    tmp_html=$(mktemp /tmp/oc_invitation_XXXXXX.html)

    if [[ -f "$template_file" ]]; then
        sed \
            -e "s|{{EMAIL}}|${email}|g" \
            -e "s|{{DONOR_EMAIL}}|${donor_email}|g" \
            -e "s|{{AMOUNT}}|${amount}|g" \
            -e "s|{{TIER_SLUG}}|${tier_slug:-standard}|g" \
            -e "s|{{STATION_URL}}|${station_url}|g" \
            -e "s|{{PROFILE_URL}}|${profile_url}|g" \
            -e "s|{{CAPTAIN_EMAIL}}|${CAPTAIN_TARGET:-support@qo-op.com}|g" \
            -e "s|{{UPLANETNAME}}|${UPLANETNAME:0:8}|g" \
            "$template_file" > "$tmp_html"
    else
        cat > "$tmp_html" << HTMLEOF
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#222">
  <h2>🌍 Votre contribution sur UPlanet</h2>
  <p>Contribution de <strong>${amount}&nbsp;€</strong> (${tier_slug:-standard}) reçue — merci !</p>
  <p>Créez votre MULTIPASS avec l'email <code>${donor_email}</code> sur
     <a href="${station_url}">${station_url}</a> ou via
     <code>bash &lt;(curl -sL https://install.astroport.com)</code>.</p>
</div>
HTMLEOF
    fi

    ## Injecter la fiche station (substitution multi-ligne via Python)
    local _card_tmpfile
    _card_tmpfile=$(mktemp /tmp/station_card_XXXXXX.html)
    _build_station_card_html > "$_card_tmpfile"
    python3 - "$_card_tmpfile" "$tmp_html" << 'PYEOF' 2>/dev/null || \
        sed -i 's/{{STATION_CARD}}//' "$tmp_html"
import sys
with open(sys.argv[1], encoding='utf-8') as f: card = f.read()
with open(sys.argv[2], encoding='utf-8') as f: html = f.read()
with open(sys.argv[2], 'w', encoding='utf-8') as f: f.write(html.replace('{{STATION_CARD}}', card))
PYEOF
    rm -f "$_card_tmpfile"

    if [[ -x "${ASTROPORT}/tools/mailjet.sh" ]]; then
        "${ASTROPORT}/tools/mailjet.sh" \
            --template "$0" \
            --expire 7d \
            "${email}" \
            "${tmp_html}" \
            "${subject}"
        local rc=$?
        rm -f "$tmp_html"
        if [[ $rc -eq 0 ]]; then
            echo "${email}:${amount}:INVITED:$(date +%s)" >> "$INVITATION_LOG"
            [[ "$JSON_OUTPUT" == "false" ]] && echo "📧 Invitation envoyée à ${email} (${amount} €)"
        else
            [[ "$JSON_OUTPUT" == "false" ]] && echo "⚠️  Échec envoi invitation à ${email} (mailjet rc=$rc)"
        fi
    else
        rm -f "$tmp_html"
        [[ "$JSON_OUTPUT" == "false" ]] && echo "⚠️  mailjet.sh introuvable — invitation non envoyée pour ${email}"
    fi
}

[[ "$JSON_OUTPUT" == "false" ]] && echo "=== Processing current month credits ==="
while IFS= read -r credit_json; do
    [[ -z "$credit_json" ]] && continue
    slug=$(echo "$credit_json" | jq -r '.fromAccount.slug // empty')
    email=$(echo "$credit_json" | jq -r '.fromAccount.emails[0] // empty')
    amount=$(echo "$credit_json" | jq -r '.amount.value // 0')
    created_at=$(echo "$credit_json" | jq -r '.createdAt // empty')
    tier_slug=$(echo "$credit_json" | jq -r '.order.tier.slug // empty')

    [[ -z "$email" || "$email" == "null" ]] && email=$(jq -r --arg s "$slug" '.[$s] // empty' ${MY_PATH}/data/slug_email_map.json 2>/dev/null)
    [[ -z "$email" || "$email" == "null" ]] && continue

    tx_id="${email}:${amount}:${created_at}"
    grep -qF "$tx_id" "$EMISSION_LOG" 2>/dev/null && continue

    ## Routage des tiers labo/R&D : l'email cible est le Capitaine, pas le donateur
    _effective_email="$email"
    case "$tier_slug" in
        *infrastructure*|*labo*|*genereux-donateur*|*r-d*|*recherche*)
            _effective_email="${CAPTAIN_TARGET:-support@qo-op.com}" ;;
    esac

    ## Vérification MULTIPASS : local d'abord, puis swarm
    if [[ ! -f "$HOME/.zen/game/nostr/${_effective_email}/G1PUBNOSTR" ]]; then
        _swarm_hit=$(find ~/.zen/tmp/swarm -name "G1PUBNOSTR" 2>/dev/null | grep -F "/${_effective_email}/" | head -1)
        if [[ -z "$_swarm_hit" ]]; then
            [[ "$JSON_OUTPUT" == "false" ]] && echo "⚠️  MULTIPASS introuvable pour ${_effective_email} — invitation en cours"
            _send_multipass_invitation "${_effective_email}" "${amount}" "${tier_slug}" "${email}"
        else
            [[ "$JSON_OUTPUT" == "false" ]] && echo "ℹ️  MULTIPASS de ${_effective_email} présent dans le swarm (${_swarm_hit})"
        fi
        continue
    fi

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
done < <(jq -c '.' ${MY_PATH}/data/current_month.credit.json 2>/dev/null)

[[ "$JSON_OUTPUT" == "false" ]] && echo "=== ẐEN emission complete ==="
[[ -x "$MY_PATH/oc_expense_monitor.sh" ]] && "$MY_PATH/oc_expense_monitor.sh" >/dev/null 2>&1 || true
