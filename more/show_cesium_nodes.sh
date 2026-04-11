#!/bin/bash
########################################################################
# Show Cesium Nodes Status and Statistics
########################################################################

echo "=== Cesium Nodes Status and Statistics ==="
echo ""

# Check if .env file exists
if [[ ! -f ".env" ]]; then
    echo "❌ .env file not found"
    echo "Run ./test_single_message.sh first to test and configure nodes"
    exit 1
fi

echo "📋 Configuration from .env file:"
echo ""

# Display primary node
if grep -q "^CESIUM_PRIMARY_NODE=" .env; then
    primary_node=$(grep "^CESIUM_PRIMARY_NODE=" .env | cut -d'=' -f2)
    echo "🎯 Primary node: $primary_node"
else
    echo "❌ No primary node configured"
fi

echo ""

# Display working nodes
if grep -q "^CESIUM_WORKING_NODES=" .env; then
    working_nodes=$(grep "^CESIUM_WORKING_NODES=" .env | cut -d'=' -f2)
    echo "✅ Working nodes:"
    for node in $working_nodes; do
        echo "  - $node"
    done
else
    echo "❌ No working nodes configured"
fi

echo ""

# Display failed nodes
if grep -q "^CESIUM_FAILED_NODES=" .env; then
    failed_nodes=$(grep "^CESIUM_FAILED_NODES=" .env | cut -d'=' -f2)
    if [[ -n "$failed_nodes" ]]; then
        echo "❌ Failed nodes:"
        for node in $failed_nodes; do
            echo "  - $node"
        done
    else
        echo "✅ No failed nodes"
    fi
else
    echo "❌ No failed nodes information"
fi

echo ""

# Display statistics
if grep -q "^CESIUM_TOTAL_TESTED=" .env; then
    total_tested=$(grep "^CESIUM_TOTAL_TESTED=" .env | cut -d'=' -f2)
    working_count=$(grep "^CESIUM_WORKING_COUNT=" .env | cut -d'=' -f2)
    failed_count=$(grep "^CESIUM_FAILED_COUNT=" .env | cut -d'=' -f2)
    
    echo "📊 Statistics:"
    echo "  Total tested: $total_tested"
    echo "  Working: $working_count"
    echo "  Failed: $failed_count"
    
    if [[ $total_tested -gt 0 ]]; then
        success_rate=$(echo "scale=1; $working_count * 100 / $total_tested" | bc -l 2>/dev/null || echo "0")
        echo "  Success rate: ${success_rate}%"
    fi
fi

echo ""

# Test current primary node connectivity
if [[ -n "$primary_node" ]]; then
    echo "🔍 Testing primary node connectivity..."
    if curl -s --connect-timeout 5 "$primary_node" >/dev/null 2>&1; then
        echo "✅ Primary node is reachable"
    else
        echo "❌ Primary node is not reachable"
        echo "Consider running ./test_single_message.sh again"
    fi
fi

echo ""
echo "=== Available Commands ==="
echo "1. Test all nodes: ./test_single_message.sh"
echo "2. Send campaign: ./send_g1fablab_presentation.sh"
echo "3. View message stats: ./show_message_stats.sh"
echo "4. View prospect stats: ./show_message_stats.sh" 