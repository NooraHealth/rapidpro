"""
Django management command to manually insert a WhatsApp auth_token for sending messages and activate the channel.

This command specifically updates the auth_token in a channel's configuration that is used
for sending WhatsApp messages via the courier service, and also activates the channel
for test environments without calling Meta's API.

Usage examples:
  # Insert auth_token and activate channel
  python manage.py insert_whatsapp_token --channel-id 5 --token YOUR_AUTH_TOKEN

  # Insert auth_token and activate with verbose output
  python manage.py insert_whatsapp_token --channel-id 5 --token YOUR_AUTH_TOKEN --verbose

  # Dry run to preview changes
  python manage.py insert_whatsapp_token --channel-id 5 --token YOUR_AUTH_TOKEN --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from temba.channels.models import Channel


class Command(BaseCommand):
    help = "Manually insert a WhatsApp auth_token and activate the channel for test environments"

    def add_arguments(self, parser):
        # Channel selection (required)
        parser.add_argument("--channel-id", type=int, required=True, help="WhatsApp channel ID to update")

        # Auth token (required)
        parser.add_argument("--token", required=True, help="WhatsApp auth_token for sending messages")

        # Options
        parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
        parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        self.verbose = options.get("verbose", False)

        try:
            # 1. Get and validate channel
            channel = self._get_channel(options["channel_id"])
            
            # 2. Get auth_token
            auth_token = options["token"]
            
            if self.verbose:
                self.stdout.write(f"Channel: {channel.id} ({channel.name})")
                self.stdout.write(f"Channel Type: {channel.channel_type}")
                self.stdout.write(f"Current Config Keys: {list(channel.config.keys())}")
                if "auth_token" in channel.config:
                    current_token = channel.config["auth_token"]
                    self.stdout.write(f"Current auth_token: {current_token[:10]}...")
                else:
                    self.stdout.write("No existing auth_token found")

            # 3. Validate auth_token format (basic check)
            if not self._validate_auth_token_format(auth_token):
                raise CommandError("Auth token format appears invalid. Please check your token.")

            # 4. Show preview if dry run
            if options["dry_run"]:
                self._show_preview(channel, auth_token)
                return

            # 5. Update channel configuration with auth_token and activation
            self._update_channel_config(channel, auth_token)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Successfully updated channel {channel.id} ({channel.name})\n"
                    f"   - Auth token inserted\n"
                    f"   - Channel activated for test environment"
                )
            )

        except Exception as e:
            raise CommandError(f"Error: {str(e)}")

    def _get_channel(self, channel_id):
        """Get and validate the WhatsApp channel"""
        try:
            channel = Channel.objects.get(id=channel_id, is_active=True)
            
            # Check if it's a WhatsApp channel
            if channel.channel_type not in ["WAC", "WA", "TWA", "ZVW", "D3C", "KWA"]:
                self.stdout.write(
                    self.style.WARNING(
                        f"Warning: Channel {channel_id} is not a WhatsApp channel type "
                        f"(found: {channel.channel_type})"
                    )
                )
            
            if self.verbose:
                self.stdout.write(f"Found channel: {channel.id} ({channel.name})")
                self.stdout.write(f"  Type: {channel.channel_type}")
                self.stdout.write(f"  Address: {channel.address}")
                self.stdout.write(f"  Config keys: {list(channel.config.keys())}")
            
            return channel
        except Channel.DoesNotExist:
            raise CommandError(f"Channel with ID {channel_id} not found or inactive")

    def _validate_auth_token_format(self, auth_token):
        """Basic validation of auth_token format"""
        if not auth_token or len(auth_token) < 10:
            return False
        
        # Check for common auth_token patterns
        if auth_token.startswith("EAAB") or auth_token.startswith("EAA"):  # Facebook/WhatsApp tokens
            return True
        if len(auth_token) >= 50:  # Generic long token
            return True
        
        return True  # Accept any token for manual insertion

    def _show_preview(self, channel, auth_token):
        """Show preview of changes without applying them"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("DRY RUN - PREVIEW OF CHANGES")
        self.stdout.write("="*50)
        
        self.stdout.write(f"Channel: {channel.id} ({channel.name})")
        self.stdout.write(f"Channel Type: {channel.channel_type}")
        
        if "auth_token" in channel.config:
            old_token = channel.config["auth_token"]
            self.stdout.write(f"Current auth_token: {old_token[:10]}...")
        else:
            self.stdout.write("Current auth_token: None")
        
        self.stdout.write(f"New auth_token: {auth_token[:10]}...")
        self.stdout.write(f"Token length: {len(auth_token)} characters")
        
        self.stdout.write("\nACTIVATION CHANGES:")
        self.stdout.write("  - Add 'activated': True")
        self.stdout.write("  - Add 'test_environment': True")
        self.stdout.write("  - Add 'skip_meta_validation': True")
        self.stdout.write("  - Add activation timestamp")
        
        # Check required fields
        config = channel.config
        required_fields = ["wa_waba_id", "wa_pin", "wa_verified_name"]
        self.stdout.write("\nREQUIRED FIELDS CHECK:")
        for field in required_fields:
            if field in config:
                value = config[field]
                if field == "wa_pin":
                    value = "*" * len(str(value))
                self.stdout.write(f"  ✅ {field}: {value}")
            else:
                self.stdout.write(f"  ❌ {field}: Missing (will be added)")
        
        self.stdout.write("\nThis would update the channel's auth_token and activate it for test use.")
        self.stdout.write("Use --verbose for more details.")

    def _update_channel_config(self, channel, auth_token):
        """Update the channel's configuration with auth_token and activation"""
        if self.verbose:
            self.stdout.write("Updating channel configuration...")
        
        # Get current config
        config = channel.config.copy()
        
        # 1. Add auth_token
        config["auth_token"] = auth_token
        
        # 2. Add activation flags
        config.update({
            "activated": True,
            "activation_date": timezone.now().isoformat(),
            "test_environment": True,  # Mark as test environment
            "skip_meta_validation": True,  # Skip Meta API validation
        })
        
        # 3. Ensure required WhatsApp config fields exist
        if "wa_waba_id" not in config:
            config["wa_waba_id"] = "test_waba_id"
            if self.verbose:
                self.stdout.write("  ✅ Added wa_waba_id")
        
        if "wa_pin" not in config:
            config["wa_pin"] = "123456"
            if self.verbose:
                self.stdout.write("  ✅ Added wa_pin")
        
        if "wa_verified_name" not in config:
            config["wa_verified_name"] = "Test Business"
            if self.verbose:
                self.stdout.write("  ✅ Added wa_verified_name")
        
        # 4. Update the channel
        channel.config = config
        channel.modified_on = timezone.now()
        channel.save(update_fields=["config", "modified_on"])
        
        if self.verbose:
            self.stdout.write("  ✅ Channel config updated")
            self.stdout.write("  ✅ Auth token stored")
            self.stdout.write("  ✅ Activation flags added")
            self.stdout.write(f"  ✅ Updated config keys: {list(channel.config.keys())}") 