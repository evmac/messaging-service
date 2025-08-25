#!/bin/bash

# Integration test script for SMS/MMS webhook processing feature
# Tests the complete end-to-end flow: HTTP API → Service → Database → Response

set -e  # Exit on any error

# Configuration
API_BASE_URL="http://localhost:8000"
WEBHOOK_ENDPOINT="/api/webhooks/sms"
HEALTH_ENDPOINT="/health"
CONVERSATIONS_ENDPOINT="/api/conversations"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

test_passed() {
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_PASSED=$((TESTS_PASSED + 1))
    log_success "$1"
}

test_failed() {
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_FAILED=$((TESTS_FAILED + 1))
    log_error "$1"
}

# Check if services are running
check_services() {
    log_info "Checking if services are running..."

    # Check API health
    if curl -s "$API_BASE_URL$HEALTH_ENDPOINT" > /dev/null 2>&1; then
        log_success "API service is running"
    else
        log_error "API service is not running at $API_BASE_URL"
        exit 1
    fi

    # Check database connectivity via health endpoint
    local health_response=$(curl -s "$API_BASE_URL$HEALTH_ENDPOINT")
    if echo "$health_response" | grep -q '"database":"connected"'; then
        log_success "Database is connected"
    else
        log_error "Database is not connected"
        exit 1
    fi
}

# Test SMS webhook processing - unified format
test_sms_webhook_unified() {
    log_info "Testing SMS webhook processing (unified format)..."

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local payload=$(cat <<EOF
{
    "from": "+18045551234",
    "to": "+12016661234",
    "type": "sms",
    "messaging_provider_id": "sms-integration-test-1",
    "body": "This is a test SMS message from integration test",
    "attachments": [],
    "timestamp": "$timestamp"
}
EOF
    )

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response contains expected fields
        if echo "$response" | grep -q '"provider_type":"sms"'; then
            if echo "$response" | grep -q '"provider_message_id":"sms-integration-test-1"'; then
                if echo "$response" | grep -q '"status":"delivered"'; then
                    if echo "$response" | grep -q '"direction":"inbound"'; then
                        test_passed "SMS webhook (unified format) processed successfully"
                        return 0
                    fi
                fi
            fi
        fi
    fi

    test_failed "SMS webhook (unified format) test failed. Response: $response"
    return 1
}

# Test MMS webhook processing - unified format
test_mms_webhook_unified() {
    log_info "Testing MMS webhook processing (unified format)..."

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local payload=$(cat <<EOF
{
    "from": "+18045551234",
    "to": "+12016661234",
    "type": "mms",
    "messaging_provider_id": "mms-integration-test-1",
    "body": "This is a test MMS message with image",
    "attachments": ["https://example.com/test-image.jpg"],
    "timestamp": "$timestamp"
}
EOF
    )

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response contains expected fields
        if echo "$response" | grep -q '"provider_type":"mms"'; then
            if echo "$response" | grep -q '"provider_message_id":"mms-integration-test-1"'; then
                if echo "$response" | grep -q '"status":"delivered"'; then
                    if echo "$response" | grep -q '"direction":"inbound"'; then
                        if echo "$response" | grep -q '"attachments":\["https://example.com/test-image.jpg"\]'; then
                            test_passed "MMS webhook (unified format) processed successfully"
                            return 0
                        fi
                    fi
                fi
            fi
        fi
    fi

    test_failed "MMS webhook (unified format) test failed. Response: $response"
    return 1
}

# Test SMS provider format (Twilio-like)
test_sms_webhook_provider_format() {
    log_info "Testing SMS webhook processing (SMS provider format)..."

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local payload=$(cat <<EOF
{
    "From": "+15551234567",
    "To": "+15559876543",
    "Body": "Test SMS from provider format",
    "MessageSid": "SM1234567890",
    "MediaUrl": [],
    "Timestamp": "$timestamp"
}
EOF
    )

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response contains expected fields
        if echo "$response" | grep -q '"provider_type":"sms"'; then
            if echo "$response" | grep -q '"provider_message_id":"SM1234567890"'; then
                if echo "$response" | grep -q '"status":"delivered"'; then
                    if echo "$response" | grep -q '"direction":"inbound"'; then
                        test_passed "SMS webhook (provider format) processed successfully"
                        return 0
                    fi
                fi
            fi
        fi
    fi

    test_failed "SMS webhook (provider format) test failed. Response: $response"
    return 1
}

