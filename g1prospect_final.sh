#!/bin/bash
########################################################################
# Version: 0.3
# License: AGPL-3.0 (https://choosealicense.com/licenses/agpl-3.0/)
########################################################################
## G1 Prospect Database Builder (Final Version)
########################################################################
## Fetch Ğ1 WoT members and enrich with Cesium data
## to build a prospect database for OC2UPlanet
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
    "source": "g1_wot_cesium"
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
    "source": "g1_wot_cesium"
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
    "source": "g1_wot_cesium"
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
myCESIUM="https://g1.data.e-is.pro"  # Default Cesium API URL
PRESERVE_CACHE=false  # Option to preserve cache between runs

# Parse command line arguments
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
MEMBERS_FILE="${1:-}"
TEMP_DIR="$HOME/.zen/tmp"
G1_WOT_API="https://g1.duniter.org/wot/members"

# Create necessary directories
mkdir -p "$(dirname "$PROSPECT_FILE")"
mkdir -p "$TEMP_DIR"

# Function to check if a server is available
check_server_availability() {
    local server_url="$1"
    local timeout="${2:-5}"
    
    echo "Checking server availability: $server_url"
    
    # Try to get basic info from the server
    local response
    response=$(curl -s -m "$timeout" "$server_url" 2>/dev/null)
    
    if [[ -n "$response" ]]; then
        # Check if it's valid JSON
        if echo "$response" | jq empty 2>/dev/null; then
            echo "Server is available and returns valid JSON"
            return 0
        else
            echo "Server responded but returned invalid JSON"
            return 1
        fi
    else
        echo "Server is not responding"
        return 1
    fi
}

