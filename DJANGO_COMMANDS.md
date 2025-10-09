# RapidPro Django Management Commands

Quick reference for all custom Django management commands. Run commands inside the Docker container:

```bash
docker compose exec rapidpro poetry run python manage.py <command> [OPTIONS]
```

---

## Export & Logging Commands

### export_webhook_logs
Export webhook logs from PostgreSQL (flow webhooks, airtime transfers, WhatsApp API calls).

**Common Usage:**
```bash
# Export failed webhooks from October
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/failed_webhooks.csv \
    --errors-only \
    --start-date "2025-10-01" \
    --include-full-request \
    --include-full-response \
    --verbose

# Copy to host
docker compose cp rapidpro:/tmp/failed_webhooks.csv ./temp_exports/
```

**Key Options:**
- `--output` (required) - Output file path (`.csv` or `.json`)
- `--org-id` - Filter by organization
- `--log-type` - Log type: `webhook_called` (default), `airtime_transferred`, `whatsapp_templates_synced`, etc.
- `--start-date` / `--end-date` - Date range (ISO format: `YYYY-MM-DD`)
- `--errors-only` - Only logs with HTTP errors (status >= 400)
- `--status-code` - Filter by specific HTTP status code
- `--url-contains` - Filter URLs containing string
- `--min-request-time` / `--max-request-time` - Filter by duration (milliseconds)
- `--limit` - Maximum number of logs
- `--include-full-request` / `--include-full-response` - Include full HTTP bodies
- `--verbose` - Show progress

**More Examples:**
```bash
# Export 500 errors with full details
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/500_errors.csv --status-code 500 \
    --include-full-response --verbose

# Export slow webhooks (>10 seconds)
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/slow.csv --min-request-time 10000 --verbose

# Export to specific endpoint
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/api_logs.json --url-contains "api.example.com" --verbose
```

---

### export_channel_logs
Export channel logs from DynamoDB (message sends/receives, IVR logs).

**Common Usage:**
```bash
# Export all logs for a channel
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/channel_logs.csv \
    --channel-uuid "12345678-1234-1234-1234-123456789abc" \
    --verbose
```

**Key Options:**
- `--output` (required) - Output file path (`.csv` or `.json`)
- `--org-id` - Filter by organization
- `--channel-uuid` - Filter by channel UUID
- `--log-type` - Log type: `msg_send`, `msg_receive`, `msg_status`, `ivr_start`, `ivr_callback`, etc.
- `--start-date` / `--end-date` - Date range (ISO format)
- `--errors-only` - Only logs with errors
- `--min-elapsed-ms` / `--max-elapsed-ms` - Filter by duration (milliseconds)
- `--limit` - Maximum number of logs
- `--include-http-logs` - Include full HTTP request/response
- `--no-redact` - Include sensitive data (use with caution!)
- `--verbose` - Show progress

**More Examples:**
```bash
# Export only error logs from last 7 days
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/errors.json --errors-only --start-date "2025-10-01" --verbose

# Export message send logs with HTTP details
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/msg_send.csv --log-type msg_send \
    --include-http-logs --limit 1000 --verbose

# Export slow requests (>5 seconds)
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/slow.csv --min-elapsed-ms 5000 --verbose
```

---

### webhook_stats
Generate statistics for webhook calls from PostgreSQL logs.

**Common Usage:**
```bash
# Summary statistics
docker compose exec rapidpro poetry run python manage.py webhook_stats summary

# Summary with options
docker compose exec rapidpro poetry run python manage.py webhook_stats summary \
    --key host_path_0 --sort timeouts --max-age 60

# Slowest webhooks
docker compose exec rapidpro poetry run python manage.py webhook_stats slowest --max-age 60
```

**Options:**
- `summary` - Aggregate statistics by URL
  - `--key` - Aggregation key: `host`, `host_path`, `host_path_0` (default)
  - `--sort` - Sort by: `alpha`, `timeouts` (default)
  - `--max-age` - Max age in minutes (0 = all)
- `slowest` - List slowest webhook calls
  - `--max-age` - Max age in minutes (0 = all)

