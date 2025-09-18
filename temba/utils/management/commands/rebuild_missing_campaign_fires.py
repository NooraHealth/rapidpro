from typing import Iterable, Set

from django.core.management.base import BaseCommand, CommandError
from django.db.models import CharField, Exists, OuterRef, Q, Value
from django.db.models.functions import Cast, Concat

from temba.campaigns.models import CampaignEvent
from temba.contacts.models import Contact, ContactFire
from temba.orgs.models import Org


class Command(BaseCommand):
    help = (
        "Rebuild campaign fires by re-scheduling events that appear missing for contacts. "
        "For a specific contact, only events that lack a matching ContactFire with the current fire_version "
        "will be re-scheduled. Use --all-contacts to scan everyone (batched)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--contact", help="Contact UUID to check and fix", default=None)
        parser.add_argument("--org", help="Limit to an org id or uuid", default=None)
        parser.add_argument("--all-contacts", action="store_true", help="Scan all contacts in scope")
        parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for all-contacts scan")
        parser.add_argument("--dry-run", action="store_true", help="Only report, don't schedule")
        parser.add_argument(
            "--recompute-all-events",
            action="store_true",
            help=(
                "Recompute scheduling for all active campaign events in scope (optionally filtered by --org). "
                "This bypasses contact scanning and schedules every active event."
            ),
        )

    def handle(self, *args, **options):
        contact_uuid = options["contact"]
        org_filter = options["org"]
        all_contacts = options["all_contacts"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        recompute_all_events = options["recompute_all_events"]

        if not contact_uuid and not all_contacts and not recompute_all_events:
            raise CommandError("Provide --contact <uuid>, --all-contacts, or --recompute-all-events")

        org: Org | None = None
        if org_filter:
            org = Org.objects.filter(Q(id__iexact=org_filter) | Q(uuid__iexact=org_filter)).first()
            if not org:
                raise CommandError(f"Org not found: {org_filter}")

        # blanket recomputation path - schedule all active events in scope (optionally filtered by org)
        if recompute_all_events:
            events_qs = CampaignEvent.objects.filter(is_active=True, campaign__is_archived=False)
            if org:
                events_qs = events_qs.filter(campaign__org=org)

            total_events = events_qs.count()
            if total_events == 0:
                self.stdout.write(self.style.WARNING("No events found to recompute in the selected scope."))
                return

            self.stdout.write(self.style.WARNING(
                f"Recomputing scheduling for {total_events} event(s)" + (" (dry-run)" if dry_run else "")
            ))

            processed = 0
            last_reported_percent = -1
            buffer_ids: Set[int] = set()

            for event in events_qs.iterator(chunk_size=500):
                processed += 1
                buffer_ids.add(event.id)

                if len(buffer_ids) >= 500:
                    self._maybe_schedule(buffer_ids, dry_run)
                    buffer_ids.clear()

                percent = int((processed * 100) / total_events)
                if percent >= last_reported_percent + 5 or processed == total_events:
                    self.stdout.write(f"Event progress: {processed}/{total_events} ({percent}%)")
                    last_reported_percent = percent

            # schedule any remaining events in buffer
            self._maybe_schedule(buffer_ids, dry_run)
            self.stdout.write(self.style.SUCCESS(f"Completed event recomputation. Events processed: {processed}"))
            return

        if contact_uuid:
            contact = Contact.objects.filter(uuid=contact_uuid)
            if org:
                contact = contact.filter(org=org)
            contact = contact.first()
            if not contact:
                raise CommandError(f"Contact not found: {contact_uuid}")

            self.stdout.write(self.style.WARNING(f"Scanning contact {contact.id} ({contact.uuid})"))
            events_to_fix = self._find_missing_events_for_contact(contact)
            self._maybe_schedule(events_to_fix, dry_run)
            return

        # all-contacts path
        qs = Contact.objects.all()
        if org:
            qs = qs.filter(org=org)

        total_contacts = qs.count()
        num_scanned = 0
        events_to_fix_global: Set[int] = set()
        last_reported_percent = -1

        for contact in qs.iterator(chunk_size=batch_size):
            num_scanned += 1
            missing_for_contact = self._find_missing_events_for_contact(contact)
            events_to_fix_global.update(missing_for_contact)

            # schedule in chunks to avoid growing set without bound
            if len(events_to_fix_global) >= 500:
                self._maybe_schedule(events_to_fix_global, dry_run)
                events_to_fix_global.clear()

            if total_contacts:
                percent = int((num_scanned * 100) / total_contacts)
                if percent >= last_reported_percent + 5 or num_scanned == total_contacts:
                    self.stdout.write(f"Progress: {num_scanned}/{total_contacts} ({percent}%)")
                    last_reported_percent = percent

        # schedule any remaining
        self._maybe_schedule(events_to_fix_global, dry_run)

        self.stdout.write(self.style.SUCCESS(f"Completed scan. Contacts scanned: {num_scanned}"))

    def _find_missing_events_for_contact(self, contact: Contact) -> Set[int]:
        """
        Returns the IDs of CampaignEvent objects for which this contact should have a fire for the current version,
        but doesn't. We detect this by checking for absence of a ContactFire with scope "<event_id>:<fire_version>".
        """

        # only consider active events in active campaigns where the contact is a member of the campaign's group
        events = (
            CampaignEvent.objects.filter(
                is_active=True,
                campaign__is_archived=False,
                campaign__group__contacts=contact,
            )
            .distinct()
            .annotate(
                scope_key=Concat(
                    Cast("id", output_field=CharField()),
                    Value(":"),
                    Cast("fire_version", output_field=CharField()),
                )
            )
        )

        has_fire = ContactFire.objects.filter(
            contact=contact,
            fire_type=ContactFire.TYPE_CAMPAIGN_EVENT,
            scope=OuterRef("scope_key"),
        )

        missing = events.filter(~Exists(has_fire))
        missing_ids = set(missing.values_list("id", flat=True))

        # if missing_ids:
        #     self.stdout.write(
        #         f"Contact {contact.id} missing fires for events: {sorted(list(missing_ids))}"
        #     )
        return missing_ids

    def _maybe_schedule(self, event_ids: Iterable[int], dry_run: bool) -> None:
        event_ids = list(set(event_ids))
        if not event_ids:
            return

        events = list(CampaignEvent.objects.filter(id__in=event_ids))
        events.sort(key=lambda e: e.name)
        event_names = [e.name for e in events]

        self.stdout.write(
            self.style.NOTICE(
                f"Rescheduling {len(event_names)} event(s): {event_names}" + (" (dry-run)" if dry_run else "")
            )
        )

        if dry_run:
            return

        for event in events:
            self.stdout.write(f"Scheduling: {event.name}")
            event.schedule_async()
        self.stdout.write(self.style.SUCCESS(f"Queued scheduling for {len(event_ids)} event(s)"))


