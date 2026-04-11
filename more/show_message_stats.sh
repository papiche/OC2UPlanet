#!/bin/bash
########################################################################
# Show Message Statistics from G1 Prospect Database
########################################################################
source ~/.zen/Astroport.ONE/tools/my.sh

PROSPECT_FILE="$HOME/.zen/game/g1prospect.json"

echo "=== G1FabLab & CopyLaRadio Message Statistics ==="
echo ""

if [[ ! -f "$PROSPECT_FILE" ]]; then
    echo "ERROR: Prospect file not found: $PROSPECT_FILE"
    exit 1
fi

# Total members
total_members=$(jq '.members | length' "$PROSPECT_FILE")
echo "📊 Total members in database: $total_members"

# Members with messages sent
members_with_messages=$(jq '.members[] | select(.message_sent) | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
echo "📨 Members with messages sent: $members_with_messages"

# Success vs failed messages
success_messages=$(jq '.members[] | select(.message_sent and .message_sent.status == "success") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)
failed_messages=$(jq '.members[] | select(.message_sent and .message_sent.status == "failed") | .uid' "$PROSPECT_FILE" 2>/dev/null | wc -l)

echo "✅ Successful messages: $success_messages"
echo "❌ Failed messages: $failed_messages"

# Members without messages
members_without_messages=$((total_members - members_with_messages))
echo "📭 Members without messages: $members_without_messages"

# Percentage
if [[ $total_members -gt 0 ]]; then
    percentage=$(echo "scale=1; $members_with_messages * 100 / $total_members" | bc -l 2>/dev/null || echo "0")
    echo "📈 Coverage: ${percentage}%"
fi

echo ""
echo "=== Recent Messages (last 10) ==="
jq -r '.members[] | select(.message_sent) | "\(.uid) - \(.message_sent.date) - \(.message_sent.status)"' "$PROSPECT_FILE" 2>/dev/null | tail -10

echo ""
echo "=== Message Subjects Sent ==="
jq -r '.members[] | select(.message_sent) | .message_sent.subject' "$PROSPECT_FILE" 2>/dev/null | sort | uniq -c

echo ""
echo "=== Sample Member with Message ==="
jq '.members[] | select(.message_sent) | {uid, pubkey, message_sent}' "$PROSPECT_FILE" 2>/dev/null | head -20

echo ""
echo "=== Ready for Next Campaign ==="
echo "Members ready to receive messages: $members_without_messages" 