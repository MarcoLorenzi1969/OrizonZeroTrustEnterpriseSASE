#!/bin/bash
#
# Orizon Zero Trust - Test Runner Script
# Installs dependencies and runs tests
#

set -e

echo "🧪 Orizon Zero Trust - Test Runner"
echo "=================================="
echo ""

# Check if we're in backend directory
if [[ ! -f "requirements.txt" ]]; then
    echo "❌ Error: Must run from backend/ directory"
    exit 1
fi

# Install core dependencies
echo "📦 Installing dependencies..."
pip install -q sqlalchemy>=2.0.30 aiosqlite fastapi pydantic python-jose passlib bcrypt loguru asyncpg redis motor

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install -q pytest pytest-asyncio pytest-cov httpx

# Create .env for tests if not exists
if [[ ! -f ".env" ]]; then
    echo "📝 Creating .env from .env.test..."
    cp .env.test .env
fi

echo ""
echo "✅ Dependencies installed"
echo ""

# Run tests with different options based on arguments
if [[ "$1" == "coverage" ]]; then
    echo "📊 Running tests with coverage..."
    python -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
elif [[ "$1" == "fast" ]]; then
    echo "⚡ Running fast tests (unit only)..."
    python -m pytest tests/unit/ -v
elif [[ "$1" == "auth" ]]; then
    echo "🔐 Running auth tests only..."
    python -m pytest tests/unit/test_auth_security.py -v
elif [[ -n "$1" ]]; then
    echo "🧪 Running specific test: $1"
    python -m pytest "$1" -v
else
    echo "🧪 Running all tests..."
    python -m pytest tests/ -v
fi

echo ""
echo "✅ Tests completed"
