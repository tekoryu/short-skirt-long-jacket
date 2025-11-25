#!/bin/bash

# ========================================
# Dump Fixtures Script
# ========================================
# This script dumps the current database state
# to fixture files for initial data loading
# ========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

print_info "Dumping current database state to fixtures..."
echo "========================================"

# Dump cities data
print_info "Dumping cities data (regions, states, municipalities)..."
docker compose run --rm app python manage.py dumpdata \
  cities.Region \
  cities.State \
  cities.IntermediateRegion \
  cities.ImmediateRegion \
  cities.Municipality \
  --indent 2 \
  --output /app/fixtures/cities_initial_data.json

if [ $? -eq 0 ]; then
    CITIES_SIZE=$(du -h app/fixtures/cities_initial_data.json | cut -f1)
    print_success "✓ Cities data dumped successfully (${CITIES_SIZE})"
else
    print_error "✗ Failed to dump cities data"
    exit 1
fi

# Dump auth data
print_info "Dumping auth data (groups, permissions)..."
docker compose run --rm app python manage.py dumpdata \
  auth.Group \
  custom_auth.ResourcePermission \
  custom_auth.GroupResourcePermission \
  --indent 2 \
  --output /app/fixtures/auth_initial_data.json

if [ $? -eq 0 ]; then
    AUTH_SIZE=$(du -h app/fixtures/auth_initial_data.json | cut -f1)
    print_success "✓ Auth data dumped successfully (${AUTH_SIZE})"
else
    print_error "✗ Failed to dump auth data"
    exit 1
fi

echo "========================================"
print_success "All fixtures dumped successfully!"
echo ""
print_info "Fixture files:"
echo "  - app/fixtures/cities_initial_data.json (${CITIES_SIZE})"
echo "  - app/fixtures/auth_initial_data.json (${AUTH_SIZE})"
echo ""
print_warning "Next steps:"
echo "  1. Review the fixture files for any sensitive data"
echo "  2. Commit to version control: git add app/fixtures/*.json"
echo "  3. Create a commit: git commit -m 'Update fixtures with current database state'"