# Function to fetch Ğ1 members
fetch_g1_members() {
    echo "Fetching Ğ1 WoT members..."
    
    if [[ -n "$MEMBERS_FILE" ]] && [[ -f "$MEMBERS_FILE" ]]; then
        echo "Using provided members file: $MEMBERS_FILE"
        cp "$MEMBERS_FILE" "$TEMP_DIR/g1_members_raw.json"
        return 0
    fi
    
    # Try primary API first
    echo "Fetching from primary Ğ1 WoT API: $G1_WOT_API"
    if check_server_availability "$G1_WOT_API" 10; then
        if curl -s -m 10 "$G1_WOT_API" > "$TEMP_DIR/g1_members_raw.json" 2>/dev/null; then
            if [[ -s "$TEMP_DIR/g1_members_raw.json" ]] && jq empty "$TEMP_DIR/g1_members_raw.json" 2>/dev/null; then
                echo "Primary API successful"
                return 0
            else
                echo "Primary API returned invalid data"
            fi
        else
            echo "Primary API failed"
        fi
    else
        echo "Primary API unavailable"
    fi
    
    # Fallback: Use duniter_getnode.sh to find a working BMAS server
    echo "Primary API unavailable, searching for working BMAS server..."
    
    # Get the path to duniter_getnode.sh
    local duniter_getnode_script="$HOME/.zen/Astroport.ONE/tools/duniter_getnode.sh"
    
    if [[ ! -f "$duniter_getnode_script" ]]; then
        echo "ERROR: duniter_getnode.sh not found at $duniter_getnode_script"
        echo "Please ensure Astroport.ONE is properly installed"
        return 1
    fi
    
   
    # Get a working BMAS server
    echo "Running duniter_getnode.sh BMAS..."
    local bmas_server
    bmas_server=$("$duniter_getnode_script" "BMAS" | tail -n 1)
    
    if [[ -z "$bmas_server" ]]; then
        echo "ERROR: No working BMAS server found"
        return 1
    fi
    
    echo "Found working BMAS server: $bmas_server"
    
    # Construct the WoT members API URL for the BMAS server
    local wot_api_url
    if [[ "$bmas_server" == *"https://"* ]]; then
        wot_api_url="${bmas_server}/wot/members"
    else
        wot_api_url="https://${bmas_server}/wot/members"
    fi
    
    echo "Fetching from BMAS server: $wot_api_url"
    
    # Try to fetch from the BMAS server
    if check_server_availability "$wot_api_url" 15; then
        if curl -s -m 15 "$wot_api_url" > "$TEMP_DIR/g1_members_raw.json" 2>/dev/null; then
            if [[ -s "$TEMP_DIR/g1_members_raw.json" ]] && jq empty "$TEMP_DIR/g1_members_raw.json" 2>/dev/null; then
                echo "BMAS server successful"
                return 0
            else
                echo "BMAS server returned invalid data"
            fi
        else
            echo "BMAS server failed"
        fi
    else
        echo "BMAS server unavailable"
    fi
    
    # Final fallback: try some known working servers
    echo "Trying known working servers as final fallback..."
    local fallback_servers=(
        "https://duniter-v1.comunes.net/wot/members"
        "https://g1.brussels.ovh/wot/members"
        "https://g1.cgeek.fr/wot/members"
        "https://g1.duniter.fr/wot/members"
    )
    
    for server_url in "${fallback_servers[@]}"; do
        echo "Trying fallback server: $server_url"
        if check_server_availability "$server_url" 10; then
            if curl -s -m 10 "$server_url" > "$TEMP_DIR/g1_members_raw.json" 2>/dev/null; then
                if [[ -s "$TEMP_DIR/g1_members_raw.json" ]] && jq empty "$TEMP_DIR/g1_members_raw.json" 2>/dev/null; then
                    echo "Fallback server successful: $server_url"
                    return 0
                fi
            fi
        fi
    done
    
    echo "ERROR: All servers failed. Cannot fetch Ğ1 WoT members."
    return 1
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

# Function to process all members
process_all_members() {
    echo "Processing members..."
    
    local processed=0
    local new_members=0
    local total_members
    
    total_members=$(jq '.results | length' "$TEMP_DIR/g1_members_raw.json")
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
    "source": "g1_wot_cesium"
  },
  "members": []
}
EOF
        existing_count=0
    else
        existing_count=$(jq '.members | length' "$PROSPECT_FILE" 2>/dev/null || echo "0")
        echo "Found $existing_count existing members"
    fi
    
    # Create a lookup table of existing pubkeys (much faster than checking one by one)
    echo "Creating lookup table of existing pubkeys..."
    jq -r '.members[].pubkey' "$PROSPECT_FILE" 2>/dev/null | sort > "$TEMP_DIR/existing_pubkeys.txt" || touch "$TEMP_DIR/existing_pubkeys.txt"
    
    # Create cache directory for Cesium profile data
    local cache_dir="$TEMP_DIR/coucou"
    mkdir -p "$cache_dir"
    
    # Show existing cache statistics
    local existing_cache_count
    existing_cache_count=$(find "$cache_dir" -name "*.cesium.json" 2>/dev/null | wc -l)
    echo "Found $existing_cache_count existing Cesium cache files"
    
    # Create a temporary file for new members
    local temp_new_members="$TEMP_DIR/new_members.json"
    echo "[]" > "$temp_new_members"
    
    # Batch processing variables
    local batch_size=50
    local current_batch=0
    
    # Process each member
    while IFS= read -r member; do
        local pubkey
        local uid
        
        pubkey=$(echo "$member" | jq -r '.pubkey')
        uid=$(echo "$member" | jq -r '.uid')
        
        processed=$((processed + 1))
        
        # Show progress every 100 members or for the last member
        if [[ $((processed % 100)) -eq 0 ]] || [[ $processed -eq $total_members ]]; then
            show_progress "$processed" "$total_members"
            echo ""
        fi
        
        echo "Processing member $processed/$total_members: $uid ($pubkey)"
        
        # Check if member already exists using grep (much faster than jq)
        if grep -q "^$pubkey$" "$TEMP_DIR/existing_pubkeys.txt" 2>/dev/null; then
            echo "Member $uid already exists, skipping..."
            # Skip delay for existing members to speed up processing
            continue
        fi
        
        # Fetch profile data from Cesium (excluding avatar content to avoid corruption)
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
        "discovery_method": "wot_member_list"
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
        
        # Random delay between 3-5 seconds to avoid being blacklisted (only for new members)
        local delay=$((RANDOM % 3 + 3))  # Random number between 3-5
        echo "Waiting $delay seconds before next request..."
        sleep $delay
        
    done < <(jq -c '.results[]' "$TEMP_DIR/g1_members_raw.json")
    
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
    
    # Update the total_members count
    jq --arg count "$final_count" '.metadata.total_members = ($count | tonumber)' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
    mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
    
    # Clean up temporary files
    rm -f "$temp_new_members" "$TEMP_DIR/existing_pubkeys.txt"
    
    # Note: Cache files in $cache_dir are preserved for future use
    
    echo "Processing complete. New members: $new_members"
    echo "Prospect database updated: $PROSPECT_FILE"
    echo "Total members in database: $final_count"
    
    # Show cache statistics
    local cache_files_count
    cache_files_count=$(find "$cache_dir" -name "*.cesium.json" 2>/dev/null | wc -l)
    echo "Cesium cache files: $cache_files_count (preserved in $cache_dir)"
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
        
        # Show linked accounts statistics
        echo ""
        echo "=== Linked Accounts Statistics ==="
        local gchange_linked_count
        local total_linked_count
        
        gchange_linked_count=$(jq -r '.members[] | select(.import_metadata.discovery_method == "cesium_linked_account") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        total_linked_count=$(jq -r '.members[] | select(.import_metadata.discovery_method != null) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        
        echo "Cesium accounts discovered via Gchange: $gchange_linked_count"
        echo "Total accounts with known discovery method: $total_linked_count"
        
        # Show linked accounts statistics
        echo ""
        echo "=== Gchange Linked Accounts Statistics ==="
        local gchange_linked_accounts
        local updated_accounts
        
        gchange_linked_accounts=$(jq -r '.members[] | select(.linked_accounts.gchange_uid != null) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        updated_accounts=$(jq -r '.members[] | select(.import_metadata.last_gchange_update != null) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
        
        echo "Cesium accounts with linked Gchange UIDs: $gchange_linked_accounts"
        echo "Accounts updated with Gchange information: $updated_accounts"
        
        # Show sample of Gchange-linked accounts
        echo ""
        echo "=== Sample Gchange-Linked Cesium Accounts ==="
        jq -r '.members[] | select(.linked_accounts.gchange_uid != null) | "\(.uid) (\(.pubkey)) -> Gchange: \(.linked_accounts.gchange_uid)"' "$PROSPECT_FILE" 2>/dev/null | head -5 || echo "No Gchange-linked accounts found"
        
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
    echo "Starting G1 prospect database build (final version)..."
    
    # Fetch Ğ1 members
    if ! fetch_g1_members; then
        echo ""
        echo "ERROR: Failed to fetch Ğ1 WoT members from any available server."
        echo ""
        echo "Troubleshooting steps:"
        echo "1. Check your internet connection"
        echo "2. Verify that Astroport.ONE is properly installed"
        echo "3. Try running manually: ~/.zen/Astroport.ONE/tools/duniter_getnode.sh BMAS"
        echo "4. Check if any firewall is blocking the connections"
        echo "5. Try again later (servers might be temporarily unavailable)"
        echo ""
        echo "If the problem persists, you can:"
        echo "- Use a local members file: ./g1prospect_final.sh /path/to/members.json"
        echo "- Check the Duniter network status"
        echo ""
        exit 1
    fi
    
    # Verify we have valid data
    if [[ ! -s "$TEMP_DIR/g1_members_raw.json" ]]; then
        echo "ERROR: No valid members data received"
        exit 1
    fi
    
    # Check if the JSON is valid and has the expected structure
    if ! jq -e '.results' "$TEMP_DIR/g1_members_raw.json" >/dev/null 2>&1; then
        echo "ERROR: Invalid JSON structure. Expected 'results' field not found."
        echo "Server response structure:"
        jq keys "$TEMP_DIR/g1_members_raw.json" 2>/dev/null || echo "Invalid JSON"
        exit 1
    fi
    
    local member_count
    member_count=$(jq '.results | length' "$TEMP_DIR/g1_members_raw.json" 2>/dev/null || echo "0")
    
    if [[ "$member_count" -eq 0 ]]; then
        echo "ERROR: No members found in the response"
        exit 1
    fi
    
    echo "Successfully fetched $member_count members from Ğ1 WoT"
    
    # Process all members
    process_all_members
    
    # Show statistics
    show_statistics
    
    echo ""
    echo "=== G1 Prospect Database Build Complete ==="
}

# Run main function
main "$@" 