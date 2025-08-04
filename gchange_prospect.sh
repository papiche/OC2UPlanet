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

# Function to display progress
show_progress() {
    local current=$1
    local total=$2
    local percentage=$((current * 100 / total))
    local bar_length=50
    local filled=$((current * bar_length / total))
    local empty=$((bar_length - filled))
    
    printf "\r["
    printf "%${filled}s" | tr ' ' '#'
    printf "%${empty}s" | tr ' ' '-'
    printf "] %d%% (%d/%d)" "$percentage" "$current" "$total"
}

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
    local gchange_uid=$2  # Add Gchange UID parameter
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

    # Create lookup table of existing G1 pubkeys (much faster than checking one by one)
    local g1_pubkeys_file="$TEMP_DIR/g1_existing_pubkeys.txt"
    if [[ ! -f "$g1_pubkeys_file" ]]; then
        jq -r '.members[].pubkey' "$G1_PROSPECT_FILE" 2>/dev/null | sort > "$g1_pubkeys_file" || touch "$g1_pubkeys_file"
    fi
    
    # Check if this pubkey is already in the G1 database using grep
    if grep -q "^$cesium_pubkey$" "$g1_pubkeys_file" 2>/dev/null; then
        echo "    -> Cesium account already in G1 database. Updating with Gchange information..."
        
        # Update the existing member with Gchange information
        jq --arg pubkey "$cesium_pubkey" \
           --arg gchange_uid "$gchange_uid" \
           --arg update_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
           '( .members[] | select(.pubkey == $pubkey) | .linked_accounts ) |= if . == null then { "gchange_uid": $gchange_uid } else . + { "gchange_uid": $gchange_uid } end
            | ( .members[] | select(.pubkey == $pubkey) | .import_metadata ) |= if . == null then { "last_gchange_update": $update_date } else . + { "last_gchange_update": $update_date } end
            | .metadata.updated_date = $update_date' "$G1_PROSPECT_FILE" > "$G1_PROSPECT_FILE.new"
        mv "$G1_PROSPECT_FILE.new" "$G1_PROSPECT_FILE"
        
        echo "    -> Successfully updated existing Cesium account with Gchange UID: $gchange_uid"
        return
    fi
    
    echo "    -> Pubkey not in G1 database. Adding it..."

    # Find the corresponding UID from the WoT data
    local wot_file="$TEMP_DIR/g1_wot_data.json"
    local cesium_uid
    cesium_uid=$(jq -r --arg pk "$cesium_pubkey" '.results[] | select(.pubkey == $pk) | .uid' "$wot_file")

    # Fetch the full Cesium profile with cache
    local cesium_cache_dir="$TEMP_DIR/coucou"
    local cesium_profile_file="$cesium_cache_dir/$cesium_pubkey.cesium.json"
    local cesium_profile_data
    
    if [[ -f "$cesium_profile_file" ]]; then
        echo "    -> Using cached Cesium profile data for $cesium_pubkey"
        cesium_profile_data=$(cat "$cesium_profile_file")
    else
        local cesium_profile_url="$CESIUM_API/user/profile/$cesium_pubkey?_source_exclude=avatar._content"
        echo "    -> Fetching Cesium profile from: $cesium_profile_url"
        cesium_profile_data=$(curl -sk "$cesium_profile_url" | jq -c '._source' || echo "{}")
        
        # Cache the profile data
        echo "$cesium_profile_data" > "$cesium_profile_file"
    fi

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
          --arg import_source "gchange_prospect.sh" \
          --arg import_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
          --arg gchange_uid "$gchange_uid" \
          '{ "pubkey": $pubkey, "uid": $uid, "added_date": $added_date, "profile": $profile, "source": "g1_wallet_discovered_via_gchange", "import_metadata": { "source_script": $import_source, "import_date": $import_date, "discovery_method": "cesium_linked_account" }, "linked_accounts": { "gchange_uid": $gchange_uid } }')

        jq --argjson member "$new_g1_member" '.members += [$member]' "$G1_PROSPECT_FILE" > "$G1_PROSPECT_FILE.new"
        mv "$G1_PROSPECT_FILE.new" "$G1_PROSPECT_FILE"
        
        # Update the lookup table
        echo "$cesium_pubkey" >> "$g1_pubkeys_file"
        sort -u "$g1_pubkeys_file" > "$g1_pubkeys_file.tmp"
        mv "$g1_pubkeys_file.tmp" "$g1_pubkeys_file"
        
        echo "    -> Successfully added $cesium_uid_fallback ($cesium_pubkey) to G1 prospect database."
    else
        # This is a certified member from the WoT
        local new_g1_member
        new_g1_member=$(jq -n \
          --arg pubkey "$cesium_pubkey" \
          --arg uid "$cesium_uid" \
          --arg added_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
          --argjson profile "$cesium_profile_data" \
          --arg import_source "gchange_prospect.sh" \
          --arg import_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
          --arg gchange_uid "$gchange_uid" \
          '{ "pubkey": $pubkey, "uid": $uid, "added_date": $added_date, "profile": $profile, "source": "g1_wot_discovered_via_gchange", "import_metadata": { "source_script": $import_source, "import_date": $import_date, "discovery_method": "cesium_linked_account" }, "linked_accounts": { "gchange_uid": $gchange_uid } }')

        jq --argjson member "$new_g1_member" '.members += [$member]' "$G1_PROSPECT_FILE" > "$G1_PROSPECT_FILE.new"
        mv "$G1_PROSPECT_FILE.new" "$G1_PROSPECT_FILE"
        
        # Update the lookup table
        echo "$cesium_pubkey" >> "$g1_pubkeys_file"
        sort -u "$g1_pubkeys_file" > "$g1_pubkeys_file.tmp"
        mv "$g1_pubkeys_file.tmp" "$g1_pubkeys_file"
        
        echo "    -> Successfully added $cesium_uid ($cesium_pubkey) to G1 prospect database."
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

    # Create lookup table of existing UIDs (much faster than checking one by one)
    echo "Creating lookup table of existing UIDs..."
    jq -r '.members[].uid' "$PROSPECT_FILE" 2>/dev/null | sort > "$TEMP_DIR/existing_uids.txt" || touch "$TEMP_DIR/existing_uids.txt"
    
    # Create cache directory for Gchange profile data
    local cache_dir="$TEMP_DIR/coucou"
    mkdir -p "$cache_dir"
    
    # Show existing cache statistics
    local existing_cache_count
    existing_cache_count=$(find "$cache_dir" -name "*.gchange.json" 2>/dev/null | wc -l)
    echo "Found $existing_cache_count existing Gchange cache files"
    
    # Create temporary files for batch processing
    local temp_new_members="$TEMP_DIR/new_gchange_members.json"
    local temp_updates="$TEMP_DIR/gchange_updates.json"
    echo "[]" > "$temp_new_members"
    echo "[]" > "$temp_updates"
    
    # Batch processing variables
    local batch_size=50
    local current_batch=0

    local total_ads
    total_ads=$(jq 'length' < "$metadata_file")
    local processed_ads=0
    local new_members=0

    while IFS= read -r ad_meta; do
        processed_ads=$((processed_ads + 1))
        
        # Show progress every 100 ads or for the last ad
        if [[ $((processed_ads % 100)) -eq 0 ]] || [[ $processed_ads -eq $total_ads ]]; then
            show_progress "$processed_ads" "$total_ads"
            echo ""
        fi
        
        local user_id
        user_id=$(echo "$ad_meta" | jq -r '._source.issuer | select(. != null)')
        local ad_id
        ad_id=$(echo "$ad_meta" | jq -r '._id')

        echo "Processing ad $processed_ads/$total_ads ($ad_id)... "

        if [[ -z "$user_id" ]]; then
            echo " -> No issuer. Skipping."
            continue
        fi
        
        # Check if user exists using grep (much faster than jq)
        if grep -q "^$user_id$" "$TEMP_DIR/existing_uids.txt" 2>/dev/null; then
            # --- EXISTING GCHANGE USER ---
            echo " -> User $user_id already in gchange database. Checking for new activity..."
            
            # Activity 1: Check for new ad (simplified check)
            local user_ads_file="$TEMP_DIR/user_${user_id}_ads.json"
            if [[ ! -f "$user_ads_file" ]]; then
                # Extract user's ads once
                jq -r --arg uid "$user_id" '.members[] | select(.uid == $uid) | .detected_ads[]?' "$PROSPECT_FILE" > "$user_ads_file" 2>/dev/null || touch "$user_ads_file"
            fi
            
            if ! grep -q "^$ad_id$" "$user_ads_file" 2>/dev/null; then
                echo "    -> New ad $ad_id found. Adding to detected_ads."
                echo "$ad_id" >> "$user_ads_file"
                
                # Queue update for batch processing
                local update_entry
                update_entry=$(jq -n --arg ad_id "$ad_id" --arg uid "$user_id" '{ "type": "add_ad", "uid": $uid, "ad_id": $ad_id }')
                jq --argjson entry "$update_entry" '. += [$entry]' "$temp_updates" > "$temp_updates.tmp"
                mv "$temp_updates.tmp" "$temp_updates"
            else
                echo "    -> Ad $ad_id already listed."
            fi

            # Activity 2: Check for linked Cesium account and enrich G1 database
            local user_profile_file="$cache_dir/${user_id}.gchange.json"
            if [[ -f "$user_profile_file" ]]; then
                local cesium_pubkey
                cesium_pubkey=$(jq -r '.pubkey | select(. != null)' "$user_profile_file")
                if [[ -n "$cesium_pubkey" ]]; then
                    enrich_g1_database "$cesium_pubkey" "$user_id"
                    
                    # Update linked accounts in the main database
                    echo "    -> Updating linked accounts information..."
                    jq --arg uid "$user_id" --arg cesium_pubkey "$cesium_pubkey" '
                        ( .members[] | select(.uid == $uid) | .linked_accounts ) |= if . == null then { "cesium_pubkey": $cesium_pubkey } else . + { "cesium_pubkey": $cesium_pubkey } end
                    ' "$PROSPECT_FILE" > "$PROSPECT_FILE.tmp"
                    mv "$PROSPECT_FILE.tmp" "$PROSPECT_FILE"
                fi
            fi
        else
            # --- NEW GCHANGE USER ---
            echo " -> New user found: $user_id"
            
            # 1. Fetch gchange profile (with cache)
            echo "    -> Fetching profile for user $user_id..."
            local user_profile_file="$cache_dir/${user_id}.gchange.json"
            local profile_data
            
            if [[ -f "$user_profile_file" ]]; then
                echo "    -> Using cached profile data for $user_id"
                profile_data=$(cat "$user_profile_file")
            else
                local user_api_url="$GCHANGE_USER_API_TPL/$user_id?_source_exclude=avatar._content"
                profile_data=$(curl -sk "$user_api_url" | jq -c '._source' || echo "{}")
                
                # Cache the profile data
                echo "$profile_data" > "$user_profile_file"
            fi

            # Extract Cesium pubkey from Gchange profile if available
            local cesium_pubkey_from_gchange
            cesium_pubkey_from_gchange=$(echo "$profile_data" | jq -r '.pubkey | select(. != null and . != "")')
            
            if [[ -n "$cesium_pubkey_from_gchange" ]]; then
                echo "    -> Found linked Cesium account in Gchange profile: $cesium_pubkey_from_gchange"
            fi

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
            
            # 3. Create new member for batch processing
            echo "    -> Queuing for batch addition..."
            local new_member
            new_member=$(jq -n \
              --arg uid "$user_id" \
              --arg ad_id "$ad_id" \
              --arg added_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
              --argjson profile "$profile_data" \
              --argjson source_ad "$source_ad" \
              --arg import_source "gchange_prospect.sh" \
              --arg import_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
              --arg cesium_pubkey "$cesium_pubkey_from_gchange" \
              '{ "uid": $uid, "added_date": $added_date, "profile": $profile, "source": "gchange", "discovery_ad": $source_ad, "detected_ads": [$ad_id], "import_metadata": { "source_script": $import_source, "import_date": $import_date, "discovery_method": "ad_issuer" }, "linked_accounts": { "cesium_pubkey": $cesium_pubkey } }')
            
            jq --argjson member "$new_member" '. += [$member]' "$temp_new_members" > "$temp_new_members.tmp"
            mv "$temp_new_members.tmp" "$temp_new_members"
            
            new_members=$((new_members + 1))
            current_batch=$((current_batch + 1))

            # 4. Check for linked Cesium account and enrich G1 database
            local cesium_pubkey_new
            cesium_pubkey_new=$(echo "$profile_data" | jq -r '.pubkey | select(. != null)')
            if [[ -n "$cesium_pubkey_new" ]]; then
                enrich_g1_database "$cesium_pubkey_new" "$user_id"
            fi
            echo "    -> Done."
            
            # Process batch when it reaches the batch size
            if [[ $current_batch -ge $batch_size ]]; then
                echo "Processing batch of $current_batch new members..."
                jq --argjson new_members "$(cat "$temp_new_members")" '.members += $new_members' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
                mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
                
                # Reset batch
                echo "[]" > "$temp_new_members"
                current_batch=0
                echo "Batch processed successfully"
            fi
        fi
    done < <(jq -c '.[]' "$metadata_file")
    
    # Process remaining new members in the last batch
    if [[ $current_batch -gt 0 ]]; then
        echo "Processing final batch of $current_batch new members..."
        jq --argjson new_members "$(cat "$temp_new_members")" '.members += $new_members' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
        mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
        echo "Final batch processed successfully"
    fi
    
    # Process all updates in batch
    local updates_count
    updates_count=$(jq 'length' "$temp_updates")
    if [[ $updates_count -gt 0 ]]; then
        echo "Processing $updates_count updates in batch..."
        
        # Apply all updates at once
        jq -r '.[] | select(.type == "add_ad") | "\(.uid)|\(.ad_id)"' "$temp_updates" | while IFS='|' read -r uid ad_id; do
            jq --arg ad_id "$ad_id" --arg uid "$uid" '
                ( .members[] | select(.uid == $uid) | .detected_ads ) |= if . == null then [$ad_id] else . + [$ad_id] end
            ' "$PROSPECT_FILE" > "$PROSPECT_FILE.tmp"
            mv "$PROSPECT_FILE.tmp" "$PROSPECT_FILE"
        done
        echo "Updates processed successfully"
    fi
    
    # Final metadata update for gchange file
    local final_count
    final_count=$(jq '.members | length' "$PROSPECT_FILE")
    jq '.metadata.updated_date = "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'" | .metadata.total_members = ('$final_count')' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
    mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
    
    # Clean up temporary files
    rm -f "$temp_new_members" "$temp_updates" "$TEMP_DIR/existing_uids.txt" "$TEMP_DIR"/user_*_ads.json "$TEMP_DIR/g1_existing_pubkeys.txt"
    
    # Note: Cache files in $cache_dir are preserved for future use
    
    echo "Processing complete."
    if [[ $new_members -gt 0 ]]; then
        echo "New gchange members added: $new_members"
    else
        echo "No new gchange users were found, but existing users may have been updated."
    fi
    echo "Total members in gchange database: $final_count"
    
    # Show cache statistics
    local cache_files_count
    cache_files_count=$(find "$cache_dir" -name "*.gchange.json" 2>/dev/null | wc -l)
    echo "Gchange cache files: $cache_files_count (preserved in $cache_dir)"
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
    
    # Show provenance statistics
    echo ""
    echo "=== Import Provenance Statistics ==="
    local gchange_count
    local unknown_count
    
    gchange_count=$(jq -r '.members[] | select(.import_metadata.source_script == "gchange_prospect.sh") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
    unknown_count=$(jq -r '.members[] | select(.import_metadata.source_script == null) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
    
    echo "Imported by gchange_prospect.sh: $gchange_count"
    echo "Unknown provenance: $unknown_count"
    
    # Show discovery method statistics
    echo ""
    echo "=== Discovery Method Statistics ==="
    local ad_issuer_count
    local cesium_linked_count
    
    ad_issuer_count=$(jq -r '.members[] | select(.import_metadata.discovery_method == "ad_issuer") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
    cesium_linked_count=$(jq -r '.members[] | select(.import_metadata.discovery_method == "cesium_linked_account") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
    
    echo "Discovered via ad issuer: $ad_issuer_count"
    echo "Discovered via Cesium linked account: $cesium_linked_count"
    
    # Show linked accounts statistics
    echo ""
    echo "=== Linked Accounts Statistics ==="
    local linked_cesium_count
    local total_linked_count
    
    linked_cesium_count=$(jq -r '.members[] | select(.linked_accounts.cesium_pubkey != null and .linked_accounts.cesium_pubkey != "") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
    total_linked_count=$(jq -r '.members[] | select(.linked_accounts != null) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
    
    echo "Users with linked Cesium accounts: $linked_cesium_count"
    echo "Total users with any linked accounts: $total_linked_count"
    
    # Show sample of linked accounts
    echo ""
    echo "=== Sample Linked Accounts ==="
    jq -r '.members[] | select(.linked_accounts.cesium_pubkey != null and .linked_accounts.cesium_pubkey != "") | "\(.uid) -> Cesium: \(.linked_accounts.cesium_pubkey)"' "$PROSPECT_FILE" 2>/dev/null | head -5 || echo "No linked accounts found"
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