#!/usr/bin/env python3
"""
Secret Rotation Script
Generates new high-entropy credentials for the OSINT Autonomous Analyst.
"""

import secrets
import string
import os
import shutil
from datetime import datetime
from pathlib import Path

# Configuration
SECRETS_DIR = Path("../../secrets")  # Relative to backend/scripts
BACKUP_DIR = SECRETS_DIR / "backups"

TARGET_SECRETS = [
    "neo4j_password",
    "timescale_password",
    "redis_password",
    "minio_secret_key",
    "app_secret_key"
]

def generate_secure_password(length=32):
    """Generate a high-entropy password safe for all services"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

def backup_secrets():
    """Backup existing secrets before rotation"""
    if not SECRETS_DIR.exists():
        os.makedirs(SECRETS_DIR)
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_backup = BACKUP_DIR / timestamp
    os.makedirs(current_backup, exist_ok=True)
    
    print(f"[*] Backing up secrets to {current_backup}...")
    
    for secret_file in SECRETS_DIR.glob("*"):
        if secret_file.is_file():
            shutil.copy2(secret_file, current_backup)

def rotate_secrets():
    """Rotate credentials"""
    print("=" * 50)
    print("OSINT ANALYST - SECRET ROTATION")
    print("=" * 50)
    
    backup_secrets()
    
    print("[*] Generating new secrets...")
    
    for secret_name in TARGET_SECRETS:
        new_password = generate_secure_password()
        secret_path = SECRETS_DIR / secret_name
        
        with open(secret_path, "w") as f:
            f.write(new_password)
        
        print(f"    [+] Rotated: {secret_name}")

    print("\n[SUCCESS] Secrets rotated successfully.")
    print("=" * 50)
    print("IMPORTANT NEXT STEPS:")
    print("1. Restart your Docker containers to apply changes:")
    print("   docker-compose down && docker-compose up -d")
    print("2. If using an external Vault, sync these values now.")
    print("=" * 50)

if __name__ == "__main__":
    # Safety Prompt
    confirmation = input("WARNING: This will break running services until restart. Continue? (y/N): ")
    if confirmation.lower() == "y":
        rotate_secrets()
    else:
        print("Aborted.")
