#!/bin/bash
########################################################################
# Version: 0.1
# License: AGPL-3.0 (https://choosealicense.com/licenses/agpl-3.0/)
########################################################################
## OC 2 UPlanet
########################################################################
## Regularly make https://api.opencollective.com/graphql/v2 calls
## to fill-up members ZenCard with their donation 1€=1Ẑ (-OC%)
########################################################################
## INIT
[[ ! -s .env ]] && echo "ERROR 0 missing .env" && exit 1
export $(xargs <.env)
mkdir -p ./data

echo "MONITORING ${OCSLUG}"
echo "API key : ${OCAPIKEY}"

#######################################################################
## UPLANET SECRETS
#######################################################################
UPLANETNAME="$(cat ~/.ipfs/swarm.key 2>/dev/null | tail -n 1)"
#######################################################################
### CAPTAIN CREDENTIALS ##
#######################################################################
if [[ ! -z $UPLANETNAME ]]; then
    source ~/.zen/game/players/.current/secret.june
    echo SALT = $SALT
    echo PEPPER = $PEPPER
else
    echo "MISSING PRIVATE SWARM ACTIVATED ASTROPORT STATION"
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
  }'  https://api.opencollective.com/graphql/v2 > data/backers.json

echo "Collective $slug BACKERS : data/backers.json"

# EXTRACT slugs and emails
echo "$SLUG_EMAIL_FILE"
cat data/backers.json \
| jq -r '.data.account.members.nodes[] | "\(.account.slug):\(.account.emails[0])"' > $SLUG_EMAIL_FILE

# Créer un fichier JSON des correspondances slug-email
echo "data/slug_email_map.json"
cat $SLUG_EMAIL_FILE | awk -F: '{print "{\"" $1 "\": \"" $2 "\"}"}' | jq -s 'add' > data/slug_email_map.json

################################################## TRANSACTIONS RECEIVED
echo "Collective $slug TX : data/tx.json"
curl -sX POST   \
        -H "Content-Type: application/json" \
        -H "Personal-Token: ${OCAPIKEY}" \
        -d '{
    "query": "query ($slug: String) { account(slug: $slug) { name slug transactions(limit: 100, type: CREDIT) { totalCount nodes { type fromAccount { name slug emails } amount { value currency } createdAt } } } }",
    "variables": {
      "slug": "'${OCSLUG}'"
    }
  }'  https://api.opencollective.com/graphql/v2 > data/tx.json


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

## bingo.json !! ?
# search for UPlanet "email" account
## Astroport.ONE
# and send Zen accordingly

## CONTROL WALLET PRIMAL TRANSACTION CONCORDANCE
