#!/usr/bin/env bash
########################################################################
# Version: 0.3
# License: AGPL-3.0 (https://choosealicense.com/licenses/agpl-3.0/)
########################################################################
## French National Assembly Database Builder
########################################################################
## Fetches French National Assembly deputies data and builds
## a prospect database for OC2UPlanet
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
    
    echo "Cleanup complete"
    exit 1
}

trap cleanup_on_exit INT TERM

# Default configuration
USER_AGENT="Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0"

# Constants
PROSPECT_FILE="$HOME/.zen/game/fr_an_prospect.json"
TEMP_DIR="$HOME/.zen/tmp"
MAIN_DIR="$HOME/.zen/tmp/coucou/FR"
AN_DATA_URL="https://data.assemblee-nationale.fr/static/openData/repository/16/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip"

# Create necessary directories
mkdir -p "$(dirname "$PROSPECT_FILE")"
mkdir -p "$TEMP_DIR"
mkdir -p "$MAIN_DIR/data/"
mkdir -p "$MAIN_DIR/data/gen/an/images/"

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

# Function to create basic database structure
create_basic_database() {
    echo ""
    echo "=== Creating Basic Database Structure ==="
    echo "Since deputy data is not available in the expected format,"
    echo "creating a basic database structure for manual data entry."
    
    # Create basic database structure
    cat > "$PROSPECT_FILE" << EOF
{
  "metadata": {
    "created_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "updated_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "total_members": 0,
    "source": "french_national_assembly_manual",
    "note": "Database created manually due to data structure changes at French National Assembly"
  },
  "members": []
}
EOF
    
    echo "Basic database structure created at: $PROSPECT_FILE"
    echo ""
    echo "You can manually add deputy information to this database using the following format:"
    echo '{'
    echo '  "id": "PA123456",'
    echo '  "added_date": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",'
    echo '  "profile": {'
    echo '    "first_name": "John",'
    echo '    "last_name": "Doe",'
    echo '    "email": "john.doe@assemblee-nationale.fr",'
    echo '    "phone": "+33123456789",'
    echo '    "twitter": "johndoe",'
    echo '    "facebook": "johndoe.depute",'
    echo '    "commissions": "Commission des Finances",'
    echo '    "county": "75",'
    echo '    "group": "La République en Marche",'
    echo '    "photo": "123456"'
    echo '  },'
    echo '  "source": "french_national_assembly",'
    echo '  "import_metadata": {'
    echo '    "source_script": "FR_AssembleeNationale.sh",'
    echo '    "import_date": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",'
    echo '    "discovery_method": "manual_entry"'
    echo '  }'
    echo '}'
    echo ""
    echo "To add a member, use: jq --argjson member 'MEMBER_JSON' '.members += [\$member]' $PROSPECT_FILE > $PROSPECT_FILE.new && mv $PROSPECT_FILE.new $PROSPECT_FILE"
    echo ""
}

# Function to check for alternative data sources
check_alternative_sources() {
    echo ""
    echo "=== Checking Alternative Data Sources ==="
    
    # Check if there are other data files in the zip
    echo "Checking for other data files in the current zip..."
    cd "${MAIN_DIR}/data/"
    local file_count
    file_count=$(unzip -l an.zip | tail -1 | awk '{print $2}')
    echo "Total files in zip: $file_count"
    
    local organe_count
    organe_count=$(unzip -l an.zip | grep "json/organe/" | wc -l)
    echo "Organe files: $organe_count"
    
    local other_count=$((file_count - organe_count - 3))  # Subtract header lines
    if [[ $other_count -gt 0 ]]; then
        echo "Other files: $other_count"
        echo "Checking for deputy-related data..."
        unzip -l an.zip | grep -v "json/organe/" | grep -v "Archive:" | grep -v "Length" | grep -v "files" | head -5
    else
        echo "No other files found in the current zip."
    fi
    
    echo ""
    echo "=== Recommendations ==="
    echo "1. The French National Assembly may have changed their data structure"
    echo "2. Check their official website for updated data access methods"
    echo "3. Consider using their web scraping approach instead of direct data download"
    echo "4. Contact the French National Assembly for updated data access"
    echo "5. Use manual data entry with the basic database structure"
    echo ""
}

