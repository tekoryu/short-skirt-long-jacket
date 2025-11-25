#!/bin/bash

# ========================================
# SEAF Production Deployment Script
# ========================================
# This script handles deployment and updates
# for the SEAF application on production server
# ========================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Functions
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

# Check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_error ".env file not found in project root!"
        print_info "Please copy .env.production to .env and configure it with production values"
        print_info "Command: cp .env.production .env"
        exit 1
    fi
}

# Check if traefik network exists
check_traefik_network() {
    if ! docker network ls | grep -q "traefik-public"; then
        print_warning "Traefik network 'traefik-public' not found. Creating it..."
        docker network create traefik-public
        print_success "Traefik network created"
    fi
}

# Pull latest changes from git
pull_changes() {
    print_info "Pulling latest changes from git..."
    git pull origin deploy/0.1
    print_success "Code updated"
}

# Build and start containers
deploy_containers() {
    print_info "Building and starting containers..."
    docker compose -f compose.prod.yaml build
    docker compose -f compose.prod.yaml up -d
    print_success "Containers deployed"
}

# Show container status
show_status() {
    print_info "Container status:"
    docker compose -f compose.prod.yaml ps
}

# Show logs
show_logs() {
    print_info "Recent logs:"
    docker compose -f compose.prod.yaml logs --tail=50
}

# Health check
health_check() {
    print_info "Waiting for application to be healthy..."
    sleep 10

    if docker compose -f compose.prod.yaml ps | grep -q "healthy"; then
        print_success "Application is healthy!"
        return 0
    else
        print_warning "Health check status unclear. Check logs for details."
        return 1
    fi
}

# Main deployment process
main() {
    print_info "Starting SEAF deployment..."
    echo "========================================"

    check_env_file
    check_traefik_network
    pull_changes
    deploy_containers

    echo "========================================"
    print_success "Deployment completed!"
    echo ""

    show_status

    if health_check; then
        echo ""
        print_success "Application is now available at: https://seaf.cenariodigital.dev"
    else
        echo ""
        print_warning "Please check the application manually"
        print_info "View logs with: docker compose -f compose.prod.yaml logs -f"
    fi
}

# Handle script arguments
case "${1:-}" in
    logs)
        docker compose -f compose.prod.yaml logs -f
        ;;
    status)
        show_status
        ;;
    restart)
        print_info "Restarting containers..."
        docker compose -f compose.prod.yaml restart
        print_success "Containers restarted"
        ;;
    stop)
        print_info "Stopping containers..."
        docker compose -f compose.prod.yaml down
        print_success "Containers stopped"
        ;;
    clean)
        print_warning "This will stop containers and remove volumes (including database)!"
        read -p "Are you sure? (yes/no): " -r
        if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            docker compose -f compose.prod.yaml down -v
            print_success "Cleanup completed"
        else
            print_info "Cleanup cancelled"
        fi
        ;;
    help|--help|-h)
        echo "SEAF Deployment Script"
        echo ""
        echo "Usage: ./deploy.sh [command]"
        echo ""
        echo "Commands:"
        echo "  (none)    - Deploy or update the application"
        echo "  logs      - Follow application logs"
        echo "  status    - Show container status"
        echo "  restart   - Restart containers"
        echo "  stop      - Stop containers"
        echo "  clean     - Stop and remove all containers and volumes"
        echo "  help      - Show this help message"
        ;;
    *)
        main
        ;;
esac
