#!/usr/bin/env bash
########################################################################
# Version: 0.1
# License: AGPL-3.0 (https://choosealicense.com/licenses/agpl-3.0/)
########################################################################
## French National Assembly Deputy Adder
########################################################################
## Helper script to manually add deputy information to the prospect database
########################################################################

set -euo pipefail

# Constants
PROSPECT_FILE="$HOME/.zen/game/fr_an_prospect.json"

# Function to add a deputy
add_deputy() {
    local id="$1"
    local first_name="$2"
    local last_name="$3"
    local email="$4"
    local phone="$5"
    local twitter="$6"
    local facebook="$7"
    local commissions="$8"
    local county="$9"
    local group="${10}"
    local photo="${11}"
    
    # Create deputy JSON
    local deputy_json
    deputy_json=$(jq -n \
        --arg id "$id" \
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
        '{ "id": $id, "added_date": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'", "profile": { "first_name": $first_name, "last_name": $last_name, "email": $email, "phone": $phone, "twitter": $twitter, "facebook": $facebook, "commissions": $commissions, "county": $county, "group": $group, "photo": $photo }, "source": "french_national_assembly", "import_metadata": { "source_script": "add_deputy.sh", "import_date": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'", "discovery_method": "manual_entry" } }')
    
    # Add to database
    jq --argjson member "$deputy_json" '.members += [$member] | .metadata.updated_date = "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'" | .metadata.total_members = (.members | length)' "$PROSPECT_FILE" > "$PROSPECT_FILE.new"
    mv "$PROSPECT_FILE.new" "$PROSPECT_FILE"
    
    echo "Deputy $first_name $last_name ($id) added successfully"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <id> <first_name> <last_name> <email> <phone> <twitter> <facebook> <commissions> <county> <group> <photo>"
    echo ""
    echo "Example:"
    echo "  $0 PA123456 \"Jean\" \"Dupont\" \"jean.dupont@assemblee-nationale.fr\" \"+33123456789\" \"jeandupont\" \"jeandupont.depute\" \"Commission des Finances\" \"75\" \"La République en Marche\" \"123456\""
    echo ""
    echo "Or use interactive mode:"
    echo "  $0"
}

# Function to run interactive mode
interactive_mode() {
    echo "=== Interactive Deputy Addition ==="
    echo ""
    
    read -p "Deputy ID (e.g., PA123456): " id
    read -p "First Name: " first_name
    read -p "Last Name: " last_name
    read -p "Email: " email
    read -p "Phone: " phone
    read -p "Twitter (without @): " twitter
    read -p "Facebook: " facebook
    read -p "Commissions: " commissions
    read -p "County: " county
    read -p "Political Group: " group
    read -p "Photo ID: " photo
    
    echo ""
    echo "Adding deputy..."
    add_deputy "$id" "$first_name" "$last_name" "$email" "$phone" "$twitter" "$facebook" "$commissions" "$county" "$group" "$photo"
}

# Main execution
main() {
    # Check if database exists
    if [[ ! -f "$PROSPECT_FILE" ]]; then
        echo "ERROR: Database file not found: $PROSPECT_FILE"
        echo "Please run FR_AssembleeNationale.sh first to create the database structure."
        exit 1
    fi
    
    # Check arguments
    if [[ $# -eq 0 ]]; then
        interactive_mode
    elif [[ $# -eq 11 ]]; then
        add_deputy "$@"
    else
        show_usage
        exit 1
    fi
    
    echo ""
    echo "Current database statistics:"
    local total_members
    total_members=$(jq -r '.metadata.total_members' "$PROSPECT_FILE")
    echo "Total deputies: $total_members"
}

# Run main function
main "$@" 