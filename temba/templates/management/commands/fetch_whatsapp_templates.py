"""
Django management command to fetch WhatsApp templates from Meta's API and insert them into RapidPro database.

Usage examples:
  # Fetch templates using existing channel
  python manage.py fetch_whatsapp_templates --waba-id 123456789 --access-token YOUR_TOKEN --channel-id 5

  # Dry run to preview templates
  python manage.py fetch_whatsapp_templates --waba-id 123456789 --access-token YOUR_TOKEN --channel-id 5 --dry-run

  # Verbose output with template details
  python manage.py fetch_whatsapp_templates --waba-id 123456789 --access-token YOUR_TOKEN --channel-id 5 --verbose
"""

import json
import requests

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from temba.channels.models import Channel
from temba.channels.types.whatsapp.type import WhatsAppType
from temba.orgs.models import Org
from temba.templates.models import TemplateTranslation
from temba.users.models import User


class Command(BaseCommand):
    help = "Fetch WhatsApp templates from Meta API and insert into RapidPro database"

    def add_arguments(self, parser):
        # Meta API credentials (required)
        parser.add_argument("--waba-id", required=True, help="WhatsApp Business Account ID")
        parser.add_argument("--access-token", required=True, help="System User Access Token for WhatsApp Business API")

        # Channel selection (required)
        parser.add_argument("--channel-id", type=int, required=True, help="WhatsApp channel ID to use for template sync")

        # Options
        parser.add_argument(
            "--dry-run", action="store_true", help="Fetch templates but don't insert them into database"
        )
        parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        self.verbose = options.get("verbose", False)

        try:
            # 1. Validate parameters
            waba_id = options["waba_id"]
            access_token = options["access_token"]

            # 2. Get and validate channel
            channel = self._get_channel(options["channel_id"])

            # 3. Fetch templates from Meta API using provided credentials
            self.stdout.write("Fetching templates from Meta WhatsApp Business API...")
            raw_templates = self._fetch_templates_from_meta(waba_id, access_token, channel)

            if not raw_templates:
                self.stdout.write(self.style.WARNING("No templates found in your WhatsApp Business Account"))
                return

            self.stdout.write(f"Found {len(raw_templates)} templates")

            # 4. Show template details if verbose
            if self.verbose or options["dry_run"]:
                self._show_template_details(raw_templates)

            # 5. Process templates using RapidPro's existing logic (unless dry run)
            if not options["dry_run"]:
                template_count = self._process_templates(channel, raw_templates)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully processed {template_count} templates for channel {channel.id} ({channel.name})"
                    )
                )
            else:
                self.stdout.write(self.style.WARNING("Dry run mode - no templates were inserted"))

        except Exception as e:
            raise CommandError(f"Error: {str(e)}")

    def _get_channel(self, channel_id):
        """Get and validate the WhatsApp channel"""
        try:
            channel = Channel.objects.get(id=channel_id, is_active=True)
            if channel.channel_type not in ["WAC", "WA"]:
                raise CommandError(f"Channel {channel_id} is not a WhatsApp channel")
            
            if self.verbose:
                self.stdout.write(f"Using channel: {channel.id} ({channel.name})")
                self.stdout.write(f"  Channel Type: {channel.channel_type}")
                
                if channel.channel_type == "WAC":
                    # WhatsApp Cloud channel info
                    self.stdout.write(f"  Phone Number: {channel.config.get('wa_number', 'N/A')}")
                    self.stdout.write(f"  Verified Name: {channel.config.get('wa_verified_name', 'N/A')}")
                    self.stdout.write(f"  WABA ID: {channel.config.get('wa_waba_id', 'N/A')}")
                elif channel.channel_type == "WA":
                    # WhatsApp Legacy channel info
                    self.stdout.write(f"  Address: {channel.address}")
                    self.stdout.write(f"  Base URL: {channel.config.get('base_url', 'N/A')}")
                    self.stdout.write(f"  Business ID: {channel.config.get('fb_business_id', 'N/A')}")
                    self.stdout.write(f"  Template Domain: {channel.config.get('fb_template_list_domain', 'N/A')}")
            
            return channel
        except Channel.DoesNotExist:
            raise CommandError(f"Channel with ID {channel_id} not found or inactive")

    def _fetch_templates_from_meta(self, waba_id, access_token, channel):
        """Fetch templates from Meta's WhatsApp Business API"""
        url = f"https://whatsapp.turn.io/graph/v14.0/{waba_id}/message_templates"
        headers = {"Authorization": f"Bearer {access_token}"}
        templates = []

        while url:
            if self.verbose:
                self.stdout.write(f"Making API request to: {url}")

            try:
                response = requests.get(url, params={"limit": 255}, headers=headers)
                response.raise_for_status()

                data = response.json()
                templates.extend(data.get("data", []))

                # Check for pagination
                url = data.get("paging", {}).get("next", None)

                if self.verbose and url:
                    self.stdout.write(f"Found pagination, continuing...")

            except requests.RequestException as e:
                raise CommandError(f"Failed to fetch templates from Meta API: {str(e)}")

        return templates

    def _show_template_details(self, raw_templates):
        """Display template details"""
        self.stdout.write("\nTemplate Details:")
        self.stdout.write("-" * 50)

        for template in raw_templates:
            status_color = self.style.SUCCESS if template.get("status") == "APPROVED" else self.style.WARNING
            self.stdout.write(
                f"Name: {template.get('name', 'N/A')}\n"
                f"  Status: {status_color(template.get('status', 'N/A'))}\n"
                f"  Language: {template.get('language', 'N/A')}\n"
                f"  ID: {template.get('id', 'N/A')}\n"
                f"  Components: {len(template.get('components', []))}\n"
            )

            if self.verbose and template.get("components"):
                for i, component in enumerate(template["components"]):
                    comp_type = component.get("type", "UNKNOWN")
                    comp_text = component.get("text", "")[:50]
                    if len(component.get("text", "")) > 50:
                        comp_text += "..."
                    self.stdout.write(f"    Component {i+1}: {comp_type} - {comp_text}")

            self.stdout.write("")

    def _process_templates(self, channel, raw_templates):
        """Process templates using RapidPro's existing TemplateTranslation.update_local logic"""
        if self.verbose:
            self.stdout.write("Processing templates using RapidPro's existing sync logic...")

        # Use RapidPro's existing template sync logic
        TemplateTranslation.update_local(channel, raw_templates)

        # Return count of templates for this channel
        return channel.template_translations.count()
