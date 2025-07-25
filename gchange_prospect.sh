#!/bin/bash
########################################################################
# Gchange Prospect Database Builder
# Version: 0.2 - Cross-Enrichment Edition
# License: AGPL-3.0
########################################################################
# Fetches gchange users and enriches their profiles.
# If a linked Cesium account (pubkey) is found, it also enriches
# the g1prospect.json database.
########################################################################

set -euo pipefail

# --- Configuration ---
PROSPECT_FILE="$HOME/.zen/game/gchange_prospect.json"
G1_PROSPECT_FILE="$HOME/.zen/game/g1prospect.json"
TEMP_DIR="$HOME/.zen/tmp"
# Gchange API
GCHANGE_ADS_API="https://data.gchange.fr/market/record/_search"
GCHANGE_USER_API_TPL="https://data.gchange.fr/user/profile"
# Cesium/G1 API for cross-enrichment
G1_WOT_API="https://g1.duniter.org/wot/members"
CESIUM_API="https://g1.data.e-is.pro"

# --- Trap for graceful exit ---
cleanup_on_exit() {
    echo ""
    echo "Script interrupted. Progress is saved."
    exit 1
}

trap cleanup_on_exit INT TERM

# --- Functions ---

# Create necessary directories
mkdir -p "$(dirname "$PROSPECT_FILE")"
mkdir -p "$TEMP_DIR"

# Fetches the Ğ1 WoT member list to resolve pubkeys to UIDs.
# Caches the data for 1 hour to avoid excessive requests.
fetch_g1_wot_data() {
    local wot_file="$TEMP_DIR/g1_wot_data.json"
    # Check for cached data less than 60 minutes old.
    if [ -f "$wot_file" ]; then
        local now
        now=$(date +%s)
        local file_mod_time
        file_mod_time=$(stat -c %Y "$wot_file")
        if (( (now - file_mod_time) < 3600 )); then
            echo "Using cached Ğ1 WoT data (less than 1 hour old)."
            return
        fi
    fi

    echo "Fetching/Refreshing Ğ1 WoT members list..."
    if curl -# -sk -o "$wot_file" "$G1_WOT_API"; then
        echo "Ğ1 WoT data fetched successfully."
    else
        echo "ERROR: Failed to fetch Ğ1 WoT data. Cesium account enrichment will be skipped for this run."
        # Create an empty file to avoid re-fetching on every ad.
        echo '{ "results": [] }' > "$wot_file"
    fi
}

# Fetches lightweight metadata for the latest ads to identify potential new users
fetch_ad_metadata() {
    local metadata_file="$TEMP_DIR/gchange_ad_metadata.json"
    echo "Fetching metadata for the latest 1000 ads..."
    echo "(This is a quick, lightweight query to identify new users...)"

    # We only fetch the ad's ID and its issuer's ID. This is very fast.
    local query='{ "size": 1000, "query": { "match_all": {} }, "_source": ["issuer"] }'

    # Fetch data and save the 'hits' array to a file
    curl -# -sk -XPOST "$GCHANGE_ADS_API" -H "Content-Type: application/json" -d "$query" |
        jq '.hits.hits' > "$metadata_file"

    echo "Metadata fetch complete."

    if [[ ! -s "$metadata_file" ]]; then
        echo "ERROR: Could not fetch any ad metadata from gchange."
        return 1
    fi
}

