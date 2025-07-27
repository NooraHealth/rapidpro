# WhatsApp Template Manual Sync Tool

This tool allows you to manually create WhatsApp Legacy channels and fetch WhatsApp templates from Turn.io's WhatsApp Business API and insert them into your RapidPro database, bypassing the automatic cron job system.

## Prerequisites

1. **WhatsApp Business Account**: You need a verified WhatsApp Business Account with Turn.io
2. **System User Access Token**: A valid access token for your WhatsApp Business Account
3. **WABA ID**: Your WhatsApp Business Account ID
4. **Auth Token**: Authentication token for WhatsApp API access
5. **RapidPro Database Access**: The script needs to run in your RapidPro environment

## Installation

The management commands are located at:
```
temba/templates/management/commands/create_whatsapp_channel.py
temba/templates/management/commands/fetch_whatsapp_templates.py
```

No additional installation is required - they use existing RapidPro dependencies.

## Overview

This tool provides **two separate commands**:

1. **`create_whatsapp_channel`** - Creates a new WhatsApp Legacy channel in RapidPro with custom base URL support
2. **`fetch_whatsapp_templates`** - Fetches templates from Meta API and syncs them to an existing channel

## Running the Commands

### Container Execution (Recommended)

Since these are Django management commands that need access to your RapidPro database and environment, you should run them **inside the Docker container**:

```bash
# Connect to the running RapidPro container
docker exec -it <container_name> bash

# Or if using docker-compose
docker-compose exec web bash

# Then run the commands inside the container
poetry run python manage.py create_whatsapp_channel [OPTIONS]
poetry run python manage.py fetch_whatsapp_templates [OPTIONS]
```

### Finding Your Container Name

To find your container name:
```bash
docker ps
# Look for the container running RapidPro (usually named something like 'rapidpro_web_1' or similar)
```

### Alternative: Direct Container Execution

You can also run the commands directly without entering the container:
```bash
docker exec -it <container_name> poetry run python manage.py create_whatsapp_channel [OPTIONS]
docker exec -it <container_name> poetry run python manage.py fetch_whatsapp_templates [OPTIONS]
```

### Using Poetry and Environment Variables (Recommended for Django Commands)

For Django commands that need database access, use this approach:

```bash
# Run Django shell with proper environment variables
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py shell

# Run the WhatsApp channel creation command
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py create_whatsapp_channel [OPTIONS]

# Run the WhatsApp template sync command
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py fetch_whatsapp_templates [OPTIONS]
```

**Note**: The `-e REMOTE_CONTAINERS=true -e POSTGIS=off` flags are essential for Django commands to work properly with the database connection.

## Command 1: Create WhatsApp Legacy Channel

### Basic Syntax
```bash
poetry run python manage.py create_whatsapp_channel --org-id <ORG_ID> --number <PHONE_NUMBER> --verified-name <BUSINESS_NAME> --phone-number-id <PHONE_NUMBER_ID> --waba-id <WABA_ID> --business-id <BUSINESS_ID> --auth-token <AUTH_TOKEN> [OPTIONS]
```

### Required Parameters

- `--org-id`: Organization ID in RapidPro
- `--number`: WhatsApp phone number (e.g., "+1234567890")
- `--verified-name`: Verified business name
- `--phone-number-id`: Phone number ID from Meta API
- `--waba-id`: WhatsApp Business Account ID
- `--business-id`: Facebook Business ID
- `--auth-token`: Authentication token for WhatsApp API access

### Optional Parameters

- `--base-url`: Custom API base URL (default: "https://whatsapp.turn.io")
- `--currency`: Account currency (default: "USD")
- `--namespace`: Message template namespace
- `--name`: Custom channel name (default: auto-generated from number and business name)
- `--skip-activation`: Skip Meta API activation and manually set channel as active

### Examples

#### 1. Create Channel with All Required Fields (from container)
```bash
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py create_whatsapp_channel \
    --org-id 1 \
    --number "+1234567890" \
    --verified-name "Your Business Name" \
    --phone-number-id "123456789" \
    --waba-id "987654321" \
    --business-id "555666777" \
    --auth-token "YOUR_AUTH_TOKEN"
```

