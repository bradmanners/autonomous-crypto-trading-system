#!/bin/bash

# Setup Check Script
# Quick verification that prerequisites are met

echo "=========================================="
echo "  Trading System - Setup Prerequisites"
echo "=========================================="
echo ""

ERRORS=0

# Check Docker
echo -n "Checking Docker... "
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        echo "✓ Docker running"
    else
        echo "✗ Docker not running (start Docker Desktop)"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "✗ Docker not installed"
    ERRORS=$((ERRORS + 1))
fi

# Check Python
echo -n "Checking Python... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
        echo "✓ Python $PYTHON_VERSION"
    else
        echo "✗ Python $PYTHON_VERSION (need 3.11+)"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "✗ Python not installed"
    ERRORS=$((ERRORS + 1))
fi

# Check RAM
echo -n "Checking RAM... "
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    TOTAL_RAM_MB=$(sysctl hw.memsize | awk '{print int($2/1024/1024)}')
else
    # Linux
    TOTAL_RAM_MB=$(free -m | awk 'NR==2{print $2}')
fi

if [ $TOTAL_RAM_MB -ge 8192 ]; then
    echo "✓ ${TOTAL_RAM_MB}MB available"
else
    echo "⚠ ${TOTAL_RAM_MB}MB (8GB recommended)"
fi

# Check disk space
echo -n "Checking disk space... "
AVAILABLE_GB=$(df -h . | awk 'NR==2 {print $4}' | sed 's/G.*//')
if [ "${AVAILABLE_GB%.*}" -ge 10 ]; then
    echo "✓ ${AVAILABLE_GB}GB available"
else
    echo "⚠ ${AVAILABLE_GB}GB available (10GB recommended)"
fi

# Check .env file
echo -n "Checking .env file... "
if [ -f ".env" ]; then
    echo "✓ .env exists"

    # Check if critical keys are set
    echo -n "  Checking API keys... "
    if grep -q "BINANCE_API_KEY=your_" .env 2>/dev/null || \
       grep -q "BINANCE_API_KEY=$" .env 2>/dev/null || \
       grep -q "BINANCE_API_KEY=\"\"" .env 2>/dev/null; then
        echo "⚠ Binance key not set"
    else
        echo "✓ Binance key configured"
    fi

    echo -n "  Checking Claude key... "
    if grep -q "ANTHROPIC_API_KEY=your_" .env 2>/dev/null || \
       grep -q "ANTHROPIC_API_KEY=$" .env 2>/dev/null || \
       grep -q "ANTHROPIC_API_KEY=\"\"" .env 2>/dev/null; then
        echo "⚠ Anthropic key not set"
    else
        echo "✓ Anthropic key configured"
    fi
else
    echo "✗ .env missing (copy from .env.template)"
    ERRORS=$((ERRORS + 1))
fi

# Check virtual environment
echo -n "Checking Python venv... "
if [ -d "venv" ]; then
    echo "✓ venv exists"
else
    echo "⚠ venv not created (run: python3 -m venv venv)"
fi

# Check Docker containers
echo -n "Checking Docker containers... "
if docker-compose ps | grep -q "Up"; then
    RUNNING=$(docker-compose ps | grep "Up" | wc -l | tr -d ' ')
    echo "✓ $RUNNING containers running"
else
    echo "⚠ No containers running (run: docker-compose up -d)"
fi

echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo "✓ Prerequisites check passed!"
    echo ""
    echo "Next steps:"
    echo "  1. Activate venv: source venv/bin/activate"
    echo "  2. Run tests: python scripts/test_infrastructure.py"
else
    echo "✗ Found $ERRORS critical issue(s)"
    echo ""
    echo "Please resolve the errors above before proceeding."
fi
echo "=========================================="
echo ""
