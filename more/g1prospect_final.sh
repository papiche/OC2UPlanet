#!/bin/bash
########################################################################
# Version: 0.4 (Duniter v2s migration)
# License: AGPL-3.0 (https://choosealicense.com/licenses/agpl-3.0/)
########################################################################
## G1 Prospect Database Builder (Duniter v2s Edition)
########################################################################
## Fetch Ğ1 WoT members via Squid GraphQL indexer (Duniter v2s)
## and enrich with Cesium+ data to build a prospect database
## for OC2UPlanet / AstroBot
########################################################################

set -euo pipefail

# Trap to handle script interruption
cleanup_on_exit() {
    echo ""
    echo "Script interrupted. Cleaning up..."
    
    # Check if the main file is valid
    if [[ -f "$PROSPECT_FILE" ]]; then
        if jq empty "$PROSPECT_FILE" 2>/dev/null; then
            local member_count
            member_count=$(jq '.members | length' "$PROSPECT_FILE" 2>/dev/null || echo "0")
            echo "Database is valid with $member_count members - progress preserved"
        else
            echo "Database is corrupted, attempting to repair..."
        fi
    fi
    
    # If the JSON file exists but is corrupted, try to fix it
    if [[ -f "$PROSPECT_FILE" ]]; then
        echo "Checking existing database file..."
        
        # Try to fix the JSON structure if corrupted
        if jq empty "$PROSPECT_FILE" 2>/dev/null; then
            echo "Existing database is valid"
        else
            echo "Existing database is corrupted, attempting to repair..."
            
            # Try to extract valid members and recreate the file
            if jq -e '.members' "$PROSPECT_FILE" >/dev/null 2>&1; then
                # Extract existing members and create new valid structure
                jq -c '.members[]' "$PROSPECT_FILE" 2>/dev/null > "$TEMP_DIR/existing_members.json" || true
                
                if [[ -s "$TEMP_DIR/existing_members.json" ]]; then
                    echo "Found existing members, recreating valid structure..."
                    
                    # Create new valid JSON structure
                    cat > "$PROSPECT_FILE" << EOF
{
  "metadata": {
    "created_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "updated_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "total_members": 0,
    "source": "g1_wot_v2s_squid"
  },
  "members": [
EOF
                    
                    # Add existing members back
                    local first=true
                    while IFS= read -r member; do
                        if [[ "$first" == "true" ]]; then
                            first=false
                        else
                            echo "," >> "$PROSPECT_FILE"
                        fi
                        echo "$member" >> "$PROSPECT_FILE"
                    done < "$TEMP_DIR/existing_members.json"
                    
                    # Close the structure
                    cat >> "$PROSPECT_FILE" << EOF
  ]
}
EOF
                    
                    # Update member count
                    local member_count
                    member_count=$(jq '.members | length' "$PROSPECT_FILE" 2>/dev/null || echo "0")
                    sed -i "s/\"total_members\": 0/\"total_members\": $member_count/" "$PROSPECT_FILE"
                    
                    if jq empty "$PROSPECT_FILE" 2>/dev/null; then
                        echo "JSON structure repaired successfully with $member_count members"
                    else
                        echo "Could not repair JSON structure"
                    fi
                else
                    echo "No valid members found, creating empty structure..."
                    cat > "$PROSPECT_FILE" << EOF
{
  "metadata": {
    "created_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "updated_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "total_members": 0,
    "source": "g1_wot_v2s_squid"
  },
  "members": []
}
EOF
                fi
            else
                echo "Could not extract members, creating empty structure..."
                cat > "$PROSPECT_FILE" << EOF
{
  "metadata": {
    "created_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "updated_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "total_members": 0,
    "source": "g1_wot_v2s_squid"
  },
  "members": []
}
EOF
            fi
        fi
    fi
    
    echo "Cleanup complete"
    exit 1
}

trap cleanup_on_exit INT TERM

# Default configuration
myCESIUM="https://g1.data.e-is.pro"  # Cesium+ API for profile enrichment
PRESERVE_CACHE=false  # Option to preserve cache between runs

