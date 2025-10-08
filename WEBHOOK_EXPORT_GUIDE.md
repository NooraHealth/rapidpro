# Webhook Logs Export Guide

This guide explains how to export webhook logs from PostgreSQL for analysis and debugging.

## Quick Start

Export failed webhook logs from October 2025:

```bash
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/failed_webhooks.csv \
    --errors-only \
    --start-date "2025-10-01" \
    --include-full-request \
    --include-full-response \
    --verbose

# Copy to host machine
docker compose cp rapidpro:/tmp/failed_webhooks.csv ./rapidpro-source/temp_exports/
```

## Available Filters

### Required Options
- `--output` - Output file path (e.g., `logs.csv` or `logs.json`)

### Format Options
- `--format` - Output format: `csv` or `json` (defaults to file extension)

### Data Filters
- `--org-id` - Filter by organization ID
- `--log-type` - Filter by log type (see types below, defaults to `webhook_called`)
- `--start-date` - Filter logs from this date (ISO format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`)
- `--end-date` - Filter logs until this date (ISO format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`)
- `--errors-only` - Only export logs with HTTP errors (status code >= 400)
- `--status-code` - Filter by specific HTTP status code (e.g., 404, 500)
- `--url-contains` - Filter logs where URL contains this string
- `--min-request-time` - Filter logs with request time greater than this value (in milliseconds)
- `--max-request-time` - Filter logs with request time less than this value (in milliseconds)

### Processing Options
- `--limit` - Maximum number of logs to export
- `--include-full-request` - Include full HTTP request body in output
- `--include-full-response` - Include full HTTP response body in output
- `--verbose` - Show progress information

## Available Log Types

1. **`webhook_called`** (default) - Webhooks called from flows
2. `airtime_transferred` - Airtime transfer requests
3. `whatsapp_templates_synced` - WhatsApp template sync operations
4. `whatsapp_tokens_synced` - WhatsApp token sync operations
5. `whatsapp_contacts_refreshed` - WhatsApp contact refresh operations
6. `whataspp_check_health` - WhatsApp health check requests

## CSV Output Fields

The CSV export includes the following fields:

- `id` - Database ID
- `org_id` - Organization ID
- `log_type` - Type of log (webhook_called, etc.)
- `url` - The URL that was called
- `status_code` - HTTP response status code
- `is_error` - Boolean (true if status >= 400)
- `request_time` - Duration in milliseconds
- `num_retries` - Number of retry attempts
- `created_on` - ISO timestamp when log was created

With `--include-full-request` and `--include-full-response`:
- `request` - Full HTTP request body
- `response` - Full HTTP response body

## Usage Examples

### 1. Export all failed webhooks from October
```bash
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/failed_october.csv \
    --errors-only \
    --start-date "2025-10-01" \
    --verbose && \
docker compose cp rapidpro:/tmp/failed_october.csv ./rapidpro-source/temp_exports/
```

### 2. Export 500 errors with full request/response
```bash
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/500_errors.csv \
    --status-code 500 \
    --include-full-request \
    --include-full-response \
    --verbose && \
docker compose cp rapidpro:/tmp/500_errors.csv ./rapidpro-source/temp_exports/
```

### 3. Export slow webhooks (>10 seconds)
```bash
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/slow_webhooks.csv \
    --min-request-time 10000 \
    --verbose && \
docker compose cp rapidpro:/tmp/slow_webhooks.csv ./rapidpro-source/temp_exports/
```

### 4. Export webhooks to a specific endpoint
```bash
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/api_webhooks.json \
    --url-contains "api.example.com" \
    --start-date "2025-10-01" \
    --verbose && \
docker compose cp rapidpro:/tmp/api_webhooks.json ./rapidpro-source/temp_exports/
```

### 5. Export recent webhooks for specific org
```bash
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/org1_webhooks.csv \
    --org-id 1 \
    --start-date "2025-10-08" \
    --verbose && \
docker compose cp rapidpro:/tmp/org1_webhooks.csv ./rapidpro-source/temp_exports/
```

### 6. Quick sample for testing
```bash
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/sample.json \
    --limit 10 \
    --include-full-request \
    --include-full-response \
    --verbose && \
docker compose cp rapidpro:/tmp/sample.json ./rapidpro-source/temp_exports/
```

### 7. Export timeouts and connection errors
```bash
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/timeouts.csv \
    --status-code 0 \
    --verbose && \
docker compose cp rapidpro:/tmp/timeouts.csv ./rapidpro-source/temp_exports/
```
*Note: status_code 0 typically indicates connection timeout or network failure*

### 8. Export specific date range with errors
```bash
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/week_errors.csv \
    --start-date "2025-10-01T00:00:00" \
    --end-date "2025-10-07T23:59:59" \
    --errors-only \
    --include-full-response \
    --verbose && \
docker compose cp rapidpro:/tmp/week_errors.csv ./rapidpro-source/temp_exports/
```

## Analyzing Exported Data

### Using CSV with Excel/Google Sheets
Simply open the CSV file in Excel or Google Sheets for quick analysis and filtering.

