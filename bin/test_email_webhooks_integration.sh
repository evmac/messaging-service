#!/bin/bash

# Integration test script for Email webhook processing feature
# Tests the complete end-to-end flow: HTTP API → Service → Database → Response

set -e  # Exit on any error

# Configuration
API_BASE_URL="http://localhost:8000"
EMAIL_WEBHOOK_ENDPOINT="/api/webhooks/email"
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

# Test email webhook processing - unified format
test_email_webhook_unified() {
    log_info "Testing email webhook processing (unified format)..."

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local payload=$(cat <<EOF
{
    "from": "contact@gmail.com",
    "to": "user@usehatchapp.com",
    "xillio_id": "email-integration-test-1",
    "body": "<html><body>This is a test email with <b>HTML</b> content</body></html>",
    "attachments": ["https://example.com/test-document.pdf"],
    "timestamp": "$timestamp"
}
EOF
    )

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response contains expected fields
        if echo "$response" | grep -q '"provider_type":"email"'; then
            if echo "$response" | grep -q '"provider_message_id":"email-integration-test-1"'; then
                if echo "$response" | grep -q '"status":"delivered"'; then
                    if echo "$response" | grep -q '"direction":"inbound"'; then
                        if echo "$response" | grep -q '"from_address":"contact@gmail.com"'; then
                            if echo "$response" | grep -q '"to_address":"user@usehatchapp.com"'; then
                                test_passed "Email webhook (unified format) processed successfully"
                                return 0
                            fi
                        fi
                    fi
                fi
            fi
        fi
    fi

    test_failed "Email webhook (unified format) test failed. Response: $response"
    return 1
}

# Test email webhook processing - email provider format (SendGrid-like)
test_email_webhook_provider_format() {
    log_info "Testing email webhook processing (email provider format)..."

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local payload=$(cat <<EOF
{
    "from_email": "sender@company.com",
    "to_email": "recipient@client.com",
    "subject": "Test Subject from Integration Test",
    "content": "This is plain text content from email provider",
    "html_content": "<html><body><h1>Test HTML Content</h1><p>From email provider</p></body></html>",
    "x_message_id": "sg1234567890",
    "timestamp": "$timestamp"
}
EOF
    )

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response contains expected fields
        if echo "$response" | grep -q '"provider_type":"email"'; then
            if echo "$response" | grep -q '"provider_message_id":"sg1234567890"'; then
                if echo "$response" | grep -q '"status":"delivered"'; then
                    if echo "$response" | grep -q '"direction":"inbound"'; then
                        if echo "$response" | grep -q '"from_address":"sender@company.com"'; then
                            if echo "$response" | grep -q '"to_address":"recipient@client.com"'; then
                                # Check if subject is prepended to body
                                if echo "$response" | grep -q 'Subject: Test Subject from Integration Test'; then
                                    test_passed "Email webhook (provider format) processed successfully"
                                    return 0
                                fi
                            fi
                        fi
                    fi
                fi
            fi
        fi
    fi

    test_failed "Email webhook (provider format) test failed. Response: $response"
    return 1
}

# Test email webhook with only plain text (no HTML)
test_email_webhook_plain_text() {
    log_info "Testing email webhook processing (plain text only)..."

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local payload=$(cat <<EOF
{
    "from_email": "plaintext@example.com",
    "to_email": "recipient@example.com",
    "subject": "Plain Text Email",
    "content": "This is a plain text email message",
    "x_message_id": "plaintext123",
    "timestamp": "$timestamp"
}
EOF
    )

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response contains expected fields
        if echo "$response" | grep -q '"provider_type":"email"'; then
            if echo "$response" | grep -q '"provider_message_id":"plaintext123"'; then
                if echo "$response" | grep -q '"status":"delivered"'; then
                    if echo "$response" | grep -q '"direction":"inbound"'; then
                        # Check if subject is prepended to body
                        if echo "$response" | grep -q 'Subject: Plain Text Email'; then
                            if echo "$response" | grep -q 'This is a plain text email message'; then
                                test_passed "Email webhook (plain text) processed successfully"
                                return 0
                            fi
                        fi
                    fi
                fi
            fi
        fi
    fi

    test_failed "Email webhook (plain text) test failed. Response: $response"
    return 1
}

# Test email conversation creation and reuse
test_email_conversation_creation_and_reuse() {
    log_info "Testing email conversation creation and reuse..."

    local timestamp1=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local timestamp2=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # First email webhook message
    local payload1=$(cat <<EOF
{
    "from": "user1@example.com",
    "to": "user2@example.com",
    "xillio_id": "email-conv-test-1",
    "body": "First email in conversation",
    "attachments": [],
    "timestamp": "$timestamp1"
}
EOF
    )

    # Second email webhook message (reverse direction, same participants)
    local payload2=$(cat <<EOF
{
    "from": "user2@example.com",
    "to": "user1@example.com",
    "xillio_id": "email-conv-test-2",
    "body": "Reply email in same conversation",
    "attachments": [],
    "timestamp": "$timestamp2"
}
EOF
    )

    local response1=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload1" \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    local response2=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload2" \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    # Extract conversation IDs
    local conversation_id1=$(echo "$response1" | grep -o '"conversation_id":"[^"]*' | cut -d'"' -f4)
    local conversation_id2=$(echo "$response2" | grep -o '"conversation_id":"[^"]*' | cut -d'"' -f4)

    if [ "$conversation_id1" = "$conversation_id2" ] && [ -n "$conversation_id1" ]; then
        test_passed "Email conversation creation and reuse working correctly"
        return 0
    else
        test_failed "Email conversation creation/reuse failed. ID1: $conversation_id1, ID2: $conversation_id2"
        return 1
    fi
}

