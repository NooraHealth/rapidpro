"""
Create a Turn.io WhatsApp (TRN) channel.

Usage:
  python manage.py create_whatsapp_channel \\
    --org-id 1 --number "+1234567890" --country US \\
    --username turn_user --password turn_pass \\
    --access-token TEMPLATE_TOKEN --namespace your_namespace
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from temba.channels.models import Channel
from temba.channels.types.turn.type import (
    CONFIG_FB_ACCESS_TOKEN,
    CONFIG_FB_BUSINESS_ID,
    CONFIG_FB_NAMESPACE,
    CONFIG_FB_TEMPLATE_LIST_DOMAIN,
)
from temba.contacts.models import URN
from temba.orgs.models import Org


class Command(BaseCommand):
    help = "Create a Turn.io WhatsApp (TRN) channel"

    def add_arguments(self, parser):
        parser.add_argument("--org-id", type=int, required=True, help="Organization ID")
        parser.add_argument("--number", required=True, help="WhatsApp phone number (e.g. +1234567890)")
        parser.add_argument("--country", required=True, help="ISO country code for the number (e.g. IN, US)")
        parser.add_argument("--username", required=True, help="Turn.io username")
        parser.add_argument("--password", required=True, help="Turn.io password")
        parser.add_argument(
            "--access-token",
            required=True,
            help="Token used to sync WhatsApp message templates from Turn/Meta",
        )
        parser.add_argument("--namespace", required=True, help="WhatsApp template namespace")
        parser.add_argument(
            "--base-url",
            default="https://whatsapp.turn.io",
            help="Turn WhatsApp API base URL (default: https://whatsapp.turn.io)",
        )
        parser.add_argument(
            "--template-domain",
            default="whatsapp.turn.io",
            help="Template list domain (default: whatsapp.turn.io)",
        )
        parser.add_argument("--name", help="Custom channel name (default: WhatsApp: <number>)")
        parser.add_argument("--tps", type=int, default=80, help="Messages per second limit (default: 80)")
        parser.add_argument("--dry-run", action="store_true", help="Print what would be created")
        parser.add_argument("--verbose", action="store_true", help="Verbose output")

    def handle(self, *args, **options):
        self.verbose = options["verbose"]

        try:
            org = self._get_organization(options["org_id"])
            admin_user = self._get_admin_user(org)
            address = self._normalize_number(options["number"], options["country"])
            channel_name = options["name"] or f"WhatsApp: {address}"
            config = self._prepare_channel_config(options, address)

            if options["dry_run"]:
                self._show_dry_run(org, channel_name, address, config)
                return

            channel = self._create_channel(org, admin_user, channel_name, address, options["country"], config, options["tps"])
            self._show_success(channel)
        except CommandError:
            raise
        except Exception as e:
            raise CommandError(f"Error: {e}") from e

    def _get_organization(self, org_id):
        try:
            org = Org.objects.get(id=org_id, is_active=True)
        except Org.DoesNotExist as e:
            raise CommandError(f"Organization with ID {org_id} not found or inactive") from e
        if self.verbose:
            self.stdout.write(f"Found organization: {org.name} (ID: {org.id})")
        return org

    def _get_admin_user(self, org):
        admin_user = org.get_admins().first()
        if not admin_user:
            raise CommandError(f"No admin users found for organization {org.id}")
        if self.verbose:
            self.stdout.write(f"Using admin user: {admin_user.email}")
        return admin_user

    def _normalize_number(self, number, country):
        normalized = URN.normalize_number(number, country)
        if not URN.validate(URN.from_parts(URN.TEL_SCHEME, normalized), country):
            raise CommandError(f"Invalid phone number for country {country}: {number}")
        return normalized

    def _prepare_channel_config(self, options, address):
        return {
            Channel.CONFIG_BASE_URL: options["base_url"],
            Channel.CONFIG_USERNAME: options["username"],
            Channel.CONFIG_PASSWORD: options["password"],
            Channel.CONFIG_AUTH_TOKEN: "",  # filled by Turn token refresh / first login if needed
            CONFIG_FB_BUSINESS_ID: address.lstrip("+"),
            CONFIG_FB_ACCESS_TOKEN: options["access_token"],
            CONFIG_FB_NAMESPACE: options["namespace"],
            CONFIG_FB_TEMPLATE_LIST_DOMAIN: options["template_domain"],
        }

    def _show_dry_run(self, org, channel_name, address, config):
        self.stdout.write(self.style.WARNING("DRY RUN MODE - No channel will be created"))
        self.stdout.write(f"Organization: {org.name} (ID: {org.id})")
        self.stdout.write(f"Channel Name: {channel_name}")
        self.stdout.write(f"Address: {address}")
        self.stdout.write("Channel Type: Turn.io WhatsApp (TRN)")
        for key, value in config.items():
            if key in {Channel.CONFIG_PASSWORD, Channel.CONFIG_AUTH_TOKEN, CONFIG_FB_ACCESS_TOKEN}:
                self.stdout.write(f"  {key}: {'*' * max(len(str(value)), 8)}")
            else:
                self.stdout.write(f"  {key}: {value}")

    def _create_channel(self, org, admin_user, name, address, country, config, tps):
        try:
            turn_type = Channel.get_type_from_code("TRN")
        except ValueError as e:
            raise CommandError("Turn.io WhatsApp (TRN) channel type not found") from e

        # Obtain a live Turn auth token the same way the claim form does.
        import requests

        resp = requests.post(
            f"{config[Channel.CONFIG_BASE_URL].rstrip('/')}/v1/users/login",
            auth=(config[Channel.CONFIG_USERNAME], config[Channel.CONFIG_PASSWORD]),
            timeout=30,
        )
        if resp.status_code != 200:
            raise CommandError(f"Turn login failed with HTTP {resp.status_code}")
        config[Channel.CONFIG_AUTH_TOKEN] = resp.json()["users"][0]["token"]

        channel = Channel.create(
            org,
            admin_user,
            country,
            turn_type,
            name=name[:64],
            address=address,
            config=config,
            tps=tps,
        )

        channel.is_active = True
        channel.is_enabled = True
        channel.role = Channel.ROLE_SEND + Channel.ROLE_RECEIVE
        cfg = channel.config.copy()
        cfg["activated"] = True
        cfg["activation_date"] = timezone.now().isoformat()
        channel.config = cfg
        channel.save(update_fields=["is_active", "is_enabled", "role", "config"])
        return channel

    def _show_success(self, channel):
        receive_path = f"/c/trn/{channel.uuid}/receive"
        self.stdout.write(
            self.style.SUCCESS(
                f"Created Turn.io WhatsApp channel\n"
                f"  ID: {channel.id}\n"
                f"  UUID: {channel.uuid}\n"
                f"  Name: {channel.name}\n"
                f"  Address: {channel.address}\n"
                f"  Org: {channel.org.name}\n"
                f"  Turn receive URL path: {receive_path}\n"
                f"Point Turn callbacks at https://<your-domain>{receive_path}"
            )
        )
