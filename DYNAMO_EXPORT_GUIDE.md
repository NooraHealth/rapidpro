# DynamoDB Channel Logs Export Guide

This guide explains how to export channel logs from DynamoDB for analysis and debugging.

## Available Filters

The `export_channel_logs` management command supports the following filters:

### Required Options
- `--output` - Output file path (e.g., `logs.csv` or `logs.json`)

### Format Options
- `--format` - Output format: `csv` or `json` (defaults to file extension)

### Data Filters
- `--org-id` - Filter by organization ID
- `--channel-uuid` - Filter by channel UUID (also sets org-id automatically)
- `--log-type` - Filter by log type (see available types below)
- `--start-date` - Filter logs from this date (ISO format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`)
- `--end-date` - Filter logs until this date (ISO format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`)
- `--errors-only` - Only export logs with errors
- `--min-elapsed-ms` - Filter logs with elapsed time greater than this value (in milliseconds)
- `--max-elapsed-ms` - Filter logs with elapsed time less than this value (in milliseconds)

### Processing Options
- `--limit` - Maximum number of logs to export
- `--include-http-logs` - Include full HTTP request/response logs in output
- `--no-redact` - Include sensitive data (use with caution!)
- `--verbose` - Show progress information

## Available Log Types

You can filter by the following log types:

1. `unknown` - Other Event
2. `msg_send` - Message Send
3. `msg_status` - Message Status
4. `msg_receive` - Message Receive
5. `event_receive` - Event Receive
6. `multi_receive` - Events Receive
7. `ivr_start` - IVR Start
8. `ivr_incoming` - IVR Incoming
9. `ivr_callback` - IVR Callback
10. `ivr_status` - IVR Status
11. `ivr_hangup` - IVR Hangup
12. `attachment_fetch` - Attachment Fetch
13. `token_refresh` - Token Refresh
14. `page_subscribe` - Page Subscribe
15. `webhook_verify` - Webhook Verify

## CSV Output Fields

The CSV export includes the following fields:

- `log_uuid` - Unique log identifier
- `channel_uuid` - Channel UUID
- `org_id` - Organization ID
- `type` - Log type
- `is_error` - Boolean indicating if this is an error
- `error_count` - Number of errors in this log
- `elapsed_ms` - Duration in milliseconds
- `created_on` - ISO timestamp when log was created
- `http_log_count` - Number of HTTP requests/responses (unless `--include-http-logs` is used)
- `errors` - JSON array of error details (if any errors exist)

With `--include-http-logs`, you'll also get:
- `http_logs` - Full HTTP request/response details (JSON array)

## JSON Output Structure

JSON export provides a structured array of log objects with all available fields.

## Usage Examples

### 1. Export all logs for a specific channel to CSV
```bash
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/channel_logs.csv \
    --channel-uuid "12345678-1234-1234-1234-123456789abc" \
    --verbose
```

### 2. Export only error logs from the last 7 days
```bash
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/error_logs.json \
    --errors-only \
    --start-date "2025-10-01" \
    --verbose
```

### 3. Export message send logs with HTTP details
```bash
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/msg_send_logs.csv \
    --log-type msg_send \
    --include-http-logs \
    --limit 1000 \
    --verbose
```

### 4. Export slow requests (over 5 seconds)
```bash
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/slow_logs.csv \
    --min-elapsed-ms 5000 \
    --verbose
```

### 5. Export logs for a specific date range
```bash
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/october_logs.json \
    --start-date "2025-10-01T00:00:00" \
    --end-date "2025-10-31T23:59:59" \
    --org-id 1 \
    --verbose
```

### 6. Export IVR-related logs
```bash
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/ivr_logs.csv \
    --log-type ivr_start \
    --verbose
```

### 7. Export first 100 logs for quick analysis
```bash
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/sample_logs.json \
    --limit 100 \
    --verbose
```

## Analyzing Exported Data

### Using CSV with Python (pandas)
```python
import pandas as pd
import json

# Read the CSV
df = pd.read_csv('logs.csv')

# Parse JSON columns
df['errors_parsed'] = df['errors'].apply(lambda x: json.loads(x) if pd.notna(x) else [])

# Basic analysis
print(f"Total logs: {len(df)}")
print(f"Error logs: {df['is_error'].sum()}")
print(f"Average elapsed time: {df['elapsed_ms'].mean():.2f}ms")

# Group by log type
print(df['type'].value_counts())

# Find slowest requests
slow_logs = df.nlargest(10, 'elapsed_ms')
print(slow_logs[['log_uuid', 'type', 'elapsed_ms', 'created_on']])
```