# Enrich the g1prospect.json file if a new Cesium pubkey is found
enrich_g1_database() {
    local cesium_pubkey=$1
    echo "    -> Found linked Cesium account: $cesium_pubkey"

    # Ensure G1 prospect file exists
    if [[ ! -f "$G1_PROSPECT_FILE" ]] || ! jq empty "$G1_PROSPECT_FILE" 2>/dev/null; then
        echo "    -> Initializing G1 prospect file..."
        cat > "$G1_PROSPECT_FILE" << EOF
{
  "metadata": { "created_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")", "updated_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")", "total_members": 0, "source": "g1_wot_cesium" },
  "members": []
}
EOF
    fi

    # Check if this pubkey is already in the G1 database
    if ! jq -e --arg pk "$cesium_pubkey" '.members[] | select(.pubkey == $pk)' "$G1_PROSPECT_FILE" >/dev/null 2>&1; then
        echo "    -> Pubkey not in G1 database. Adding it..."

        # Find the corresponding UID from the WoT data
        local wot_file="$TEMP_DIR/g1_wot_data.json"
        local cesium_uid
        cesium_uid=$(jq -r --arg pk "$cesium_pubkey" '.results[] | select(.pubkey == $pk) | .uid' "$wot_file")

        # Fetch the full Cesium profile regardless of WoT status
        local cesium_profile_url="$CESIUM_API/user/profile/$cesium_pubkey?_source_exclude=avatar._content"
        local cesium_profile_data
        cesium_profile_data=$(curl -sk "$cesium_profile_url" | jq -c '._source' || echo "{}")

        if [[ -z "$cesium_uid" ]]; then
            echo "    -> UID not found in WoT. Treating as a non-member wallet."
            
            # Use the profile's title as a fallback UID
            local cesium_uid_fallback
            cesium_uid_fallback=$(echo "$cesium_profile_data" | jq -r '.title // "(Wallet User)"')
            
            # Create and save the new G1 member from a non-WoT source
            local new_g1_member
            new_g1_member=$(jq -n \
              --arg pubkey "$cesium_pubkey" \
              --arg uid "$cesium_uid_fallback" \
              --arg added_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
              --argjson profile "$cesium_profile_data" \
              '{ "pubkey": $pubkey, "uid": $uid, "added_date": $added_date, "profile": $profile, "source": "g1_wallet_discovered_via_gchange" }')

            jq --argjson member "$new_g1_member" '.members += [$member]' "$G1_PROSPECT_FILE" > "$G1_PROSPECT_FILE.new"
            mv "$G1_PROSPECT_FILE.new" "$G1_PROSPECT_FILE"
            echo "    -> Successfully added $cesium_uid_fallback ($cesium_pubkey) to G1 prospect database."
        else
            # This is a certified member from the WoT
            local new_g1_member
            new_g1_member=$(jq -n \
              --arg pubkey "$cesium_pubkey" \
              --arg uid "$cesium_uid" \
              --arg added_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
              --argjson profile "$cesium_profile_data" \
              '{ "pubkey": $pubkey, "uid": $uid, "added_date": $added_date, "profile": $profile, "source": "g1_wot_discovered_via_gchange" }')

            jq --argjson member "$new_g1_member" '.members += [$member]' "$G1_PROSPECT_FILE" > "$G1_PROSPECT_FILE.new"
            mv "$G1_PROSPECT_FILE.new" "$G1_PROSPECT_FILE"
            echo "    -> Successfully added $cesium_uid ($cesium_pubkey) to G1 prospect database."
        fi
    else
        echo "    -> Cesium account already in G1 database. Nothing to do."
    fi
}