# Test MMS provider format (Twilio-like)
test_mms_webhook_provider_format() {
    log_info "Testing MMS webhook processing (SMS provider format)..."

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local payload=$(cat <<EOF
{
    "From": "+15551234567",
    "To": "+15559876543",
    "Body": "Test MMS from provider format",
    "MessageSid": "MM1234567890",
    "MediaUrl": ["https://api.twilio.com/2010-04-01/Accounts/AC123/Messages/MM123/Media/ME123"],
    "Timestamp": "$timestamp"
}
EOF
    )

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response contains expected fields
        if echo "$response" | grep -q '"provider_type":"mms"'; then
            if echo "$response" | grep -q '"provider_message_id":"MM1234567890"'; then
                if echo "$response" | grep -q '"status":"delivered"'; then
                    if echo "$response" | grep -q '"direction":"inbound"'; then
                        test_passed "MMS webhook (provider format) processed successfully"
                        return 0
                    fi
                fi
            fi
        fi
    fi

    test_failed "MMS webhook (provider format) test failed. Response: $response"
    return 1
}

# Test conversation creation and reuse
test_conversation_creation_and_reuse() {
    log_info "Testing conversation creation and reuse..."

    local timestamp1=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local timestamp2=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # First webhook message
    local payload1=$(cat <<EOF
{
    "from": "+18045551111",
    "to": "+12016662222",
    "type": "sms",
    "messaging_provider_id": "conv-test-1",
    "body": "First message in conversation",
    "attachments": [],
    "timestamp": "$timestamp1"
}
EOF
    )

    # Second webhook message (reverse direction, same participants)
    local payload2=$(cat <<EOF
{
    "from": "+12016662222",
    "to": "+18045551111",
    "type": "sms",
    "messaging_provider_id": "conv-test-2",
    "body": "Reply in same conversation",
    "attachments": [],
    "timestamp": "$timestamp2"
}
EOF
    )

    local response1=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload1" \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    local response2=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload2" \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    # Extract conversation IDs
    local conversation_id1=$(echo "$response1" | grep -o '"conversation_id":"[^"]*' | cut -d'"' -f4)
    local conversation_id2=$(echo "$response2" | grep -o '"conversation_id":"[^"]*' | cut -d'"' -f4)

    if [ "$conversation_id1" = "$conversation_id2" ] && [ -n "$conversation_id1" ]; then
        test_passed "Conversation creation and reuse working correctly"
        return 0
    else
        test_failed "Conversation creation/reuse failed. ID1: $conversation_id1, ID2: $conversation_id2"
        return 1
    fi
}

