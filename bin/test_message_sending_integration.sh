#!/bin/bash

# Integration test script for message sending feature
# Tests the complete end-to-end flow: HTTP API → Service → Database → Providers

set -e  # Exit on any error

# Configuration
API_BASE_URL="http://localhost:8000"
SMS_ENDPOINT="/api/messages/sms"
EMAIL_ENDPOINT="/api/messages/email"
HEALTH_ENDPOINT="/health"

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

    # Check SMS provider
    if curl -s "http://localhost:8001/health" > /dev/null 2>&1; then
        log_success "SMS provider is running"
    else
        log_error "SMS provider is not running at localhost:8001"
        exit 1
    fi

    # Check Email provider
    if curl -s "http://localhost:8002/health" > /dev/null 2>&1; then
        log_success "Email provider is running"
    else
        log_error "Email provider is not running at localhost:8002"
        exit 1
    fi
}

# Test SMS message sending
test_sms_message() {
    log_info "Testing SMS message sending..."

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local payload=$(cat <<EOF
{
    "from_address": "+1234567890",
    "to_address": "+0987654321",
    "body": "Test SMS message from integration test",
    "attachments": [],
    "timestamp": "$timestamp"
}
EOF
    )

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$SMS_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response contains expected fields
        if echo "$response" | grep -q '"provider_type":"sms"'; then
            if echo "$response" | grep -q '"provider_message_id"'; then
                if echo "$response" | grep -q '"status":"delivered"'; then
                    test_passed "SMS message sent successfully"
                    return 0
                fi
            fi
        fi
    fi

    test_failed "SMS message test failed. Response: $response"
    return 1
}

# Test MMS message sending (with attachments)
test_mms_message() {
    log_info "Testing MMS message sending..."

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local payload=$(cat <<EOF
{
    "from_address": "+1234567890",
    "to_address": "+0987654321",
    "body": "Test MMS message with image",
    "attachments": ["image.jpg", "document.pdf"],
    "timestamp": "$timestamp"
}
EOF
    )

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$SMS_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response contains expected fields for MMS
        if echo "$response" | grep -q '"provider_type":"mms"'; then
            if echo "$response" | grep -q '"provider_message_id"'; then
                if echo "$response" | grep -q '"status":"delivered"'; then
                    if echo "$response" | grep -q '"attachments":\["image.jpg","document.pdf"\]'; then
                        test_passed "MMS message sent successfully"
                        return 0
                    fi
                fi
            fi
        fi
    fi

    test_failed "MMS message test failed. Response: $response"
    return 1
}

# Test email message sending
test_email_message() {
    log_info "Testing email message sending..."

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local payload=$(cat <<EOF
{
    "from_address": "sender@example.com",
    "to_address": "recipient@example.com",
    "body": "Test email message from integration test",
    "attachments": ["document.pdf"],
    "timestamp": "$timestamp"
}
EOF
    )

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$EMAIL_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response contains expected fields
        if echo "$response" | grep -q '"provider_type":"email"'; then
            if echo "$response" | grep -q '"provider_message_id"'; then
                if echo "$response" | grep -q '"status":"delivered"'; then
                    test_passed "Email message sent successfully"
                    return 0
                fi
            fi
        fi
    fi

    test_failed "Email message test failed. Response: $response"
    return 1
}

# Test conversation reuse
test_conversation_reuse() {
    log_info "Testing conversation reuse..."

    local timestamp1=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local timestamp2=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # First message
    local payload1=$(cat <<EOF
{
    "from_address": "alice@example.com",
    "to_address": "bob@example.com",
    "body": "Hello Bob!",
    "attachments": [],
    "timestamp": "$timestamp1"
}
EOF
    )

    # Second message (reverse direction)
    local payload2=$(cat <<EOF
{
    "from_address": "bob@example.com",
    "to_address": "alice@example.com",
    "body": "Hello Alice!",
    "attachments": [],
    "timestamp": "$timestamp2"
}
EOF
    )

    local response1=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload1" \
        "$API_BASE_URL$EMAIL_ENDPOINT")

    local response2=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload2" \
        "$API_BASE_URL$EMAIL_ENDPOINT")

    # Extract conversation IDs
    local conversation_id1=$(echo "$response1" | grep -o '"conversation_id":"[^"]*' | cut -d'"' -f4)
    local conversation_id2=$(echo "$response2" | grep -o '"conversation_id":"[^"]*' | cut -d'"' -f4)

    if [ "$conversation_id1" = "$conversation_id2" ] && [ -n "$conversation_id1" ]; then
        test_passed "Conversation reuse working correctly"
        return 0
    else
        test_failed "Conversation reuse failed. ID1: $conversation_id1, ID2: $conversation_id2"
        return 1
    fi
}

# Test invalid data handling
test_invalid_data() {
    log_info "Testing invalid data handling..."

    local payload=$(cat <<EOF
{
    "to_address": "recipient@example.com",
    "body": "Missing from_address"
}
EOF
    )

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$EMAIL_ENDPOINT")

    if [ "$http_code" = "422" ]; then
        test_passed "Invalid data properly rejected with 422"
        return 0
    else
        test_failed "Invalid data test failed. Expected 422, got: $http_code"
        return 1
    fi
}

# Test non-existent endpoint
test_non_existent_endpoint() {
    log_info "Testing non-existent endpoint..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "{}" \
        "$API_BASE_URL/api/messages/nonexistent")

    if [ "$http_code" = "404" ]; then
        test_passed "Non-existent endpoint properly returns 404"
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

# Main test execution
main() {
    log_info "Starting Message Sending Integration Tests"
    log_info "API Base URL: $API_BASE_URL"
    echo

    # Check prerequisites
    check_services
    echo

    # Run tests
    test_api_health
    test_sms_message
    test_mms_message
    test_email_message
    test_conversation_reuse
    test_invalid_data
    test_non_existent_endpoint

    echo
    log_info "Test Results:"
    log_info "Total tests run: $TESTS_RUN"
    log_success "Tests passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Tests failed: $TESTS_FAILED"
        exit 1
    else
        log_success "All integration tests passed! 🎉"
        exit 0
    fi
}

# Run main function
main
