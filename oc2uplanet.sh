#!/bin/bash
########################################################################
# Version: 0.1
# License: AGPL-3.0 (https://choosealicense.com/licenses/agpl-3.0/)
########################################################################
## OC 2 UPlanet
########################################################################
## Regularly make OpenCollective GraphQL API calls
## to fill-up members ZenCard with their donation 1€=1Ẑ (-OC%)
########################################################################
## INIT
## Charger .env local si présent (optionnel — le DID NOSTR coopératif peut suffire)
[[ -s .env ]] && export $(xargs <.env)
mkdir -p ./data

##############################################################################
## FALLBACK : DID NOSTR coopératif (kind 30800, chiffré avec $UPLANETNAME)
## Toutes les stations du même essaim partagent automatiquement OCAPIKEY/OCSLUG
##############################################################################
ASTROPORT="${HOME}/.zen/Astroport.ONE"
COOP_CONFIG="${ASTROPORT}/tools/cooperative_config.sh"

if [[ -z "${OCAPIKEY}" && -f "${COOP_CONFIG}" ]]; then
    echo "ℹ️  OCAPIKEY absent du .env → lecture depuis le DID NOSTR coopératif..."
    source "${COOP_CONFIG}" 2>/dev/null
    _coop_ocapikey=$(coop_config_get "OCAPIKEY" 2>/dev/null)
    [[ -n "${_coop_ocapikey}" ]] && export OCAPIKEY="${_coop_ocapikey}" \
        && echo "✅ OCAPIKEY chargé depuis le DID NOSTR coopératif"
    _coop_ocslug=$(coop_config_get "OCSLUG" 2>/dev/null)
    [[ -n "${_coop_ocslug}" && -z "${OCSLUG}" ]] && export OCSLUG="${_coop_ocslug}"
    _coop_oc_api=$(coop_config_get "OC_API" 2>/dev/null)
    [[ -n "${_coop_oc_api}" && -z "${OC_API}" ]] && export OC_API="${_coop_oc_api}"
fi

[[ -z "${OCAPIKEY}" ]] && echo "ERROR 0 : OCAPIKEY manquant (ni dans .env ni dans le DID NOSTR coopératif)" && exit 1

echo "MONITORING ${OCSLUG}"
echo "API key : ${OCAPIKEY:0:8}…"

#######################################################################
## UPLANET SECRETS & ORIGIN DETECTION
#######################################################################
UPLANETNAME="$(cat ~/.ipfs/swarm.key 2>/dev/null | tail -n 1)"
ORIGIN_KEY="0000000000000000000000000000000000000000000000000000000000000000"

## Si OC_API est explicitement défini dans .env → le respecter toujours
## Sinon, auto-détecter selon swarm.key (staging si ORIGIN, prod sinon)
if [[ -n "${OC_API}" ]]; then
    ## OC_API forcé via .env — priorité absolue
    IS_ORIGIN=0
    echo "✅ OC_API forcé via .env : ${OC_API}"
elif [[ "$UPLANETNAME" == "$ORIGIN_KEY" || -z "$UPLANETNAME" ]]; then
    IS_ORIGIN=1
    OC_API="https://api-staging.opencollective.com/graphql/v2"
    echo "⚠ MODE ORIGIN (DEV) — Using OC staging API"
else
    IS_ORIGIN=0
    OC_API="https://api.opencollective.com/graphql/v2"
    echo "✅ MODE PRODUCTION — Using OC production API"
fi
#######################################################################
### CAPTAIN CREDENTIALS ##
#######################################################################
if [[ -z $UPLANETNAME ]]; then
    echo "MISSING PRIVATE SWARM ACTIVATED ASTROPORT STATION"
    exit 1
fi
## CLEAN OLD data
find ./data -mtime +1 -type f -exec rm '{}' \;

## DEFINE TIME
# Get today's date in the format YYYY-MM-DD
today=$(date +"%Y-%m-%d")
# Début du mois en cours
start_of_month=$(date -d "$(date +%Y-%m-01)" +"%Y-%m-%d")
# Début du mois dernier
start_of_last_month=$(date -d "$(date +%Y-%m-01) -1 month" +"%Y-%m-%d")
# Fin du mois dernier
end_of_last_month=$(date -d "$(date +%Y-%m-01) -1 day" +"%Y-%m-%d")
echo "today : ${today}"
echo "start_of_month : ${start_of_month}"
echo "start_of_last_month : ${start_of_last_month}"
echo "end_of_last_month : ${end_of_last_month}"

################################################## ALL Backers (email)
  #~ -d '{
    #~ "query": "query account($slug: String) {
      #~ account(slug: $slug) {
        #~ name
        #~ slug
        #~ members(role: BACKER, limit: 200) {
          #~ totalCount
          #~ nodes {
            #~ account {
              #~ name
              #~ slug
              #~ emails
            #~ }
          #~ }
        #~ }
      #~ }
    #~ }",
    #~ "variables": {
      #~ "slug": "'${OCSLUG}'"
    #~ }
  #~ }'