### Using CSV with Excel
Simply open the CSV file in Microsoft Excel or Google Sheets for analysis.

### Using JSON with jq
```bash
# Count logs by type
cat logs.json | jq 'group_by(.type) | map({type: .[0].type, count: length})'

# Find all error logs
cat logs.json | jq '[.[] | select(.is_error == true)]'

# Calculate average elapsed time
cat logs.json | jq '[.[].elapsed_ms] | add / length'

# Find slowest logs
cat logs.json | jq 'sort_by(.elapsed_ms) | reverse | .[0:10]'
```

## Performance Considerations

- **Scanning is slow**: DynamoDB scan operations read the entire table. For large datasets, this can take several minutes.
- **Use filters**: Apply as many filters as possible to reduce the amount of data processed.
- **Use --limit**: When testing or doing quick analysis, use `--limit` to avoid processing all logs.
- **Channel-specific queries are faster**: When possible, filter by channel UUID to leverage DynamoDB's partitioning.

## Troubleshooting

### "Channel with UUID X not found"
Make sure the channel UUID is correct and the channel exists in your database.

### "Organization with ID X not found"
Verify the organization ID is correct.

### "Invalid date format"
Use ISO format dates: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`

### No logs exported
- Check that logs exist in DynamoDB for your filters
- Try removing filters one by one to identify which filter is too restrictive
- Use `--verbose` to see how many items are being scanned

## Additional Use Cases

### Debugging Webhook Issues
```bash
# Export all webhook-related errors
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/webhook_errors.csv \
    --log-type msg_send \
    --errors-only \
    --include-http-logs \
    --verbose
```

### Performance Analysis
```bash
# Export slow message sends
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/slow_sends.csv \
    --log-type msg_send \
    --min-elapsed-ms 3000 \
    --start-date "2025-10-01" \
    --verbose
```

### Channel Health Check
```bash
# Export recent errors for monitoring
docker compose exec rapidpro poetry run python manage.py export_channel_logs \
    --output /tmp/recent_errors.json \
    --errors-only \
    --start-date "2025-10-08T00:00:00" \
    --verbose
```

## DynamoDB Schema Reference

### Table Structure
- **Table Name**: `TembaMain` (production) or `TestMain` (testing)
- **Partition Key (PK)**: `cha#{channel_uuid}#{partition}` where partition is 0-f
- **Sort Key (SK)**: `log#{log_uuid}`

### Item Fields
- `OrgID` - Organization ID
- `Data` - JSON object with log data
- `DataGZ` - Gzipped JSON for larger data
- `TTL` - Time-to-live for automatic expiration

### Log Data Structure
```json
{
  "type": "msg_send",
  "http_logs": [
    {
      "url": "https://api.example.com/send",
      "request": "POST body...",
      "response": "Response body...",
      "status_code": 200,
      "elapsed_ms": 150
    }
  ],
  "errors": [
    {
      "message": "Connection timeout",
      "code": "timeout",
      "ext_code": "E1001"
    }
  ],
  "is_error": false,
  "elapsed_ms": 150,
  "created_on": "2025-10-08T10:30:00Z"
}
```

## Best Practices

1. **Start with --verbose**: Always use `--verbose` flag to monitor progress
2. **Use --limit for testing**: Test your filters with `--limit 10` first
3. **Filter by time**: Use date ranges to reduce scan time
4. **Export to JSON for complex analysis**: JSON preserves data structure better than CSV
5. **Be cautious with --include-http-logs**: This can create very large files
6. **Regular exports**: Consider scheduling regular exports for monitoring and analysis

## Future Enhancement Ideas

Additional options that could be added to this script:

1. **Filter by HTTP status code** - Find all 4xx or 5xx responses
2. **Filter by URL pattern** - Find logs for specific endpoints
3. **Export to database** - Load directly into PostgreSQL for analysis
4. **Aggregate statistics** - Generate summary reports
5. **Real-time streaming** - Stream logs as they're written
6. **Compressed output** - Export to gzipped files for large datasets
7. **Multi-channel export** - Export logs for multiple channels at once
8. **Error categorization** - Group errors by type/code
9. **Time-based bucketing** - Group logs by hour/day/week
10. **Anonymization** - Redact sensitive data automatically