# Function to download and extract AN data
download_an_data() {
    echo "Downloading French National Assembly data..."
    
    if [[ ! -s "${MAIN_DIR}/data/an.zip" ]]; then
        echo -n "Downloading data from Assemblée Nationale..."
        if wget -q -U "${USER_AGENT}" "$AN_DATA_URL" -O "${MAIN_DIR}/data/an.zip"; then
            echo " done."
        else
            echo " failed."
            return 1
        fi
        
        echo -n "Extracting data..."
        cd "${MAIN_DIR}/data/"
        if unzip -q an.zip; then
            echo " done."
        else
            echo " failed."
            return 1
        fi
    else
        echo "Using existing AN data file."
    fi
    
    # Check if the expected data structure exists
    if [[ ! -d "${MAIN_DIR}/data/json/acteur" ]]; then
        echo ""
        echo "WARNING: Expected deputy data directory 'json/acteur' not found in the extracted data."
        echo "This indicates that the French National Assembly has changed their data structure."
        echo ""
        echo "Available data structure:"
        ls -la "${MAIN_DIR}/data/json/" 2>/dev/null || echo "No json directory found"
        echo ""
        echo "The current data appears to only contain organizational data (organe) but not deputy data (acteur)."
        echo "This script requires deputy data to function properly."
        echo ""
        echo "Possible solutions:"
        echo "1. Check if there's a different data source or URL for deputy information"
        echo "2. The French National Assembly may have changed their data format"
        echo "3. Contact the French National Assembly for updated data access"
        echo ""
        echo "For now, the script cannot proceed without deputy data."
        return 1
    fi
    
    return 0
}

