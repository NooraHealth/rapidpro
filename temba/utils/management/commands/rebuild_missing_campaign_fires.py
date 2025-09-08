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

    def handle(self, *args, **options):
        contact_uuid = options["contact"]
        org_filter = options["org"]
        all_contacts = options["all_contacts"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        if not contact_uuid and not all_contacts:
            raise CommandError("Provide --contact <uuid> or --all-contacts")

        org: Org | None = None
        if org_filter:
            org = Org.objects.filter(Q(id__iexact=org_filter) | Q(uuid__iexact=org_filter)).first()
            if not org:
                raise CommandError(f"Org not found: {org_filter}")

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

        num_scanned = 0
        events_to_fix_global: Set[int] = set()

        for contact in qs.iterator(chunk_size=batch_size):
            num_scanned += 1
            missing_for_contact = self._find_missing_events_for_contact(contact)
            events_to_fix_global.update(missing_for_contact)

            # schedule in chunks to avoid growing set without bound
            if len(events_to_fix_global) >= 500:
                self._maybe_schedule(events_to_fix_global, dry_run)
                events_to_fix_global.clear()

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

        if missing_ids:
            self.stdout.write(
                f"Contact {contact.id} missing fires for events: {sorted(list(missing_ids))}"
            )
        return missing_ids

    def _maybe_schedule(self, event_ids: Iterable[int], dry_run: bool) -> None:
        event_ids = list(set(event_ids))
        if not event_ids:
            return

        self.stdout.write(
            self.style.NOTICE(
                f"Rescheduling {len(event_ids)} event(s): {sorted(event_ids)}" + (" (dry-run)" if dry_run else "")
            )
        )

        if dry_run:
            return

        for event in CampaignEvent.objects.filter(id__in=event_ids):
            event.schedule_async()
        self.stdout.write(self.style.SUCCESS(f"Queued scheduling for {len(event_ids)} event(s)"))