# Test invalid email data handling - missing from address
test_invalid_email_data_missing_from() {
    log_info "Testing invalid email data handling (missing from address)..."

    local payload=$(cat <<EOF
{
    "to": "user@usehatchapp.com",
    "xillio_id": "invalid-email-test-1",
    "body": "Missing from address",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    )

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    if [ "$http_code" = "400" ]; then
        test_passed "Invalid email data (missing from) properly rejected with 400"
        return 0
    else
        test_failed "Invalid email data test failed. Expected 400, got: $http_code"
        return 1
    fi
}

# Test invalid email format
test_invalid_email_format() {
    log_info "Testing invalid email format handling..."

    local payload=$(cat <<EOF
{
    "from": "invalid-email-format",
    "to": "user@usehatchapp.com",
    "xillio_id": "invalid-email-test-2",
    "body": "Invalid email format test",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    )

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    if [ "$http_code" = "400" ]; then
        test_passed "Invalid email format properly rejected with 400"
        return 0
    else
        test_failed "Invalid email format test failed. Expected 400, got: $http_code"
        return 1
    fi
}

# Test invalid email data format (neither format)
test_invalid_email_data_format() {
    log_info "Testing invalid email data handling (invalid format)..."

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
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    if [ "$http_code" = "400" ]; then
        test_passed "Invalid email format properly rejected with 400"
        return 0
    else
        test_failed "Invalid email format test failed. Expected 400, got: $http_code"
        return 1
    fi
}

# Test invalid email timestamp
test_invalid_email_timestamp() {
    log_info "Testing invalid email timestamp handling..."

    local payload=$(cat <<EOF
{
    "from": "sender@example.com",
    "to": "recipient@example.com",
    "xillio_id": "invalid-timestamp-test",
    "body": "Invalid timestamp test",
    "timestamp": "invalid-timestamp-format"
}
EOF
    )

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    if [ "$http_code" = "400" ]; then
        test_passed "Invalid email timestamp properly rejected with 400"
        return 0
    else
        test_failed "Invalid email timestamp test failed. Expected 400, got: $http_code"
        return 1
    fi
}

# Test email webhook message acceptance (database persistence test)
test_email_webhook_acceptance() {
    log_info "Testing email webhook message acceptance..."

    # Send a webhook message and verify it's accepted
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local test_payload=$(cat <<EOF
{
    "from": "acceptance@test.com",
    "to": "recipient@test.com",
    "xillio_id": "email-acceptance-test-1",
    "body": "Test email message for acceptance check",
    "attachments": [],
    "timestamp": "$timestamp"
}
EOF
    )

    # Send the webhook and capture both response and HTTP code
    local response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$test_payload" \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    # Extract HTTP code from the last line
    local http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)
    # Remove the HTTP_CODE line from response
    local json_response=$(echo "$response" | sed '/HTTP_CODE:/d')

    # Check if webhook was accepted (200 OK)
    if [ "$http_code" = "200" ]; then
        # Verify the response contains expected fields for a successful webhook
        if echo "$json_response" | grep -q '"provider_type":"email"'; then
            if echo "$json_response" | grep -q '"provider_message_id":"email-acceptance-test-1"'; then
                if echo "$json_response" | grep -q '"status":"delivered"'; then
                    if echo "$json_response" | grep -q '"direction":"inbound"'; then
                        test_passed "Email webhook message accepted and processed successfully"
                        return 0
                    fi
                fi
            fi
        fi
    fi

    test_failed "Email webhook acceptance test failed. HTTP Code: $http_code, Response: $json_response"
    return 1
}

# Test email webhook wrong HTTP method
test_email_wrong_http_method() {
    log_info "Testing email webhook wrong HTTP method..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    if [ "$http_code" = "405" ]; then
        test_passed "Email webhook wrong HTTP method properly returns 405"
        return 0
    else
        test_failed "Email webhook wrong HTTP method test failed. Expected 405, got: $http_code"
        return 1
    fi
}

# Test email webhook endpoint existence
test_email_webhook_endpoint_exists() {
    log_info "Testing email webhook endpoint existence..."

    # Test POST request with invalid data to check endpoint exists
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "{}" \
        "$API_BASE_URL$EMAIL_WEBHOOK_ENDPOINT")

    if [ "$http_code" = "400" ]; then
        test_passed "Email webhook endpoint exists and accepts POST requests"
        return 0
    else
        test_failed "Email webhook endpoint test failed. Expected 400, got: $http_code"
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
    log_info "Starting Email Webhooks Integration Tests"
    log_info "API Base URL: $API_BASE_URL"
    log_info "Email Webhook Endpoint: $EMAIL_WEBHOOK_ENDPOINT"
    echo

    # Check prerequisites
    check_services
    echo

    # Run tests
    test_api_health
    test_email_webhook_endpoint_exists
    test_email_webhook_unified
    test_email_webhook_provider_format
    test_email_webhook_plain_text
    test_email_conversation_creation_and_reuse
    test_email_webhook_acceptance
    test_invalid_email_data_missing_from
    test_invalid_email_format
    test_invalid_email_data_format
    test_invalid_email_timestamp
    test_email_wrong_http_method

    echo
    log_info "Test Results:"
    log_info "Total tests run: $TESTS_RUN"
    log_success "Tests passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Tests failed: $TESTS_FAILED"
        exit 1
    else
        log_success "All email webhook integration tests passed! 🎉"
        exit 0
    fi
}

# Run main function
main
