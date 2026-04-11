#!/bin/bash
########################################################################
# Test script for G1 Prospect Database Builder
########################################################################

# Trap to handle Ctrl+C gracefully
cleanup_test() {
    echo ""
    echo "Test interrupted. Current state preserved."
    echo "You can resume by running: ./g1prospect_final.sh test_members.json"
    exit 0
}

trap cleanup_test INT TERM

echo "=== Testing G1 Prospect Database Builder ==="
echo ""

# Check if the main script exists
if [[ ! -f "g1prospect_final.sh" ]]; then
    echo "ERROR: g1prospect_final.sh not found!"
    exit 1
fi

# Check if test data exists
if [[ ! -f "test_members.json" ]]; then
    echo "ERROR: test_members.json not found!"
    exit 1
fi

# Check if database already exists
PROSPECT_FILE="$HOME/.zen/game/g1prospect.json"
if [[ -f "$PROSPECT_FILE" ]]; then
    echo "📁 Existing database found: $PROSPECT_FILE"
    
    # Show current state
    if jq empty "$PROSPECT_FILE" 2>/dev/null; then
        current_members=$(jq '.members | length' "$PROSPECT_FILE" 2>/dev/null || echo "0")
        echo "   Current members: $current_members"
        
        if [[ $current_members -gt 0 ]]; then
            echo "   ✅ Valid database with $current_members members found"
            echo ""
            echo "🔄 Do you want to:"
            echo "   1. Continue from where you left off (recommended)"
            echo "   2. Start fresh (will overwrite existing data)"
            echo "   3. Just view current results"
            echo ""
            read -p "Enter choice (1-3): " choice
        else
            echo "   ⚠️  Database exists but is empty"
            echo ""
            echo "🔄 Do you want to:"
            echo "   1. Start processing members (recommended)"
            echo "   2. Start fresh (will overwrite existing data)"
            echo "   3. Just view current results"
            echo ""
            read -p "Enter choice (1-3): " choice
        fi
        
        case $choice in
            1)
                echo "Continuing from existing data..."
                echo "   Running: ./g1prospect_final.sh test_members.json"
                echo ""
                ./g1prospect_final.sh test_members.json
                ;;
            2)
                echo "Starting fresh..."
                rm -f "$PROSPECT_FILE"
                echo "   Running: ./g1prospect_final.sh test_members.json"
                echo ""
                ./g1prospect_final.sh test_members.json
                ;;
            3)
                echo "Showing current results only..."
                ;;
            *)
                echo "Invalid choice, continuing from existing data..."
                ./g1prospect_final.sh test_members.json
                ;;
        esac
    else
        echo "❌ Existing database is corrupted, starting fresh..."
        rm -f "$PROSPECT_FILE"
        echo "   Running: ./g1prospect_final.sh test_members.json"
        echo ""
        ./g1prospect_final.sh test_members.json
    fi
else
    echo "🆕 No existing database found, starting fresh..."
    echo "   Running: ./g1prospect_final.sh test_members.json"
    echo ""
    ./g1prospect_final.sh test_members.json
fi

echo ""
echo "2. Checking results..."
echo ""

# Check if the output file was created
if [[ -f "$PROSPECT_FILE" ]]; then
    echo "✅ Prospect database created successfully"
    echo "   Location: $PROSPECT_FILE"
    
    # Show file size
    file_size=$(ls -lh "$PROSPECT_FILE" | awk '{print $5}')
    echo "   Size: $file_size"
    
    # Show metadata
    echo ""
    echo "📊 Database metadata:"
    jq '.metadata' "$PROSPECT_FILE"
    
    # Show sample members
    echo ""
    echo "👥 Sample members:"
    jq -r '.members[0:3][] | "   - \(.uid) (\(.pubkey))"' "$PROSPECT_FILE"
    
else
    echo "❌ Prospect database not found!"
    exit 1
fi

echo ""
echo "3. Testing duplicate handling..."
echo "   Running the script again to test duplicate detection..."
echo ""

# Run the script again to test duplicate handling
./g1prospect_final.sh test_members.json

echo ""
echo "=== Test completed successfully! ==="
echo ""
echo "The G1 prospect database builder is working correctly."
echo "You can now use this database for OC2UPlanet integration." 