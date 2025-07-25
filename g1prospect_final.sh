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

# Constants
PROSPECT_FILE="$HOME/.zen/game/g1prospect.json"
MEMBERS_FILE="${1:-}"
TEMP_DIR="$HOME/.zen/tmp"
G1_WOT_API="https://g1.duniter.org/wot/members"

# Create necessary directories
mkdir -p "$(dirname "$PROSPECT_FILE")"
mkdir -p "$TEMP_DIR"

# Function to fetch Ğ1 members
fetch_g1_members() {
    echo "Fetching Ğ1 WoT members..."
    
    if [[ -n "$MEMBERS_FILE" ]] && [[ -f "$MEMBERS_FILE" ]]; then
        echo "Using provided members file: $MEMBERS_FILE"
        cp "$MEMBERS_FILE" "$TEMP_DIR/g1_members_raw.json"
    else
        echo "Fetching from Ğ1 WoT API: $G1_WOT_API"
        curl -s "$G1_WOT_API" > "$TEMP_DIR/g1_members_raw.json"
    fi
    
    if [[ ! -s "$TEMP_DIR/g1_members_raw.json" ]]; then
        echo "ERROR: Failed to fetch or read members data"
        return 1
    fi
    
    echo "Members data fetched successfully"
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
    
    # Process each member
    while IFS= read -r member; do
        local pubkey
        local uid
        
        pubkey=$(echo "$member" | jq -r '.pubkey')
        uid=$(echo "$member" | jq -r '.uid')
        
        processed=$((processed + 1))
        echo "Processing member $processed/$total_members: $uid ($pubkey)"
        
        # Check if member already exists
        if jq -e --arg pk "$pubkey" '.members[] | select(.pubkey == $pk)' "$PROSPECT_FILE" >/dev/null 2>&1; then
            echo "Member $uid already exists, skipping..."
            continue
        fi
        
        # Fetch profile data from Cesium (excluding avatar content to avoid corruption)
        local cesium_url="$myCESIUM/user/profile/$pubkey?_source_exclude=avatar._content"
        echo "Fetching profile from: $cesium_url"
        
        local profile_data
        profile_data=$(curl -s "$cesium_url" 2>/dev/null || echo "{}")
        
        # Create new member object
        local new_member
        new_member=$(cat << EOF
    {
      "pubkey": "$pubkey",
      "uid": "$uid",
      "added_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
      "profile": $profile_data,
      "source": "g1_wot"
    }
EOF
)
        
        # Add member directly to the main file using jq (this ensures JSON validity)
        jq --argjson member "$new_member" '.members += [$member] | .metadata.updated_date = "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
        mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
        
        new_members=$((new_members + 1))
        echo "Member $uid added to database"
        
        # Random delay between 3-5 seconds to avoid being blacklisted
        local delay=$((RANDOM % 3 + 3))  # Random number between 3-5
        echo "Waiting $delay seconds before next request..."
        sleep $delay
        
    done < <(jq -c '.results[]' "$TEMP_DIR/g1_members_raw.json")
    
    # Update final metadata
    local final_count
    final_count=$(jq '.members | length' "$PROSPECT_FILE")
    
    # Update the total_members count
    jq --arg count "$final_count" '.metadata.total_members = ($count | tonumber)' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
    mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
    
    echo "Processing complete. New members: $new_members"
    echo "Prospect database updated: $PROSPECT_FILE"
    echo "Total members in database: $final_count"
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
    fetch_g1_members
    
    # Process all members
    process_all_members
    
    # Show statistics
    show_statistics
    
    echo ""
    echo "=== G1 Prospect Database Build Complete ==="
}

# Run main function
main "$@" 