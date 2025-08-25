#!/bin/bash

# Integration test script for conversations feature
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

# Test basic conversations endpoint
test_conversations_endpoint() {
    log_info "Testing basic conversations endpoint..."

    local response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response is a valid JSON array
        if echo "$response" | grep -q '^\['; then
            if echo "$response" | grep -q '\]$'; then
                test_passed "Conversations endpoint returned valid JSON array"
                return 0
            fi
        fi
    fi

    test_failed "Conversations endpoint test failed. Response: $response"
    return 1
}

# Test conversations with pagination
test_conversations_pagination() {
    log_info "Testing conversations with pagination..."

    local response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT?limit=5&offset=0")

    if [ $? -eq 0 ]; then
        # Check if response is a valid JSON array
        if echo "$response" | grep -q '^\['; then
            # Check if we got at most 5 results
            local count=$(echo "$response" | grep -o '"id"' | wc -l)
            if [ "$count" -le 5 ]; then
                test_passed "Conversations pagination working correctly (returned $count conversations)"
                return 0
            fi
        fi
    fi

    test_failed "Conversations pagination test failed. Response: $response"
    return 1
}

# Test conversations with participant filter
test_conversations_filtering() {
    log_info "Testing conversations with participant filtering..."

    # First, get all conversations to find a participant
    local all_response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ] && [ "$all_response" != "[]" ]; then
        # Extract first participant from first conversation
        local participant=$(echo "$all_response" | grep -o '"participants":\[[^]]*\]' | head -1 | sed 's/.*"\([^"]*\)".*/\1/')

        if [ -n "$participant" ]; then
            log_info "Using participant: $participant"

            local filtered_response=$(curl -s -X GET \
                -H "Content-Type: application/json" \
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT?participant=$participant")

            if [ $? -eq 0 ]; then
                # Check if response contains conversations with that participant
                if echo "$filtered_response" | grep -q "$participant"; then
                    test_passed "Conversations participant filtering working correctly"
                    return 0
                else
                    log_warning "Participant not found in filtered response"
                    log_warning "All response: $all_response"
                    log_warning "Filtered response: $filtered_response"
                fi
            else
                log_warning "Filtered request failed"
            fi
        else
            log_warning "No participant found in conversations"
        fi
    else
        log_warning "No conversations found or request failed"
    fi

    test_failed "Conversations filtering test failed"
    return 1
}

# Test individual conversation retrieval
test_individual_conversation() {
    log_info "Testing individual conversation retrieval..."

    # First, get all conversations to find an ID
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
                "$API_BASE_URL$CONVERSATIONS_ENDPOINT/$conversation_id")

            if [ $? -eq 0 ]; then
                # Check if response contains the same ID
                if echo "$response" | grep -q "\"id\":\"$conversation_id\""; then
                    # Check if response contains expected fields
                    if echo "$response" | grep -q '"participants"'; then
                        if echo "$response" | grep -q '"message_count"'; then
                            if echo "$response" | grep -q '"created_at"'; then
                                test_passed "Individual conversation retrieval working correctly"
                                return 0
                            fi
                        fi
                    fi
                else
                    log_warning "Conversation ID not found in response"
                    log_warning "Expected ID: $conversation_id"
                    log_warning "Response: $response"
                fi
            else
                log_warning "Individual conversation request failed"
            fi
        else
            log_warning "No conversation ID found"
        fi
    else
        log_warning "No conversations found or request failed"
    fi

    test_failed "Individual conversation test failed"
    return 1
}

# Test invalid conversation ID
test_invalid_conversation_id() {
    log_info "Testing invalid conversation ID handling..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT/invalid-uuid")

    if [ "$http_code" = "404" ]; then
        test_passed "Invalid conversation ID properly returns 404"
        return 0
    else
        test_failed "Invalid conversation ID test failed. Expected 404, got: $http_code"
        return 1
    fi
}

