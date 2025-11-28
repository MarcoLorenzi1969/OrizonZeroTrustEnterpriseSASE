#!/bin/bash
# Orizon SSH Tunnel Server - Key Management
# For: Marco @ Syneto/Orizon

set -e

KEYS_DIR="/etc/ssh/authorized_keys"

usage() {
    echo "Usage: $0 [add|remove|list] [node_id] [public_key]"
    echo ""
    echo "Commands:"
    echo "  add NODE_ID PUBLIC_KEY    Add authorized key for node"
    echo "  remove NODE_ID            Remove node authorization"
    echo "  list                      List all authorized nodes"
    exit 1
}

add_key() {
    local node_id="$1"
    local public_key="$2"

    if [[ -z "$node_id" || -z "$public_key" ]]; then
        echo "Error: node_id and public_key required"
        exit 1
    fi

    # Create user if doesn't exist
    if ! id "$node_id" &>/dev/null; then
        adduser -D -s /bin/false "$node_id"
        echo "Created user: $node_id"
    fi

    # Add public key
    echo "$public_key" > "${KEYS_DIR}/${node_id}"
    chmod 600 "${KEYS_DIR}/${node_id}"

    echo "Added key for node: $node_id"
}

remove_key() {
    local node_id="$1"

    if [[ -z "$node_id" ]]; then
        echo "Error: node_id required"
        exit 1
    fi

    rm -f "${KEYS_DIR}/${node_id}"
    deluser "$node_id" 2>/dev/null || true

    echo "Removed node: $node_id"
}

list_keys() {
    echo "Authorized nodes:"
    echo ""
    for keyfile in ${KEYS_DIR}/*; do
        if [[ -f "$keyfile" ]]; then
            node_id=$(basename "$keyfile")
            echo "  - $node_id"
        fi
    done
}

case "${1:-}" in
    add)
        add_key "$2" "$3"
        ;;
    remove)
        remove_key "$2"
        ;;
    list)
        list_keys
        ;;
    *)
        usage
        ;;
esac
