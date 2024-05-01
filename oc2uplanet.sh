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

## CLEAN OLD data
find ./data -mtime +1 -type f -exec rm '{}' \;

## DEFINE TIME
# Get today's date in the format YYYY-MM-DD
today=$(date +"%Y-%m-%d")
yesterday=$(date -d 'yesterday' +'%Y-%m-%d')
# Get the start and end dates for the current week
start_of_week=$(date -d "last monday" +"%Y-%m-%d")
# Get the start and end dates for the current month
start_of_month=$(date -d "$(date +%Y-%m-01)" +"%Y-%m-%d")
# Get the start and end dates for the current year
start_of_year=$(date -d "$(date +%Y-01-01)" +"%Y-%m-%d")

## Get ALL Backers emails
[[ ! -s data/backers.json ]] \
&& curl -sX POST   -H "Content-Type: application/json"   -H "Personal-Token: ${OCAPIKEY}"   -d '{
    "query": "query account($slug: String) { account(slug: $slug) { name slug members(role: BACKER, limit: 100) { totalCount nodes { account { name slug emails } } } } }",
    "variables": {
      "slug": "'${OCSLUG}'"
    }
  }'   https://api.opencollective.com/graphql/v2 > data/backers.json

# EXTRACT slugs and emails
cat data/backers.json \
| jq -r '.data.account.members.nodes[] | "\(.account.slug):\(.account.emails[0])"' > data/slugemail.list

# SEARCH FOR YESTERDAY CREDIT
curl -X POST  -H "Content-Type: application/json"    -H "Content-Personal-Token: dedab23fbf01dc62a9b5d894aa696486dc0fe36201dc62a9b5d894aa696486dc0fe362"   -d '{
    "query": "query ($slug: String) { account(slug: $slug) { name slug transactions(limit: 10, type: CREDIT) { totalCount nodes { type fromAccount { name slug emails } amount { value currency } createdAt } } } }",
    "variables": {
      "slug": "'${OCSLUG}'"
    }
  }'   https://api.opencollective.com/graphql/v2 \
    | jq --arg yesterday "$yesterday" '.data.account.transactions.nodes[] | select(.type == "CREDIT" and (.createdAt | startswith($yesterday)))' \
    > data/yesterday.credit.json

## data/yesterday.credit.json EXEMPLE
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

cat data/yesterday.credit.json | jq '.fromAccount.slug, .amount.value' > data/bingo.json

## bingo.json !! ?
# search for UPlanet "email" account
# and send Zen accordingly

## CONTROL WALLET PRIMAL TRANSACTION CONCORDANCE