#### 2. Create Channel with Custom Base URL (from container)
```bash
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py create_whatsapp_channel \
    --org-id 1 \
    --number "+1234567890" \
    --verified-name "Your Business Name" \
    --phone-number-id "123456789" \
    --waba-id "987654321" \
    --business-id "555666777" \
    --auth-token "YOUR_AUTH_TOKEN" \
    --base-url "https://whatsapp.turn.io"
```

#### 3. Create Channel with Skip Activation (for testing)
```bash
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py create_whatsapp_channel \
    --org-id 1 \
    --number "+1234567890" \
    --verified-name "Your Business Name" \
    --phone-number-id "123456789" \
    --waba-id "987654321" \
    --business-id "555666777" \
    --auth-token "YOUR_AUTH_TOKEN" \
    --skip-activation \
    --verbose
```

#### 4. Dry Run (Preview Only) - from container
```bash
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py create_whatsapp_channel \
    --org-id 1 \
    --number "+1234567890" \
    --verified-name "Your Business Name" \
    --phone-number-id "123456789" \
    --waba-id "987654321" \
    --business-id "555666777" \
    --auth-token "YOUR_AUTH_TOKEN" \
    --dry-run \
    --verbose
```

## Command 2: Fetch WhatsApp Templates

### Basic Syntax
```bash
python manage.py fetch_whatsapp_templates --waba-id <WABA_ID> --access-token <ACCESS_TOKEN> --channel-id <CHANNEL_ID> [OPTIONS]
```

### Required Parameters

- `--waba-id`: Your WhatsApp Business Account ID
- `--access-token`: System User Access Token for WhatsApp Business API
- `--channel-id`: WhatsApp channel ID to use for template sync

### Examples

#### 1. Fetch Templates Using Existing Channel (from container)
```bash
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py fetch_whatsapp_templates \
    --waba-id 123456789012345 \
    --access-token EAABwzLixnjYBOZCxxx \
    --channel-id 5
```

#### 2. Dry Run (Preview Only) - from container
```bash
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py fetch_whatsapp_templates \
    --waba-id 123456789012345 \
    --access-token EAABwzLixnjYBOZCxxx \
    --channel-id 5 \
    --dry-run \
    --verbose
```

## Complete Workflow Example

Here's a complete example of creating a channel and then fetching templates:

### Step 1: Create the WhatsApp Legacy Channel
```bash
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py create_whatsapp_channel \
    --org-id 1 \
    --number "+1234567890" \
    --verified-name "My Business" \
    --phone-number-id "123456789" \
    --waba-id "987654321" \
    --business-id "555666777" \
    --auth-token "YOUR_AUTH_TOKEN" \
    --base-url "https://whatsapp.turn.io" \
    --verbose
```

**Output:**
```
✅ Successfully created WhatsApp Legacy channel!
   Channel ID: 5
   Channel Name: +1234567890 - My Business
   Phone Number ID: 123456789
   Organization: My Organization
   Channel Type: WA (WhatsApp Legacy)
   Base URL: https://whatsapp.turn.io
   Created: 2024-01-15 10:30:00

   You can now use this channel ID (5) with the fetch_whatsapp_templates command.
```

### Step 2: Fetch Templates Using the Created Channel
```bash
docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py fetch_whatsapp_templates \
    --waba-id 987654321 \
    --access-token EAABwzLixnjYBOZCxxx \
    --channel-id 5 \
    --verbose
```

**Output:**
```
Fetching templates from Meta WhatsApp Business API...
Found 15 templates
Successfully processed 15 templates for channel 5 (+1234567890 - My Business)
```

## Command Options

### create_whatsapp_channel Options

#### Required
- `--org-id`: Organization ID in RapidPro
- `--number`: WhatsApp phone number
- `--verified-name`: Verified business name
- `--phone-number-id`: Phone number ID from Meta API
- `--waba-id`: WhatsApp Business Account ID
- `--business-id`: Facebook Business ID
- `--auth-token`: Authentication token for WhatsApp API access