# Test invalid data handling - missing from address
test_invalid_data_missing_from() {
    log_info "Testing invalid data handling (missing from address)..."

    local payload=$(cat <<EOF
{
    "to": "+12016661234",
    "type": "sms",
    "messaging_provider_id": "invalid-test-1",
    "body": "Missing from address",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    )

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    if [ "$http_code" = "400" ]; then
        test_passed "Invalid data (missing from) properly rejected with 400"
        return 0
    else
        test_failed "Invalid data test failed. Expected 400, got: $http_code"
        return 1
    fi
}

# Test invalid data handling - invalid format
test_invalid_data_format() {
    log_info "Testing invalid data handling (invalid format)..."

    local payload=$(cat <<EOF
{
    "some_field": "some_value",
    "another_field": "another_value"
}
EOF
    )

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    if [ "$http_code" = "400" ]; then
        test_passed "Invalid format properly rejected with 400"
        return 0
    else
        test_failed "Invalid format test failed. Expected 400, got: $http_code"
        return 1
    fi
}

# Test invalid timestamp
test_invalid_timestamp() {
    log_info "Testing invalid timestamp handling..."

    local payload=$(cat <<EOF
{
    "from": "+18045551234",
    "to": "+12016661234",
    "type": "sms",
    "messaging_provider_id": "invalid-timestamp-test",
    "body": "Invalid timestamp test",
    "timestamp": "invalid-timestamp-format"
}
EOF
    )

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    if [ "$http_code" = "400" ]; then
        test_passed "Invalid timestamp properly rejected with 400"
        return 0
    else
        test_failed "Invalid timestamp test failed. Expected 400, got: $http_code"
        return 1
    fi
}

# Test non-existent endpoint
test_non_existent_endpoint() {
    log_info "Testing non-existent webhook endpoint..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "{}" \
        "$API_BASE_URL/api/webhooks/nonexistent")

    if [ "$http_code" = "404" ]; then
        test_passed "Non-existent webhook endpoint properly returns 404"
        return 0
    else
        test_failed "Non-existent endpoint test failed. Expected 404, got: $http_code"
        return 1
    fi
}

# Test API health endpoint
test_api_health() {
    log_info "Testing API health endpoint..."

    local response=$(curl -s "$API_BASE_URL$HEALTH_ENDPOINT")

    if echo "$response" | grep -q '"status":"healthy"'; then
        if echo "$response" | grep -q '"database":"connected"'; then
            test_passed "API health check passed"
            return 0
        fi
    fi

    test_failed "API health check failed. Response: $response"
    return 1
}

# Test webhook message acceptance (database persistence test)
# Note: Full persistence verification requires the conversations endpoint (Feature 5)
test_webhook_acceptance() {
    log_info "Testing webhook message acceptance..."

    # Send a webhook message and verify it's accepted
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local test_payload=$(cat <<EOF
{
    "from": "+18045559999",
    "to": "+12016668888",
    "type": "sms",
    "messaging_provider_id": "acceptance-test-1",
    "body": "Test message for acceptance check",
    "attachments": [],
    "timestamp": "$timestamp"
}
EOF
    )

    # Send the webhook and capture both response and HTTP code
    local response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$test_payload" \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    # Extract HTTP code from the last line
    local http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)
    # Remove the HTTP_CODE line from response
    local json_response=$(echo "$response" | sed '/HTTP_CODE:/d')

    # Check if webhook was accepted (200 OK)
    if [ "$http_code" = "200" ]; then
        # Verify the response contains expected fields for a successful webhook
        if echo "$json_response" | grep -q '"provider_type":"sms"'; then
            if echo "$json_response" | grep -q '"provider_message_id":"acceptance-test-1"'; then
                if echo "$json_response" | grep -q '"status":"delivered"'; then
                    if echo "$json_response" | grep -q '"direction":"inbound"'; then
                        test_passed "Webhook message accepted and processed successfully"
                        return 0
                    fi
                fi
            fi
        fi
    fi

    test_failed "Webhook acceptance test failed. HTTP Code: $http_code, Response: $json_response"
    return 1
}

# Test wrong HTTP method
test_wrong_http_method() {
    log_info "Testing wrong HTTP method..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
        "$API_BASE_URL$WEBHOOK_ENDPOINT")

    if [ "$http_code" = "405" ]; then
        test_passed "Wrong HTTP method properly returns 405"
        return 0
    else
        test_failed "Wrong HTTP method test failed. Expected 405, got: $http_code"
        return 1
    fi
}

# Main test execution
main() {
    log_info "Starting SMS/MMS Webhooks Integration Tests"
    log_info "API Base URL: $API_BASE_URL"
    echo

    # Check prerequisites
    check_services
    echo

    # Run tests
    test_api_health
    test_sms_webhook_unified
    test_mms_webhook_unified
    test_sms_webhook_provider_format
    test_mms_webhook_provider_format
    test_conversation_creation_and_reuse
    test_webhook_acceptance
    test_invalid_data_missing_from
    test_invalid_data_format
    test_invalid_timestamp
    test_non_existent_endpoint
    test_wrong_http_method

    echo
    log_info "Test Results:"
    log_info "Total tests run: $TESTS_RUN"
    log_success "Tests passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Tests failed: $TESTS_FAILED"
        exit 1
    else
        log_success "All webhook integration tests passed! 🎉"
        exit 0
    fi
}

# Run main function
main