# Function to process all deputies
process_all_deputies() {
    echo "Processing deputies..."
    
    cd "${MAIN_DIR}/data/"
    
    # Initialize or load existing database
    if [[ ! -f "$PROSPECT_FILE" ]] || [[ ! -s "$PROSPECT_FILE" ]] || ! jq empty "$PROSPECT_FILE" 2>/dev/null; then
        echo "Creating new database structure..."
        cat > "$PROSPECT_FILE" << EOF
{
  "metadata": {
    "created_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "updated_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "total_members": 0,
    "source": "french_national_assembly"
  },
  "members": []
}
EOF
        existing_count=0
    else
        existing_count=$(jq '.members | length' "$PROSPECT_FILE" 2>/dev/null || echo "0")
        echo "Found $existing_count existing members"
    fi
    
    # Create a lookup table of existing IDs (much faster than checking one by one)
    echo "Creating lookup table of existing IDs..."
    jq -r '.members[].id' "$PROSPECT_FILE" 2>/dev/null | sort > "$TEMP_DIR/existing_ids.txt" || touch "$TEMP_DIR/existing_ids.txt"
    
    # Show existing cache statistics
    local existing_cache_count
    existing_cache_count=$(find "$MAIN_DIR" -name "*.an.json" 2>/dev/null | wc -l)
    echo "Found $existing_cache_count existing AN cache files"
    
    # Get all deputy files
    local deputy_files
    deputy_files=$(find json/acteur/ -type f -name "*.json" | sed 's/\.json//i' | sed 's/json\/acteur\///i')
    local total_deputies
    total_deputies=$(echo "$deputy_files" | wc -l)
    
    echo "Total deputies to process: $total_deputies"
    
    local processed=0
    local new_members=0
    
    # Process each deputy
    while IFS= read -r key; do
        processed=$((processed + 1))
        
        # Show progress every 10 deputies or for the last deputy
        if [[ $((processed % 10)) -eq 0 ]] || [[ $processed -eq $total_deputies ]]; then
            show_progress "$processed" "$total_deputies"
            echo ""
        fi
        
        echo "Processing deputy $processed/$total_deputies: $key"
        
        # Check if deputy already exists using grep (much faster than jq)
        if grep -q "^$key$" "$TEMP_DIR/existing_ids.txt" 2>/dev/null; then
            echo "Deputy $key already exists, skipping..."
            continue
        fi
        
        # Check cache first
        local cache_file="$MAIN_DIR/$key.an.json"
        local deputy_data
        
        if [[ -f "$cache_file" ]]; then
            echo "Using cached deputy data for $key"
            deputy_data=$(cat "$cache_file")
        else
            echo "Processing deputy data for $key"
            
            # Extract deputy information
            local first_name
            local last_name
            local email
            local phone
            local twitter
            local facebook
            local commissions
            local county
            local group
            local photo
            
            first_name=$(jq -r .acteur.etatCivil.ident.prenom "json/acteur/${key}.json" 2>/dev/null || echo "")
            last_name=$(jq -r .acteur.etatCivil.ident.nom "json/acteur/${key}.json" 2>/dev/null || echo "")
            
            # Extract email addresses
            email=$(jq -r '.acteur.adresses.adresse | map(. | select(.type=="15")) | .[].valElec' "json/acteur/${key}.json" 2>/dev/null | tac | awk '{print tolower($0)}' | tr '\n' ',' | sed 's/,$//')
            
            # Extract phone numbers
            local phoneRaw
            phoneRaw=$(jq -r '.acteur.adresses.adresse | map(. | select(.type=="11")) | .[].valElec' "json/acteur/${key}.json" 2>/dev/null | tac)
            
            phone=""
            if [[ -n "$phoneRaw" ]]; then
                while IFS= read -r i; do
                    if [[ -n "$i" ]]; then
                        local formatted_phone
                        formatted_phone=$(echo "$i" | tr -d ' .' | sed 's/(0)//i' | sed 's/^00/\+/i' | sed 's/^0590/\+590/i' | sed 's/^0596/\+596/i' | sed 's/^0594/\+594/i' | sed 's/^0262/\+262/i' | sed 's/^0508/\+508/i' | sed 's/^0269/\+262269/i')
                        if [[ -n "$phone" ]]; then
                            phone="${phone},${formatted_phone}"
                        else
                            phone="$formatted_phone"
                        fi
                    fi
                done <<< "$phoneRaw"
            fi
            
            # Extract social media
            twitter=$(jq -r '.acteur.adresses.adresse | map(. | select(.type=="24")) | .[].valElec' "json/acteur/${key}.json" 2>/dev/null | sed 's/\@//i' | tr '\n' ',' | sed 's/,$//')
            facebook=$(jq -r '.acteur.adresses.adresse | map(. | select(.type=="25")) | .[].valElec' "json/acteur/${key}.json" 2>/dev/null | sed 's/\@//i' | tr '\n' ',' | sed 's/,$//')
            
            # Extract commissions
            local commissionsRef
            commissionsRef=$(jq -r '.acteur.mandats[] | map(. | select(.typeOrgane=="COMPER" or .typeOrgane=="COMNL")) | .[].organes.organeRef' "json/acteur/${key}.json" 2>/dev/null | sort -u)
            
            commissions=""
            if [[ -n "$commissionsRef" ]]; then
                while IFS= read -r i; do
                    if [[ -n "$i" ]]; then
                        local commission_name
                        commission_name=$(jq -r .organe.libelleAbrege "json/organe/${i}.json" 2>/dev/null || echo "")
                        if [[ -n "$commission_name" ]]; then
                            if [[ -n "$commissions" ]]; then
                                commissions="${commissions},${commission_name}"
                            else
                                commissions="$commission_name"
                            fi
                        fi
                    fi
                done <<< "$commissionsRef"
            fi
            
            # Extract county
            county=$(jq -r '.acteur.mandats[] | map(. | select(.typeOrgane=="ASSEMBLEE")) | .[].election.lieu.departement' "json/acteur/${key}.json" 2>/dev/null | head -1)
            
            # Extract political group
            local groupRef
            groupRef=$(jq -r '.acteur.mandats[] | map(. | select(.typeOrgane=="GP")) | .[].organes.organeRef' "json/acteur/${key}.json" 2>/dev/null | head -1)
            group=$(jq -r .organe.libelle "json/organe/${groupRef}.json" 2>/dev/null || echo "")
            
            # Extract photo ID
            photo=$(echo "$key" | sed 's/PA//i')
            
            # Create deputy data object
            deputy_data=$(jq -n \
                --arg id "$key" \
                --arg first_name "$first_name" \
                --arg last_name "$last_name" \
                --arg email "$email" \
                --arg phone "$phone" \
                --arg twitter "$twitter" \
                --arg facebook "$facebook" \
                --arg commissions "$commissions" \
                --arg county "$county" \
                --arg group "$group" \
                --arg photo "$photo" \
                '{ "id": $id, "first_name": $first_name, "last_name": $last_name, "email": $email, "phone": $phone, "twitter": $twitter, "facebook": $facebook, "commissions": $commissions, "county": $county, "group": $group, "photo": $photo }')
            
            # Cache the deputy data
            echo "$deputy_data" > "$cache_file"
        fi
        
        # Download photo if not already cached
        local photo_id
        photo_id=$(echo "$deputy_data" | jq -r '.photo')
        if [[ -n "$photo_id" ]] && [[ "$photo_id" != "null" ]]; then
            local photo_file="${MAIN_DIR}/data/gen/an/images/${photo_id}.jpg"
            if [[ ! -f "$photo_file" ]]; then
                echo "Downloading photo for $photo_id..."
                wget -q -U "${USER_AGENT}" "https://www2.assemblee-nationale.fr/static/tribun/16/photos/${photo_id}.jpg" -O "$photo_file" 2>/dev/null || echo "Photo download failed for $photo_id"
            fi
        fi
        
        # Create new member object
        local new_member
        new_member=$(jq -n \
            --arg id "$key" \
            --arg added_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
            --argjson profile "$deputy_data" \
            --arg import_source "FR_AssembleeNationale.sh" \
            --arg import_date "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
            '{ "id": $id, "added_date": $added_date, "profile": $profile, "source": "french_national_assembly", "import_metadata": { "source_script": $import_source, "import_date": $import_date, "discovery_method": "an_official_data" } }')
        
        # Add to database
        jq --argjson member "$new_member" '.members += [$member]' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
        mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
        
        # Update the lookup table
        echo "$key" >> "$TEMP_DIR/existing_ids.txt"
        
        new_members=$((new_members + 1))
        echo "Deputy $key added successfully"
        
        # Random delay between 1-3 seconds to avoid being blacklisted
        local delay=$((RANDOM % 3 + 1))
        echo "Waiting $delay seconds before next request..."
        sleep $delay
        
    done <<< "$deputy_files"
    
    # Update final metadata
    local final_count
    final_count=$(jq '.members | length' "$PROSPECT_FILE")
    
    # Update the total_members count
    jq --arg count "$final_count" '.metadata.total_members = ($count | tonumber)' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
    mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
    
    # Clean up temporary files
    rm -f "$TEMP_DIR/existing_ids.txt"
    
    # Note: Cache files in $MAIN_DIR are preserved for future use
    
    echo "Processing complete. New members: $new_members"
    echo "Prospect database updated: $PROSPECT_FILE"
    echo "Total members in database: $final_count"
    
    # Show cache statistics
    local cache_files_count
    cache_files_count=$(find "$MAIN_DIR" -name "*.an.json" 2>/dev/null | wc -l)
    echo "AN cache files: $cache_files_count (preserved in $MAIN_DIR)"
}

