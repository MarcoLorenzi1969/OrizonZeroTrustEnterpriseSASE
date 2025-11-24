#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ORIZON CRUD OPERATIONS TEST SUITE                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

BASE_URL="http://139.59.149.48/api/v1"
TESTS_PASSED=0
TESTS_FAILED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Login and get token
echo "🔐 Authenticating..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"marco@syneto.eu","password":"profano.69"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Authentication failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Authenticated successfully${NC}"
echo ""

# ============================================================================
# GROUPS CRUD TESTS
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "📦 GROUPS CRUD OPERATIONS"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Test 1: Create Group
echo "Test 1: Create new group..."
CREATE_GROUP=$(curl -s -X POST "$BASE_URL/groups" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"test-crud-group-'$(date +%s)'","description":"Created via CRUD test","settings":{}}')

GROUP_ID=$(echo "$CREATE_GROUP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

if [ ! -z "$GROUP_ID" ]; then
    test_result 0 "Create Group (ID: $GROUP_ID)"
else
    test_result 1 "Create Group"
    echo "Response: $CREATE_GROUP"
fi

# Test 2: Read Group
echo "Test 2: Read created group..."
READ_GROUP=$(curl -s -w "\n%{http_code}" "$BASE_URL/groups/$GROUP_ID" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$READ_GROUP" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    test_result 0 "Read Group by ID"
else
    test_result 1 "Read Group by ID (HTTP $HTTP_CODE)"
fi

# Test 3: Update Group
echo "Test 3: Update group..."
UPDATE_GROUP=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/groups/$GROUP_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"test-crud-group-updated","description":"Updated via CRUD test","settings":{}}')

HTTP_CODE=$(echo "$UPDATE_GROUP" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    test_result 0 "Update Group"
else
    test_result 1 "Update Group (HTTP $HTTP_CODE)"
fi

# Test 4: List Groups (verify creation)
echo "Test 4: List groups..."
LIST_GROUPS=$(curl -s "$BASE_URL/groups" \
  -H "Authorization: Bearer $TOKEN")

GROUPS_COUNT=$(echo "$LIST_GROUPS" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('groups',[])))" 2>/dev/null)
if [ "$GROUPS_COUNT" -gt 0 ]; then
    test_result 0 "List Groups (Found: $GROUPS_COUNT groups)"
else
    test_result 1 "List Groups"
fi

# Test 5: Delete Group
echo "Test 5: Delete group..."
DELETE_GROUP=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/groups/$GROUP_ID" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$DELETE_GROUP" | tail -n1)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    test_result 0 "Delete Group"
else
    test_result 1 "Delete Group (HTTP $HTTP_CODE)"
fi

