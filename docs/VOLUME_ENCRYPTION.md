# Encrypted Data at Rest - Implementation Guide

**Standard Operating Procedure (SOP) for Deployment**

## Overview
The "OSINT Autonomous Analyst" stores highly sensitive intelligence. While Enterprise databases offer native encryption, the most robust "Government-Grade" protection for a containerized stack is **Disk-Level Encryption** (LUKS) on the host server.

This ensures that even if the physical drive is stolen or the container volume is copied, the data remains unreadable.

## Prerequisites
- Linux Host (Ubuntu/Debian/RHEL)
- `cryptsetup` installed
- Root (`sudo`) access

## Implementation Steps

### 1. Create an Encrypted Volume Container
Instead of a whole partition, we can create a file-based encrypted volume for portability.

```bash
# 1. Create a 50GB file to hold the encrypted volume
sudo fallocate -l 50G /opt/osa_data.img

# 2. Format as a LUKS encryption container
sudo cryptsetup luksFormat /opt/osa_data.img
# (You will be prompted to set a strong decryption passphrase)

# 3. Open the encrypted container
sudo cryptsetup luksOpen /opt/osa_data.img osa_encrypted_volume
```

### 2. Format and Mount the Volume
```bash
# 1. Format the mapper device with Ext4
sudo mkfs.ext4 /dev/mapper/osa_encrypted_volume

# 2. Create the mount point
sudo mkdir -p /mnt/osa_secure_data

# 3. Mount it
sudo mount /dev/mapper/osa_encrypted_volume /mnt/osa_secure_data
```

### 3. Migrate Docker Data
Move your existing project data path (or where you want the Docker volumes to live) to this secure mount.

```bash
# Example: If your Validated Docker Compose path is /opt/osint-analyst
# We want the 'neo4j_data', 'timescale_data', etc., to live inside /mnt/osa_secure_data

# Create data directories inside the encrypted mount
sudo mkdir -p /mnt/osa_secure_data/neo4j_data
sudo mkdir -p /mnt/osa_secure_data/timescale_data
sudo mkdir -p /mnt/osa_secure_data/minio_data

# Update permissions (User 1000 usually)
sudo chown -R 1000:1000 /mnt/osa_secure_data
```

### 4. Update Docker Compose
Modify your `docker-compose.yml` to point to these absolute paths instead of managed volumes.

```yaml
services:
  neo4j:
    volumes:
      # OLD: - neo4j_data:/data
      # NEW:
      - /mnt/osa_secure_data/neo4j_data:/data
    ...
```

### 5. Deployment / Reboot Protocol
When the server reboots, the data will be **locked** and unreachable. Docker containers will fail to start until "unlocked".

**Unlock Procedure:**
```bash
# Administrator runs this manually after reboot:
sudo cryptsetup luksOpen /opt/osa_data.img osa_encrypted_volume
sudo mount /dev/mapper/osa_encrypted_volume /mnt/osa_secure_data
sudo docker-compose up -d
```

## Verification
1. **Check Mount:** `df -h` should show `/dev/mapper/osa_encrypted_volume`.
2. **Check Lock:** Unmount and close the volume (`sudo cryptsetup luksClose ...`). Try to read the `/opt/osa_data.img` file—it will be garbled binary data.