# Processes ad metadata incrementally, fetching full data for new users,
# and enriching existing users with new ad discoveries.
process_ads_incrementally() {
    local metadata_file="$TEMP_DIR/gchange_ad_metadata.json"
    if [[ ! -f "$metadata_file" ]]; then
        echo "Ad metadata file not found! Please run 'fetch_ad_metadata' first."
        return 1
    fi

    echo "Scanning ads and processing users incrementally..."

    # Initialize gchange prospect file if it doesn't exist or is invalid
    if [[ ! -f "$PROSPECT_FILE" ]] || ! jq empty "$PROSPECT_FILE" 2>/dev/null; then
        echo "Creating new gchange prospect database structure at $PROSPECT_FILE"
        cat > "$PROSPECT_FILE" << EOF
{
  "metadata": { "created_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")", "updated_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")", "total_members": 0, "source": "gchange_users" },
  "members": []
}
EOF
    fi

    local total_ads
    total_ads=$(jq 'length' < "$metadata_file")
    local processed_ads=0
    local new_members=0

    while IFS= read -r ad_meta; do
        processed_ads=$((processed_ads + 1))
        local user_id
        user_id=$(echo "$ad_meta" | jq -r '._source.issuer | select(. != null)')
        local ad_id
        ad_id=$(echo "$ad_meta" | jq -r '._id')

        echo "Processing ad $processed_ads/$total_ads ($ad_id)... "

        if [[ -z "$user_id" ]]; then
            echo " -> No issuer. Skipping."
            continue
        fi
        
        # Check if user exists in the main gchange database
        if jq -e --arg uid "$user_id" '.members[] | select(.uid == $uid)' "$PROSPECT_FILE" >/dev/null 2>&1; then
            # --- EXISTING GCHANGE USER ---
            echo " -> User $user_id already in gchange database. Checking for new activity..."
            
            # Activity 1: Check for new ad
            if jq -e --arg ad_id "$ad_id" --arg uid "$user_id" '([.members[] | select(.uid == $uid) | .detected_ads[]?] | index($ad_id)) == null' "$PROSPECT_FILE" >/dev/null; then
                echo "    -> New ad $ad_id found. Adding to detected_ads."
                jq --arg ad_id "$ad_id" --arg uid "$user_id" '
                    ( .members[] | select(.uid == $uid) | .detected_ads ) |= if . == null then [$ad_id] else . + [$ad_id] end
                    | .metadata.updated_date = "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
                ' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
                mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
            else
                echo "    -> Ad $ad_id already listed."
            fi

            # Activity 2: Check for linked Cesium account and enrich G1 database
            local existing_profile
            existing_profile=$(jq -c --arg uid "$user_id" '.members[] | select(.uid == $uid) | .profile' "$PROSPECT_FILE")
            local cesium_pubkey
            cesium_pubkey=$(echo "$existing_profile" | jq -r '.pubkey | select(. != null)')
            if [[ -n "$cesium_pubkey" ]]; then
                enrich_g1_database "$cesium_pubkey"
            fi
        else
            # --- NEW GCHANGE USER ---
            echo " -> New user found: $user_id"
            
            # 1. Fetch gchange profile
            echo "    -> Fetching profile for user $user_id..."
            local user_api_url="$GCHANGE_USER_API_TPL/$user_id?_source_exclude=avatar._content"
            local profile_data
            profile_data=$(curl -sk "$user_api_url" | jq -c '._source' || echo "{}")

            # 2. Fetch full ad data
            echo "    -> Fetching full details for ad $ad_id (excluding images)..."
            local ad_details_query
            ad_details_query=$(jq -n --arg ad_id "$ad_id" '{ "query": { "ids": { "values": [$ad_id] } } }')
            local ad_details_response
            ad_details_response=$(curl -# -sk -XPOST "$GCHANGE_ADS_API" -H "Content-Type: application/json" -d "$ad_details_query")
            local source_ad
            source_ad=$(echo "$ad_details_response" | jq -c '.hits.hits[0]._source | del(.thumbnail, .pictures, .gallery, .image, .images, .avatar, ."*.content")')

            if [[ -z "$source_ad" || "$source_ad" == "null" ]]; then
                echo "    -> ERROR: Failed to fetch or process details for ad $ad_id. Skipping user."
                continue
            fi
            
            # 3. Create and save the new gchange member
            echo "    -> Saving to gchange database..."
            local new_member
            new_member=$(jq -n \
              --arg uid "$user_id" \
              --arg ad_id "$ad_id" \
              --arg added_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
              --argjson profile "$profile_data" \
              --argjson source_ad "$source_ad" \
              '{ "uid": $uid, "added_date": $added_date, "profile": $profile, "source": "gchange", "discovery_ad": $source_ad, "detected_ads": [$ad_id] }')
            
            jq --argjson member "$new_member" '.members += [$member]' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
            mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
            
            new_members=$((new_members + 1))

            # 4. Check for linked Cesium account and enrich G1 database
            local cesium_pubkey_new
            cesium_pubkey_new=$(echo "$profile_data" | jq -r '.pubkey | select(. != null)')
            if [[ -n "$cesium_pubkey_new" ]]; then
                enrich_g1_database "$cesium_pubkey_new"
            fi
            echo "    -> Done."
        fi
    done < <(jq -c '.[]' "$metadata_file")
    
    # Final metadata update for gchange file
    local final_count
    final_count=$(jq '.members | length' "$PROSPECT_FILE")
    jq '.metadata.updated_date = "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'" | .metadata.total_members = ('$final_count')' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
    mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
    
    echo "Processing complete."
    if [[ $new_members -gt 0 ]]; then
        echo "New gchange members added: $new_members"
    else
        echo "No new gchange users were found, but existing users may have been updated."
    fi
    echo "Total members in gchange database: $final_count"
}

# Shows statistics about the created database
show_statistics() {
    if [[ ! -f "$PROSPECT_FILE" ]]; then
        echo "Database file not found."
        return
    fi
    echo ""
    echo "=== Gchange Prospect Database Statistics ==="
    local total_members
    total_members=$(jq -r '.metadata.total_members' "$PROSPECT_FILE")
    local updated_date
    updated_date=$(jq -r '.metadata.updated_date' "$PROSPECT_FILE")
    
    echo "Total members: $total_members"
    echo "Last updated: $updated_date"
    echo "Database file: $PROSPECT_FILE"
}

# --- Main Execution ---
main() {
    echo "Starting Gchange prospect database build (Cross-Enrichment Mode)..."
    fetch_g1_wot_data
    fetch_ad_metadata
    process_ads_incrementally
    show_statistics
    echo ""
    echo "=== Gchange Prospect Database Build Complete ==="
}

# Run main function
main "$@" 