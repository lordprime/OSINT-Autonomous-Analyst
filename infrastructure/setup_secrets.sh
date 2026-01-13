#!/bin/bash

# Create secrets directory
mkdir -p secrets

# Function to generate random password
generate_password() {
    openssl rand -hex 16
}

# Generate secrets if they don't exist
if [ ! -f secrets/neo4j_password ]; then
    echo "osint_secure_password_change_me" > secrets/neo4j_password
    echo "Generated secrets/neo4j_password"
fi

if [ ! -f secrets/timescale_password ]; then
    echo "osint_timescale_password_change_me" > secrets/timescale_password
    echo "Generated secrets/timescale_password"
fi

if [ ! -f secrets/redis_password ]; then
    echo "osint_redis_password_change_me" > secrets/redis_password
    echo "Generated secrets/redis_password"
fi

if [ ! -f secrets/minio_secret_key ]; then
    echo "osint_minio_password_change_me" > secrets/minio_secret_key
    echo "Generated secrets/minio_secret_key"
fi

echo "✅ Secrets generation complete."