#### Optional
- `--base-url`: Custom API base URL (default: "https://whatsapp.turn.io")
- `--currency`: Account currency (default: "USD")
- `--namespace`: Message template namespace
- `--name`: Custom channel name

#### Execution Options
- `--skip-activation`: Skip Meta API activation and manually set channel as active
- `--dry-run`: Show what would be created without creating it
- `--verbose`: Show detailed output
- `--verbosity {0,1,2,3}`: Set Django verbosity level

### fetch_whatsapp_templates Options

#### Required
- `--waba-id`: WhatsApp Business Account ID
- `--access-token`: System User Access Token
- `--channel-id`: WhatsApp channel ID to use for template sync

#### Execution Options
- `--dry-run`: Fetch templates but don't insert into database
- `--verbose`: Show detailed output including template details
- `--verbosity {0,1,2,3}`: Set Django verbosity level

## How It Works

### Channel Creation (WhatsApp Legacy)
1. **Validation**: Validates organization and admin user
2. **Configuration**: Prepares channel configuration with Legacy format:
   - `base_url`: Custom API endpoint (default: "https://whatsapp.turn.io")
   - `username`, `password`, `auth_token`: Authentication credentials
   - `fb_business_id`, `fb_access_token`: Facebook Business API credentials
   - `fb_namespace`, `fb_template_list_domain`: Template management settings
3. **Creation**: Uses RapidPro's existing `Channel.create()` method with `WA` channel type
4. **Manual Activation**: If `--skip-activation` is used, manually sets channel as active
5. **Output**: Returns channel ID for use with template sync

### Template Fetching
1. **Channel Validation**: Validates the specified WhatsApp channel
2. **API Fetching**: Makes authenticated requests to `https://whatsapp.turn.io/graph/v14.0/{waba_id}/message_templates`
3. **Pagination**: Automatically handles paginated responses from Turn.io's API
4. **Template Processing**: Uses RapidPro's existing `TemplateTranslation.update_local()` logic
5. **Database Insertion**: Safely inserts/updates templates using the same code paths as the built-in sync

## Key Differences from WhatsApp Cloud

### WhatsApp Legacy vs WhatsApp Cloud
- **Channel Type**: Uses `WA` instead of `WAC`
- **Base URL**: Supports custom API endpoints via `base_url` configuration
- **Authentication**: Uses username/password/auth_token instead of Facebook access tokens
- **TPS**: Lower throughput (80 TPS vs higher for Cloud)
- **Activation**: Can skip Meta API activation for testing environments

### Configuration Structure
```json
{
  "base_url": "https://whatsapp.turn.io",
  "username": "test_user",
  "password": "test_pass",
  "auth_token": "YOUR_AUTH_TOKEN",
  "fb_business_id": "8801678380056",
  "fb_access_token": "EAABwzLixnjYBOZCxxx",
  "fb_namespace": "test_namespace",
  "fb_template_list_domain": "graph.facebook.com",
  "fb_template_list_domain_api_version": "v14.0"
}
```

## Output Examples

### Successful Channel Creation
```
✅ Successfully created WhatsApp Legacy channel!
   Channel ID: 5
   Channel Name: +1234567890 - My Business
   Phone Number ID: 123456789
   Organization: My Organization
   Channel Type: WA (WhatsApp Legacy)
   Base URL: https://whatsapp.turn.io
   Created: 2024-01-15 10:30:00

   You can now use this channel ID (5) with the fetch_whatsapp_templates command.
```

### Successful Template Sync
```
Fetching templates from Meta WhatsApp Business API...
Found 15 templates
Successfully processed 15 templates for channel 5 (+1234567890 - My Business)
```

### Dry Run Output
```
DRY RUN MODE - No channel will be created
==================================================
Organization: My Organization (ID: 1)
Channel Name: +1234567890 - My Business
Channel Type: WhatsApp Legacy (WA)
Configuration:
  base_url: https://whatsapp.turn.io
  username: test_user
  password: ******
  auth_token: ******
  fb_business_id: 8801678380056
  fb_access_token: ******
  fb_namespace: test_namespace
  fb_template_list_domain: graph.facebook.com
  fb_template_list_domain_api_version: v14.0
==================================================
```

