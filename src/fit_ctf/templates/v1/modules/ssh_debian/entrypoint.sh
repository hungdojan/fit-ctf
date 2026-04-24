#!/usr/bin/env bash
set -e

# Start sshd
exec /usr/sbin/sshd -D