---

## WhatsApp Commands

### create_whatsapp_channel
Create a new WhatsApp Legacy channel.

**Common Usage:**
```bash
docker compose exec rapidpro poetry run python manage.py create_whatsapp_channel \
    --org-id 1 \
    --number "+1234567890" \
    --verified-name "Your Business" \
    --phone-number-id "123456789" \
    --waba-id "987654321" \
    --business-id "555666777" \
    --auth-token "YOUR_AUTH_TOKEN" \
    --base-url "https://whatsapp.turn.io" \
    --verbose
```

**Required Options:**
- `--org-id` - Organization ID
- `--number` - WhatsApp phone number (e.g., `+1234567890`)
- `--verified-name` - Verified business name
- `--phone-number-id` - Phone number ID from Meta API
- `--waba-id` - WhatsApp Business Account ID
- `--business-id` - Facebook Business ID
- `--auth-token` - Authentication token

**Optional:**
- `--base-url` - API base URL (default: `https://whatsapp.turn.io`)
- `--username` - API username (default: `test_user`)
- `--password` - API password (default: `test_pass`)
- `--namespace` - Template namespace (default: `test_namespace`)
- `--name` - Custom channel name (auto-generated if omitted)
- `--dry-run` - Preview without creating
- `--verbose` - Show detailed output

---

### fetch_whatsapp_templates
Fetch WhatsApp templates from Meta API and sync to RapidPro.

**Common Usage:**
```bash
docker compose exec rapidpro poetry run python manage.py fetch_whatsapp_templates \
    --waba-id 123456789012345 \
    --access-token EAABwzLixnjYBOZCxxx \
    --channel-id 5 \
    --verbose
```

**Required Options:**
- `--waba-id` - WhatsApp Business Account ID
- `--access-token` - System User Access Token
- `--channel-id` - WhatsApp channel ID to use for sync

**Optional:**
- `--dry-run` - Fetch but don't insert into database
- `--verbose` - Show detailed template information

---

### reactivate_fb_channels
Reactivate Facebook channel webhooks.

**Usage:**
```bash
docker compose exec rapidpro poetry run python manage.py reactivate_fb_channels
```

Automatically finds all active Facebook channels and reactivates their webhooks.

---

## Archive Commands

### search_archives
Search through S3 archives (messages or flow runs).

**Common Usage:**
```bash
# Search message archives
docker compose exec rapidpro poetry run python manage.py search_archives \
    1 msg --limit 10

# Search with SQL filter
docker compose exec rapidpro poetry run python manage.py search_archives \
    1 flowrun --where "s.flow.name = 'Registration'" --limit 5

# Raw JSONL output
docker compose exec rapidpro poetry run python manage.py search_archives \
    1 msg --limit 100 --raw
```

**Arguments:**
- `org_id` (required) - Organization ID
- `archive_type` (required) - `msg` or `flowrun`

**Options:**
- `--where` - S3 Select SQL expression
- `--limit` - Max records to return (default: 10)
- `--raw` - Output unformatted JSONL

---

### audit_archives
Audit archive integrity and fix issues.

**Common Usage:**
```bash
# Audit message archives
docker compose exec rapidpro poetry run python manage.py audit_archives 1 msg

# Audit and fix flowrun archives
docker compose exec rapidpro poetry run python manage.py audit_archives 1 flowrun --fix

# Check run counts
docker compose exec rapidpro poetry run python manage.py audit_archives 1 flowrun --run-counts
```

**Arguments:**
- `org_id` (required) - Organization ID
- `archive_type` (required) - `msg` or `flowrun`

**Options:**
- `--fix` - Fix archives with records that are too long
- `--run-counts` - Check run counts for flows

---

## Flow Commands

### inspect_flows
Inspect all flows for validation issues.

**Usage:**
```bash
docker compose exec rapidpro poetry run python manage.py inspect_flows
```

Validates all active flows and updates their `has_issues` flag. Shows:
- Number of flows inspected
- Number updated
- Number with invalid definitions

---

### migrate_flows
Migrate flows to the current spec version.