# Function to display statistics
show_statistics() {
    if [[ -f "$PROSPECT_FILE" ]]; then
        echo ""
        echo "=== French National Assembly Database Statistics ==="
        local total_members
        local updated_date
        
        total_members=$(jq -r '.metadata.total_members' "$PROSPECT_FILE" 2>/dev/null || echo "0")
        updated_date=$(jq -r '.metadata.updated_date' "$PROSPECT_FILE" 2>/dev/null || echo "Unknown")
        
        echo "Total deputies: $total_members"
        echo "Last updated: $updated_date"
        echo "Database file: $PROSPECT_FILE"
        
        # Show political group statistics
        echo ""
        echo "=== Political Group Statistics ==="
        jq -r '.members[].profile.group' "$PROSPECT_FILE" 2>/dev/null | sort | uniq -c | sort -nr | head -10 || echo "No group data available"
        
        # Show county statistics
        echo ""
        echo "=== County Statistics ==="
        jq -r '.members[].profile.county' "$PROSPECT_FILE" 2>/dev/null | sort | uniq -c | sort -nr | head -10 || echo "No county data available"
        
        # Show sample of deputies
        echo ""
        echo "=== Sample Deputies ==="
        jq -r '.members[0:5][] | "\(.profile.first_name) \(.profile.last_name) (\(.id)) - \(.profile.group)"' "$PROSPECT_FILE" 2>/dev/null || echo "No deputies found"
    else
        echo "No prospect database found"
    fi
}

# Main execution
main() {
    echo "Starting French National Assembly prospect database build..."
    
    # Download AN data
    if ! download_an_data; then
        echo ""
        echo "ERROR: Failed to download French National Assembly data or data structure is incompatible."
        echo ""
        
        # Check for alternative sources
        check_alternative_sources
        
        echo "Troubleshooting steps:"
        echo "1. Check your internet connection"
        echo "2. Verify that the AN data URL is accessible"
        echo "3. Check if any firewall is blocking the connections"
        echo "4. Try again later (server might be temporarily unavailable)"
        echo "5. The French National Assembly may have changed their data structure"
        echo ""
        
        # Offer to create basic database
        echo "Would you like to create a basic database structure for manual data entry? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            create_basic_database
            show_statistics
            echo ""
            echo "=== Basic Database Created ==="
            echo "You can now manually add deputy information to the database."
            exit 0
        else
            echo "Exiting without creating database."
            exit 1
        fi
    fi
    
    # Process all deputies
    process_all_deputies
    
    # Show statistics
    show_statistics
    
    echo ""
    echo "=== French National Assembly Database Build Complete ==="
}

# Run main function
main "$@"
