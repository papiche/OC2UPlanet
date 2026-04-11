#!/bin/bash
########################################################################
# Test script for G1FabLab & CopyLaRadio Presentation Campaign
########################################################################
source ~/.zen/Astroport.ONE/tools/my.sh

echo "=== Testing G1FabLab & CopyLaRadio Presentation Campaign ==="
echo ""

# Check if the main script exists
if [[ ! -f "send_g1fablab_presentation.sh" ]]; then
    echo "ERROR: send_g1fablab_presentation.sh not found!"
    exit 1
fi

# Check if prospect file exists
if [[ ! -f "$HOME/.zen/game/g1prospect.json" ]]; then
    echo "ERROR: Prospect file not found: $HOME/.zen/game/g1prospect.json"
    echo "Please run g1prospect_final.sh first"
    exit 1
fi

# Check environment variables
echo "1. Checking environment variables..."
if [[ -z "${CAPTAINEMAIL:-}" ]]; then
    echo "WARNING: CAPTAINEMAIL not set"
else
    echo "✓ CAPTAINEMAIL is set"
fi

if [[ -z "${contactG1PUB:-}" ]]; then
    echo "WARNING: contactG1PUB not set"
else
    echo "✓ contactG1PUB is set"
fi

# Check jaklis
echo ""
echo "2. Checking jaklis..."
if [[ ! -f "$HOME/.zen/Astroport.ONE/tools/jaklis/jaklis.py" ]]; then
    echo "ERROR: jaklis.py not found"
    exit 1
else
    echo "✓ jaklis.py found"
fi

# Check prospect file structure
echo ""
echo "3. Checking prospect file structure..."
total_members=$(jq '.members | length' "$HOME/.zen/game/g1prospect.json")
echo "✓ Found $total_members members"

# Check for existing message_sent fields
existing_messages=$(jq '.members[] | select(.message_sent) | .uid' "$HOME/.zen/game/g1prospect.json" 2>/dev/null | wc -l)
echo "✓ $existing_messages members already have message_sent field"

# Show sample member structure
echo ""
echo "4. Sample member structure:"
jq '.members[0]' "$HOME/.zen/game/g1prospect.json" | head -20

echo ""
echo "5. Testing dry-run mode..."
echo "Running: ./send_g1fablab_presentation.sh --dry-run"
echo ""

# Run dry-run test
./send_g1fablab_presentation.sh --dry-run

echo ""
echo "=== Test Completed ==="
echo ""
echo "To run the actual campaign:"
echo "  ./send_g1fablab_presentation.sh"
echo ""
echo "To run in test mode (single test pubkey):"
echo "  ./send_g1fablab_presentation.sh --test"
echo ""
echo "To test single message to specific pubkey:"
echo "  ./test_single_message.sh"
echo ""
echo "To view Cesium nodes status:"
echo "  ./show_cesium_nodes.sh" 