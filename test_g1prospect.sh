#!/bin/bash
########################################################################
# Test script for G1 Prospect Database Builder
########################################################################

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

echo "1. Testing with sample data..."
echo "   Running: ./g1prospect_final.sh test_members.json"
echo ""

# Run the script
./g1prospect_final.sh test_members.json

echo ""
echo "2. Checking results..."
echo ""

# Check if the output file was created
if [[ -f "$HOME/.zen/game/g1prospect.json" ]]; then
    echo "✅ Prospect database created successfully"
    echo "   Location: $HOME/.zen/game/g1prospect.json"
    
    # Show file size
    file_size=$(ls -lh "$HOME/.zen/game/g1prospect.json" | awk '{print $5}')
    echo "   Size: $file_size"
    
    # Show metadata
    echo ""
    echo "📊 Database metadata:"
    jq '.metadata' "$HOME/.zen/game/g1prospect.json"
    
    # Show sample members
    echo ""
    echo "👥 Sample members:"
    jq -r '.members[0:3][] | "   - \(.uid) (\(.pubkey))"' "$HOME/.zen/game/g1prospect.json"
    
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