## Getting Your Credentials

### WhatsApp Business Account ID (WABA ID)
1. Go to Turn.io Business Manager
2. Navigate to WhatsApp Business Accounts
3. Your WABA ID is shown in the account details

### System User Access Token
1. Create a System User in Turn.io Business Manager
2. Assign WhatsApp Business Management permissions
3. Generate a permanent access token
4. The token should have these permissions:
   - `whatsapp_business_management`
   - `whatsapp_business_messaging`

### Auth Token
1. This is your WhatsApp API authentication token
2. Can be obtained from Turn.io or your WhatsApp Business API provider
3. Used for authenticating API requests to your custom base URL

### Phone Number ID
1. In Turn.io Business Manager, go to your WhatsApp Business Account
2. Navigate to Phone Numbers
3. Select your phone number
4. The Phone Number ID is displayed in the details

### Facebook Business ID
1. In Turn.io Business Manager, go to Business Settings
2. Your Business ID is shown in the account information

### Finding Organization ID
```bash
# From inside the container
docker exec -it <container_name> python manage.py shell
>>> from temba.orgs.models import Org
>>> Org.objects.all().values('id', 'name')
```

### Finding Existing Channel ID
```bash
# From inside the container
docker exec -it <container_name> python manage.py shell
>>> from temba.channels.models import Channel
>>> Channel.objects.filter(channel_type='WA', is_active=True).values('id', 'name', 'address')
```

## Troubleshooting

### Common Errors

**"Organization with ID X not found or inactive"**
- The specified organization ID doesn't exist or is inactive
- Check organization ID with the query above

**"No admin users found for organization X"**
- The organization has no admin users
- Add an admin user to the organization first

**"Channel X is not a WhatsApp channel"**
- The specified channel ID is not a WhatsApp (WA) channel type
- Use the query above to find WhatsApp Legacy channels

**"Failed to fetch templates from Turn.io API: 401"**
- Invalid or expired access token
- Check token permissions and expiration

**"No templates found in your WhatsApp Business Account"**
- No templates exist in your WABA
- Create templates in Turn.io Business Manager first

**"Container not found"**
- Make sure your RapidPro container is running
- Use `docker ps` to find the correct container name

**"Database connection failed" or "ModuleNotFoundError: No module named 'django'"**
- Use the correct command format with environment variables:
  ```bash
  docker exec -e REMOTE_CONTAINERS=true -e POSTGIS=off -it rapidpro-rapidpro-1 poetry run python manage.py <command>
  ```
- The `-e REMOTE_CONTAINERS=true -e POSTGIS=off` flags are essential for Django commands to work properly
- Always use `poetry run python` instead of just `python` to ensure Django is available

**"Unable to subscribe to app to WABA"**
- This is expected when using `--skip-activation`
- The script will automatically handle this and manually activate the channel
- For production, ensure proper Meta API credentials

### API Rate Limits
Turn.io's API has rate limits. If you hit them:
- Wait a few minutes and retry
- The script automatically handles pagination to minimize requests

### Database Permissions
Ensure the Django user has permissions to:
- Read from `orgs_org`, `channels_channel`, `users_user` tables
- Write to `channels_channel`, `templates_template`, `templates_templatetranslation` tables

## Security Notes

- Access tokens and auth tokens are sensitive - don't log them or include in version control
- Use environment variables for credentials in production
- The scripts validate all inputs and use existing RapidPro security measures
- Dry run mode is recommended for first-time usage
- Auth tokens are masked in verbose output for security

## Support

For issues with:
- **RapidPro Integration**: Check Django logs and database permissions
- **Turn.io API**: Verify credentials and WABA status in Turn.io Business Manager
- **Template Processing**: Compare with existing RapidPro template sync logs
- **Container Access**: Ensure your Docker container is running and accessible
- **Custom Base URLs**: Verify your API endpoint is accessible and properly configured