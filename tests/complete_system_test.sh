#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ORIZON ZERO TRUST - COMPLETE SYSTEM TEST                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
TOTAL=0

function test_pass() {
    ((PASS++))
    ((TOTAL++))
    echo -e "${GREEN}✓${NC} $1"
}

function test_fail() {
    ((FAIL++))
    ((TOTAL++))
    echo -e "${RED}✗${NC} $1"
}

function test_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Section 1: Backend Health
test_section "1. BACKEND HEALTH CHECK"

HEALTH=$(curl -s http://139.59.149.48/health 2>/dev/null)
if echo "$HEALTH" | grep -q "healthy"; then
    test_pass "Backend /health endpoint: OK"
else
    test_fail "Backend /health endpoint: FAILED"
fi

# Section 2: Authentication
test_section "2. AUTHENTICATION TESTS"

# Test login
LOGIN_RESPONSE=$(curl -s -X POST http://139.59.149.48/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"marco@syneto.eu","password":"profano.69"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
    test_pass "POST /auth/login: Token received"
else
    test_fail "POST /auth/login: FAILED"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

# Test /auth/me
ME_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://139.59.149.48/api/v1/auth/me)
USER_EMAIL=$(echo "$ME_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('email',''))" 2>/dev/null)

if [ "$USER_EMAIL" = "marco@syneto.eu" ]; then
    test_pass "GET /auth/me: Returns correct user"
else
    test_fail "GET /auth/me: FAILED"
fi

# Test invalid credentials
INVALID_LOGIN=$(curl -s -X POST http://139.59.149.48/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"wrong@test.com","password":"wrongpass"}')

if echo "$INVALID_LOGIN" | grep -q "detail"; then
    test_pass "POST /auth/login with invalid credentials: Rejected correctly"
else
    test_fail "POST /auth/login with invalid credentials: Not rejected"
fi

# Section 3: Groups Management
test_section "3. GROUPS MANAGEMENT"

GROUPS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://139.59.149.48/api/v1/groups)
GROUPS_COUNT=$(echo "$GROUPS_RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('groups',[])))" 2>/dev/null)

if [ -n "$GROUPS_COUNT" ] && [ "$GROUPS_COUNT" -gt 0 ]; then
    test_pass "GET /groups: Found $GROUPS_COUNT groups"
else
    test_fail "GET /groups: No groups or error"
fi

# Check response structure
HAS_GROUPS=$(echo "$GROUPS_RESPONSE" | python3 -c "import sys,json; print('groups' in json.load(sys.stdin))" 2>/dev/null)
HAS_TOTAL=$(echo "$GROUPS_RESPONSE" | python3 -c "import sys,json; print('total' in json.load(sys.stdin))" 2>/dev/null)

if [ "$HAS_GROUPS" = "True" ] && [ "$HAS_TOTAL" = "True" ]; then
    test_pass "GET /groups: Response structure correct (has 'groups' and 'total')"
else
    test_fail "GET /groups: Response structure incorrect"
fi

# Section 4: Nodes Management
test_section "4. NODES MANAGEMENT"

NODES_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://139.59.149.48/api/v1/nodes)
NODES_COUNT=$(echo "$NODES_RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('nodes',[])))" 2>/dev/null)

if [ -n "$NODES_COUNT" ] && [ "$NODES_COUNT" -ge 0 ]; then
    test_pass "GET /nodes: Found $NODES_COUNT nodes"
else
    test_fail "GET /nodes: Error"
fi

# Check response structure
HAS_NODES=$(echo "$NODES_RESPONSE" | python3 -c "import sys,json; print('nodes' in json.load(sys.stdin))" 2>/dev/null)
HAS_TOTAL_NODES=$(echo "$NODES_RESPONSE" | python3 -c "import sys,json; print('total' in json.load(sys.stdin))" 2>/dev/null)

if [ "$HAS_NODES" = "True" ] && [ "$HAS_TOTAL_NODES" = "True" ]; then
    test_pass "GET /nodes: Response structure correct (has 'nodes' and 'total')"
else
    test_fail "GET /nodes: Response structure incorrect"
fi

# Section 5: Frontend Tests
test_section "5. FRONTEND TESTS"

# Login page
LOGIN_PAGE=$(curl -s http://139.59.149.48/auth/login.html)

if echo "$LOGIN_PAGE" | grep -q "api/v1/auth/login"; then
    test_pass "Login page: Uses correct endpoint (/api/v1/auth/login)"
else
    test_fail "Login page: Wrong endpoint"
fi

if echo "$LOGIN_PAGE" | grep -q "window.location.href = '/dashboard/'"; then
    test_pass "Login page: Redirects to /dashboard/ after login"
else
    test_fail "Login page: Does not redirect to /dashboard/"
fi

# Dashboard page
DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://139.59.149.48/dashboard/)

if [ "$DASHBOARD_STATUS" = "200" ]; then
    test_pass "Dashboard page: Loads successfully (HTTP 200)"
else
    test_fail "Dashboard page: Failed to load (HTTP $DASHBOARD_STATUS)"
fi

DASHBOARD_PAGE=$(curl -s http://139.59.149.48/dashboard/)

if echo "$DASHBOARD_PAGE" | grep -q "localStorage.getItem.*orizon_token"; then
    test_pass "Dashboard: Reads token from localStorage"
else
    test_fail "Dashboard: Does not read token from localStorage"
fi

if echo "$DASHBOARD_PAGE" | grep -q "apiCall('/auth/me')"; then
    test_pass "Dashboard: Calls /auth/me"
else
    test_fail "Dashboard: Does not call /auth/me"
fi

if echo "$DASHBOARD_PAGE" | grep -q "apiCall('/groups')"; then
    test_pass "Dashboard: Calls /groups"
else
    test_fail "Dashboard: Does not call /groups"
fi

if echo "$DASHBOARD_PAGE" | grep -q "apiCall('/nodes')"; then
    test_pass "Dashboard: Calls /nodes"
else
    test_fail "Dashboard: Does not call /nodes"
fi

# Section 6: Security Tests
test_section "6. SECURITY TESTS"

# Test unauthenticated request
UNAUTH=$(curl -s http://139.59.149.48/api/v1/groups)

if echo "$UNAUTH" | grep -q "Not authenticated"; then
    test_pass "Unauthenticated request: Blocked correctly"
else
    test_fail "Unauthenticated request: Not blocked"
fi

# Test CORS headers
CORS_HEADERS=$(curl -s -I http://139.59.149.48/api/v1/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://139.59.149.48" | grep -i "access-control")

if echo "$CORS_HEADERS" | grep -q "Access-Control-Allow-Origin"; then
    test_pass "CORS: Headers present"
else
    test_fail "CORS: Headers missing"
fi

# Final Report
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                     TEST SUMMARY                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "Total Tests:    ${BLUE}$TOTAL${NC}"
echo -e "Passed:         ${GREEN}$PASS${NC}"
echo -e "Failed:         ${RED}$FAIL${NC}"
echo ""

PASS_RATE=$((PASS * 100 / TOTAL))
echo -e "Pass Rate:      ${BLUE}$PASS_RATE%${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ ALL TESTS PASSED - SYSTEM FULLY OPERATIONAL              ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    exit 0
else
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  ⚠️  SOME TESTS FAILED - SEE DETAILS ABOVE                   ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    exit 1
fi
