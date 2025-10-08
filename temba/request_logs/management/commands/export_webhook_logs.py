import csv
import json
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from temba.orgs.models import Org
from temba.request_logs.models import HTTPLog


class Command(BaseCommand):
    help = "Export webhook logs from PostgreSQL to CSV or JSON format"

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
            "--log-type",
            choices=[
                HTTPLog.WEBHOOK_CALLED,
                HTTPLog.AIRTIME_TRANSFERRED,
                HTTPLog.WHATSAPP_TEMPLATES_SYNCED,
                HTTPLog.WHATSAPP_TOKENS_SYNCED,
                HTTPLog.WHATSAPP_CONTACTS_REFRESHED,
                HTTPLog.WHATSAPP_CHECK_HEALTH,
            ],
            default=HTTPLog.WEBHOOK_CALLED,
            help="Filter by log type (defaults to webhook_called)",
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
            help="Only export logs with HTTP errors (status code >= 400)",
        )
        parser.add_argument(
            "--min-request-time",
            type=int,
            help="Filter logs with request time greater than this value (in milliseconds)",
        )
        parser.add_argument(
            "--max-request-time",
            type=int,
            help="Filter logs with request time less than this value (in milliseconds)",
        )
        parser.add_argument(
            "--status-code",
            type=int,
            help="Filter by specific HTTP status code",
        )
        parser.add_argument(
            "--url-contains",
            type=str,
            help="Filter logs where URL contains this string",
        )

        # Processing options
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of logs to export",
        )
        parser.add_argument(
            "--include-full-request",
            action="store_true",
            help="Include full HTTP request body in output",
        )
        parser.add_argument(
            "--include-full-response",
            action="store_true",
            help="Include full HTTP response body in output",
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

        # Validate org
        org_id = options.get("org_id")
        if org_id:
            org = Org.objects.filter(id=org_id).first()
            if not org:
                raise CommandError(f"Organization with ID {org_id} not found")

        if options["verbose"]:
            self.stdout.write("Starting webhook log export...")
            self.stdout.write(f"  Output: {output_file} ({output_format})")
            if org_id:
                self.stdout.write(f"  Organization ID: {org_id}")
            self.stdout.write(f"  Log Type: {options['log_type']}")
            if start_date:
                self.stdout.write(f"  Start Date: {start_date}")
            if end_date:
                self.stdout.write(f"  End Date: {end_date}")

        # Query HTTPLog
        logs = self._query_logs(
            org_id=org_id,
            log_type=options["log_type"],
            start_date=start_date,
            end_date=end_date,
            errors_only=options.get("errors_only", False),
            min_request_time=options.get("min_request_time"),
            max_request_time=options.get("max_request_time"),
            status_code=options.get("status_code"),
            url_contains=options.get("url_contains"),
            limit=options.get("limit"),
            include_full_request=options.get("include_full_request", False),
            include_full_response=options.get("include_full_response", False),
            verbose=options.get("verbose", False),
        )

        # Export to file
        if output_format == "csv":
            self._export_csv(
                logs,
                output_file,
                options.get("include_full_request", False),
                options.get("include_full_response", False),
            )
        else:
            self._export_json(logs, output_file)

        self.stdout.write(self.style.SUCCESS(f"Successfully exported {len(logs)} logs to {output_file}"))

    def _query_logs(
        self,
        org_id=None,
        log_type=None,
        start_date=None,
        end_date=None,
        errors_only=False,
        min_request_time=None,
        max_request_time=None,
        status_code=None,
        url_contains=None,
        limit=None,
        include_full_request=False,
        include_full_response=False,
        verbose=False,
    ):
        """Query HTTPLog table with filters"""
        if verbose:
            self.stdout.write("Querying database...")

        # Build query
        qs = HTTPLog.objects.all()

        if org_id:
            qs = qs.filter(org_id=org_id)

        if log_type:
            qs = qs.filter(log_type=log_type)

        if start_date:
            qs = qs.filter(created_on__gte=start_date)

        if end_date:
            qs = qs.filter(created_on__lte=end_date)

        if errors_only:
            qs = qs.filter(status_code__gte=400)

        if status_code:
            qs = qs.filter(status_code=status_code)

        if url_contains:
            qs = qs.filter(url__icontains=url_contains)

        if min_request_time:
            qs = qs.filter(request_time__gte=min_request_time)

        if max_request_time:
            qs = qs.filter(request_time__lte=max_request_time)

        # Order by most recent first
        qs = qs.order_by("-created_on")

        if limit:
            qs = qs[:limit]

        # Fetch data
        logs = []
        for log in qs:
            log_data = {
                "id": log.id,
                "org_id": log.org_id,
                "log_type": log.log_type,
                "url": log.url,
                "status_code": log.status_code,
                "request_time": log.request_time,
                "num_retries": log.num_retries,
                "created_on": log.created_on.isoformat(),
                "is_error": log.status_code >= 400 if log.status_code else False,
            }

            if include_full_request:
                log_data["request"] = log.request

            if include_full_response:
                log_data["response"] = log.response

            logs.append(log_data)

            if verbose and len(logs) % 100 == 0:
                self.stdout.write(f"  Processed {len(logs)} logs...")

        if verbose:
            self.stdout.write(f"Query complete. Found {len(logs)} logs")

        return logs

    def _parse_date(self, date_str):
        """Parse date string to datetime object"""
        try:
            # Try parsing as datetime with timezone
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # Make timezone-aware if it's not already
            if dt.tzinfo is None:
                dt = timezone.make_aware(dt)
            return dt
        except Exception:
            try:
                # Try parsing as simple date and make timezone-aware
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return timezone.make_aware(dt)
            except Exception:
                raise CommandError(
                    f"Invalid date format: {date_str}. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                )

    def _export_csv(self, logs, output_file, include_full_request, include_full_response):
        """Export logs to CSV format"""
        if not logs:
            raise CommandError("No logs to export")

        # Define CSV columns
        fieldnames = [
            "id",
            "org_id",
            "log_type",
            "url",
            "status_code",
            "is_error",
            "request_time",
            "num_retries",
            "created_on",
        ]

        if include_full_request:
            fieldnames.append("request")

        if include_full_response:
            fieldnames.append("response")

        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for log in logs:
                writer.writerow(log)

    def _export_json(self, logs, output_file):
        """Export logs to JSON format"""
        with open(output_file, "w", encoding="utf-8") as jsonfile:
            json.dump(logs, jsonfile, indent=2, default=str)

