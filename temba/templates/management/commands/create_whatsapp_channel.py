"""
Django management command to create WhatsApp channels in RapidPro.

Usage examples:
  # Create a new WhatsApp channel
  python manage.py create_whatsapp_channel --org-id 1 --number "+1234567890" --verified-name "Your Business" --phone-number-id "123456789" --waba-id "987654321" --business-id "555666777" --currency "USD" --namespace "your_namespace"

  # Create with minimal required fields
  python manage.py create_whatsapp_channel --org-id 1 --number "+1234567890" --verified-name "Your Business" --phone-number-id "123456789" --waba-id "987654321" --business-id "555666777"
"""

from random import randint

from django.core.management.base import BaseCommand, CommandError

from temba.channels.models import Channel
from temba.orgs.models import Org


class Command(BaseCommand):
    help = "Create a new WhatsApp channel in RapidPro"

    def add_arguments(self, parser):
        # Organization (required)
        parser.add_argument("--org-id", type=int, required=True, help="Organization ID")

        # Channel details (required)
        parser.add_argument("--number", required=True, help="WhatsApp phone number (e.g., '+1234567890')")
        parser.add_argument("--verified-name", required=True, help="Verified business name")
        parser.add_argument("--phone-number-id", required=True, help="Phone number ID from Meta API")
        parser.add_argument("--waba-id", required=True, help="WhatsApp Business Account ID")
        parser.add_argument("--business-id", required=True, help="Facebook Business ID")

        # Optional channel details
        parser.add_argument("--currency", default="USD", help="Account currency (default: USD)")
        parser.add_argument("--namespace", default="", help="Message template namespace")
        parser.add_argument("--name", help="Custom channel name (default: auto-generated)")

        # Options
        parser.add_argument("--verbose", action="store_true", help="Show detailed output")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be created without creating it")

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        self.verbose = options.get("verbose", False)

        try:
            # 1. Validate organization
            org = self._get_organization(options["org_id"])

            # 2. Get admin user
            admin_user = self._get_admin_user(org)

            # 3. Prepare channel configuration
            channel_config = self._prepare_channel_config(options)

            # 4. Generate channel name
            channel_name = self._generate_channel_name(options)

            # 5. Show what would be created (if dry run)
            if options["dry_run"]:
                self._show_dry_run_info(org, channel_name, channel_config, options)
                return

            # 6. Create the channel
            channel = self._create_channel(org, admin_user, channel_name, options["phone_number_id"], channel_config)

            # 7. Show success message
            self._show_success_message(channel)

        except Exception as e:
            raise CommandError(f"Error: {str(e)}")

    def _get_organization(self, org_id):
        """Get and validate organization"""
        try:
            org = Org.objects.get(id=org_id, is_active=True)
            if self.verbose:
                self.stdout.write(f"Found organization: {org.name} (ID: {org.id})")
            return org
        except Org.DoesNotExist:
            raise CommandError(f"Organization with ID {org_id} not found or inactive")

    def _get_admin_user(self, org):
        """Get admin user for the organization"""
        admin_user = org.get_admins().first()
        if not admin_user:
            raise CommandError(f"No admin users found for organization {org.id}")
        
        if self.verbose:
            self.stdout.write(f"Using admin user: {admin_user.username}")
        
        return admin_user

    def _prepare_channel_config(self, options):
        """Prepare channel configuration dictionary"""
        config = {
            "wa_number": options["number"],
            "wa_verified_name": options["verified_name"],
            "wa_waba_id": options["waba_id"],
            "wa_currency": options.get("currency", "USD"),
            "wa_business_id": options["business_id"],
            "wa_message_template_namespace": options.get("namespace", ""),
            "wa_pin": str(randint(100000, 999999)),
        }
        
        if self.verbose:
            self.stdout.write("Channel configuration prepared:")
            for key, value in config.items():
                if key == "wa_pin":
                    self.stdout.write(f"  {key}: {'*' * len(value)}")
                else:
                    self.stdout.write(f"  {key}: {value}")
        
        return config

    def _generate_channel_name(self, options):
        """Generate channel name"""
        if options.get("name"):
            return options["name"][:64]  # Truncate to 64 chars
        
        # Auto-generate name from number and verified name
        name = f"{options['number']} - {options['verified_name']}"
        return name[:64]  # Truncate to 64 chars

    def _show_dry_run_info(self, org, channel_name, channel_config, options):
        """Show what would be created in dry run mode"""
        self.stdout.write(self.style.WARNING("DRY RUN MODE - No channel will be created"))
        self.stdout.write("=" * 50)
        self.stdout.write(f"Organization: {org.name} (ID: {org.id})")
        self.stdout.write(f"Channel Name: {channel_name}")
        self.stdout.write(f"Phone Number ID: {options['phone_number_id']}")
        self.stdout.write(f"Channel Type: WhatsApp (WAC)")
        self.stdout.write("Configuration:")
        for key, value in channel_config.items():
            if key == "wa_pin":
                self.stdout.write(f"  {key}: {'*' * len(value)}")
            else:
                self.stdout.write(f"  {key}: {value}")
        self.stdout.write("=" * 50)

    def _create_channel(self, org, admin_user, name, phone_number_id, config):
        """Create the WhatsApp channel"""
        if self.verbose:
            self.stdout.write("Creating WhatsApp channel...")

        # Get WhatsApp channel type
        whatsapp_type = None
        for channel_type in Channel.get_types():
            if channel_type.code == "WAC":
                whatsapp_type = channel_type
                break

        if not whatsapp_type:
            raise CommandError("WhatsApp channel type not found")

        # Create the channel
        channel = Channel.create(
            org,
            admin_user,
            None,  # country
            whatsapp_type,
            name=name,
            address=phone_number_id,
            config=config,
            tps=80,
        )

        if self.verbose:
            self.stdout.write(f"Channel created with ID: {channel.id}")
            self.stdout.write(f"Channel UUID: {channel.uuid}")

        return channel

    def _show_success_message(self, channel):
        """Show success message with channel details"""
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Successfully created WhatsApp channel!\n"
                f"   Channel ID: {channel.id}\n"
                f"   Channel Name: {channel.name}\n"
                f"   Phone Number ID: {channel.address}\n"
                f"   Organization: {channel.org.name}\n"
                f"   Created: {channel.created_on.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"   You can now use this channel ID ({channel.id}) with the fetch_whatsapp_templates command."
            )
        ) 