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

set -euo pipefail

# Load environment variables
[[ ! -s .env ]] && echo "ERROR: missing .env" && exit 1
export $(xargs <.env)

# Constants
DATA_DIR="./data"
SLUG_EMAIL_FILE="$DATA_DIR/slugemail.list"
LAST_MONTH_CREDIT_FILE="$DATA_DIR/last_month.credit.json"
UPDATED_LAST_MONTH_CREDIT_FILE="$DATA_DIR/last_month.credit.updated.json"

# Create necessary directories
mkdir -p "$DATA_DIR"

# Log the monitoring details
echo "MONITORING COLLECTIVE : ${OCSLUG}"
echo "Using API key: ${OCAPIKEY}"

########################### PROD CRYPTO KEYS
# Load UPlanet secrets
# Load Captain credentials
#~ UPLANETNAME="$(tail -n 1 ~/.ipfs/swarm.key)"
#~ source ~/.zen/game/players/.current/secret.june
#~ echo "SALT = $SALT"
#~ echo "PEPPER = $PEPPER"

# Clean old data files
find "$DATA_DIR" -mtime +1 -type f -exec rm '{}' \;

# Define time variables
today=$(date +"%Y-%m-%d")
start_of_month=$(date -d "$(date +%Y-%m-01)" +"%Y-%m-%d")
start_of_last_month=$(date -d "$(date +%Y-%m-01) -1 month" +"%Y-%m-%d")
end_of_last_month=$(date -d "$(date +%Y-%m-01) -1 day" +"%Y-%m-%d")

# Fetch backers data if not already present
if [[ ! -s "$DATA_DIR/backers.json" ]]; then
  curl -sX POST \
    -H "Content-Type: application/json" \
    -H "Personal-Token: ${OCAPIKEY}" \
    -d '{
      "query": "query account($slug: String) { account(slug: $slug) { name slug members(role: BACKER, limit: 200) { totalCount nodes { account { name slug emails } } } } }",
      "variables": { "slug": "'${OCSLUG}'" }
    }' \
    https://api.opencollective.com/graphql/v2 > "$DATA_DIR/backers.json"
fi

echo "Collective $OCSLUG BACKERS: $DATA_DIR/backers.json"

# Extract slugs and emails
jq -r '.data.account.members.nodes[] | "\(.account.slug):\(.account.emails[0])"' "$DATA_DIR/backers.json" > "$SLUG_EMAIL_FILE"

# Fetch transactions data
curl -sX POST \
  -H "Content-Type: application/json" \
  -H "Personal-Token: ${OCAPIKEY}" \
  -d '{
    "query": "query ($slug: String) { account(slug: $slug) { name slug transactions(limit: 100, type: CREDIT) { totalCount nodes { type fromAccount { name slug emails } amount { value currency } createdAt } } } }",
    "variables": { "slug": "'${OCSLUG}'" }
  }' \
  https://api.opencollective.com/graphql/v2 > "$DATA_DIR/tx.json"

echo "Collective $OCSLUG TX: $DATA_DIR/tx.json"

# Extract last month's credits
jq --arg start_of_last_month "$start_of_last_month" --arg end_of_last_month "$end_of_last_month" '
  .data.account.transactions.nodes[] |
  select(.type == "CREDIT" and (.createdAt >= $start_of_last_month and .createdAt <= $end_of_last_month))
' "$DATA_DIR/tx.json" > "$LAST_MONTH_CREDIT_FILE"

echo "$LAST_MONTH_CREDIT_FILE"