# Fichier contenant les correspondances slug:email
SLUG_EMAIL_FILE="data/slugemail.list"

[[ ! -s data/backers.json ]] \
&& curl -sX POST   \
        -H "Content-Type: application/json" \
        -H "Personal-Token: ${OCAPIKEY}" \
        -d '{
    "query": "query account($slug: String) { account(slug: $slug) { name slug members(role: BACKER, limit: 200) { totalCount nodes { account { name slug emails } } } } }",
    "variables": {
      "slug": "'${OCSLUG}'"
    }
  }'  ${OC_API} > data/backers.json

echo "Collective $slug BACKERS : data/backers.json"

# EXTRACT slugs and emails
echo "$SLUG_EMAIL_FILE"
cat data/backers.json \
| jq -r '.data.account.members.nodes[] | "\(.account.slug):\(.account.emails[0])"' > $SLUG_EMAIL_FILE

# Créer un fichier JSON des correspondances slug-email
echo "data/slug_email_map.json"
cat $SLUG_EMAIL_FILE | awk -F: '{print "{\"" $1 "\": \"" $2 "\"}"}' | jq -s 'add' > data/slug_email_map.json

################################################## TRANSACTIONS RECEIVED (with order/tier info)
echo "Collective $slug TX : data/tx.json"
curl -sX POST   \
        -H "Content-Type: application/json" \
        -H "Personal-Token: ${OCAPIKEY}" \
        -d '{
    "query": "query ($slug: String) { account(slug: $slug) { name slug transactions(limit: 100, type: CREDIT) { totalCount nodes { type fromAccount { name slug emails } amount { value currency } order { tier { slug name } } createdAt } } } }",
    "variables": {
      "slug": "'${OCSLUG}'"
    }
  }'  ${OC_API} > data/tx.json


# Crédit du mois dernier
LAST_MONTH_CREDIT_FILE="data/last_month.credit.json"
echo "$LAST_MONTH_CREDIT_FILE"
cat data/tx.json | jq --arg start_of_last_month "$start_of_last_month" --arg end_of_last_month "$end_of_last_month" '
  .data.account.transactions.nodes[] |
  select(.type == "CREDIT" and (.createdAt >= $start_of_last_month and .createdAt <= $end_of_last_month))
' > $LAST_MONTH_CREDIT_FILE


# crédits du mois en cours
echo "data/current_month.credit.json"
cat data/tx.json | jq --arg start_of_month "$start_of_month" '
  .data.account.transactions.nodes[] |
  select(.type == "CREDIT" and (.createdAt >= $start_of_month))
' > data/current_month.credit.json


# Credits reçus hier.
echo "data/yesterday.credit.json"
cat data/tx.json | jq --arg yesterday "$yesterday" '
  .data.account.transactions.nodes[] |
  select(.type == "CREDIT" and (.createdAt | startswith($yesterday)))
' > data/yesterday.credit.json


## data/*.credit.json EXEMPLE
#~ {
  #~ "type": "CREDIT",
  #~ "fromAccount": {
    #~ "name": "Astroport",
    #~ "slug": "monnaie-libre",
    #~ "emails": null
  #~ },
  #~ "amount": {
    #~ "value": 259.53,
    #~ "currency": "EUR"
  #~ },
  #~ "createdAt": "2023-02-06T10:15:28.042Z"
#~ }

########################################################################
## EMISSION ẐEN — Match OC transactions to MULTIPASS accounts
########################################################################
MY_PATH="$(cd "$(dirname "$0")" && pwd)"
ASTROPORT="$HOME/.zen/Astroport.ONE"
EMISSION_LOG="./data/emission.log"
touch "$EMISSION_LOG"

