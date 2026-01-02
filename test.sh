#!/usr/bin/env bash

# script used to test declarr against my own config

set -euo pipefail

SRC_BASE="/var/lib"
BACKUP_BASE="/var/lib/old"

DIRS=(jellyseerr sonarr radarr prowlarr lidarr)

fix_perms() {
    for dir in "${DIRS[@]}"; do
        chown "$dir:media" -R "$SRC_BASE/$dir" || true
    done
}

create_folders() {
    echo "Create folders"
    systemd-tmpfiles --create || true

    fix_perms

    systemd-tmpfiles --create
}

rsync_things() {
    local from
    local to
    from=$1
    to=$2

    echo "Copying directories to $to..."
    for dir in "${DIRS[@]}"; do
        rsync -a "$from/$dir/" "$to/$dir/"
    done
}

backup() {
    echo "Creating backup directory..."
    mkdir -p "$BACKUP_BASE"

    rsync_things "$SRC_BASE" "$BACKUP_BASE"
}

clear_folders() {
    echo "Deleting original directories..."
    for dir in "${DIRS[@]}"; do
        rm -rf "${SRC_BASE:?}/$dir"/*
        rm -rf "${SRC_BASE:?}/$dir"/.*
    done

    create_folders

    fix_perms
}

revert() {
    clear_folders 

    rsync_things "$BACKUP_BASE" "$SRC_BASE"

    fix_perms
}

main() {
    echo "Stopping services..."
    systemctl stop declarr
    systemctl stop sonarr radarr lidarr prowlarr jellyseerr

    # backup
    # clear_folders
    revert

    echo "Starting core services..."
    systemctl start sonarr radarr lidarr prowlarr jellyseerr

    echo "Starting declarr..."
    systemctl start declarr
}

main