### Using CSV with Python (pandas)
```python
import pandas as pd
import json

# Read the CSV
df = pd.read_csv('failed_webhooks.csv')

# Basic statistics
print(f"Total logs: {len(df)}")
print(f"Failed logs: {df['is_error'].sum()}")
print(f"Success rate: {(1 - df['is_error'].mean()) * 100:.1f}%")
print(f"Average request time: {df['request_time'].mean():.2f}ms")

# Group by status code
print("\nStatus Code Distribution:")
print(df['status_code'].value_counts())

# Find slowest requests
print("\nSlowest 10 requests:")
print(df.nlargest(10, 'request_time')[['url', 'status_code', 'request_time']])

# Analyze URLs
print("\nMost problematic URLs:")
error_df = df[df['is_error'] == True]
print(error_df['url'].value_counts().head(10))

# Parse request/response if included
if 'request' in df.columns:
    # Example: Find all POST requests
    post_requests = df[df['request'].str.contains('POST', na=False)]
    print(f"\nPOST requests: {len(post_requests)}")

# Time-based analysis
df['created_on'] = pd.to_datetime(df['created_on'])
df['hour'] = df['created_on'].dt.hour
print("\nErrors by hour of day:")
print(df[df['is_error'] == True].groupby('hour').size())
```

### Using JSON with jq
```bash
# Count logs by status code
cat webhooks.json | jq 'group_by(.status_code) | map({status: .[0].status_code, count: length})'

# Find all 500 errors
cat webhooks.json | jq '[.[] | select(.status_code >= 500)]'

# Calculate average request time
cat webhooks.json | jq '[.[].request_time] | add / length'

# Find unique URLs
cat webhooks.json | jq '[.[].url] | unique'

# Get slowest 5 requests
cat webhooks.json | jq 'sort_by(.request_time) | reverse | .[0:5]'

# Count errors by URL
cat webhooks.json | jq '[.[] | select(.is_error == true)] | group_by(.url) | map({url: .[0].url, count: length}) | sort_by(.count) | reverse'
```

## Common Debugging Scenarios

### 1. Why are my webhooks failing?
```bash
# Export with full request/response to see error messages
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/failures.csv \
    --errors-only \
    --start-date "2025-10-01" \
    --include-full-response \
    --limit 100 \
    --verbose && \
docker compose cp rapidpro:/tmp/failures.csv ./rapidpro-source/temp_exports/
```

Then open the CSV and look at the `response` column for error messages.

### 2. Which webhooks are timing out?
```bash
# Long request times often indicate timeouts
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/slow.csv \
    --min-request-time 30000 \
    --verbose && \
docker compose cp rapidpro:/tmp/slow.csv ./rapidpro-source/temp_exports/
```

### 3. Is a specific endpoint causing problems?
```bash
# Filter by URL pattern
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/endpoint.csv \
    --url-contains "problematic-api.com" \
    --errors-only \
    --verbose && \
docker compose cp rapidpro:/tmp/endpoint.csv ./rapidpro-source/temp_exports/
```

### 4. What's the error rate over time?
```bash
# Export all logs for a period and analyze with pandas
docker compose exec rapidpro poetry run python manage.py export_webhook_logs \
    --output /tmp/weekly.json \
    --start-date "2025-10-01" \
    --end-date "2025-10-07" \
    --verbose && \
docker compose cp rapidpro:/tmp/weekly.json ./rapidpro-source/temp_exports/
```

## Performance Tips

1. **Use date filters**: Always filter by date range to limit the result set
2. **Avoid full request/response unless needed**: These fields are large and slow down exports
3. **Use --limit for testing**: Test your filters with `--limit 10` first
4. **Export to JSON for complex analysis**: JSON preserves structure better than CSV
5. **Use --verbose**: Monitor progress for large exports

## Troubleshooting

### Command not found
Make sure you've rebuilt the rapidpro container after adding the command:
```bash
docker compose up -d --build rapidpro
```

### Timezone warnings
The command automatically handles timezones. If you see warnings, they should be harmless.

### Large files
For very large exports (>100K logs):
- Use `--limit` to split into smaller batches
- Don't use `--include-full-request` and `--include-full-response` unless necessary
- Export to JSON and process incrementally

### Out of memory
If exports crash with large datasets:
- Reduce the date range
- Use `--limit` to export in batches
- Remove `--include-full-request` and `--include-full-response` flags

## Quick Reference

| Filter | Example | Use Case |
|--------|---------|----------|
| `--errors-only` | `--errors-only` | Only failed requests |
| `--status-code` | `--status-code 404` | Specific HTTP errors |
| `--url-contains` | `--url-contains "api.example.com"` | Specific endpoints |
| `--start-date` | `--start-date "2025-10-01"` | Recent logs only |
| `--min-request-time` | `--min-request-time 5000` | Slow requests (>5s) |
| `--org-id` | `--org-id 1` | Specific organization |
| `--limit` | `--limit 100` | Quick sampling |

## Differences from Channel Logs Export

**Webhook Logs** (`export_webhook_logs`):
- ✅ Stored in **PostgreSQL**
- ✅ Faster queries with database indexes
- ✅ Flow webhook calls, airtime transfers, WhatsApp API calls
- ✅ Use for debugging **flow integrations**

**Channel Logs** (`export_channel_logs`):
- ✅ Stored in **DynamoDB**
- ✅ Message sends/receives, IVR logs
- ✅ Use for debugging **messaging channels**

## Need More Help?

- Check the full logs in the database: `temba.request_logs_httplog` table
- Use `--verbose` flag to see what the command is doing
- Start with `--limit 10` to test your filters before full export
- Combine with other tools like `grep`, `jq`, or pandas for analysis

