#!/bin/bash

# Docker Bridge Network Diagnostic Script
# This script helps diagnose and fix common Docker bridge networking issues

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Docker Bridge Network Diagnostic Tool ==="
echo

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# 1. Check kernel modules
echo "=== Checking Required Kernel Modules ==="
modules=("bridge" "br_netfilter" "veth")
missing_modules=()

for module in "${modules[@]}"; do
    if lsmod | grep -q "^$module"; then
        echo -e "${GREEN}✓ $module module is loaded${NC}"
    else
        echo -e "${RED}✗ $module module is not loaded${NC}"
        missing_modules+=("$module")
    fi
done

if [ ${#missing_modules[@]} -ne 0 ]; then
    echo -e "\n${YELLOW}Loading missing modules...${NC}"
    for module in "${missing_modules[@]}"; do
        modprobe $module
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Successfully loaded $module${NC}"
        else
            echo -e "${RED}Failed to load $module${NC}"
        fi
    done
fi

# 2. Test manual bridge creation
echo -e "\n=== Testing Manual Bridge Creation ==="
ip link show testbridge > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${YELLOW}Removing existing testbridge...${NC}"
    ip link delete testbridge
fi

echo "Creating test bridge..."
if ip link add name testbridge type bridge; then
    echo -e "${GREEN}✓ Successfully created test bridge${NC}"
    ip link delete testbridge
else
    echo -e "${RED}✗ Failed to create test bridge - kernel may be blocking bridge creation${NC}"
fi

# 3. Check iptables backend
echo -e "\n=== Checking iptables Configuration ==="
if update-alternatives --get-selections | grep -q "iptables"; then
    current_iptables=$(update-alternatives --get-selections | grep "^iptables " | awk '{print $3}')
    echo -e "Current iptables implementation: ${YELLOW}$current_iptables${NC}"
    if [[ $current_iptables == *"nft"* ]]; then
        echo -e "${YELLOW}System is using nftables backend. Docker works better with iptables-legacy${NC}"
        echo "To switch to legacy:"
        echo "sudo update-alternatives --set iptables /usr/sbin/iptables-legacy"
    fi
else
    echo -e "${YELLOW}Could not determine iptables backend${NC}"
fi

# 4. Check security modules
echo -e "\n=== Checking Security Modules ==="
if systemctl is-active --quiet apparmor; then
    echo -e "${YELLOW}AppArmor is active${NC}"
    echo "Recent AppArmor denials (if any):"
    grep -i docker /var/log/audit/audit.log 2>/dev/null || echo "No Docker-related AppArmor denials found"
else
    echo -e "${GREEN}AppArmor is not running${NC}"
fi

if sestatus 2>/dev/null | grep -q "SELinux status: *enabled"; then
    echo -e "${YELLOW}SELinux is active${NC}"
else
    echo -e "${GREEN}SELinux is not enabled${NC}"
fi

# 5. Check Docker installation
echo -e "\n=== Checking Docker Installation ==="
if command -v docker >/dev/null 2>&1; then
    docker_path=$(which docker)
    echo -e "Docker binary path: ${YELLOW}$docker_path${NC}"
    if [[ $docker_path == "/snap/"* ]]; then
        echo -e "${RED}Docker is installed via Snap. Consider using official repository installation${NC}"
    elif [[ $docker_path == "/usr/bin/docker" ]]; then
        echo -e "${GREEN}Docker appears to be installed from official repositories${NC}"
    fi
else
    echo -e "${RED}Docker not found in PATH${NC}"
fi

# 6. Test Docker networking
echo -e "\n=== Testing Docker Networking ==="
echo "Attempting to run test container..."
if docker run --rm hello-world >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Test container ran successfully${NC}"
else
    echo -e "${RED}✗ Test container failed${NC}"
    echo "Last few lines of Docker daemon logs:"
    journalctl -u docker.service -n 5
fi

echo -e "\n=== Diagnostic Summary ==="
echo "If you're still experiencing issues:"
echo "1. If manual bridge creation failed: Try booting with a generic kernel"
echo "2. If using nftables: Consider switching to iptables-legacy"
echo "3. Check Docker logs for detailed error messages: journalctl -u docker.service"
echo "4. Consider reinstalling Docker from official repositories if using Snap"