# Parse command line arguments
MEMBERS_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --preserve-cache)
            PRESERVE_CACHE=true
            shift
            ;;
        --cesium)
            myCESIUM="$2"
            shift 2
            ;;
        *)
            MEMBERS_FILE="$1"
            shift
            ;;
    esac
done

# Constants
PROSPECT_FILE="$HOME/.zen/game/g1prospect.json"
TEMP_DIR="$HOME/.zen/tmp"

# Duniter v2s Squid indexer endpoints (GraphQL)
# Fetched dynamically via duniter_getnode.sh, with hardcoded fallbacks
DUNITER_GETNODE="${HOME}/.zen/Astroport.ONE/tools/duniter_getnode.sh"

SQUID_FALLBACKS=(
    "https://g1-squid.axiom-team.fr/v1/graphql"
    "https://squid.g1.gyroi.de/v1/graphql"
    "https://squid.g1.coinduf.eu/v1/graphql"
    "https://g1-squid.asycn.io/v1/graphql"
    "https://squid.g1.brussels.ovh/v1/graphql"
)

# Create necessary directories
mkdir -p "$(dirname "$PROSPECT_FILE")"
mkdir -p "$TEMP_DIR"

########################################################################
# Helper: execute a GraphQL query against the Squid indexer
# Tries each squid endpoint until one succeeds.
# $1 = compact JSON query payload
# Outputs JSON response or returns 1 on failure
########################################################################
graphql_query() {
    local payload="$1"
    local response

    # Build squid list: dynamic best node first, then fallbacks
    local squids=()
    if [[ -x "$DUNITER_GETNODE" ]]; then
        local best_squid
        best_squid=$("$DUNITER_GETNODE" squid 2>/dev/null || true)
        [[ -n "$best_squid" ]] && squids+=("$best_squid")
    fi
    for sq in "${SQUID_FALLBACKS[@]}"; do
        squids+=("$sq")
    done

    for sq in "${squids[@]}"; do
        response=$(curl -sf --max-time 30 \
            -X POST "$sq" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json" \
            --data "$payload" 2>/dev/null) || { echo "Squid $sq failed" >&2; continue; }

        # Check for GraphQL errors
        if echo "$response" | grep -q '"errors"'; then
            echo "GraphQL error on $sq" >&2
            continue
        fi

        # Check data is present
        if echo "$response" | jq -e '.data' >/dev/null 2>&1; then
            echo "$response"
            return 0
        fi

        echo "No data in response from $sq" >&2
    done

    echo "ERROR: All squid endpoints failed" >&2
    return 1
}

########################################################################
# Fetch all active Ğ1 WoT members via Squid GraphQL (paginated)
# Output: $TEMP_DIR/g1_members_raw.json
#   Format: { "data": { "identities": { "nodes": [...], "totalCount": N } } }
########################################################################
fetch_g1_members() {
    echo "Fetching Ğ1 WoT members from Duniter v2s Squid indexer..."

    # Allow pre-supplied members file (for testing / offline use)
    if [[ -n "$MEMBERS_FILE" ]] && [[ -f "$MEMBERS_FILE" ]]; then
        echo "Using provided members file: $MEMBERS_FILE"
        cp "$MEMBERS_FILE" "$TEMP_DIR/g1_members_raw.json"
        return 0
    fi

    # Use a NDJSON temp file to accumulate nodes page by page
    # (avoids "Argument list too long" when shell vars exceed ARG_MAX with 7000+ members)
    local nodes_ndjson="$TEMP_DIR/g1_wot_nodes.ndjson"
    > "$nodes_ndjson"   # truncate/create

    local offset=0
    local page_size=1000
    local total_count=0
    local fetched=0
    local page=0

    while true; do
        page=$((page + 1))
        echo "Fetching page $page (offset=$offset, size=$page_size)..."

        # GraphQL query: active WoT members, paginated
        # Fields: name (=uid), accountId (=pubkey SS58 g1), index (IdtyId)
        local payload="{\"query\":\"{ identities(filter:{isMember:{equalTo:true}},orderBy:INDEX_ASC,first:${page_size},offset:${offset}){nodes{name accountId index}totalCount} }\"}"

        local response
        if ! response=$(graphql_query "$payload"); then
            echo "ERROR: Failed to fetch WoT members from any squid endpoint"
            return 1
        fi

        local page_count
        page_count=$(echo "$response" | jq '.data.identities.nodes | length')

        # Get total on first page
        if [[ $page -eq 1 ]]; then
            total_count=$(echo "$response" | jq '.data.identities.totalCount // 0')
            echo "Total active WoT members reported by indexer: $total_count"
        fi

        if [[ "$page_count" -eq 0 ]]; then
            echo "No more members to fetch (empty page)"
            break
        fi

        # Append each node as a single JSON line (NDJSON) — no huge shell variables
        echo "$response" | jq -c '.data.identities.nodes[]' >> "$nodes_ndjson"

        fetched=$((fetched + page_count))
        echo "Fetched $fetched / $total_count members so far..."

        # Exit when all members fetched
        if [[ "$fetched" -ge "$total_count" ]] || [[ "$page_count" -lt "$page_size" ]]; then
            break
        fi

        offset=$((offset + page_size))
    done

    # Build the final unified JSON from the NDJSON file
    # jq --slurpfile reads each JSON line as an element of an array → $nodes
    jq -n \
        --argjson total "$fetched" \
        --slurpfile nodes "$nodes_ndjson" \
        '{"data":{"identities":{"nodes":$nodes,"totalCount":$total}}}' \
        > "$TEMP_DIR/g1_members_raw.json"

    rm -f "$nodes_ndjson"

    echo "Total WoT members fetched: $fetched"
    return 0
}

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

########################################################################
# Process all members from g1_members_raw.json and build g1prospect.json
# Nodes format: { "name": "uid", "accountId": "SS58addr", "index": N }
# Output members format: { "pubkey": "...", "uid": "...", ... }
#   (pubkey/uid field names kept for AstroBot backward compatibility)
########################################################################
process_all_members() {
    echo "Processing members..."
    
    local processed=0
    local new_members=0
    local migrated_v1=0
    local total_members
    
    total_members=$(jq '.data.identities.nodes | length' "$TEMP_DIR/g1_members_raw.json")
    echo "Total members to process: $total_members"
    
    # Initialize or load existing database
    if [[ ! -f "$PROSPECT_FILE" ]] || [[ ! -s "$PROSPECT_FILE" ]] || ! jq empty "$PROSPECT_FILE" 2>/dev/null; then
        echo "Creating new database structure..."
        cat > "$PROSPECT_FILE" << EOF
{
  "metadata": {
    "created_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "updated_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "total_members": 0,
    "source": "g1_wot_v2s_squid"
  },
  "members": []
}
EOF
        existing_count=0
    else
        existing_count=$(jq '.members | length' "$PROSPECT_FILE" 2>/dev/null || echo "0")
        echo "Found $existing_count existing members"
    fi
    
    # Lookup table 1: existing SS58 pubkeys (v2s already migrated)
    echo "Creating lookup tables (pubkeys + uids)..."
    jq -r '.members[].pubkey' "$PROSPECT_FILE" 2>/dev/null | sort > "$TEMP_DIR/existing_pubkeys.txt" || touch "$TEMP_DIR/existing_pubkeys.txt"
    
    # Lookup table 2: uid → pubkey mapping (to detect v1 members by their uid)
    # Format: "uid<TAB>pubkey" — used to migrate v1 pubkeys to v2s SS58
    jq -r '.members[] | [.uid, .pubkey] | @tsv' "$PROSPECT_FILE" 2>/dev/null | sort > "$TEMP_DIR/uid_to_pubkey.tsv" || touch "$TEMP_DIR/uid_to_pubkey.tsv"
    
    # Create cache directory for Cesium+ profile data
    local cache_dir="$TEMP_DIR/coucou"
    mkdir -p "$cache_dir"
    
    # Show existing cache statistics
    local existing_cache_count
    existing_cache_count=$(find "$cache_dir" -name "*.cesium.json" 2>/dev/null | wc -l)
    echo "Found $existing_cache_count existing Cesium+ cache files"
    
    # Create a temporary file for new members
    local temp_new_members="$TEMP_DIR/new_members.json"
    echo "[]" > "$temp_new_members"
    
    # Batch processing variables
    local batch_size=50
    local current_batch=0
    
    # Process each member
    # Duniter v2s fields: accountId (=pubkey SS58 g1), name (=uid), index
    # Output fields: pubkey, uid (kept for AstroBot backward compatibility)
    while IFS= read -r member; do
        local pubkey
        local uid
        
        pubkey=$(echo "$member" | jq -r '.accountId')
        uid=$(echo "$member" | jq -r '.name')
        
        processed=$((processed + 1))
        
        # Show progress every 100 members or for the last member
        if [[ $((processed % 100)) -eq 0 ]] || [[ $processed -eq $total_members ]]; then
            show_progress "$processed" "$total_members"
            echo ""
        fi
        
        echo "Processing member $processed/$total_members: $uid ($pubkey)"
        
        # ── Check 1: Already present with v2s SS58 pubkey → skip ──────────
        if grep -q "^${pubkey}$" "$TEMP_DIR/existing_pubkeys.txt" 2>/dev/null; then
            echo "Member $uid already up-to-date (v2s pubkey), skipping..."
            continue
        fi
        
        # ── Check 2: Exists with old v1 pubkey (same uid) → migrate ───────
        # Duniter v1 used base58 pubkeys; v2s uses SS58 g1-prefixed addresses.
        # The uid (username) is stable across the migration.
        if grep -q "^${uid}	" "$TEMP_DIR/uid_to_pubkey.tsv" 2>/dev/null; then
            local old_pubkey
            old_pubkey=$(grep "^${uid}	" "$TEMP_DIR/uid_to_pubkey.tsv" | head -1 | cut -f2)
            echo "  → Migrating v1→v2s: $uid  old=$old_pubkey  new=$pubkey"
            
            # Update the existing record: new pubkey SS58, preserve old as pubkey_v1
            jq --arg old "$old_pubkey" \
               --arg new "$pubkey" \
               --arg date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
               '(.members[] | select(.pubkey == $old)) |= . + {
                   "pubkey": $new,
                   "pubkey_v1": $old,
                   "import_metadata": ((.import_metadata // {}) + {
                       "duniter_version": "v2s",
                       "indexer": "squid_graphql",
                       "v2s_migration_date": $date
                   })
               } | .metadata.updated_date = $date' \
               "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
            mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
            
            # Update lookup tables so duplicates are not processed again
            sed -i "s|^${old_pubkey}$|${pubkey}|" "$TEMP_DIR/existing_pubkeys.txt"
            sed -i "s|^${uid}	.*|${uid}	${pubkey}|" "$TEMP_DIR/uid_to_pubkey.tsv"
            
            migrated_v1=$((migrated_v1 + 1))
            continue
        fi
        
        # ── Check 3: Truly new member → add to database ───────────────────
        
        # Fetch profile data from Cesium+ (excluding avatar content to avoid corruption)
        local cesium_url="$myCESIUM/user/profile/$pubkey?_source_exclude=avatar._content"
        
        # Check cache first
        local profile_data
        local cache_file="$cache_dir/$pubkey.cesium.json"
        if [[ -f "$cache_file" ]]; then
            echo "Using cached profile data for $uid"
            profile_data=$(cat "$cache_file")
        else
            echo "Fetching profile from: $cesium_url"
            profile_data=$(curl -s "$cesium_url" 2>/dev/null || echo "{}")
            
            # Cache the profile data
            echo "$profile_data" > "$cache_file"
        fi
        
        # Create new member object
        # Note: pubkey/uid field names are preserved for AstroBot compatibility
        #       pubkey = accountId (SS58 g1 address from Duniter v2s)
        #       uid    = name (identity username from Duniter v2s)
        local new_member
        new_member=$(cat << EOF
    {
      "pubkey": "$pubkey",
      "uid": "$uid",
      "added_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
      "profile": $profile_data,
      "source": "g1_wot",
      "import_metadata": {
        "source_script": "g1prospect_final.sh",
        "import_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
        "discovery_method": "wot_member_list",
        "duniter_version": "v2s",
        "indexer": "squid_graphql"
      }
    }
EOF
)
        
        # Add to temporary new members array (batch processing)
        jq --argjson member "$new_member" '. += [$member]' "$temp_new_members" > "$temp_new_members.tmp"
        mv "$temp_new_members.tmp" "$temp_new_members"
        
        new_members=$((new_members + 1))
        current_batch=$((current_batch + 1))
        echo "Member $uid queued for batch addition ($current_batch/$batch_size)"
        
        # Process batch when it reaches the batch size
        if [[ $current_batch -ge $batch_size ]]; then
            echo "Processing batch of $current_batch members..."
            jq --argjson new_members "$(cat "$temp_new_members")" '.members += $new_members | .metadata.updated_date = "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
            mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
            
            # Reset batch
            echo "[]" > "$temp_new_members"
            current_batch=0
            echo "Batch processed successfully"
        fi
        
        # Random delay between 3-5 seconds to avoid being blacklisted by Cesium+
        local delay=$((RANDOM % 3 + 3))
        echo "Waiting $delay seconds before next request..."
        sleep $delay
        
    done < <(jq -c '.data.identities.nodes[]' "$TEMP_DIR/g1_members_raw.json")
    
    # Process remaining members in the last batch
    if [[ $current_batch -gt 0 ]]; then
        echo "Processing final batch of $current_batch members..."
        jq --argjson new_members "$(cat "$temp_new_members")" '.members += $new_members | .metadata.updated_date = "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
        mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
        echo "Final batch processed successfully"
    fi
    
    # Update final metadata
    local final_count
    final_count=$(jq '.members | length' "$PROSPECT_FILE")
    
    # Update the total_members count and source
    jq --arg count "$final_count" \
       '.metadata.total_members = ($count | tonumber) | .metadata.source = "g1_wot_v2s_squid"' \
       "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
    mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
    
    # Clean up temporary files
    rm -f "$temp_new_members" "$TEMP_DIR/existing_pubkeys.txt" "$TEMP_DIR/uid_to_pubkey.tsv"
    
    # Note: Cache files in $cache_dir are preserved for future use
    
    echo ""
    echo "=== Processing Summary ==="
    echo "  New members added    : $new_members"
    echo "  v1→v2s pubkey migrated: $migrated_v1"
    echo "  Total in database    : $final_count"
    echo "Prospect database updated: $PROSPECT_FILE"
    
    # Show cache statistics
    local cache_files_count
    cache_files_count=$(find "$cache_dir" -name "*.cesium.json" 2>/dev/null | wc -l)
    echo "Cesium+ cache files: $cache_files_count (preserved in $cache_dir)"
}

