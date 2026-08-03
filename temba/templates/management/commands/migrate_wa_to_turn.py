"""
Migrate WhatsApp Legacy (WA) channels that talk to Turn.io onto Turn (TRN).

Must be run on 26.0.x (or any build still before Courier noops WA) so messaging
keeps working during cutover. After TRN is verified, deactivate WA and only then
bump Courier past v26.1.16.

Usage:
  # Inventory
  python manage.py migrate_wa_to_turn --list

  # Dry-run one channel
  python manage.py migrate_wa_to_turn --channel-id 123 --dry-run

  # Create TRN from WA config (keeps WA active)
  python manage.py migrate_wa_to_turn --channel-id 123

  # Create TRN and deactivate the source WA channel
  python manage.py migrate_wa_to_turn --channel-id 123 --deactivate-wa

  # All active WA channels for an org
  python manage.py migrate_wa_to_turn --org-id 1 --deactivate-wa
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from temba.channels.models import Channel
from temba.channels.types.turn.type import (
    CONFIG_FB_ACCESS_TOKEN,
    CONFIG_FB_BUSINESS_ID,
    CONFIG_FB_NAMESPACE,
    CONFIG_FB_TEMPLATE_LIST_DOMAIN,
    CONFIG_FB_TEMPLATE_API_VERSION,
)


class Command(BaseCommand):
    help = "Migrate WhatsApp Legacy (WA) channels to Turn.io WhatsApp (TRN)"

    def add_arguments(self, parser):
        parser.add_argument("--list", action="store_true", help="List active WA/TRN/WAC channels")
        parser.add_argument("--org-id", type=int, help="Limit to one organization")
        parser.add_argument("--channel-id", type=int, help="Migrate a single WA channel by ID")
        parser.add_argument(
            "--deactivate-wa",
            action="store_true",
            help="Deactivate the source WA channel after creating TRN",
        )
        parser.add_argument(
            "--auth-token",
            help="Override Turn auth_token (otherwise reuse WA config or login with username/password)",
        )
        parser.add_argument("--dry-run", action="store_true", help="Show actions without writing")
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args, **options):
        self.verbose = options["verbose"]

        if options["list"]:
            self._list_channels(options.get("org_id"))
            return

        channels = self._select_wa_channels(options)
        if not channels:
            raise CommandError("No matching active WA channels found")

        for wa in channels:
            self._migrate_one(wa, options)

    def _list_channels(self, org_id):
        qs = Channel.objects.filter(channel_type__in=["WA", "TRN", "WAC"], is_active=True).order_by("org_id", "id")
        if org_id:
            qs = qs.filter(org_id=org_id)
        self.stdout.write(f"{'ID':>6}  {'TYPE':<3}  {'ORG':>5}  {'ADDRESS':<20}  NAME")
        for ch in qs:
            self.stdout.write(f"{ch.id:>6}  {ch.channel_type:<3}  {ch.org_id:>5}  {str(ch.address)[:20]:<20}  {ch.name}")

    def _select_wa_channels(self, options):
        qs = Channel.objects.filter(channel_type="WA", is_active=True).select_related("org")
        if options.get("channel_id"):
            qs = qs.filter(id=options["channel_id"])
        elif options.get("org_id"):
            qs = qs.filter(org_id=options["org_id"])
        else:
            raise CommandError("Provide --channel-id, --org-id, or --list")
        return list(qs)

    def _migrate_one(self, wa: Channel, options):
        config = dict(wa.config or {})
        address = self._resolve_address(wa, config)
        country = wa.country
        turn_config = self._build_turn_config(wa, config, address, options.get("auth_token"))

        existing = Channel.objects.filter(
            org=wa.org, channel_type="TRN", address=address, is_active=True
        ).first()
        if existing:
            self.stdout.write(
                self.style.WARNING(
                    f"WA#{wa.id}: active TRN already exists as #{existing.id} ({existing.uuid}); skipping create"
                )
            )
            if options["deactivate_wa"] and not options["dry_run"]:
                self._deactivate_wa(wa, existing)
            return

        self.stdout.write(
            f"WA#{wa.id} ({wa.name}) -> TRN address={address} org={wa.org_id} "
            f"deactivate_wa={options['deactivate_wa']}"
        )
        if self.verbose or options["dry_run"]:
            for key, value in turn_config.items():
                secret = key in {
                    Channel.CONFIG_PASSWORD,
                    Channel.CONFIG_AUTH_TOKEN,
                    CONFIG_FB_ACCESS_TOKEN,
                }
                self.stdout.write(f"  {key}: {'***' if secret else value}")

        if options["dry_run"]:
            return

        try:
            turn_type = Channel.get_type_from_code("TRN")
        except ValueError as e:
            raise CommandError("TRN channel type not found") from e

        admin = wa.org.get_admins().first() or wa.created_by
        with transaction.atomic():
            trn = Channel.create(
                wa.org,
                admin,
                country,
                turn_type,
                name=(wa.name or f"WhatsApp: {address}")[:64],
                address=address,
                config=turn_config,
                tps=wa.tps or 80,
            )
            trn.is_active = True
            trn.is_enabled = True
            trn.role = wa.role or (Channel.ROLE_SEND + Channel.ROLE_RECEIVE)
            cfg = trn.config.copy()
            cfg["migrated_from_wa_id"] = wa.id
            cfg["migrated_from_wa_uuid"] = str(wa.uuid)
            cfg["activation_date"] = timezone.now().isoformat()
            trn.config = cfg
            trn.save(update_fields=["is_active", "is_enabled", "role", "config"])

            if options["deactivate_wa"]:
                self._deactivate_wa(wa, trn)

        receive_path = f"/c/trn/{trn.uuid}/receive"
        self.stdout.write(
            self.style.SUCCESS(
                f"Created TRN#{trn.id} uuid={trn.uuid}\n"
                f"  Turn receive URL path: {receive_path}\n"
                f"  Update Turn callbacks to https://<domain>{receive_path} before relying on inbound"
            )
        )

    def _resolve_address(self, wa, config):
        # Prefer E.164-looking WA address; else fb_business_id / number-like config.
        address = (wa.address or "").strip()
        if address.startswith("+") or address.isdigit():
            if not address.startswith("+") and address.isdigit():
                address = f"+{address}"
            return address

        for key in ("fb_business_id", "number", "phone_number"):
            val = str(config.get(key) or "").strip()
            if val:
                return val if val.startswith("+") else f"+{val.lstrip('+')}"

        raise CommandError(
            f"WA#{wa.id}: cannot derive phone address from address={wa.address!r}; "
            "set a proper number on the WA channel or migrate manually"
        )

    def _build_turn_config(self, wa, config, address, auth_token_override):
        base_url = config.get(Channel.CONFIG_BASE_URL) or config.get("base_url") or "https://whatsapp.turn.io"
        username = config.get(Channel.CONFIG_USERNAME) or config.get("username")
        password = config.get(Channel.CONFIG_PASSWORD) or config.get("password")
        auth_token = auth_token_override or config.get(Channel.CONFIG_AUTH_TOKEN) or config.get("auth_token")
        access_token = config.get(CONFIG_FB_ACCESS_TOKEN) or config.get("fb_access_token") or ""
        namespace = config.get(CONFIG_FB_NAMESPACE) or config.get("fb_namespace") or ""
        template_domain = (
            config.get(CONFIG_FB_TEMPLATE_LIST_DOMAIN)
            or config.get("fb_template_list_domain")
            or "whatsapp.turn.io"
        )

        if not username or not password:
            raise CommandError(f"WA#{wa.id}: missing Turn username/password in channel config")

        if not auth_token:
            import requests

            resp = requests.post(
                f"{base_url.rstrip('/')}/v1/users/login",
                auth=(username, password),
                timeout=30,
            )
            if resp.status_code != 200:
                raise CommandError(f"WA#{wa.id}: Turn login failed with HTTP {resp.status_code}")
            auth_token = resp.json()["users"][0]["token"]

        turn_config = {
            Channel.CONFIG_BASE_URL: base_url,
            Channel.CONFIG_USERNAME: username,
            Channel.CONFIG_PASSWORD: password,
            Channel.CONFIG_AUTH_TOKEN: auth_token,
            CONFIG_FB_BUSINESS_ID: address.lstrip("+"),
            CONFIG_FB_ACCESS_TOKEN: access_token,
            CONFIG_FB_NAMESPACE: namespace,
            CONFIG_FB_TEMPLATE_LIST_DOMAIN: template_domain,
        }
        api_version = config.get(CONFIG_FB_TEMPLATE_API_VERSION)
        if api_version:
            turn_config[CONFIG_FB_TEMPLATE_API_VERSION] = api_version
        return turn_config

    def _deactivate_wa(self, wa, trn):
        wa.is_active = False
        wa.is_enabled = False
        cfg = wa.config.copy()
        cfg["migrated_to_trn_id"] = trn.id
        cfg["migrated_to_trn_uuid"] = str(trn.uuid)
        cfg["deactivated_for_trn_migration"] = timezone.now().isoformat()
        wa.config = cfg
        wa.save(update_fields=["is_active", "is_enabled", "config", "modified_on"])
        self.stdout.write(self.style.WARNING(f"Deactivated WA#{wa.id}"))