## Map OC tier slug → UPLANET.official.sh command
## OC tier slugs (from opencollective.com/monnaie-libre/projects/coeurbox/contribute/):
##   parrainage-infrastructure-extension-128-go  → Satellite sociétaire (ZEN Card → SCIC 33/33/33/1)
##   parrainage-infrastructure-module-gpu-1-24   → Constellation sociétaire (ZEN Card → SCIC 33/33/33/1)
##   cotisation-services-cloud-usage             → Cloud locataire (recharge MULTIPASS immédiate)
##   membre-resident-soutien-mensuel             → Membre locataire (recharge MULTIPASS mensuelle)
dispatch_zen_emission() {
    local email="$1" amount="$2" tier_slug="$3"
    local zen_amount=$(echo "scale=2; $amount * 1" | bc)

    case "$tier_slug" in
        *parrainage*128-go*|*extension-128*|*satellite*)
            ## Satellite 50€/an → process_societaire uniquement (ZEN Card → SCIC 33/33/33/1)
            ## Le MULTIPASS reçoit son crédit initial lors de make_NOSTRCARD.sh (PRIMO TX)
            ## Le montant offert est paramétré dans le DID Zen Economy de l'essaim
            echo "  🛰 Satellite (${tier_slug}) → process_societaire"
            ${ASTROPORT}/UPLANET.official.sh -s "${email}" -t satellite -m "${zen_amount}"
            return $?
            ;;
        *parrainage*gpu*|*module-gpu*|*constellation*)
            ## Constellation 540€/an → process_societaire uniquement (ZEN Card → SCIC 33/33/33/1)
            ## Le MULTIPASS reçoit son crédit initial lors de make_NOSTRCARD.sh (PRIMO TX)
            echo "  🌟 Constellation (${tier_slug}) → process_societaire"
            ${ASTROPORT}/UPLANET.official.sh -s "${email}" -t constellation -m "${zen_amount}"
            return $?
            ;;
        *cotisation*|*cloud-usage*|*services-cloud*)
            ## Cotisation cloud usage → locataire (recharge MULTIPASS immédiate)
            echo "  ☁ Cloud usage (${tier_slug}) → process_locataire"
            ${ASTROPORT}/UPLANET.official.sh -l "${email}" -m "${zen_amount}"
            return $?
            ;;
        *membre-resident*|*soutien-mensuel*)
            ## Membre résident soutien mensuel → locataire (MULTIPASS cycle 4 semaines)
            echo "  🏠 Membre résident (${tier_slug}) → process_locataire"
            ${ASTROPORT}/UPLANET.official.sh -l "${email}" -m "${zen_amount}"
            return $?
            ;;
        "")
            ## No tier info — default to locataire
            echo "  ⚠ No tier slug — default process_locataire"
            ${ASTROPORT}/UPLANET.official.sh -l "${email}" -m "${zen_amount}"
            return $?
            ;;
        *)
            ## Unknown tier — log and default to locataire
            echo "  ❓ Unknown tier '${tier_slug}' — default process_locataire"
            ${ASTROPORT}/UPLANET.official.sh -l "${email}" -m "${zen_amount}"
            return $?
            ;;
    esac
}

## Process current month CREDIT transactions
echo "=== Processing current month credits ==="
while IFS= read -r credit_json; do
    [[ -z "$credit_json" ]] && continue

    slug=$(echo "$credit_json" | jq -r '.fromAccount.slug // empty')
    email=$(echo "$credit_json" | jq -r '.fromAccount.emails[0] // empty')
    amount=$(echo "$credit_json" | jq -r '.amount.value // 0')
    currency=$(echo "$credit_json" | jq -r '.amount.currency // "EUR"')
    created_at=$(echo "$credit_json" | jq -r '.createdAt // empty')
    tier_slug=$(echo "$credit_json" | jq -r '.order.tier.slug // empty')

    ## If email is null in transaction, look up from slug:email map
    if [[ -z "$email" || "$email" == "null" ]]; then
        email=$(jq -r --arg s "$slug" '.[$s] // empty' data/slug_email_map.json 2>/dev/null)
    fi

    [[ -z "$email" || "$email" == "null" ]] && echo "⚠ No email for slug=$slug — skipping" && continue

    ## Idempotency: check if transaction already processed
    tx_id="${email}:${amount}:${created_at}"
    if grep -qF "$tx_id" "$EMISSION_LOG" 2>/dev/null; then
        echo "⏭ Already processed: $tx_id"
        continue
    fi

    ## Check MULTIPASS exists
    if [[ ! -f "$HOME/.zen/game/nostr/${email}/G1PUBNOSTR" ]]; then
        echo "⚠ No MULTIPASS for ${email} — skipping"
        continue
    fi

    ## Net amount from OC (fees already deducted). 1€ = 1Ẑ
    echo "💰 ${email}: ${amount} ${currency} (tier: ${tier_slug:-unknown})"

    ## Dispatch to correct UPLANET.official.sh mode
    if [[ -x "${ASTROPORT}/UPLANET.official.sh" ]]; then
        dispatch_zen_emission "${email}" "${amount}" "${tier_slug}"
        RESULT=$?
        if [[ $RESULT -eq 0 ]]; then
            echo "  ✅ Emission OK"
            echo "${tx_id}:${amount}:${tier_slug}:$(date +%s):OK" >> "$EMISSION_LOG"
        else
            echo "  ❌ Emission FAILED (exit $RESULT)"
            echo "${tx_id}:${amount}:${tier_slug}:$(date +%s):FAIL" >> "$EMISSION_LOG"
        fi
    else
        echo "  ❌ UPLANET.official.sh not found at ${ASTROPORT}"
    fi

done < <(jq -c '.' data/current_month.credit.json 2>/dev/null)

echo "=== ẐEN emission complete ==="
echo "Log: $EMISSION_LOG"

########################################################################
## EXPENSE MONITORING — Refund rejected restitutions
########################################################################
if [[ -x "$MY_PATH/oc_expense_monitor.sh" ]]; then
    echo ""
    echo "=== Running expense monitor (restitution refunds) ==="
    "$MY_PATH/oc_expense_monitor.sh" || echo "⚠ Expense monitor returned non-zero"
fi