# Function to display statistics
show_statistics() {
    if [[ -f "$PROSPECT_FILE" ]]; then
        echo ""
        echo "=== Prospect Database Statistics ==="
        local total_members
        local updated_date
        
        total_members=$(jq -r '.metadata.total_members' "$PROSPECT_FILE" 2>/dev/null || echo "0")
        updated_date=$(jq -r '.metadata.updated_date' "$PROSPECT_FILE" 2>/dev/null || echo "Unknown")
        
        echo "Total members: $total_members"
        echo "Last updated: $updated_date"
        echo "Database file: $PROSPECT_FILE"
        
        # Show provenance statistics
        echo ""
        echo "=== Import Provenance Statistics ==="
        local g1prospect_count
        local gchange_count
        local unknown_count
        
        g1prospect_count=$(jq -r '.members[] | select(.import_metadata.source_script == "g1prospect_final.sh") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        gchange_count=$(jq -r '.members[] | select(.import_metadata.source_script == "gchange_prospect.sh") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        unknown_count=$(jq -r '.members[] | select(.import_metadata.source_script == null) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        
        echo "Imported by g1prospect_final.sh: $g1prospect_count"
        echo "Imported by gchange_prospect.sh: $gchange_count"
        echo "Unknown provenance: $unknown_count"
        
        # Show Duniter version statistics
        echo ""
        echo "=== Duniter Version Statistics ==="
        local v2s_count
        local v1_count
        
        v2s_count=$(jq -r '.members[] | select(.import_metadata.duniter_version == "v2s") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        v1_count=$(jq -r '.members[] | select(.import_metadata.duniter_version == null) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        
        echo "Imported via Duniter v2s (squid): $v2s_count"
        echo "Imported via Duniter v1 (legacy): $v1_count"
        
        # Show linked accounts statistics
        echo ""
        echo "=== Linked Accounts Statistics ==="
        local gchange_linked_count
        local total_linked_count
        
        gchange_linked_count=$(jq -r '.members[] | select(.import_metadata.discovery_method == "cesium_linked_account") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        total_linked_count=$(jq -r '.members[] | select(.import_metadata.discovery_method != null) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        
        echo "Cesium accounts discovered via Gchange: $gchange_linked_count"
        echo "Total accounts with known discovery method: $total_linked_count"
        
        # Show Gchange linked accounts statistics
        echo ""
        echo "=== Gchange Linked Accounts Statistics ==="
        local gchange_linked_accounts
        local updated_accounts
        
        gchange_linked_accounts=$(jq -r '.members[] | select(.linked_accounts.gchange_uid != null) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        updated_accounts=$(jq -r '.members[] | select(.import_metadata.last_gchange_update != null) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        
        echo "Cesium accounts with linked Gchange UIDs: $gchange_linked_accounts"
        echo "Accounts updated with Gchange information: $updated_accounts"
        
        # Show sample of members
        echo ""
        echo "=== Sample Members ==="
        jq -r '.members[0:5][] | "\(.uid) (\(.pubkey))"' "$PROSPECT_FILE" 2>/dev/null || echo "No members found"
    else
        echo "No prospect database found"
    fi
}

# Main execution
main() {
    echo "Starting G1 prospect database build (Duniter v2s edition)..."
    echo "Using Squid GraphQL indexer (replaces Duniter v1 REST API)"
    echo ""
    
    # Fetch Ğ1 members via Squid GraphQL
    if ! fetch_g1_members; then
        echo ""
        echo "ERROR: Failed to fetch Ğ1 WoT members from any Squid indexer."
        echo ""
        echo "Troubleshooting steps:"
        echo "1. Check your internet connection"
        echo "2. Run: ${DUNITER_GETNODE} squid  (to test indexer discovery)"
        echo "3. Try a manual query:"
        echo "   curl -X POST https://g1-squid.axiom-team.fr/v1/graphql \\"
        echo "     -H 'Content-Type: application/json' \\"
        echo "     -d '{\"query\":\"{ identities(filter:{isMember:{equalTo:true}},first:5){nodes{name accountId}totalCount} }\"}'"
        echo "4. Check available squids: ${DUNITER_GETNODE} status"
        echo ""
        echo "If the problem persists, you can:"
        echo "- Use a pre-downloaded members file: $0 /path/to/members.json"
        echo ""
        exit 1
    fi
    
    # Verify we have valid data
    if [[ ! -s "$TEMP_DIR/g1_members_raw.json" ]]; then
        echo "ERROR: No valid members data received"
        exit 1
    fi
    
    # Check if the JSON is valid and has the expected structure
    if ! jq -e '.data.identities.nodes' "$TEMP_DIR/g1_members_raw.json" >/dev/null 2>&1; then
        echo "ERROR: Invalid JSON structure. Expected '.data.identities.nodes' not found."
        echo "Actual structure:"
        jq keys "$TEMP_DIR/g1_members_raw.json" 2>/dev/null || echo "Invalid JSON"
        exit 1
    fi
    
    local member_count
    member_count=$(jq '.data.identities.nodes | length' "$TEMP_DIR/g1_members_raw.json" 2>/dev/null || echo "0")
    
    if [[ "$member_count" -eq 0 ]]; then
        echo "ERROR: No members found in the response"
        exit 1
    fi
    
    echo "Successfully fetched $member_count members from Ğ1 WoT (Duniter v2s)"
    
    # Process all members
    process_all_members
    
    # Show statistics
    show_statistics
    
    echo ""
    echo "=== G1 Prospect Database Build Complete (Duniter v2s) ==="
}

# Run main function
main "$@"