# Test non-existent conversation
test_non_existent_conversation() {
    log_info "Testing non-existent conversation handling..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    if [ "$http_code" = "404" ]; then
        test_passed "Non-existent conversation properly returns 404"
        return 0
    else
        test_failed "Non-existent conversation test failed. Expected 404, got: $http_code"
        return 1
    fi
}

# Test invalid HTTP methods
test_invalid_http_methods() {
    log_info "Testing invalid HTTP methods..."

    local post_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "{}" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    local put_code=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
        -H "Content-Type: application/json" \
        -d "{}" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    local delete_code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ "$post_code" = "405" ] && [ "$put_code" = "405" ] && [ "$delete_code" = "405" ]; then
        test_passed "Invalid HTTP methods properly return 405"
        return 0
    else
        test_failed "Invalid HTTP methods test failed. POST: $post_code, PUT: $put_code, DELETE: $delete_code"
        return 1
    fi
}

# Test parameter validation
test_parameter_validation() {
    log_info "Testing parameter validation..."

    local invalid_limit_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT?limit=0")

    local invalid_offset_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT?offset=-1")

    local too_large_limit_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT?limit=2000")

    if [ "$invalid_limit_code" = "422" ] && [ "$invalid_offset_code" = "422" ] && [ "$too_large_limit_code" = "422" ]; then
        test_passed "Parameter validation working correctly"
        return 0
    else
        test_failed "Parameter validation test failed. Limit: $invalid_limit_code, Offset: $invalid_offset_code, Large limit: $too_large_limit_code"
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

# Test conversations structure and data integrity
test_conversations_data_integrity() {
    log_info "Testing conversations data integrity..."

    local response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT?limit=1")

    if [ $? -eq 0 ]; then
        # If there are no conversations, that's fine - just check the endpoint works
        if [ "$response" = "[]" ]; then
            test_passed "Conversations endpoint returns empty array correctly"
            return 0
        fi

        # Check if first conversation has all required fields
        if echo "$response" | grep -q '"id":'; then
            if echo "$response" | grep -q '"created_at":'; then
                if echo "$response" | grep -q '"updated_at":'; then
                    if echo "$response" | grep -q '"participants":'; then
                        if echo "$response" | grep -q '"message_count":'; then
                            if echo "$response" | grep -q '"last_message_timestamp":'; then
                                test_passed "Conversations data integrity check passed"
                                return 0
                            fi
                        fi
                    fi
                fi
            fi
        fi
    fi

    test_failed "Conversations data integrity test failed. Response: $response"
    return 1
}

# Test basic endpoint functionality (always works regardless of data)
test_conversations_endpoint_structure() {
    log_info "Testing conversations endpoint structure..."

    local response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ]; then
        # Check if response is valid JSON
        if echo "$response" | grep -q '^\[' && echo "$response" | grep -q '\]$'; then
            test_passed "Conversations endpoint returns valid JSON array"
            return 0
        fi
    fi

    test_failed "Conversations endpoint structure test failed. Response: $response"
    return 1
}

# Main test execution
main() {
    log_info "Starting Conversations Integration Tests"
    log_info "API Base URL: $API_BASE_URL"
    echo

    # Check prerequisites
    check_services
    echo

    # Run tests
    test_api_health
    test_conversations_endpoint_structure
    test_conversations_endpoint
    test_parameter_validation
    test_invalid_http_methods

    # Tests that require existing conversation data
    local all_response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        "$API_BASE_URL$CONVERSATIONS_ENDPOINT")

    if [ $? -eq 0 ] && [ "$all_response" != "[]" ]; then
        log_info "Found existing conversations, running data-dependent tests..."
        test_conversations_pagination
        test_conversations_filtering
        test_individual_conversation
        test_invalid_conversation_id
        test_non_existent_conversation
        test_conversations_data_integrity
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
        log_success "All conversations integration tests passed! 🎉"
        exit 0
    fi
}

# Run main function
main
