#!/usr/bin/env bash
set -e

# Fix ownership of mounted volumes for the container's user account
# This handles rootless podman UID mapping issues
if [ -d /home/user ]; then
    chown -R user:user /home/user
fi

if [ -f /etc/shadow ]; then
    chown root:root /etc/shadow
    chmod 640 /etc/shadow
fi

# Start sshd
exec /usr/sbin/sshd -D
