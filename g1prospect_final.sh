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
    
    # Start building the JSON structure
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
    
    # Process each member
    local first_member=true
    while IFS= read -r member; do
        local pubkey
        local uid
        
        pubkey=$(echo "$member" | jq -r '.pubkey')
        uid=$(echo "$member" | jq -r '.uid')
        
        processed=$((processed + 1))
        echo "Processing member $processed/$total_members: $uid ($pubkey)"
        
        # Check if member already exists (simple check)
        if [[ -f "$PROSPECT_FILE" ]] && grep -q "$pubkey" "$PROSPECT_FILE" 2>/dev/null; then
            echo "Member $uid already exists, skipping..."
            continue
        fi
        
        # Fetch profile data from Cesium
        local cesium_url="$myCESIUM/user/profile/$pubkey"
        echo "Fetching profile from: $cesium_url"
        
        local profile_data
        profile_data=$(curl -s "$cesium_url" 2>/dev/null || echo "{}")
        
        # Add comma if not first member
        if [[ "$first_member" == "true" ]]; then
            first_member=false
        else
            echo "," >> "$PROSPECT_FILE"
        fi
        
        # Add member to file
        cat >> "$PROSPECT_FILE" << EOF
    {
      "pubkey": "$pubkey",
      "uid": "$uid",
      "added_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
      "profile": $profile_data,
      "source": "g1_wot"
    }
EOF
        
        new_members=$((new_members + 1))
        echo "Member $uid added to database"
        
        # Random delay between 3-5 seconds to avoid being blacklisted
        local delay=$((RANDOM % 3 + 3))  # Random number between 3-5
        echo "Waiting $delay seconds before next request..."
        sleep $delay
        
    done < <(jq -c '.results[]' "$TEMP_DIR/g1_members_raw.json")
    
    # Close the JSON structure (remove trailing comma if exists)
    sed -i 's/,$//' "$PROSPECT_FILE"
    cat >> "$PROSPECT_FILE" << EOF
  ]
}
EOF
    
    # Update metadata with correct count
    local final_count
    final_count=$(jq '.members | length' "$PROSPECT_FILE")
    
    # Update the total_members count
    sed -i "s/\"total_members\": 0/\"total_members\": $final_count/" "$PROSPECT_FILE"
    
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