#!/bin/sh

RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
MAGENTA="\033[0;35m"
CYAN="\033[0;36m"
WHITE="\033[0;37m"
BOLD="\033[1m"
UNDERLINE="\033[4m"
NC="\033[0m"

echo_error() {
    echo "${RED}${BOLD}!!!ERROR: $1!!!${NC}"
}

echo_warning() {
    echo "${MAGENTA}${BOLD}WARNING: $1!!!${NC}"
}

echo_info() {
    echo "${CYAN}INFO: $1${NC}"
}