# Test 6: Verify deletion
echo "Test 6: Verify group deletion..."
VERIFY_DELETE=$(curl -s -w "\n%{http_code}" "$BASE_URL/groups/$GROUP_ID" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$VERIFY_DELETE" | tail -n1)
if [ "$HTTP_CODE" = "404" ]; then
    test_result 0 "Verify Group Deleted (404 as expected)"
else
    test_result 1 "Verify Group Deleted (HTTP $HTTP_CODE, expected 404)"
fi

echo ""

# ============================================================================
# NODES CRUD TESTS
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "🖥️  NODES CRUD OPERATIONS"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Test 7: Create Node
echo "Test 7: Create new node..."
CREATE_NODE=$(curl -s -X POST "$BASE_URL/nodes" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"test-crud-node-'$(date +%s)'","hostname":"test-crud.local","node_type":"linux","public_ip":"192.168.1.100"}')

NODE_ID=$(echo "$CREATE_NODE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

if [ ! -z "$NODE_ID" ]; then
    test_result 0 "Create Node (ID: $NODE_ID)"
else
    test_result 1 "Create Node"
    echo "Response: $CREATE_NODE"
fi

# Test 8: Read Node
echo "Test 8: Read created node..."
READ_NODE=$(curl -s -w "\n%{http_code}" "$BASE_URL/nodes/$NODE_ID" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$READ_NODE" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    test_result 0 "Read Node by ID"
else
    test_result 1 "Read Node by ID (HTTP $HTTP_CODE)"
fi

# Test 9: Update Node
echo "Test 9: Update node..."
UPDATE_NODE=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/nodes/$NODE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"test-crud-node-updated","hostname":"test-crud-updated.local","node_type":"linux","public_ip":"192.168.1.101"}')

HTTP_CODE=$(echo "$UPDATE_NODE" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    test_result 0 "Update Node"
else
    test_result 1 "Update Node (HTTP $HTTP_CODE)"
fi

# Test 10: List Nodes
echo "Test 10: List nodes..."
LIST_NODES=$(curl -s "$BASE_URL/nodes" \
  -H "Authorization: Bearer $TOKEN")

NODES_COUNT=$(echo "$LIST_NODES" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('nodes',[])))" 2>/dev/null)
if [ "$NODES_COUNT" -gt 0 ]; then
    test_result 0 "List Nodes (Found: $NODES_COUNT nodes)"
else
    test_result 1 "List Nodes"
fi

# Test 11: Delete Node
echo "Test 11: Delete node..."
DELETE_NODE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/nodes/$NODE_ID" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$DELETE_NODE" | tail -n1)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    test_result 0 "Delete Node"
else
    test_result 1 "Delete Node (HTTP $HTTP_CODE)"
fi

# Test 12: Verify deletion
echo "Test 12: Verify node deletion..."
VERIFY_DELETE=$(curl -s -w "\n%{http_code}" "$BASE_URL/nodes/$NODE_ID" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$VERIFY_DELETE" | tail -n1)
if [ "$HTTP_CODE" = "404" ]; then
    test_result 0 "Verify Node Deleted (404 as expected)"
else
    test_result 1 "Verify Node Deleted (HTTP $HTTP_CODE, expected 404)"
fi

echo ""

# ============================================================================
# USERS CRUD TESTS
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "👤 USERS CRUD OPERATIONS"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Test 13: Create User
echo "Test 13: Create new user..."
CREATE_USER=$(curl -s -X POST "$BASE_URL/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"email":"test-crud-'$(date +%s)'@example.com","username":"testcrud'$(date +%s)'","password":"TestPassword123!","full_name":"Test CRUD User","role":"USER"}')

USER_ID=$(echo "$CREATE_USER" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

if [ ! -z "$USER_ID" ]; then
    test_result 0 "Create User (ID: $USER_ID)"
else
    test_result 1 "Create User"
    echo "Response: $CREATE_USER"
fi

# Test 14: Read User
echo "Test 14: Read created user..."
READ_USER=$(curl -s -w "\n%{http_code}" "$BASE_URL/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$READ_USER" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    test_result 0 "Read User by ID"
else
    test_result 1 "Read User by ID (HTTP $HTTP_CODE)"
fi

# Test 15: Update User
echo "Test 15: Update user..."
UPDATE_USER=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"full_name":"Test CRUD User Updated","role":"USER"}')

HTTP_CODE=$(echo "$UPDATE_USER" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    test_result 0 "Update User"
else
    test_result 1 "Update User (HTTP $HTTP_CODE)"
fi

# Test 16: List Users
echo "Test 16: List users..."
LIST_USERS=$(curl -s "$BASE_URL/users" \
  -H "Authorization: Bearer $TOKEN")

USERS_COUNT=$(echo "$LIST_USERS" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('users',[])))" 2>/dev/null)
if [ "$USERS_COUNT" -gt 0 ]; then
    test_result 0 "List Users (Found: $USERS_COUNT users)"
else
    test_result 1 "List Users"
fi

# Test 17: Delete User
echo "Test 17: Delete user..."
DELETE_USER=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$DELETE_USER" | tail -n1)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    test_result 0 "Delete User"
else
    test_result 1 "Delete User (HTTP $HTTP_CODE)"
fi

# Test 18: Verify deletion
echo "Test 18: Verify user deletion..."
VERIFY_DELETE=$(curl -s -w "\n%{http_code}" "$BASE_URL/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$VERIFY_DELETE" | tail -n1)
if [ "$HTTP_CODE" = "404" ]; then
    test_result 0 "Verify User Deleted (404 as expected)"
else
    test_result 1 "Verify User Deleted (HTTP $HTTP_CODE, expected 404)"
fi

echo ""

# ============================================================================
# FRONTEND INTEGRATION TESTS
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "🌐 FRONTEND INTEGRATION TESTS"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Test 19: Dashboard loads
echo "Test 19: Dashboard page loads..."
DASHBOARD_RESPONSE=$(curl -s -w "\n%{http_code}" "http://139.59.149.48/dashboard/")
HTTP_CODE=$(echo "$DASHBOARD_RESPONSE" | tail -n1)
DASHBOARD_CONTENT=$(echo "$DASHBOARD_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ] && echo "$DASHBOARD_CONTENT" | grep -q "Orizon Zero Trust"; then
    test_result 0 "Dashboard Page Loads"
else
    test_result 1 "Dashboard Page Loads (HTTP $HTTP_CODE)"
fi

# Test 20: Dashboard has CRUD modals
echo "Test 20: Dashboard contains CRUD modals..."
if echo "$DASHBOARD_CONTENT" | grep -q "groupModal" && \
   echo "$DASHBOARD_CONTENT" | grep -q "nodeModal" && \
   echo "$DASHBOARD_CONTENT" | grep -q "userModal"; then
    test_result 0 "Dashboard Has CRUD Modals (Groups, Nodes, Users)"
else
    test_result 1 "Dashboard Has CRUD Modals"
fi

# Test 21: Dashboard has create buttons
echo "Test 21: Dashboard contains create buttons..."
if echo "$DASHBOARD_CONTENT" | grep -q "showCreateGroupModal" && \
   echo "$DASHBOARD_CONTENT" | grep -q "showCreateNodeModal" && \
   echo "$DASHBOARD_CONTENT" | grep -q "showCreateUserModal"; then
    test_result 0 "Dashboard Has Create Buttons"
else
    test_result 1 "Dashboard Has Create Buttons"
fi

# Test 22: Dashboard has edit/delete functions
echo "Test 22: Dashboard contains edit/delete functions..."
if echo "$DASHBOARD_CONTENT" | grep -q "editGroup" && \
   echo "$DASHBOARD_CONTENT" | grep -q "deleteGroup" && \
   echo "$DASHBOARD_CONTENT" | grep -q "editNode" && \
   echo "$DASHBOARD_CONTENT" | grep -q "deleteNode" && \
   echo "$DASHBOARD_CONTENT" | grep -q "editUser" && \
   echo "$DASHBOARD_CONTENT" | grep -q "deleteUser"; then
    test_result 0 "Dashboard Has Edit/Delete Functions"
else
    test_result 1 "Dashboard Has Edit/Delete Functions"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "                     TEST RESULTS SUMMARY"
echo "═══════════════════════════════════════════════════════════════"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))

echo "Total Tests:    $TOTAL_TESTS"
echo "Passed:         $TESTS_PASSED"
echo "Failed:         $TESTS_FAILED"
echo "Pass Rate:      $PASS_RATE%"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ ALL CRUD TESTS PASSED - SYSTEM FULLY OPERATIONAL        ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ⚠️  SOME TESTS FAILED - REVIEW REQUIRED                    ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
