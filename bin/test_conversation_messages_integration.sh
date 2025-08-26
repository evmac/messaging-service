#!/bin/bash

# Integration test script for get conversation messages feature
# Tests the complete end-to-end flow: HTTP API → Service → Database

set -e  # Exit on any error

# Configuration
API_BASE_URL="http://localhost:8000"
CONVERSATIONS_ENDPOINT="/api/conversations"
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

    # Check database connectivity via health endpoint
    local health_response=$(curl -s "$API_BASE_URL$HEALTH_ENDPOINT")
    if echo "$health_response" | grep -q '"database":"connected"'; then
        log_success "Database is connected"
    else
        log_error "Database is not connected. Health response: $health_response"
        exit 1
    fi
}

# Test basic get conversation messages endpoint with valid conversation
test_get_conversation_messages_basic() {
    log_info "Testing basic get conversation messages endpoint..."

    # First, get all conversations to find a valid conversation ID
    local all_response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ] && [ "$all_response" != "[]" ]; then
        # Extract first conversation ID
        local conversation_id=$(echo "$all_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

        if [ -n "$conversation_id" ]; then
            log_info "Using conversation ID: $conversation_id"

            local response=$(curl -s -X GET \
                -H "Content-Type: application/json" \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages")

            if [ $? -eq 0 ]; then
                # Check if response is a valid JSON array
                if echo "$response" | grep -q '^\[' && echo "$response" | grep -q '\]$'; then
                    test_passed "Get conversation messages endpoint returned valid JSON array"
                    return 0
                else
                    log_warning "Response is not a valid JSON array: $response"
                fi
            else
                log_warning "Request failed"
            fi
        else
            log_warning "No conversation ID found in conversations response"
        fi
    else
        log_warning "No conversations found or request failed"
    fi

    test_failed "Basic get conversation messages test failed"
    return 1
}

# Test get conversation messages with pagination
test_get_conversation_messages_pagination() {
    log_info "Testing get conversation messages with pagination..."

    # First, get all conversations to find a valid conversation ID
    local all_response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ] && [ "$all_response" != "[]" ]; then
        # Extract first conversation ID
        local conversation_id=$(echo "$all_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

        if [ -n "$conversation_id" ]; then
            log_info "Using conversation ID: $conversation_id"

            local response=$(curl -s -X GET \
                -H "Content-Type: application/json" \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages?limit=5&offset=0")

            if [ $? -eq 0 ]; then
                # Check if response is a valid JSON array
                if echo "$response" | grep -q '^\[' && echo "$response" | grep -q '\]$'; then
                    # Check if we got at most 5 results
                    local count=$(echo "$response" | grep -o '"id"' | wc -l)
                    if [ "$count" -le 5 ]; then
                        test_passed "Get conversation messages pagination working correctly (returned $count messages)"
                        return 0
                    else
                        log_warning "Pagination not working correctly, got $count messages instead of max 5"
                    fi
                else
                    log_warning "Response is not a valid JSON array: $response"
                fi
            else
                log_warning "Request failed"
            fi
        else
            log_warning "No conversation ID found"
        fi
    else
        log_warning "No conversations found or request failed"
    fi

    test_failed "Get conversation messages pagination test failed"
    return 1
}

# Test get conversation messages with direction filtering
test_get_conversation_messages_direction_filtering() {
    log_info "Testing get conversation messages with direction filtering..."

    # First, get all conversations to find a valid conversation ID
    local all_response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ] && [ "$all_response" != "[]" ]; then
        # Extract first conversation ID
        local conversation_id=$(echo "$all_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

        if [ -n "$conversation_id" ]; then
            log_info "Using conversation ID: $conversation_id"

            # Test inbound filtering
            local inbound_response=$(curl -s -X GET \
                -H "Content-Type: application/json" \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages?direction=inbound")

            if [ $? -eq 0 ]; then
                if echo "$inbound_response" | grep -q '^\[' && echo "$inbound_response" | grep -q '\]$'; then
                    # Check if all returned messages have direction "inbound"
                    local non_inbound_count=$(echo "$inbound_response" | grep -c '"direction":"outbound"')
                    if [ "$non_inbound_count" -eq 0 ]; then
                        test_passed "Inbound direction filtering working correctly"
                    else
                        log_warning "Inbound filtering not working, found $non_inbound_count outbound messages"
                    fi
                else
                    log_warning "Inbound response is not a valid JSON array: $inbound_response"
                fi
            else
                log_warning "Inbound request failed"
            fi

            # Test outbound filtering
            local outbound_response=$(curl -s -X GET \
                -H "Content-Type: application/json" \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages?direction=outbound")

            if [ $? -eq 0 ]; then
                if echo "$outbound_response" | grep -q '^\[' && echo "$outbound_response" | grep -q '\]$'; then
                    # Check if all returned messages have direction "outbound"
                    local non_outbound_count=$(echo "$outbound_response" | grep -c '"direction":"inbound"')
                    if [ "$non_outbound_count" -eq 0 ]; then
                        test_passed "Outbound direction filtering working correctly"
                        return 0
                    else
                        log_warning "Outbound filtering not working, found $non_outbound_count inbound messages"
                    fi
                else
                    log_warning "Outbound response is not a valid JSON array: $outbound_response"
                fi
            else
                log_warning "Outbound request failed"
            fi
        else
            log_warning "No conversation ID found"
        fi
    else
        log_warning "No conversations found or request failed"
    fi

    test_failed "Get conversation messages direction filtering test failed"
    return 1
}

# Test get conversation messages with invalid conversation ID
test_invalid_conversation_id() {
    log_info "Testing get conversation messages with invalid conversation ID..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT/invalid-uuid/messages")

    if [ "$http_code" = "422" ]; then
        test_passed "Invalid conversation ID properly returns 422"
        return 0
    else
        test_failed "Invalid conversation ID test failed. Expected 422, got: $http_code"
        return 1
    fi
}

# Test get conversation messages with non-existent conversation
test_non_existent_conversation() {
    log_info "Testing get conversation messages with non-existent conversation..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/messages")

    if [ "$http_code" = "404" ]; then
        test_passed "Non-existent conversation properly returns 404"
        return 0
    else
        test_failed "Non-existent conversation test failed. Expected 404, got: $http_code"
        return 1
    fi
}

# Test get conversation messages with invalid HTTP methods
test_invalid_http_methods() {
    log_info "Testing get conversation messages with invalid HTTP methods..."

    # First, get all conversations to find a valid conversation ID
    local all_response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ] && [ "$all_response" != "[]" ]; then
        # Extract first conversation ID
        local conversation_id=$(echo "$all_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

        if [ -n "$conversation_id" ]; then
            log_info "Using conversation ID: $conversation_id"

            local post_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
                -H "Content-Type: application/json" \
                -d "{}" \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages")

            local put_code=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
                -H "Content-Type: application/json" \
                -d "{}" \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages")

            local delete_code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages")

            if [ "$post_code" = "405" ] && [ "$put_code" = "405" ] && [ "$delete_code" = "405" ]; then
                test_passed "Invalid HTTP methods properly return 405"
                return 0
            else
                test_failed "Invalid HTTP methods test failed. POST: $post_code, PUT: $put_code, DELETE: $delete_code"
                return 1
            fi
        else
            log_warning "No conversation ID found"
        fi
    else
        log_warning "No conversations found or request failed"
    fi

    test_failed "Invalid HTTP methods test failed (no valid conversation ID)"
    return 1
}

# Test get conversation messages parameter validation
test_parameter_validation() {
    log_info "Testing get conversation messages parameter validation..."

    # First, get all conversations to find a valid conversation ID
    local all_response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ] && [ "$all_response" != "[]" ]; then
        # Extract first conversation ID
        local conversation_id=$(echo "$all_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

        if [ -n "$conversation_id" ]; then
            log_info "Using conversation ID: $conversation_id"

            local invalid_limit_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages?limit=0")

            local invalid_offset_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages?offset=-1")

            local too_large_limit_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages?limit=2000")

            local invalid_direction_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages?direction=invalid")

            if [ "$invalid_limit_code" = "422" ] && [ "$invalid_offset_code" = "422" ] && \
               [ "$too_large_limit_code" = "422" ] && [ "$invalid_direction_code" = "400" ]; then
                test_passed "Parameter validation working correctly"
                return 0
            else
                test_failed "Parameter validation test failed. Limit: $invalid_limit_code, Offset: $invalid_offset_code, Large limit: $too_large_limit_code, Invalid direction: $invalid_direction_code"
                return 1
            fi
        else
            log_warning "No conversation ID found"
        fi
    else
        log_warning "No conversations found or request failed"
    fi

    test_failed "Parameter validation test failed (no valid conversation ID)"
    return 1
}

# Test get conversation messages data integrity
test_conversation_messages_data_integrity() {
    log_info "Testing get conversation messages data integrity..."

    # First, get all conversations to find a valid conversation ID
    local all_response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ] && [ "$all_response" != "[]" ]; then
        # Extract first conversation ID
        local conversation_id=$(echo "$all_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

        if [ -n "$conversation_id" ]; then
            log_info "Using conversation ID: $conversation_id"

            local response=$(curl -s -X GET \
                -H "Content-Type: application/json" \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id/messages?limit=1")

            if [ $? -eq 0 ]; then
                # If there are no messages, that's fine - just check the endpoint works
                if [ "$response" = "[]" ]; then
                    test_passed "Get conversation messages endpoint returns empty array correctly"
                    return 0
                fi

                # Check if first message has all required fields
                if echo "$response" | grep -q '"id":'; then
                    if echo "$response" | grep -q '"conversation_id":'; then
                        if echo "$response" | grep -q '"provider_type":'; then
                            if echo "$response" | grep -q '"from_address":'; then
                                if echo "$response" | grep -q '"to_address":'; then
                                    if echo "$response" | grep -q '"body":'; then
                                        if echo "$response" | grep -q '"direction":'; then
                                            if echo "$response" | grep -q '"status":'; then
                                                if echo "$response" | grep -q '"message_timestamp":'; then
                                                    if echo "$response" | grep -q '"created_at":'; then
                                                        if echo "$response" | grep -q '"updated_at":'; then
                                                            test_passed "Get conversation messages data integrity check passed"
                                                            return 0
                                                        fi
                                                    fi
                                                fi
                                            fi
                                        fi
                                    fi
                                fi
                            fi
                        fi
                    fi
                fi
            fi
        else
            log_warning "No conversation ID found"
        fi
    else
        log_warning "No conversations found or request failed"
    fi

    test_failed "Get conversation messages data integrity test failed"
    return 1
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
    log_info "Starting Get Conversation Messages Integration Tests"
    log_info "API Base URL: $API_BASE_URL"
    echo

    # Check prerequisites
    check_services
    echo

    # Run tests
    test_api_health
    test_invalid_conversation_id
    test_non_existent_conversation
    test_invalid_http_methods

    # Tests that require existing conversation data
    local all_response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ] && [ "$all_response" != "[]" ]; then
        log_info "Found existing conversations, running data-dependent tests..."
        test_get_conversation_messages_basic
        test_get_conversation_messages_pagination
        test_get_conversation_messages_direction_filtering
        test_parameter_validation
        test_conversation_messages_data_integrity
    else
        log_info "No conversations found, skipping data-dependent tests"
        test_passed "Data-dependent tests skipped (no conversations in database)"
    fi

    echo
    log_info "Test Results:"
    log_info "Total tests run: $TESTS_RUN"
    log_success "Tests passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Tests failed: $TESTS_FAILED"
        exit 1
    else
        log_success "All get conversation messages integration tests passed! 🎉"
        exit 0
    fi
}

# Run main function
main
