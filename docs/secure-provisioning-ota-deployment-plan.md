# Secure Device Provisioning & OTA Updates - Deployment Plan

**Version:** 1.0  
**Date:** 2025-11-04  
**Status:** Planning Phase  

## Executive Summary

This deployment plan implements secure device provisioning and Over-The-Air (OTA) updates for the Golf CMS e-ink device fleet. The system will enable remote updates without site visits, reduce support costs, and enable faster iteration cycles.

**Key Objectives:**
- Per-device authentication credentials (not just device_id)
- Secure provisioning with one-time codes
- Signed OTA updates with automatic rollback
- Staged rollout capability (canary → beta → stable)
- Zero-downtime updates with A/B slot architecture

**Impact:**
- Eliminate site visits for software updates
- Reduce support costs by 70%+
- Enable rapid bug fixes and feature deployment
- Improve security posture with per-device credentials

---

## Current State Analysis

### Existing Infrastructure

**Device Setup:**
- Manual installation via `install-device.sh` script
- Downloads device client from GitHub
- Creates config.json with device_id, api_base_url
- No per-device authentication (only device_id identification)
- Systemd service for automatic startup

**Backend:**
- FastAPI + PostgreSQL/Supabase
- Device model has `firmware_version`, `hardware_version`, `remote_update_enabled` fields
- Remote command system (`DeviceRemoteCommand` model)
- Command queue with timeout and deduplication

**Device Client:**
- Python-based, runs as systemd service
- Polls API every 15 minutes for content updates
- Sends health heartbeat every 10 minutes
- No authentication headers currently

### Security Gaps

1. **No per-device credentials** - Any device with a valid device_id can impersonate another
2. **No provisioning security** - Manual config file creation is error-prone
3. **No update mechanism** - Requires SSH access or site visit for updates
4. **Secrets in repository** - .env.production was committed (needs rotation)
5. **No request signing** - API tokens could be logged/leaked

---

## Architecture Design

### 1. Per-Device Authentication

**Approach: API Key-Based Authentication (Phase 1)**

Each device receives a unique, cryptographically random API key during provisioning.

**Database Schema Changes:**

```sql
-- Add to devices table
ALTER TABLE devices
  ADD COLUMN IF NOT EXISTS api_key_hash VARCHAR(255),
  ADD COLUMN IF NOT EXISTS token_version INTEGER DEFAULT 1,
  ADD COLUMN IF NOT EXISTS last_auth_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_seen_ip VARCHAR(45),
  ADD COLUMN IF NOT EXISTS update_channel VARCHAR(20) DEFAULT 'stable',
  ADD COLUMN IF NOT EXISTS last_update_attempt TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_update_status VARCHAR(50);

-- Create index for auth lookups
CREATE INDEX IF NOT EXISTS idx_devices_api_key_hash ON devices(api_key_hash);
```

**Authentication Flow:**
1. Device sends `Authorization: Bearer <device_token>` header on all requests
2. Backend validates token hash against database
3. Updates `last_auth_at` and `last_seen_ip` on successful auth
4. Returns 401 Unauthorized for invalid/missing tokens

**Token Format:**
- 32-byte random token (base64url encoded)
- Example: `gad_dev_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
- Prefix `gad_dev_` for easy identification in logs (can be scrubbed)

**Security Features:**
- Tokens hashed with bcrypt (cost factor 12)
- Token rotation capability (increments token_version)
- Revocation support (set api_key_hash to NULL)
- Rate limiting on auth failures (10 attempts per hour per device)

### 2. Provisioning System

**Provisioning Code Architecture:**

```sql
-- New table for provisioning codes
CREATE TABLE provisioning_codes (
  id SERIAL PRIMARY KEY,
  code VARCHAR(64) UNIQUE NOT NULL,
  course_id INTEGER REFERENCES courses(id) NOT NULL,
  device_label VARCHAR(255),
  expires_at TIMESTAMPTZ NOT NULL,
  max_uses INTEGER DEFAULT 1,
  use_count INTEGER DEFAULT 0,
  status VARCHAR(20) DEFAULT 'active', -- active, used, expired, revoked
  used_by_device_id INTEGER REFERENCES devices(id),
  used_at TIMESTAMPTZ,
  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT
);