**Common Usage:**
```bash
# Migrate all flows (with confirmation prompt)
docker compose exec rapidpro poetry run python manage.py migrate_flows

# With custom delay between migrations
docker compose exec rapidpro poetry run python manage.py migrate_flows --delay 200
```

**Options:**
- `--delay` - Delay in milliseconds between migrations (default: 100)

Migrates all flows that are not on the current spec version. Includes safety prompt.

---

## Campaign Commands

### rebuild_missing_campaign_fires
Rebuild missing campaign event fires for contacts.

**Common Usage:**
```bash
# Fix a specific contact
docker compose exec rapidpro poetry run python manage.py rebuild_missing_campaign_fires \
    --contact "12345678-1234-1234-1234-123456789abc"

# Scan all contacts
docker compose exec rapidpro poetry run python manage.py rebuild_missing_campaign_fires \
    --all-contacts --batch-size 1000

# Scan all contacts in an org
docker compose exec rapidpro poetry run python manage.py rebuild_missing_campaign_fires \
    --all-contacts --org 1

# Recompute all campaign events
docker compose exec rapidpro poetry run python manage.py rebuild_missing_campaign_fires \
    --recompute-all-events

# Dry run to see what would be fixed
docker compose exec rapidpro poetry run python manage.py rebuild_missing_campaign_fires \
    --all-contacts --dry-run
```

**Options:**
- `--contact` - Contact UUID to check and fix
- `--org` - Limit to org ID or UUID
- `--all-contacts` - Scan all contacts in scope
- `--batch-size` - Batch size for all-contacts scan (default: 1000)
- `--recompute-all-events` - Recompute all active campaign events
- `--dry-run` - Report only, don't schedule

**Note:** Provide one of `--contact`, `--all-contacts`, or `--recompute-all-events`.

---

## Debugging Commands

### msg_console
Interactive console for sending/receiving messages (requires Courier).

**Common Usage:**
```bash
# Default (org 1, tel:+250788123123)
docker compose exec rapidpro poetry run python manage.py msg_console

# Specific org and URN
docker compose exec rapidpro poetry run python manage.py msg_console \
    --org 1 --urn "tel:+1234567890"
```

**Options:**
- `--org` - Organization ID or name (default: 1)
- `--urn` - URN to send from (default: `tel:+250788123123`)

**Requirements:**
- Courier must be running at `http://localhost:8080`
- Use Ctrl+C to quit

Type messages interactively and see responses in real-time.

---

## Quick Reference

### Finding IDs

**Organization ID:**
```bash
docker compose exec rapidpro poetry run python manage.py shell
>>> from temba.orgs.models import Org
>>> Org.objects.all().values('id', 'name')
```

**Channel UUID/ID:**
```bash
docker compose exec rapidpro poetry run python manage.py shell
>>> from temba.channels.models import Channel
>>> Channel.objects.filter(is_active=True).values('id', 'uuid', 'name', 'channel_type')
```

**Contact UUID:**
```bash
docker compose exec rapidpro poetry run python manage.py shell
>>> from temba.contacts.models import Contact
>>> Contact.objects.filter(name__icontains="john").values('uuid', 'name')
```

---

## Tips

1. **Always use --verbose** for long-running exports to see progress
2. **Test with --limit** first before full exports
3. **Use --dry-run** when available to preview changes
4. **Copy files from container** using `docker compose cp rapidpro:/tmp/file.csv ./`
5. **Filter by date** to reduce dataset size and improve performance
6. **Check container logs** if commands fail: `docker compose logs rapidpro`

---

## Storage Locations

- **Webhook Logs**: PostgreSQL (`temba.request_logs_httplog` table)
- **Channel Logs**: DynamoDB (`TembaMain` table)
- **Archives**: S3 (messages and flow runs)

---

## Documentation Files

- Full webhook export guide: `WEBHOOK_EXPORT_GUIDE.md`
- Full DynamoDB export guide: `DYNAMO_EXPORT_GUIDE.md`
- WhatsApp template sync guide: `WHATSAPP_TEMPLATE_SYNC.md`

