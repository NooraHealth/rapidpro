import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from temba.flows.models import FlowRevision
from temba.msgs.models import Media, Msg
from temba.utils import json


class Command(BaseCommand):
    help = (
        "Repair attachment URLs that are missing the MinIO bucket, i.e. https://host/orgs/... instead of "
        "https://host/temba-attachments/orgs/.... Those were written while AWS_S3_CUSTOM_DOMAIN was passed to "
        "django-storages as a CloudFront domain, which drops the bucket from generated URLs."
    )

    def add_arguments(self, parser):
        parser.add_argument("--host", help="Public storage host to repair (defaults to the S3 endpoint host)")
        parser.add_argument("--dry-run", action="store_true", help="Only report, don't write")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        host = options["host"] or urlparse(settings.AWS_S3_ENDPOINT_URL).netloc
        if not host:
            raise CommandError("Unable to determine storage host, pass --host")

        bucket = f"{settings.BUCKET_PREFIX}-attachments"
        self.bare_url = re.compile(rf"(https?://{re.escape(host)})/orgs/")
        self.replacement = rf"\1/{bucket}/orgs/"

        media = self._fix_media(bucket, dry_run)
        revisions = self._fix_flow_revisions(bucket, dry_run)
        msgs = self._fix_msgs(bucket, dry_run)

        verb = "Would fix" if dry_run else "Fixed"
        self.stdout.write(self.style.SUCCESS(f"{verb} {media} media, {revisions} flow revisions, {msgs} messages"))

    def _fix_media(self, bucket: str, dry_run: bool) -> int:
        fixed = 0

        for media in Media.objects.exclude(url__contains=f"/{bucket}/").order_by("id"):
            new_url, count = self.bare_url.subn(self.replacement, media.url)
            if not count:
                continue

            self.stdout.write(f"media {media.uuid}: {media.url} -> {new_url}")

            if not dry_run:
                media.url = new_url
                media.save(update_fields=("url",))
            fixed += 1

        return fixed

    def _fix_flow_revisions(self, bucket: str, dry_run: bool) -> int:
        fixed = 0

        for rev in FlowRevision.objects.filter(id__in=self._revision_ids(bucket)).order_by("id"):
            as_json = json.dumps(rev.definition)
            new_json, count = self.bare_url.subn(self.replacement, as_json)
            if not count:
                continue

            self.stdout.write(f"flow revision {rev.id} (flow {rev.flow_id}, revision {rev.revision}): {count} URLs")

            if not dry_run:
                rev.definition = json.loads(new_json)
                rev.save(update_fields=("definition",))
            fixed += 1

        return fixed

    def _revision_ids(self, bucket: str) -> list:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id FROM flows_flowrevision
                   WHERE definition::text LIKE %s AND definition::text NOT LIKE %s""",
                ["%/orgs/%/media/%", f"%/{bucket}/orgs/%/media/%"],
            )
            return [row[0] for row in cursor.fetchall()]

    def _fix_msgs(self, bucket: str, dry_run: bool) -> int:
        fixed = 0

        for msg in Msg.objects.filter(id__in=self._msg_ids(bucket)).order_by("id"):
            attachments = [self.bare_url.sub(self.replacement, a) for a in msg.attachments]
            if attachments == msg.attachments:
                continue

            self.stdout.write(f"msg {msg.id}: {msg.attachments} -> {attachments}")

            if not dry_run:
                msg.attachments = attachments
                msg.save(update_fields=("attachments",))
            fixed += 1

        return fixed

    def _msg_ids(self, bucket: str) -> list:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id FROM msgs_msg
                   WHERE attachments IS NOT NULL
                     AND attachments::text LIKE %s AND attachments::text NOT LIKE %s""",
                ["%/orgs/%", f"%/{bucket}/orgs/%"],
            )
            return [row[0] for row in cursor.fetchall()]