CREATE INDEX idx_provisioning_codes_code ON provisioning_codes(code);
CREATE INDEX idx_provisioning_codes_status ON provisioning_codes(status, expires_at);
```

**Provisioning Flow:**

1. **Admin Dashboard:**
   - Course admin generates provisioning code
   - Specifies: device label, expiry (24-72h), optional notes
   - System generates UUID-based code: `PROV-a1b2c3d4-e5f6-g7h8`
   - Display as QR code + copyable text

2. **Device Installation:**
   ```bash
   # Updated install script
   ./install-device.sh --provision-code PROV-a1b2c3d4-e5f6-g7h8
   ```

3. **Provisioning Endpoint:**
   ```
   POST /api/devices/provision
   {
     "provision_code": "PROV-a1b2c3d4-e5f6-g7h8",
     "device_id": "Device-POC-001",
     "hardware_info": {
       "model": "Raspberry Pi 4B",
       "serial": "10000000a1b2c3d4",
       "mac_address": "dc:a6:32:xx:xx:xx"
     }
   }
   
   Response:
   {
     "device_token": "gad_dev_...",  // Only shown once!
     "device_id": "Device-POC-001",
     "api_base_url": "https://...",
     "config": { ... }
   }
   ```

4. **Backend Processing:**
   - Validate code (exists, not expired, not used)
   - Create device record in database
   - Generate and hash API key
   - Mark code as used
   - Return device token (plaintext, only once)
   - Send notification to course admin

5. **Device Configuration:**
   - Install script writes token to `/etc/eink_device/config.json`
   - File permissions: `root:root 600` (read-only by root)
   - Never log the token in plaintext

**Optional: Manual Approval Workflow**
- Toggle per-tenant: `require_device_approval`
- Provisioned devices land in "pending" status
- Admin reviews and approves/rejects
- Useful for high-security deployments

### 3. OTA Update System

**A/B Slot Architecture:**

```
/opt/gad/
├── app-A/           # Slot A
│   ├── venv/
│   ├── eink_device_client.py
│   └── version.json
├── app-B/           # Slot B
│   ├── venv/
│   ├── eink_device_client.py
│   └── version.json
├── current -> app-A # Symlink to active slot
└── update/          # Temporary download location
```

**Update Release Model:**

```sql
CREATE TABLE update_releases (
  id SERIAL PRIMARY KEY,
  version VARCHAR(50) UNIQUE NOT NULL,
  channel VARCHAR(20) NOT NULL, -- canary, beta, stable
  artifact_url TEXT NOT NULL,
  artifact_sha256 VARCHAR(64) NOT NULL,
  artifact_signature TEXT NOT NULL, -- Ed25519 signature
  artifact_size_bytes BIGINT,
  min_client_version VARCHAR(50),
  release_notes TEXT,
  rollout_percent INTEGER DEFAULT 0, -- 0-100
  rollout_start_time TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT true,
  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE device_update_status (
  id SERIAL PRIMARY KEY,
  device_id INTEGER REFERENCES devices(id) NOT NULL,
  release_id INTEGER REFERENCES update_releases(id) NOT NULL,
  status VARCHAR(50) NOT NULL, -- downloading, verifying, installing, confirming, completed, failed, rolled_back
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  error_message TEXT,
  rollback_reason TEXT,
  attempt_number INTEGER DEFAULT 1
);

CREATE INDEX idx_device_update_status_device ON device_update_status(device_id, started_at DESC);
```

**Update Flow:**

1. **Check for Updates (Device → Backend):**
   ```
   GET /api/devices/{device_id}/updates/check
   Headers: Authorization: Bearer <device_token>
   
   Response:
   {
     "update_available": true,
     "version": "2.3.0",
     "channel": "stable",
     "artifact_url": "https://storage.../gad-client-2.3.0.tar.gz?signed_url",
     "sha256": "abc123...",
     "signature": "ed25519_sig...",
     "size_bytes": 15728640,
     "release_notes": "Bug fixes and performance improvements",
     "download_after": "2025-11-04T15:30:00Z"  // Jitter to avoid stampede
   }
   ```

2. **Download & Verify (Device):**
   ```python
   # Download to temp location
   download_to("/opt/gad/update/update.tar.gz")
   
   # Verify SHA256
   if sha256(file) != expected_sha256:
       report_failure("SHA256 mismatch")
       return
   
   # Verify Ed25519 signature
   if not verify_signature(file, signature, public_key):
       report_failure("Signature verification failed")
       return
   ```

3. **Install to Inactive Slot:**
   ```python
   # Determine inactive slot
   current_slot = readlink("/opt/gad/current")  # "app-A"
   inactive_slot = "app-B" if current_slot == "app-A" else "app-A"
   
   # Extract to inactive slot
   extract_tarball("/opt/gad/update/update.tar.gz", f"/opt/gad/{inactive_slot}")
   
   # Run preflight checks
   result = run_command(f"/opt/gad/{inactive_slot}/venv/bin/python --version")
   if result.returncode != 0:
       report_failure("Preflight check failed")
       return
   ```

4. **Atomic Swap:**
   ```python
   # Update symlink atomically
   os.symlink(f"/opt/gad/{inactive_slot}", "/opt/gad/current.new")
   os.rename("/opt/gad/current.new", "/opt/gad/current")
   
   # Restart service
   subprocess.run(["sudo", "systemctl", "restart", "eink-device.service"])
   ```

5. **Health Confirmation:**
   ```python
   # New version must report health within 5 minutes
   POST /api/devices/{device_id}/updates/confirm
   {
     "version": "2.3.0",
     "status": "success",
     "boot_time": "2025-11-04T15:35:00Z"
   }
   ```

6. **Automatic Rollback:**
   ```python
   # If health not confirmed within 5 minutes, watchdog triggers rollback
   # Watchdog runs as separate systemd timer
   
   if not health_confirmed_within(5 minutes):
       # Flip symlink back to previous slot
       previous_slot = "app-A" if current == "app-B" else "app-B"
       os.symlink(f"/opt/gad/{previous_slot}", "/opt/gad/current.new")
       os.rename("/opt/gad/current.new", "/opt/gad/current")
       
       # Restart service
       subprocess.run(["sudo", "systemctl", "restart", "eink-device.service"])
       
       # Report rollback
       report_rollback("Health check timeout")
   ```

**Systemd Configuration:**

```ini
# /etc/systemd/system/eink-device.service
[Unit]
Description=E-ink Device Client for Golf CMS
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/gad/current
ExecStart=/opt/gad/current/venv/bin/python eink_device_client.py
Restart=always
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=300
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/eink-update-watchdog.timer
[Unit]
Description=E-ink Update Watchdog Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

### 4. Staged Rollout System

**Rollout Strategy:**

1. **Canary (1-5 devices):** Test on designated canary devices first
2. **Beta (10%):** Roll out to beta channel devices
3. **Stable (100%):** Full rollout to all devices

**Rollout Control:**

```python
# Backend logic for determining if device should update
def should_device_update(device, release):
    # Check channel match
    if device.update_channel != release.channel:
        return False
    
    # Check rollout percentage
    if release.rollout_percent < 100:
        # Use device ID hash for deterministic selection
        device_hash = int(hashlib.sha256(str(device.id).encode()).hexdigest(), 16)
        device_percent = device_hash % 100
        if device_percent >= release.rollout_percent:
            return False
    
    # Check failure rate
    recent_failures = get_recent_update_failures(release.id, hours=1)
    if recent_failures > 10:  # More than 10 failures in last hour
        # Pause rollout automatically
        release.is_active = False
        send_alert("Update rollout paused due to high failure rate")
        return False
    
    return True
```

**Admin Dashboard Controls:**
- Create new release (upload artifact, set channel)
- Set rollout percentage (0%, 10%, 50%, 100%)
- Pause/resume rollout
- View rollout status (success rate, failure reasons)
- Emergency rollback (revert all devices to previous version)

### 5. Signing & Verification

**Ed25519 Signature System:**

**Key Generation (One-time, offline):**
```bash
# Generate Ed25519 keypair
python3 -c "
from nacl.signing import SigningKey
import base64

# Generate private key (keep offline!)
private_key = SigningKey.generate()
public_key = private_key.verify_key

print('Private key (KEEP SECRET):')
print(base64.b64encode(bytes(private_key)).decode())
print()
print('Public key (embed in device client):')
print(base64.b64encode(bytes(public_key)).decode())
"
```

**Release Signing (CI/CD):**
```python
# In release pipeline
from nacl.signing import SigningKey
import base64

# Load private key from secure storage (GitHub Secrets, etc.)
private_key_bytes = base64.b64decode(os.environ['RELEASE_SIGNING_KEY'])
signing_key = SigningKey(private_key_bytes)

# Sign the artifact
with open('gad-client-2.3.0.tar.gz', 'rb') as f:
    artifact_bytes = f.read()

signature = signing_key.sign(artifact_bytes).signature
signature_b64 = base64.b64encode(signature).decode()

print(f"Signature: {signature_b64}")
```

**Verification (Device):**
```python
# In device client
from nacl.signing import VerifyKey
import base64

# Public key embedded in client code
PUBLIC_KEY_B64 = "base64_encoded_public_key_here"
verify_key = VerifyKey(base64.b64decode(PUBLIC_KEY_B64))

def verify_update_signature(artifact_path, signature_b64):
    with open(artifact_path, 'rb') as f:
        artifact_bytes = f.read()
    
    signature = base64.b64decode(signature_b64)
    
    try:
        verify_key.verify(artifact_bytes, signature)
        return True
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False
```

---

## Implementation Phases

### Phase 0: Security Hygiene (Week 1)

**Objectives:**
- Remove committed secrets
- Rotate exposed credentials
- Enforce TLS everywhere
- Add rate limiting

**Tasks:**

1. **Secret Rotation:**
   - [ ] Rotate DATABASE_URL credentials
   - [ ] Rotate SUPABASE_KEY
   - [ ] Remove .env.production from git history
   - [ ] Move all secrets to Render environment variables
   - [ ] Update deployment documentation

2. **TLS Enforcement:**
   - [ ] Verify all API endpoints use HTTPS
   - [ ] Add HSTS headers
   - [ ] Disable HTTP fallback

3. **Rate Limiting:**
   - [ ] Add rate limiting to device endpoints (100 req/min per device)
   - [ ] Add stricter limits on auth endpoints (10 failures/hour)
   - [ ] Log rate limit violations

4. **Logging Security:**
   - [ ] Scrub Authorization headers from access logs
   - [ ] Never log device tokens in plaintext
   - [ ] Add structured logging for security events

**Acceptance Criteria:**
- No secrets in git repository
- All API traffic over HTTPS
- Rate limiting active on all device endpoints
- Security audit log in place

### Phase 1: Per-Device Credentials (Weeks 2-3)

**Objectives:**
- Implement API key authentication
- Add token management endpoints
- Update device client to use tokens
- Build admin UI for token management

**Backend Tasks:**

1. **Database Migration:**
   ```bash
   # Create migration file
   python backend/create_device_auth_migration.py
   ```
   - [ ] Add api_key_hash, token_version, last_auth_at columns
   - [ ] Create indexes
   - [ ] Test migration on staging database

2. **Authentication Middleware:**
   - [ ] Create `DeviceAuthMiddleware` class
   - [ ] Implement token validation logic
   - [ ] Add to device endpoints
   - [ ] Handle 401 responses gracefully

3. **Token Management Endpoints:**
   ```python
   POST /api/devices/{device_id}/token/rotate
   POST /api/devices/{device_id}/token/revoke
   GET /api/devices/{device_id}/token/status
   ```
   - [ ] Implement token generation (32-byte random)
   - [ ] Implement bcrypt hashing (cost 12)
   - [ ] Add audit logging
   - [ ] Add admin authorization checks

**Device Client Tasks:**

1. **Config File Updates:**
   - [ ] Add `device_token` field to config.json
   - [ ] Set file permissions to 600 (root:root)
   - [ ] Add config validation on startup

2. **Authentication Implementation:**
   - [ ] Add Authorization header to all requests
   - [ ] Handle 401 responses (log error, retry with backoff)
   - [ ] Never log token in plaintext
   - [ ] Add token refresh logic (if 401, check for new token)

3. **Backward Compatibility:**
   - [ ] Support devices without tokens (grace period)
   - [ ] Log warning for unauthenticated requests
   - [ ] Plan cutover date (2 weeks after deployment)

**Frontend Tasks:**

1. **Device Management UI:**
   - [ ] Add "Rotate Token" button to device detail page
   - [ ] Add "Revoke Token" button with confirmation
   - [ ] Show last authentication time
   - [ ] Show token version
   - [ ] Add bulk token rotation for multiple devices

2. **Security Dashboard:**
   - [ ] Show devices without tokens
   - [ ] Show devices with old token versions
   - [ ] Show recent authentication failures
   - [ ] Alert on suspicious activity

**Testing:**

- [ ] Unit tests for token generation/validation
- [ ] Integration tests for auth middleware
- [ ] End-to-end test: provision device → authenticate → make requests
- [ ] Load test: 1000 devices authenticating simultaneously
- [ ] Security test: attempt replay attacks, token reuse

**Rollout Plan:**

1. Deploy backend with auth middleware (permissive mode - log only)
2. Update device clients with token support (use existing device_id as fallback)
3. Generate tokens for all existing devices via migration script
4. Switch auth middleware to enforcement mode
5. Monitor for auth failures, fix issues
6. After 2 weeks, remove fallback support

**Acceptance Criteria:**
- All devices authenticate with unique tokens
- Token rotation works without device restart
- Admin can revoke compromised tokens
- Auth failures are logged and alerted
- No plaintext tokens in logs

### Phase 2: Provisioning System (Weeks 4-5)

**Objectives:**
- Implement provisioning code system
- Update install script to use codes
- Build admin UI for code generation
- Enable QR code workflow

**Backend Tasks:**

1. **Database Migration:**
   - [ ] Create provisioning_codes table
   - [ ] Add indexes
   - [ ] Test migration

2. **Provisioning Endpoints:**
   ```python
   POST /api/provisioning/codes/generate
   POST /api/devices/provision
   GET /api/provisioning/codes
   DELETE /api/provisioning/codes/{code}
   ```
   - [ ] Implement code generation (UUID-based)
   - [ ] Implement device provisioning logic
   - [ ] Add validation (code exists, not expired, not used)
   - [ ] Generate device token on successful provision
   - [ ] Send notification to course admin

3. **Audit Logging:**
   - [ ] Log code generation (who, when, for which course)
   - [ ] Log code usage (which device, when, from which IP)
   - [ ] Log code expiry/revocation

**Device Installation:**

1. **Update install-device.sh:**
   ```bash
   # New usage
   ./install-device.sh --provision-code PROV-abc123
   
   # Or interactive mode
   ./install-device.sh
   # Prompts: Enter provisioning code:
   ```
   - [ ] Add --provision-code parameter
   - [ ] Call /api/devices/provision endpoint
   - [ ] Receive and store device token
   - [ ] Write config.json with token (600 permissions)
   - [ ] Handle errors gracefully (invalid code, expired, etc.)

2. **Hardware Fingerprinting:**
   - [ ] Collect Pi serial number
   - [ ] Collect MAC address
   - [ ] Send to backend during provisioning
   - [ ] Store in device record for audit trail

**Frontend Tasks:**

1. **Provisioning Code Management:**
   - [ ] Add "Generate Provisioning Code" button
   - [ ] Form: device label, expiry (24h/48h/72h), notes
   - [ ] Display generated code (large, copyable)
   - [ ] Generate QR code (contains code + API URL)
   - [ ] List active/used/expired codes
   - [ ] Revoke code functionality

2. **Device Onboarding Workflow:**
   - [ ] Show pending devices (provisioned but not yet online)
   - [ ] Show device details after provisioning
   - [ ] Link to installation guide
   - [ ] Show provisioning history

**Documentation:**

- [ ] Update installation guide with provisioning workflow
- [ ] Create video tutorial for device provisioning
- [ ] Document troubleshooting steps
- [ ] Create runbook for common issues

**Testing:**

- [ ] Test code generation and expiry
- [ ] Test single-use enforcement
- [ ] Test device provisioning flow end-to-end
- [ ] Test error cases (expired code, already used, invalid code)
- [ ] Test QR code scanning workflow

**Acceptance Criteria:**
- Admin can generate provisioning code in dashboard
- Install script accepts code and provisions device automatically
- Device appears in dashboard after successful provisioning
- Expired/used codes are rejected
- QR code workflow works on mobile devices

### Phase 3: OTA Update System (Weeks 6-9)

**Objectives:**
- Implement A/B slot architecture
- Build update release system
- Implement download/verify/install logic
- Add automatic rollback
- Create admin UI for releases

**Backend Tasks:**

1. **Database Migration:**
   - [ ] Create update_releases table
   - [ ] Create device_update_status table
   - [ ] Add update_channel to devices
   - [ ] Add indexes

2. **Update Endpoints:**
   ```python
   GET /api/devices/{device_id}/updates/check
   POST /api/devices/{device_id}/updates/report
   POST /api/devices/{device_id}/updates/confirm
   POST /api/admin/releases
   PATCH /api/admin/releases/{id}/rollout
   ```
   - [ ] Implement update check logic (channel, rollout %)
   - [ ] Generate signed artifact URLs (S3/Supabase)
   - [ ] Track update status per device
   - [ ] Implement rollout controls
   - [ ] Add failure rate monitoring

3. **Artifact Storage:**
   - [ ] Set up S3 bucket or Supabase Storage
   - [ ] Configure signed URL generation (1-hour expiry)
   - [ ] Implement artifact upload endpoint
   - [ ] Add artifact cleanup (delete old versions)

4. **Signing Infrastructure:**
   - [ ] Generate Ed25519 keypair (offline)
   - [ ] Store private key in GitHub Secrets
   - [ ] Embed public key in device client
   - [ ] Create signing script for CI/CD

**Device Client Tasks:**

1. **A/B Slot Setup:**
   ```bash
   # Migration script for existing devices
   sudo mkdir -p /opt/gad/{app-A,app-B,update}
   sudo cp -r /home/pi/eink-device/* /opt/gad/app-A/
   sudo ln -s /opt/gad/app-A /opt/gad/current
   sudo chown -R pi:pi /opt/gad
   ```
   - [ ] Create directory structure
   - [ ] Move existing installation to app-A
   - [ ] Update systemd service to use /opt/gad/current
   - [ ] Test service restart

2. **Update Client Implementation:**
   ```python
   class UpdateManager:
       def check_for_updates(self)
       def download_update(self, url, sha256, signature)
       def verify_update(self, path, sha256, signature)
       def install_update(self, path)
       def swap_slots(self)
       def confirm_update(self)
       def rollback(self, reason)
   ```
   - [ ] Implement update check (every 6 hours)
   - [ ] Implement download with progress tracking
   - [ ] Implement SHA256 verification
   - [ ] Implement Ed25519 signature verification
   - [ ] Implement slot swapping
   - [ ] Implement health confirmation
   - [ ] Add jitter to avoid stampede (random 0-30 min delay)

3. **Rollback Watchdog:**
   ```python
   # Separate watchdog script
   def check_update_health():
       if update_in_progress():
           if not health_confirmed_within(5 minutes):
               rollback_to_previous_slot()
               report_rollback()
   ```
   - [ ] Create watchdog script
   - [ ] Add systemd timer (runs every 1 minute)
   - [ ] Implement rollback logic
   - [ ] Test rollback scenarios

4. **Preflight Checks:**
   - [ ] Verify Python version
   - [ ] Verify dependencies importable
   - [ ] Verify config file readable
   - [ ] Run --version command
   - [ ] Check disk space (need 2x artifact size)

**Frontend Tasks:**

1. **Release Management UI:**
   - [ ] Create release form (version, channel, artifact upload)
   - [ ] Show release list (version, channel, rollout %, status)
   - [ ] Rollout controls (set percentage, pause/resume)
   - [ ] View release details (success rate, failures)
   - [ ] Emergency rollback button

2. **Device Update Status:**
   - [ ] Show current version per device
   - [ ] Show update status (downloading, installing, etc.)
   - [ ] Show update history
   - [ ] Show rollback events
   - [ ] Filter devices by version/channel

3. **Rollout Dashboard:**
   - [ ] Show rollout progress (% complete)
   - [ ] Show success/failure rate
   - [ ] Show failure reasons (grouped)
   - [ ] Auto-pause indicator
   - [ ] Canary device status

**CI/CD Integration:**

1. **Build Pipeline:**
   ```yaml
   # .github/workflows/release.yml
   - name: Build artifact
     run: ./scripts/build-device-client.sh
   
   - name: Sign artifact
     run: ./scripts/sign-artifact.sh
     env:
       SIGNING_KEY: ${{ secrets.RELEASE_SIGNING_KEY }}
   
   - name: Upload to storage
     run: ./scripts/upload-artifact.sh
   
   - name: Create release
     run: ./scripts/create-release.sh
   ```
   - [ ] Create build script (package client + deps)
   - [ ] Create signing script
   - [ ] Create upload script
   - [ ] Create release creation script
   - [ ] Test full pipeline

**Testing:**

- [ ] Test update download and verification
- [ ] Test successful update (A → B)
- [ ] Test rollback on failure
- [ ] Test rollback on health timeout
- [ ] Test staged rollout (10%, 50%, 100%)
- [ ] Test auto-pause on high failure rate
- [ ] Test concurrent updates (multiple devices)
- [ ] Test network interruption during download
- [ ] Test disk full scenario
- [ ] Test signature verification failure

**Rollout Plan:**

1. Deploy backend update system
2. Update 1 canary device with A/B slots
3. Test manual update on canary
4. Test automatic rollback on canary
5. Roll out A/B slots to 10 devices
6. Test staged rollout (10% → 50% → 100%)
7. Roll out to all devices
8. Create first production release

**Acceptance Criteria:**
- Admin can create and publish releases
- Devices automatically check for updates
- Updates download, verify, and install without manual intervention
- Failed updates automatically rollback
- Rollout can be paused/resumed
- High failure rate triggers automatic pause
- Zero-downtime updates (service stays running)

### Phase 4: Hardening & Advanced Features (Weeks 10-12)

**Objectives:**
- Add HMAC request signing
- Implement canary automation
- Add alerting and monitoring
- Create operational runbooks
- Optional: Explore mTLS

**Security Enhancements:**

1. **HMAC Request Signing:**
   ```python
   # Request signature
   signature = HMAC_SHA256(
       secret=device_token,
       message=f"{method}|{path}|{body}|{timestamp}"
   )
   
   # Headers
   X-Device-ID: Device-POC-001
   X-Timestamp: 1699123456
   X-Signature: abc123...
   ```
   - [ ] Implement signing on device client
   - [ ] Implement verification on backend
   - [ ] Add timestamp validation (±5 min window)
   - [ ] Add replay attack prevention (nonce tracking)

2. **Authorization Policies:**
   - [ ] Device can only access its own data
   - [ ] Device cannot access other devices' commands
   - [ ] Device cannot modify its own configuration
   - [ ] Admin can access all devices in their course

**Operational Features:**

1. **Canary Automation:**
   - [ ] Auto-select canary devices (oldest, newest, different Pi models)
   - [ ] Auto-promote to beta after canary success (24h, 0 failures)
   - [ ] Auto-promote to stable after beta success (48h, <1% failure rate)
   - [ ] Auto-rollback on canary failure

2. **Alerting:**
   - [ ] Alert on high update failure rate (>5%)
   - [ ] Alert on rollback events
   - [ ] Alert on auth failures spike
   - [ ] Alert on device offline after update
   - [ ] Send to email, Slack, PagerDuty

3. **Monitoring Dashboard:**
   - [ ] Fleet health overview (online/offline, versions)
   - [ ] Update rollout status
   - [ ] Auth failure rate
   - [ ] API latency and error rates
   - [ ] Device health metrics

**Runbooks:**

1. **"Recover a Bricked Device":**
   - SSH access steps
   - Manual rollback procedure
   - Factory reset procedure
   - When to schedule site visit

2. **"Rotate Device Keys":**
   - Single device rotation
   - Bulk rotation procedure
   - Emergency revocation
   - Verify rotation success

3. **"Emergency Rollback of Release":**
   - Pause rollout
   - Revert all devices to previous version
   - Investigate failure root cause
   - Create hotfix release

4. **"Provision New Device":**
   - Generate provisioning code
   - Run install script
   - Verify device online
   - Troubleshooting common issues

**Documentation:**

- [ ] Architecture documentation
- [ ] API documentation (device endpoints)
- [ ] Security best practices
- [ ] Operational runbooks
- [ ] Troubleshooting guide
- [ ] FAQ for field technicians

**Testing:**

- [ ] Penetration testing (auth bypass, replay attacks)
- [ ] Load testing (1000 devices updating simultaneously)
- [ ] Chaos testing (network failures, disk full, etc.)
- [ ] Security audit (external firm)

**Acceptance Criteria:**
- HMAC signing prevents token leakage
- Canary automation works end-to-end
- Alerts fire correctly for failure scenarios
- Runbooks tested and validated
- Documentation complete and reviewed

---

## Rollback Plan

### If Phase 1 Fails (Auth Issues)

**Symptoms:**
- Devices unable to authenticate
- High 401 error rate
- Devices offline

**Rollback:**
1. Switch auth middleware to permissive mode (log only)
2. Allow device_id-only authentication temporarily
3. Investigate root cause
4. Fix and redeploy
5. Re-enable enforcement

**Prevention:**
- Gradual rollout (10% → 50% → 100%)
- Monitor auth success rate
- Keep fallback mechanism for 2 weeks

### If Phase 2 Fails (Provisioning Issues)

**Symptoms:**
- Devices cannot provision
- Codes not working
- Install script failures

**Rollback:**
1. Keep manual installation process available
2. Manually provision affected devices
3. Fix provisioning endpoint
4. Redeploy and test

**Prevention:**
- Test provisioning on staging environment
- Keep manual process documented
- Gradual rollout to new installations only

### If Phase 3 Fails (Update Issues)

**Symptoms:**
- Updates failing
- Devices bricked
- Rollback not working

**Rollback:**
1. Pause all rollouts immediately
2. SSH to affected devices
3. Manual rollback to previous slot
4. Investigate failure root cause
5. Fix and test on canary devices
6. Resume rollout

**Prevention:**
- Extensive testing on canary devices
- Automatic rollback on failure
- Keep previous version in inactive slot
- Monitor rollout closely (first 24h)

---

## Success Metrics

### Phase 1: Per-Device Credentials
- **Target:** 100% of devices authenticated with unique tokens
- **Metric:** Auth success rate > 99.9%
- **Metric:** Zero plaintext tokens in logs
- **Metric:** Token rotation works without device restart

### Phase 2: Provisioning System
- **Target:** 100% of new devices provisioned via codes
- **Metric:** Provisioning success rate > 95%
- **Metric:** Average provisioning time < 10 minutes
- **Metric:** Zero manual config file edits

### Phase 3: OTA Updates
- **Target:** 100% of devices support OTA updates
- **Metric:** Update success rate > 98%
- **Metric:** Rollback success rate > 99%
- **Metric:** Zero site visits for software updates
- **Metric:** Average update time < 5 minutes
- **Metric:** Zero downtime during updates

### Overall Impact
- **Target:** Reduce support costs by 70%
- **Target:** Enable weekly release cadence
- **Target:** Reduce time-to-fix from days to hours
- **Target:** Zero security incidents related to device auth

---

## Risk Assessment

### High Risk

**Risk:** Devices bricked during OTA update  
**Impact:** Site visit required, customer downtime  
**Mitigation:** Automatic rollback, extensive testing, staged rollout  
**Contingency:** SSH access, manual rollback procedure, field technician dispatch

**Risk:** Private signing key compromised  
**Impact:** Attacker can push malicious updates  
**Mitigation:** Offline key storage, key rotation capability, audit logging  
**Contingency:** Revoke key, generate new keypair, push emergency update with new public key

### Medium Risk

**Risk:** High update failure rate (>10%)  
**Impact:** Rollout paused, delayed feature deployment  
**Mitigation:** Canary testing, auto-pause on failures, thorough testing  
**Contingency:** Investigate failures, fix issues, resume rollout

**Risk:** Provisioning code leaked  
**Impact:** Unauthorized device provisioned  
**Mitigation:** Short expiry (24-48h), single-use codes, manual approval option  
**Contingency:** Revoke code, revoke device token, investigate breach

### Low Risk

**Risk:** Token rotation causes temporary auth failures  
**Impact:** Brief device offline period  
**Mitigation:** Graceful token refresh, retry logic  
**Contingency:** Manual token reset, device restart

---

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 0: Security Hygiene | 1 week | Secrets rotated, TLS enforced, rate limiting |
| Phase 1: Per-Device Credentials | 2 weeks | API key auth, token management, admin UI |
| Phase 2: Provisioning System | 2 weeks | Provisioning codes, updated install script, QR codes |
| Phase 3: OTA Updates | 4 weeks | A/B slots, update system, rollback, admin UI |
| Phase 4: Hardening | 3 weeks | HMAC signing, canary automation, runbooks |
| **Total** | **12 weeks** | **Secure provisioning & OTA updates** |

---

## Resource Requirements

### Development Team
- 1 Backend Engineer (full-time, 12 weeks)
- 1 Frontend Engineer (part-time, 6 weeks)
- 1 DevOps Engineer (part-time, 4 weeks)
- 1 QA Engineer (part-time, 4 weeks)

### Infrastructure
- S3 or Supabase Storage for artifacts (~$50/month)
- Additional Render resources for update endpoints (~$25/month)
- Test devices (5 Raspberry Pi units for testing)

### External Services
- Code signing infrastructure (GitHub Secrets - free)
- Monitoring/alerting (existing tools)
- Optional: Security audit firm ($5,000-$10,000)

---

## Appendix

### A. API Endpoint Reference

```
# Authentication
POST /api/devices/provision
POST /api/devices/{device_id}/token/rotate
POST /api/devices/{device_id}/token/revoke

# Provisioning
POST /api/provisioning/codes/generate
GET /api/provisioning/codes
DELETE /api/provisioning/codes/{code}

# Updates
GET /api/devices/{device_id}/updates/check
POST /api/devices/{device_id}/updates/report
POST /api/devices/{device_id}/updates/confirm

# Admin
POST /api/admin/releases
GET /api/admin/releases
PATCH /api/admin/releases/{id}/rollout
POST /api/admin/releases/{id}/rollback
```

### B. Configuration File Format

```json
{
  "device_id": "Device-POC-001",
  "device_token": "gad_dev_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "api_base_url": "https://golfadvertisingdisplays.onrender.com",
  "update_channel": "stable",
  "sync_interval": 900,
  "update_check_interval": 21600,
  "max_retries": 3,
  "timeout": 30,
  "connectivity": {
    "wifi_interface": "wlan0",
    "lte_interface": "ppp0",
    "failover_enabled": true
  },
  "power_management": {
    "solar_optimization": true,
    "battery_monitoring": true,
    "low_power_threshold": 20
  }
}
```

### C. Update Artifact Structure

```
gad-client-2.3.0.tar.gz
├── eink_device_client.py
├── uptime_tracker.py
├── update_manager.py
├── requirements.txt
├── version.json
└── venv/
    └── (pre-built virtualenv)
```

### D. Signature Verification Example

```python
from nacl.signing import VerifyKey
import base64

PUBLIC_KEY = "base64_encoded_public_key"

def verify_artifact(artifact_path, signature_b64):
    verify_key = VerifyKey(base64.b64decode(PUBLIC_KEY))
    
    with open(artifact_path, 'rb') as f:
        data = f.read()
    
    signature = base64.b64decode(signature_b64)
    
    try:
        verify_key.verify(data, signature)
        return True
    except:
        return False
```

### E. Rollback Watchdog Script

```python
#!/usr/bin/env python3
"""
Update Watchdog - Monitors update health and triggers rollback if needed
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

WATCHDOG_STATE = "/var/lib/gad/update_watchdog.json"
HEALTH_TIMEOUT_MINUTES = 5

def load_state():
    if not os.path.exists(WATCHDOG_STATE):
        return None
    with open(WATCHDOG_STATE) as f:
        return json.load(f)

def save_state(state):
    os.makedirs(os.path.dirname(WATCHDOG_STATE), exist_ok=True)
    with open(WATCHDOG_STATE, 'w') as f:
        json.dump(state, f)

def get_current_slot():
    current = os.readlink("/opt/gad/current")
    return os.path.basename(current)

def rollback_to_slot(slot):
    logging.info(f"Rolling back to {slot}")
    os.symlink(f"/opt/gad/{slot}", "/opt/gad/current.new")
    os.rename("/opt/gad/current.new", "/opt/gad/current")
    os.system("sudo systemctl restart eink-device.service")

def main():
    state = load_state()
    
    if not state or state.get("status") != "awaiting_confirmation":
        return
    
    update_time = datetime.fromisoformat(state["update_time"])
    timeout = update_time + timedelta(minutes=HEALTH_TIMEOUT_MINUTES)
    
    if datetime.now() > timeout:
        logging.warning("Update health check timeout - triggering rollback")
        previous_slot = state["previous_slot"]
        rollback_to_slot(previous_slot)
        
        state["status"] = "rolled_back"
        state["rollback_time"] = datetime.now().isoformat()
        state["rollback_reason"] = "Health check timeout"
        save_state(state)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
```

---

## Conclusion

This deployment plan provides a comprehensive roadmap for implementing secure device provisioning and OTA updates for the Golf CMS e-ink device fleet. The phased approach minimizes risk while delivering incremental value. The A/B slot architecture with automatic rollback ensures zero-downtime updates and rapid recovery from failures.

**Next Steps:**
1. Review and approve this deployment plan
2. Allocate development resources
3. Begin Phase 0: Security Hygiene
4. Set up project tracking and milestones
5. Schedule weekly progress reviews

**Questions or Concerns:**
- Contact the development team for technical clarification
- Escalate blockers to project management
- Security concerns should be raised immediately

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-04  
**Author:** Devin (AI Software Engineer)  
**Reviewers:** TBD  
**Approval:** Pending
