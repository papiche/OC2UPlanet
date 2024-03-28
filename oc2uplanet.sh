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

while read line; do
    pslug=$(echo $line | cut -d ':' -f 1)
    pmail=$(echo $line | cut -d ':' -f 2)
    ## GET DEBIT
    echo "======================================================"
    echo "$line"
    [[ ! -s data/${pmail}.DEBIT.json ]] \
    && curl -sX POST  -H "Content-Type: application/json"    -H "Content-Personal-Token: ${OCAPIKEY}"   -d '{
        "query": "query ($slug: String) { account(slug: $slug) { name slug transactions(limit: 50, type: DEBIT) { totalCount nodes { type fromAccount { name slug } amount { value currency } createdAt } } } }",
        "variables": {
          "slug": "'${pslug}'"
        }
      }'   https://api.opencollective.com/graphql/v2 | jq > data/${pmail}.DEBIT.json

# Function to convert date to Unix timestamp
date_to_unix() {
    date -d "$1" +"%s"
}

# Calculate total for today
total_today=$(jq -r --arg today "$today" '.data.account.transactions.nodes[] | select(.createdAt | startswith("$today")) | .amount.value' data/${pmail}.DEBIT.json | awk '{s+=$1} END {print s}')
# Calculate total for this week
total_week=$(jq -r --arg start "$start_of_week" '.data.account.transactions.nodes[] | select(.createdAt >= $start) | .amount.value' data/${pmail}.DEBIT.json 2>/dev/null | awk '{s+=$1} END {print s}') || 0
# Calculate total for this month
total_month=$(jq -r --arg start "$start_of_month" '.data.account.transactions.nodes[] | select(.createdAt >= $start) | .amount.value' data/${pmail}.DEBIT.json 2>/dev/null | awk '{s+=$1} END {print s}') || 0
# Calculate total for this year
total_year=$(jq -r --arg start "$start_of_year" '.data.account.transactions.nodes[] | select(.createdAt >= $start) | .amount.value' data/${pmail}.DEBIT.json 2>/dev/null | awk '{s+=$1} END {print s}'  2>/dev/null) || 0
# Calculate total overall
# echo "jq -r '.data.account.transactions.nodes[].amount.value' data/${pmail}.DEBIT.json | awk '{s+=\$1} END {print s}'"
total_overall=$(jq -r '.data.account.transactions.nodes[].amount.value' data/${pmail}.DEBIT.json | awk '{s+=$1} END {print s}' 2>/dev/null)

last_transaction=$(jq -r '.data.account.transactions.nodes | sort_by(.createdAt) | last' data/${pmail}.DEBIT.json 2>/dev/null)

# Print the totals
echo "Total for $today: $total_today EUR"
echo "Total from $start_of_week: $total_week EUR"
echo "Total from $start_of_month: $total_month EUR"
echo "Total from $start_of_year: $total_year EUR"
echo "Total overall: $total_overall EUR"
echo "Details of the last transaction:"
echo "$last_transaction"
    echo "---------- cat data/${pmail}.DEBIT.json | jq -r"

    sleep 5

done < data/slugemail.list

