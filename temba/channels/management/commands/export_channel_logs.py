import csv
import json
from datetime import datetime
from decimal import Decimal

import iso8601
from django.core.management.base import BaseCommand, CommandError

from temba.channels.models import Channel, ChannelLog
from temba.orgs.models import Org
from temba.utils import dynamo


class Command(BaseCommand):
    help = "Export channel logs from DynamoDB to CSV or JSON format"

    def add_arguments(self, parser):
        # Output options
        parser.add_argument(
            "--output",
            type=str,
            required=True,
            help="Output file path (e.g., logs.csv or logs.json)",
        )
        parser.add_argument(
            "--format",
            choices=["csv", "json"],
            default=None,
            help="Output format (defaults to file extension)",
        )

        # Filter options
        parser.add_argument(
            "--org-id",
            type=int,
            help="Filter by organization ID",
        )
        parser.add_argument(
            "--channel-uuid",
            type=str,
            help="Filter by channel UUID",
        )
        parser.add_argument(
            "--log-type",
            choices=[
                ChannelLog.LOG_TYPE_UNKNOWN,
                ChannelLog.LOG_TYPE_MSG_SEND,
                ChannelLog.LOG_TYPE_MSG_STATUS,
                ChannelLog.LOG_TYPE_MSG_RECEIVE,
                ChannelLog.LOG_TYPE_EVENT_RECEIVE,
                ChannelLog.LOG_TYPE_MULTI_RECEIVE,
                ChannelLog.LOG_TYPE_IVR_START,
                ChannelLog.LOG_TYPE_IVR_INCOMING,
                ChannelLog.LOG_TYPE_IVR_CALLBACK,
                ChannelLog.LOG_TYPE_IVR_STATUS,
                ChannelLog.LOG_TYPE_IVR_HANGUP,
                ChannelLog.LOG_TYPE_ATTACHMENT_FETCH,
                ChannelLog.LOG_TYPE_TOKEN_REFRESH,
                ChannelLog.LOG_TYPE_PAGE_SUBSCRIBE,
                ChannelLog.LOG_TYPE_WEBHOOK_VERIFY,
            ],
            help="Filter by log type",
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="Filter logs from this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            help="Filter logs until this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
        )
        parser.add_argument(
            "--errors-only",
            action="store_true",
            help="Only export logs with errors",
        )
        parser.add_argument(
            "--min-elapsed-ms",
            type=int,
            help="Filter logs with elapsed time greater than this value (in milliseconds)",
        )
        parser.add_argument(
            "--max-elapsed-ms",
            type=int,
            help="Filter logs with elapsed time less than this value (in milliseconds)",
        )

        # Processing options
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of logs to export",
        )
        parser.add_argument(
            "--no-redact",
            action="store_true",
            help="Include sensitive data (use with caution!)",
        )
        parser.add_argument(
            "--include-http-logs",
            action="store_true",
            help="Include full HTTP request/response logs in output",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show progress information",
        )

    def handle(self, *args, **options):
        # Parse output format
        output_file = options["output"]
        output_format = options["format"]
        if not output_format:
            output_format = "json" if output_file.endswith(".json") else "csv"

        # Parse date filters
        start_date = self._parse_date(options.get("start_date")) if options.get("start_date") else None
        end_date = self._parse_date(options.get("end_date")) if options.get("end_date") else None

        # Validate filters
        org_id = options.get("org_id")
        channel_uuid = options.get("channel_uuid")
        
        if channel_uuid:
            channel = Channel.objects.filter(uuid=channel_uuid).first()
            if not channel:
                raise CommandError(f"Channel with UUID {channel_uuid} not found")
            org_id = channel.org_id
        elif org_id:
            org = Org.objects.filter(id=org_id).first()
            if not org:
                raise CommandError(f"Organization with ID {org_id} not found")

        if options["verbose"]:
            self.stdout.write("Starting log export...")
            self.stdout.write(f"  Output: {output_file} ({output_format})")
            if org_id:
                self.stdout.write(f"  Organization ID: {org_id}")
            if channel_uuid:
                self.stdout.write(f"  Channel UUID: {channel_uuid}")
            if options.get("log_type"):
                self.stdout.write(f"  Log Type: {options['log_type']}")
            if start_date:
                self.stdout.write(f"  Start Date: {start_date}")
            if end_date:
                self.stdout.write(f"  End Date: {end_date}")

        # Scan DynamoDB and collect logs
        logs = self._scan_logs(
            org_id=org_id,
            channel_uuid=channel_uuid,
            log_type=options.get("log_type"),
            start_date=start_date,
            end_date=end_date,
            errors_only=options.get("errors_only", False),
            min_elapsed_ms=options.get("min_elapsed_ms"),
            max_elapsed_ms=options.get("max_elapsed_ms"),
            limit=options.get("limit"),
            include_http_logs=options.get("include_http_logs", False),
            verbose=options.get("verbose", False),
        )

        # Export to file
        if output_format == "csv":
            self._export_csv(logs, output_file, options.get("include_http_logs", False))
        else:
            self._export_json(logs, output_file)

        self.stdout.write(self.style.SUCCESS(f"Successfully exported {len(logs)} logs to {output_file}"))

    def _scan_logs(
        self,
        org_id=None,
        channel_uuid=None,
        log_type=None,
        start_date=None,
        end_date=None,
        errors_only=False,
        min_elapsed_ms=None,
        max_elapsed_ms=None,
        limit=None,
        include_http_logs=False,
        verbose=False,
    ):
        """Scan DynamoDB table and filter logs based on criteria"""
        logs = []
        scanned_count = 0
        
        table = dynamo.MAIN
        
        if verbose:
            self.stdout.write("Scanning DynamoDB table...")

        # Scan the table
        scan_kwargs = {}
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        while True:
            for item in items:
                scanned_count += 1
                if verbose and scanned_count % 1000 == 0:
                    self.stdout.write(f"  Scanned {scanned_count} items, found {len(logs)} matching logs...")

                # Only process channel log items
                if not item.get("SK", "").startswith("log#"):
                    continue

                # Parse the log data
                try:
                    log_data = self._parse_log_item(item, include_http_logs)
                    
                    # Apply filters
                    if org_id and item.get("OrgID") != org_id:
                        continue
                    
                    if channel_uuid:
                        pk = item.get("PK", "")
                        if not pk.startswith(f"cha#{channel_uuid}#"):
                            continue
                    
                    if log_type and log_data.get("type") != log_type:
                        continue
                    
                    if errors_only and not log_data.get("is_error", False):
                        continue
                    
                    # Date filtering
                    created_on = iso8601.parse_date(log_data["created_on"])
                    if start_date and created_on < start_date:
                        continue
                    if end_date and created_on > end_date:
                        continue
                    
                    # Elapsed time filtering
                    elapsed_ms = log_data.get("elapsed_ms", 0)
                    if min_elapsed_ms and elapsed_ms < min_elapsed_ms:
                        continue
                    if max_elapsed_ms and elapsed_ms > max_elapsed_ms:
                        continue
                    
                    # Add additional metadata
                    log_data["log_uuid"] = item["SK"].split("#")[1]
                    log_data["channel_uuid"] = item["PK"].split("#")[1]
                    log_data["org_id"] = int(item.get("OrgID", 0))
                    
                    logs.append(log_data)
                    
                    if limit and len(logs) >= limit:
                        if verbose:
                            self.stdout.write(f"Reached limit of {limit} logs")
                        return logs
                        
                except Exception as e:
                    if verbose:
                        self.stderr.write(f"Error parsing log item: {e}")
                    continue

            # Check if there are more items to scan
            if "LastEvaluatedKey" not in response:
                break
            
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = table.scan(**scan_kwargs)
            items = response.get("Items", [])

        if verbose:
            self.stdout.write(f"Scan complete. Scanned {scanned_count} items, found {len(logs)} matching logs")

        return logs

    def _parse_log_item(self, item, include_http_logs=False):
        """Parse a DynamoDB log item into a dictionary"""
        # Merge Data and DataGZ
        data = dict(item.get("Data", {}))
        if "DataGZ" in item:
            data.update(dynamo.load_jsongz(item["DataGZ"]))
        
        # Build log dict
        log = {
            "type": data.get("type"),
            "is_error": data.get("is_error", False),
            "elapsed_ms": int(data.get("elapsed_ms", 0)),
            "created_on": data.get("created_on"),
        }
        
        # Add errors if present
        if data.get("errors"):
            log["errors"] = data["errors"]
            log["error_count"] = len(data["errors"])
        else:
            log["error_count"] = 0
        
        # Add HTTP logs if requested
        if include_http_logs and data.get("http_logs"):
            log["http_logs"] = data["http_logs"]
        elif data.get("http_logs"):
            # Just add count
            log["http_log_count"] = len(data["http_logs"])
        
        return log

    def _parse_date(self, date_str):
        """Parse date string to datetime object"""
        try:
            # Try parsing as ISO format
            return iso8601.parse_date(date_str)
        except Exception:
            try:
                # Try parsing as simple date
                return datetime.strptime(date_str, "%Y-%m-%d")
            except Exception as e:
                raise CommandError(f"Invalid date format: {date_str}. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")

    def _export_csv(self, logs, output_file, include_http_logs=False):
        """Export logs to CSV format"""
        if not logs:
            raise CommandError("No logs to export")

        # Define CSV columns
        fieldnames = [
            "log_uuid",
            "channel_uuid",
            "org_id",
            "type",
            "is_error",
            "error_count",
            "elapsed_ms",
            "created_on",
        ]
        
        if include_http_logs:
            fieldnames.append("http_logs")
        else:
            fieldnames.append("http_log_count")
        
        # Check if any logs have errors
        if any(log.get("errors") for log in logs):
            fieldnames.append("errors")

        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            
            for log in logs:
                # Convert complex fields to JSON strings for CSV
                row = log.copy()
                if "http_logs" in row:
                    row["http_logs"] = json.dumps(row["http_logs"])
                if "errors" in row:
                    row["errors"] = json.dumps(row["errors"])
                writer.writerow(row)

    def _export_json(self, logs, output_file):
        """Export logs to JSON format"""
        with open(output_file, "w", encoding="utf-8") as jsonfile:
            json.dump(logs, jsonfile, indent=2, default=str)

