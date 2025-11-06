# Security Best Practices - Trading System

## API Key Management

### 1. Key Rotation Policy

**Recommended Schedule**:
- Rotate Bybit API keys every 90 days
- Rotate Gmail App Password every 180 days
- Immediate rotation if breach suspected

### 2. Secure Storage

**Current Implementation**:
- API keys stored in `.env` file
- `.env` excluded from git via `.gitignore`
- Database credentials in environment variables

**Best Practices**:
```bash
# Set restrictive permissions on .env file
chmod 600 .env

# Verify .env is not tracked by git
git check-ignore .env
# Should output: .env
```

### 3. API Key Permissions

**Bybit API Configuration**:
- ✅ **Enable**: Read, Trade
- ❌ **Disable**: Withdraw, Transfer, SubAccount
- ✅ **IP Whitelist**: Add your server IP for production
- ✅ **Use Testnet**: For development/testing

**How to Rotate Bybit Keys**:
1. Log in to Bybit.com
2. Go to Account & Security → API Management
3. Create new API key with appropriate permissions
4. Update `.env` file:
   ```
   BYBIT_API_KEY=your_new_key
   BYBIT_API_SECRET=your_new_secret
   ```
5. Restart trading system: `./start_trading.sh`
6. Delete old API key from Bybit after confirming new key works

### 4. Gmail App Password Rotation

**How to Rotate**:
1. Go to https://myaccount.google.com/security
2. Navigate to App Passwords
3. Revoke old password
4. Generate new 16-character password
5. Update database:
   ```bash
   venv/bin/python scripts/update_email_password.py
   ```
6. Restart meta agents to pick up new password

## Database Security

### 1. Access Control

**Current Setup**:
- PostgreSQL user: `trader`
- Database: `trading_db`
- Access: localhost only

**Hardening**:
```sql
-- Verify no remote access
SELECT * FROM pg_hba_conf WHERE type != 'local' AND address != '127.0.0.1/32';

-- Rotate database password quarterly
ALTER USER trader WITH PASSWORD 'new_secure_password';
```

### 2. Enable Query Logging

Monitor database access for suspicious activity:

```bash
# Edit PostgreSQL config
# Location: /opt/homebrew/var/postgresql@14/postgresql.conf

log_statement = 'mod'  # Log all INSERT/UPDATE/DELETE
log_connections = on
log_disconnections = on
log_duration = on

# Restart PostgreSQL
brew services restart postgresql@14
```

**Review Logs**:
```bash
# View recent database activity
tail -100 /opt/homebrew/var/log/postgresql@14.log
```

### 3. Backup Encryption

**Current Backup Strategy**:
```bash
# Database backup script
./scripts/backup_database.sh

# Backups stored in: ./backups/
```

**Encrypt Backups**:
```bash
# Encrypt backup with GPG
gpg --symmetric --cipher-algo AES256 backup_file.sql

# Decrypt when needed
gpg backup_file.sql.gpg
```

## Network Security

### 1. Firewall Configuration

**For Production Servers**:
```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 3000/tcp # Grafana (optional, or use SSH tunnel)
sudo ufw enable
```

### 2. SSH Hardening

**If Running on Remote Server**:
```bash
# Disable password authentication
# Edit /etc/ssh/sshd_config
PasswordAuthentication no
PubkeyAuthentication yes

# Use SSH keys only
# Disable root login
PermitRootLogin no
```

### 3. HTTPS for Grafana

**Production Setup**:
- Use reverse proxy (nginx/caddy)
- Enable SSL/TLS certificates
- Use Let's Encrypt for free certificates

## Application Security

### 1. Paper Trading Mode

**CRITICAL**: System is configured for paper trading only:
```python
# In config or environment
TRADING_MODE=paper  # NEVER set to 'live' without review
```

**Before Going Live**:
- [ ] Complete at least 30 days of paper trading
- [ ] Verify profitability over multiple market conditions
- [ ] Review all agent performance metrics
- [ ] Test with minimal capital first ($100-$500)
- [ ] Set up monitoring alerts
- [ ] Have kill switch ready

### 2. Rate Limiting

**Bybit API Limits**:
- 120 requests per minute for most endpoints
- System respects rate limits via `time.sleep()` delays

**Monitor Rate Limits**:
```sql
-- Check request frequency
SELECT
    DATE_TRUNC('minute', created_at) as minute,
    COUNT(*) as requests
FROM api_requests
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY minute
ORDER BY minute DESC;
```

### 3. Error Handling

**Security-Related Errors**:
- API key failures → Stop trading immediately
- Database connection loss → Halt new trades
- Abnormal P&L changes → Alert + pause

**Monitoring**:
```bash
# Watch for security errors
tail -f logs/orchestrator.log | grep -i "error\|fail\|security"
```

## Monitoring & Alerts

### 1. Set Up Alerts

**Critical Events to Monitor**:
- API authentication failures
- Unexpected trades outside normal hours
- P&L drops > 5% in 1 hour
- Database connection failures
- System metrics anomalies

**Implementation** (Future):
```python
# Add to project_manager.py
def check_security_alerts():
    # Monitor failed API calls
    # Check for unusual trading patterns
    # Alert on large losses
    pass
```

### 2. Audit Trail

**Current Logging**:
- All trades: `paper_orders` table
- Agent decisions: `agent_signals` table
- System events: `agent_work_log` table

**Review Regularly**:
```sql
-- Unusual trading hours
SELECT * FROM paper_orders
WHERE EXTRACT(HOUR FROM created_at) NOT BETWEEN 0 AND 23;

-- Large orders
SELECT * FROM paper_orders
WHERE ABS(quantity * price) > 1000;
```

## Incident Response

### 1. Emergency Procedures

**If System Compromised**:
1. **IMMEDIATELY** stop all services:
   ```bash
   pkill -f orchestrator
   pkill -f meta_orchestrator
   ```

2. Rotate all credentials:
   - Bybit API keys
   - Database password
   - Gmail App Password

3. Review logs for unauthorized access:
   ```bash
   grep -i "unauthorized\|failed\|error" logs/*.log
   ```

4. Check for unauthorized trades:
   ```sql
   SELECT * FROM paper_orders
   WHERE created_at > 'suspicious_time'
   ORDER BY created_at DESC;
   ```

### 2. Recovery Checklist

- [ ] Identify breach vector
- [ ] Rotate all credentials
- [ ] Review and patch vulnerabilities
- [ ] Verify database integrity
- [ ] Check for unauthorized code changes (`git diff`)
- [ ] Resume operations only after security review

## Compliance

### 1. Data Retention

**Current Policy**:
- Trade data: Retained indefinitely
- Logs: Rotate after 30 days
- Backups: Keep for 90 days

### 2. Privacy

- No personal data collected
- API keys never logged
- Email sent only to authorized recipient (brad@skylie.com)

## Security Checklist

**Monthly**:
- [ ] Review database access logs
- [ ] Check for failed API authentication attempts
- [ ] Verify firewall rules (if applicable)
- [ ] Test backup restoration

**Quarterly**:
- [ ] Rotate API keys
- [ ] Update dependencies: `pip list --outdated`
- [ ] Review and update this document
- [ ] Security audit of new code

**Annually**:
- [ ] Full security audit
- [ ] Penetration testing (if in production)
- [ ] Review disaster recovery plan

## Contact

**Security Issues**:
Report to: brad@skylie.com

**Emergency Contact**:
For critical security incidents, contact immediately

---

**Last Updated**: November 6, 2025
**Next Review**: December 6, 2025
