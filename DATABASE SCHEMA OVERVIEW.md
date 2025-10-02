# RapidPro Database Schema Documentation

This document provides a comprehensive overview of RapidPro's PostgreSQL database schema, focusing on business-critical tables that are useful for analytics, campaign tracking, and contact interaction analysis.

> 💡 **Interactive Visualization**: For an interactive, visual exploration of this schema with clickable tables and relationships, open the `database_visualization.html` file in your browser.

## Table of Contents

1. [Core Tables](#core-tables)
   - [Organizations](#organizations-orgs_org)
   - [Contacts](#contacts-contacts_contact)
   - [Contact Groups](#contact-groups-contacts_contactgroup)
   - [Contact URNs](#contact-urns-contacts_contacturn)
   - [Contact Fields](#contact-fields-contacts_contactfield)
2. [Messaging Tables](#messaging-tables)
   - [Messages](#messages-msgs_msg)
   - [Broadcasts](#broadcasts-msgs_broadcast)
   - [Labels](#labels-msgs_label)
   - [Opt-Ins](#opt-ins-msgs_optin)
   - [Media](#media-msgs_media)
3. [Flow Tables](#flow-tables)
   - [Flows](#flows-flows_flow)
   - [Flow Runs](#flow-runs-flows_flowrun)
   - [Flow Sessions](#flow-sessions-flows_flowsession)
   - [Flow Starts](#flow-starts-flows_flowstart)
   - [Flow Labels](#flow-labels-flows_flowlabel)
4. [Campaign Tables](#campaign-tables)
   - [Campaigns](#campaigns-campaigns_campaign)
   - [Campaign Events](#campaign-events-campaigns_campaignevent)
5. [Channel Tables](#channel-tables)
   - [Channels](#channels-channels_channel)
   - [Channel Events](#channel-events-channels_channelevent)
6. [Ticketing Tables](#ticketing-tables)
   - [Tickets](#tickets-tickets_ticket)
   - [Ticket Events](#ticket-events-tickets_ticketevent)
   - [Topics](#topics-tickets_topic)
   - [Teams](#teams-tickets_team)
7. [Automation Tables](#automation-tables)
   - [Triggers](#triggers-triggers_trigger)
   - [Schedules](#schedules-schedules_schedule)
   - [Globals](#globals-globals_global)
8. [Template Tables](#template-tables)
   - [Templates](#templates-templates_template)
   - [Template Translations](#template-translations-templates_templatetranslation)
9. [AI & Classifier Tables](#ai--classifier-tables)
   - [Classifiers](#classifiers-classifiers_classifier)
   - [Intents](#intents-classifiers_intent)

---

## Core Tables

### Organizations (`orgs_org`)

The root organizational entity that contains all other data. Each organization represents a separate workspace.

| Column           | Type         | Description                                                                  |
| ---------------- | ------------ | ---------------------------------------------------------------------------- |
| `id`             | integer      | Primary key                                                                  |
| `uuid`           | uuid         | Unique identifier for the organization                                       |
| `name`           | varchar(128) | Organization name                                                            |
| `parent_id`      | integer      | Foreign key to parent org (for child workspaces)                             |
| `timezone`       | varchar      | Organization timezone (e.g., 'America/New_York')                             |
| `date_format`    | char(1)      | Date format preference: 'D' (day-first), 'M' (month-first), 'Y' (year-first) |
| `language`       | varchar(64)  | Default language code                                                        |
| `flow_languages` | text[]       | Array of language codes used in flows                                        |
| `country_id`     | integer      | Foreign key to default country (locations_adminboundary)                     |
| `is_anon`        | boolean      | Whether contact identifiers are anonymized                                   |
| `is_flagged`     | boolean      | Whether org is flagged for suspicious activity                               |
| `is_suspended`   | boolean      | Whether org is currently suspended                                           |
| `suspended_on`   | timestamp    | When org was suspended                                                       |
| `released_on`    | timestamp    | When org was released (deleted)                                              |
| `config`         | jsonb        | Configuration settings                                                       |
| `features`       | text[]       | Array of enabled features                                                    |
| `limits`         | jsonb        | Resource limits                                                              |
| `created_on`     | timestamp    | When org was created                                                         |
| `modified_on`    | timestamp    | Last modification time                                                       |

**Key Relationships:**

- Parent to `contacts_contact`, `flows_flow`, `msgs_msg`, `campaigns_campaign`, `channels_channel`, `tickets_ticket`

---

### Contacts (`contacts_contact`)

Represents individuals/entities that can be messaged and tracked.

| Column                 | Type         | Description                                                |
| ---------------------- | ------------ | ---------------------------------------------------------- |
| `id`                   | integer      | Primary key                                                |
| `uuid`                 | uuid         | Unique identifier                                          |
| `org_id`               | integer      | Foreign key to orgs_org                                    |
| `name`                 | varchar(128) | Contact's name                                             |
| `language`             | varchar(3)   | Contact's preferred language (ISO-639-3)                   |
| `status`               | char(1)      | 'A' (Active), 'B' (Blocked), 'S' (Stopped), 'V' (Archived) |
| `fields`               | jsonb        | Custom field values, keyed by field UUID                   |
| `current_flow_id`      | integer      | Foreign key to flow contact is currently in                |
| `current_session_uuid` | uuid         | UUID of active session if waiting                          |
| `ticket_count`         | integer      | Number of open tickets                                     |
| `last_seen_on`         | timestamp    | Last time contact interacted                               |
| `created_on`           | timestamp    | When contact was created                                   |
| `modified_on`          | timestamp    | Last modification time                                     |
| `created_by_id`        | integer      | User who created the contact                               |
| `modified_by_id`       | integer      | User who last modified                                     |

**Key Relationships:**

- Many-to-Many with `contacts_contactgroup` (via contacts_contactgroup_contacts)
- One-to-Many with `contacts_contacturn` (contact URNs)
- One-to-Many with `msgs_msg` (messages)
- One-to-Many with `flows_flowrun` (flow runs)
- One-to-Many with `tickets_ticket` (tickets)

**Status Values:**

- **A (Active)**: Contact is active and can participate in flows and campaigns
- **B (Blocked)**: Contact is blocked; messages will be ignored
- **S (Stopped)**: Contact opted out; messages ignored until they message again
- **V (Archived)**: Contact is archived (soft deleted)

---

### Contact Groups (`contacts_contactgroup`)

Groups of contacts, either manually managed or query-based (smart groups).

| Column        | Type         | Description                                                       |
| ------------- | ------------ | ----------------------------------------------------------------- |
| `id`          | integer      | Primary key                                                       |
| `uuid`        | uuid         | Unique identifier                                                 |
| `org_id`      | integer      | Foreign key to orgs_org                                           |
| `name`        | varchar(128) | Group name                                                        |
| `group_type`  | char(1)      | 'M' (Manual), 'Q' (Smart/Query), 'A/B/S/V' (System status groups) |
| `status`      | char(1)      | 'I' (Initializing), 'V' (Evaluating), 'R' (Ready)                 |
| `query`       | text         | Query string for smart groups                                     |
| `is_system`   | boolean      | Whether this is a system group                                    |
| `is_active`   | boolean      | Whether group is active                                           |
| `created_on`  | timestamp    | When group was created                                            |
| `modified_on` | timestamp    | Last modification time                                            |

**Group Types:**

- **M (Manual)**: Membership is manually managed
- **Q (Smart)**: Membership based on query evaluation
- **A (DB Active)**: System group for status=Active contacts
- **B (DB Blocked)**: System group for status=Blocked contacts
- **S (DB Stopped)**: System group for status=Stopped contacts
- **V (DB Archived)**: System group for status=Archived contacts

**Key Relationships:**

- Many-to-Many with `contacts_contact` (via contacts_contactgroup_contacts)
- Many-to-Many with `contacts_contactfield` (query_fields - fields used in smart group query)
- One-to-Many with `campaigns_campaign` (campaigns targeting this group)

---

### Contact URNs (`contacts_contacturn`)

Universal Resource Names - unique identifiers for contacts (phone numbers, social media handles, etc.)

| Column        | Type         | Description                                        |
| ------------- | ------------ | -------------------------------------------------- |
| `id`          | integer      | Primary key                                        |
| `org_id`      | integer      | Foreign key to orgs_org                            |
| `contact_id`  | integer      | Foreign key to contacts_contact                    |
| `channel_id`  | integer      | Foreign key to channels_channel (channel affinity) |
| `identity`    | varchar(255) | Full URN (scheme:path)                             |
| `scheme`      | varchar(128) | URN scheme (tel, mailto, whatsapp, telegram, etc.) |
| `path`        | varchar(255) | URN path (the actual identifier)                   |
| `display`     | varchar(255) | Display name (optional)                            |
| `priority`    | integer      | Priority (1000=highest, used for ordering)         |
| `auth_tokens` | jsonb        | Authentication tokens (channel-specific)           |

**Common Schemes:**

- **tel**: Phone numbers (E.164 format recommended)
- **mailto**: Email addresses
- **whatsapp**: WhatsApp identifiers
- **telegram**: Telegram user IDs
- **facebook**: Facebook Messenger IDs
- **instagram**: Instagram IDs
- **twitter**: Twitter handles
- **twitterid**: Twitter user IDs

**Key Relationships:**

- Many-to-One with `contacts_contact`
- Many-to-One with `channels_channel`
- One-to-Many with `msgs_msg` (messages sent/received via this URN)

---

### Contact Fields (`contacts_contactfield`)

Custom fields defined for contacts to store additional attributes.

| Column          | Type        | Description                                                  |
| --------------- | ----------- | ------------------------------------------------------------ |
| `id`            | integer     | Primary key                                                  |
| `uuid`          | uuid        | Unique identifier                                            |
| `org_id`        | integer     | Foreign key to orgs_org                                      |
| `key`           | varchar(36) | Field key (lowercase, alphanumeric + underscore)             |
| `name`          | varchar(36) | Display name                                                 |
| `value_type`    | char(1)     | 'T' (Text), 'N' (Number), 'D' (Datetime), 'S/I/W' (Location) |
| `is_system`     | boolean     | Whether this is a system field (created_on, last_seen_on)    |
| `is_proxy`      | boolean     | Whether field is a proxy for a contact property              |
| `show_in_table` | boolean     | Whether to show in contact tables                            |
| `priority`      | integer     | Display priority                                             |
| `agent_access`  | char(1)     | 'N' (None/Hidden), 'V' (View), 'E' (Edit)                    |
| `is_active`     | boolean     | Whether field is active                                      |
| `created_on`    | timestamp   | When field was created                                       |
| `modified_on`   | timestamp   | Last modification time                                       |

**Value Types:**

- **T (Text)**: Free text values
- **N (Number)**: Numeric values
- **D (Datetime)**: Date and time values
- **S (State)**: Location state
- **I (District)**: Location district
- **W (Ward)**: Location ward

**System Fields:**

- **created_on**: When contact was created
- **last_seen_on**: Last interaction time

---

## Messaging Tables

### Messages (`msgs_msg`)

All messages sent to or received from contacts.

| Column           | Type         | Description                                                                   |
| ---------------- | ------------ | ----------------------------------------------------------------------------- |
| `id`             | bigint       | Primary key                                                                   |
| `uuid`           | uuid         | Unique identifier                                                             |
| `org_id`         | integer      | Foreign key to orgs_org                                                       |
| `channel_id`     | integer      | Foreign key to channels_channel                                               |
| `contact_id`     | integer      | Foreign key to contacts_contact                                               |
| `contact_urn_id` | integer      | Foreign key to contacts_contacturn                                            |
| `broadcast_id`   | integer      | Foreign key to msgs_broadcast (if from broadcast)                             |
| `flow_id`        | integer      | Foreign key to flows_flow (if from flow)                                      |
| `ticket_id`      | integer      | Foreign key to tickets_ticket (if ticket reply)                               |
| `text`           | text         | Message text content                                                          |
| `attachments`    | text[]       | Array of attachment URLs                                                      |
| `quick_replies`  | text[]       | Array of quick reply options                                                  |
| `locale`         | varchar(6)   | Language locale (e.g., 'eng', 'spa-MX')                                       |
| `direction`      | char(1)      | 'I' (Incoming), 'O' (Outgoing)                                                |
| `status`         | char(1)      | Message status (see below)                                                    |
| `msg_type`       | char(1)      | 'T' (Text), 'O' (Opt-In), 'V' (Voice/IVR)                                     |
| `visibility`     | char(1)      | 'V' (Visible), 'A' (Archived), 'D' (Deleted by user), 'X' (Deleted by sender) |
| `high_priority`  | boolean      | Whether message should be sent with high priority                             |
| `created_on`     | timestamp    | When message was created (event time for flow messages)                       |
| `modified_on`    | timestamp    | Last modification time                                                        |
| `sent_on`        | timestamp    | When message was sent                                                         |
| `msg_count`      | integer      | Number of actual channel messages sent                                        |
| `error_count`    | integer      | Number of send attempts that errored                                          |
| `next_attempt`   | timestamp    | When next retry will occur                                                    |
| `failed_reason`  | char(1)      | Reason for failure (if failed)                                                |
| `external_id`    | varchar(255) | External ID from channel provider                                             |

**Status Values (Outgoing):**

- **I (Initializing)**: Created but not yet queued
- **Q (Queued)**: Queued to courier for sending
- **W (Wired)**: Sent request to channel
- **S (Sent)**: Channel confirmed sent
- **D (Delivered)**: Channel confirmed delivered
- **R (Read)**: Channel confirmed read
- **E (Errored)**: Temporary error, will retry
- **F (Failed)**: Permanent failure

**Status Values (Incoming):**

- **P (Pending)**: Received but not yet handled
- **H (Handled)**: Processed by flow engine

**Key Relationships:**

- Many-to-One with `contacts_contact`
- Many-to-One with `channels_channel`
- Many-to-One with `msgs_broadcast`
- Many-to-One with `flows_flow`
- Many-to-Many with `msgs_label` (via msgs_msg_labels)

---

### Broadcasts (`msgs_broadcast`)

Messages sent to multiple recipients at once.

| Column          | Type       | Description                                                                                  |
| --------------- | ---------- | -------------------------------------------------------------------------------------------- |
| `id`            | integer    | Primary key                                                                                  |
| `org_id`        | integer    | Foreign key to orgs_org                                                                      |
| `status`        | char(1)    | 'P' (Pending), 'Q' (Queued), 'S' (Started), 'C' (Completed), 'F' (Failed), 'I' (Interrupted) |
| `contact_count` | integer    | Total number of recipients (null until queued)                                               |
| `translations`  | jsonb      | Message content by language                                                                  |
| `base_language` | varchar(3) | Base language (ISO-639-3)                                                                    |
| `optin_id`      | integer    | Foreign key to msgs_optin (if opt-in broadcast)                                              |
| `template_id`   | integer    | Foreign key to templates_template (if template message)                                      |
| `urns`          | text[]     | Array of URN strings to send to                                                              |
| `query`         | text       | Query string for dynamic recipients                                                          |
| `exclusions`    | jsonb      | Exclusion criteria                                                                           |
| `schedule_id`   | integer    | Foreign key to schedules_schedule (if scheduled)                                             |
| `parent_id`     | integer    | Foreign key to parent broadcast (for scheduled broadcasts)                                   |
| `is_active`     | boolean    | Whether broadcast is active                                                                  |
| `created_on`    | timestamp  | When broadcast was created                                                                   |
| `created_by_id` | integer    | User who created                                                                             |

**Key Relationships:**

- Many-to-Many with `contacts_contact` (via msgs_broadcast_contacts)
- Many-to-Many with `contacts_contactgroup` (via msgs_broadcast_groups)
- One-to-Many with `msgs_msg` (messages created from broadcast)

---

### Labels (`msgs_label`)

Tags that can be applied to messages for organization.

| Column        | Type        | Description             |
| ------------- | ----------- | ----------------------- |
| `id`          | integer     | Primary key             |
| `uuid`        | uuid        | Unique identifier       |
| `org_id`      | integer     | Foreign key to orgs_org |
| `name`        | varchar(64) | Label name              |
| `is_active`   | boolean     | Whether label is active |
| `created_on`  | timestamp   | When label was created  |
| `modified_on` | timestamp   | Last modification time  |

**Key Relationships:**

- Many-to-Many with `msgs_msg` (via msgs_msg_labels)

---

### Opt-Ins (`msgs_optin`)

Contact opt-in status for specific messaging topics (required for some channels).

| Column        | Type        | Description              |
| ------------- | ----------- | ------------------------ |
| `id`          | integer     | Primary key              |
| `uuid`        | uuid        | Unique identifier        |
| `org_id`      | integer     | Foreign key to orgs_org  |
| `name`        | varchar(64) | Opt-in name              |
| `is_active`   | boolean     | Whether opt-in is active |
| `created_on`  | timestamp   | When created             |
| `modified_on` | timestamp   | Last modification time   |

---

### Media (`msgs_media`)

Uploaded media files that can be used as attachments on messages.

| Column          | Type          | Description                                             |
| --------------- | ------------- | ------------------------------------------------------- |
| `uuid`          | uuid          | Primary key / unique identifier                         |
| `org_id`        | integer       | Foreign key to orgs_org                                 |
| `url`           | varchar(2048) | Public URL to access the media                          |
| `content_type`  | varchar(255)  | MIME type (image/jpeg, audio/mp3, video/mp4, etc.)      |
| `path`          | varchar(2048) | Storage path                                            |
| `size`          | integer       | File size in bytes                                      |
| `duration`      | integer       | Duration in milliseconds (for audio/video)              |
| `width`         | integer       | Width in pixels (for images/video)                      |
| `height`        | integer       | Height in pixels (for images/video)                     |
| `status`        | char(1)       | 'P' (Pending), 'R' (Ready), 'F' (Failed)                |
| `original_id`   | uuid          | Foreign key to original media (if this is an alternate) |
| `created_by_id` | integer       | Foreign key to auth_user                                |
| `created_on`    | timestamp     | When media was uploaded                                 |

**Key Relationships:**

- Many-to-One with `orgs_org`
- Referenced by `msgs_msg` via attachments array

---

## Flow Tables

### Flows (`flows_flow`)

Automated conversation flows (decision trees) that contacts can go through.

| Column                  | Type         | Description                                                    |
| ----------------------- | ------------ | -------------------------------------------------------------- |
| `id`                    | integer      | Primary key                                                    |
| `uuid`                  | uuid         | Unique identifier                                              |
| `org_id`                | integer      | Foreign key to orgs_org                                        |
| `name`                  | varchar(128) | Flow name                                                      |
| `flow_type`             | char(1)      | 'M' (Message), 'V' (Voice/IVR), 'B' (Background), 'S' (Survey) |
| `is_active`             | boolean      | Whether flow is active                                         |
| `is_archived`           | boolean      | Whether flow is archived                                       |
| `is_system`             | boolean      | Whether this is a system flow                                  |
| `base_language`         | varchar(3)   | Authoring language (ISO-639-3)                                 |
| `version_number`        | varchar(8)   | Flow spec version                                              |
| `expires_after_minutes` | integer      | Inactivity timeout in minutes                                  |
| `ignore_triggers`       | boolean      | Whether to ignore keyword triggers while in flow               |
| `has_issues`            | boolean      | Whether flow has validation issues                             |
| `info`                  | jsonb        | Flow metadata (results, dependencies, etc.)                    |
| `created_on`            | timestamp    | When flow was created                                          |
| `modified_on`           | timestamp    | Last modification time                                         |
| `saved_on`              | timestamp    | Last time definition was saved                                 |
| `saved_by_id`           | integer      | User who last saved                                            |

**Flow Types:**

- **M (Message)**: Standard messaging flow
- **V (Voice)**: IVR/voice call flow
- **B (Background)**: Flow that runs without user interaction
- **S (Survey)**: Surveyor app flow (offline data collection)

**Key Relationships:**

- One-to-Many with `flows_flowrun` (runs of this flow)
- One-to-Many with `flows_flowstart` (times this flow was started)
- One-to-Many with `campaigns_campaignevent` (campaign events using this flow)
- One-to-Many with `triggers_trigger` (triggers that start this flow)

---

### Flow Runs (`flows_flowrun`)

Individual instances of contacts going through flows.

| Column              | Type        | Description                                                                                  |
| ------------------- | ----------- | -------------------------------------------------------------------------------------------- |
| `id`                | bigint      | Primary key                                                                                  |
| `uuid`              | uuid        | Unique identifier                                                                            |
| `org_id`            | integer     | Foreign key to orgs_org                                                                      |
| `flow_id`           | integer     | Foreign key to flows_flow                                                                    |
| `contact_id`        | integer     | Foreign key to contacts_contact                                                              |
| `session_uuid`      | uuid        | UUID of session this run belongs to                                                          |
| `start_id`          | integer     | Foreign key to flows_flowstart                                                               |
| `status`            | char(1)     | 'A' (Active), 'W' (Waiting), 'C' (Completed), 'I' (Interrupted), 'X' (Expired), 'F' (Failed) |
| `responded`         | boolean     | Whether contact has sent a message during run                                                |
| `results`           | jsonb       | Results collected, keyed by result name                                                      |
| `path`              | jsonb       | Path taken through flow (legacy)                                                             |
| `path_nodes`        | uuid[]      | Array of node UUIDs visited                                                                  |
| `path_times`        | timestamp[] | Array of timestamps for each node                                                            |
| `current_node_uuid` | uuid        | Current position in flow (if active/waiting)                                                 |
| `created_on`        | timestamp   | When run started                                                                             |
| `modified_on`       | timestamp   | Last modification time                                                                       |
| `exited_on`         | timestamp   | When run exited                                                                              |

**Status Values:**

- **A (Active)**: Run is actively progressing
- **W (Waiting)**: Run is waiting for user input
- **C (Completed)**: Run completed successfully
- **I (Interrupted)**: Run was interrupted
- **X (Expired)**: Run expired due to inactivity
- **F (Failed)**: Run failed due to error

**Key Relationships:**

- Many-to-One with `flows_flow`
- Many-to-One with `contacts_contact`
- Many-to-One with `flows_flowstart`

---

### Flow Sessions (`flows_flowsession`)

Sessions that may contain multiple flow runs (e.g., parent-child flows).

| Column            | Type          | Description                                                                    |
| ----------------- | ------------- | ------------------------------------------------------------------------------ |
| `id`              | bigint        | Primary key                                                                    |
| `uuid`            | uuid          | Unique identifier                                                              |
| `contact_id`      | integer       | Foreign key to contacts_contact                                                |
| `status`          | char(1)       | 'W' (Waiting), 'C' (Completed), 'I' (Interrupted), 'X' (Expired), 'F' (Failed) |
| `session_type`    | char(1)       | 'M' (Message), 'V' (Voice)                                                     |
| `output`          | jsonb         | Engine output (if stored in DB)                                                |
| `output_url`      | varchar(2048) | S3 URL to output (if stored externally)                                        |
| `current_flow_id` | integer       | Foreign key to waiting run's flow                                              |
| `created_on`      | timestamp     | When session started                                                           |
| `ended_on`        | timestamp     | When session ended                                                             |

---

### Flow Starts (`flows_flowstart`)

Records of flows being started (manually or automatically).

| Column          | Type      | Description                                                                                  |
| --------------- | --------- | -------------------------------------------------------------------------------------------- |
| `id`            | integer   | Primary key                                                                                  |
| `uuid`          | uuid      | Unique identifier                                                                            |
| `org_id`        | integer   | Foreign key to orgs_org                                                                      |
| `flow_id`       | integer   | Foreign key to flows_flow                                                                    |
| `start_type`    | char(1)   | 'M' (Manual), 'A' (API), 'Z' (Zapier), 'T' (Trigger)                                         |
| `status`        | char(1)   | 'P' (Pending), 'Q' (Queued), 'S' (Started), 'C' (Completed), 'F' (Failed), 'I' (Interrupted) |
| `contact_count` | integer   | Number of contacts started (null until queued)                                               |
| `urns`          | text[]    | Array of URN strings                                                                         |
| `query`         | text      | Query string for dynamic recipients                                                          |
| `exclusions`    | jsonb     | Exclusion criteria                                                                           |
| `params`        | jsonb     | Parameters to pass to flow                                                                   |
| `created_on`    | timestamp | When start was created                                                                       |
| `created_by_id` | integer   | User who created                                                                             |

**Key Relationships:**

- Many-to-One with `flows_flow`
- Many-to-Many with `contacts_contact` (via flows_flowstart_contacts)
- Many-to-Many with `contacts_contactgroup` (via flows_flowstart_groups)
- One-to-Many with `flows_flowrun` (runs created by this start)

---

### Flow Labels (`flows_flowlabel`)

Labels/tags for organizing and categorizing flows.

| Column        | Type        | Description             |
| ------------- | ----------- | ----------------------- |
| `id`          | integer     | Primary key             |
| `uuid`        | uuid        | Unique identifier       |
| `org_id`      | integer     | Foreign key to orgs_org |
| `name`        | varchar(64) | Label name              |
| `is_active`   | boolean     | Whether label is active |
| `created_on`  | timestamp   | When label was created  |
| `modified_on` | timestamp   | Last modification time  |

**Key Relationships:**

- Many-to-Many with `flows_flow` (via flows_flow_labels)

---

## Campaign Tables

### Campaigns (`campaigns_campaign`)

Automated message sequences based on dates in contact fields.

| Column        | Type         | Description                                         |
| ------------- | ------------ | --------------------------------------------------- |
| `id`          | integer      | Primary key                                         |
| `uuid`        | uuid         | Unique identifier                                   |
| `org_id`      | integer      | Foreign key to orgs_org                             |
| `name`        | varchar(255) | Campaign name                                       |
| `group_id`    | integer      | Foreign key to contacts_contactgroup (target group) |
| `is_archived` | boolean      | Whether campaign is archived                        |
| `is_active`   | boolean      | Whether campaign is active                          |
| `created_on`  | timestamp    | When campaign was created                           |
| `modified_on` | timestamp    | Last modification time                              |

**Key Relationships:**

- Many-to-One with `contacts_contactgroup`
- One-to-Many with `campaigns_campaignevent` (events in campaign)

---

### Campaign Events (`campaigns_campaignevent`)

Individual events within a campaign (send message or start flow).

| Column           | Type       | Description                                                         |
| ---------------- | ---------- | ------------------------------------------------------------------- |
| `id`             | integer    | Primary key                                                         |
| `uuid`           | uuid       | Unique identifier                                                   |
| `campaign_id`    | integer    | Foreign key to campaigns_campaign                                   |
| `event_type`     | char(1)    | 'F' (Flow), 'M' (Message)                                           |
| `status`         | char(1)    | 'S' (Scheduling), 'R' (Ready)                                       |
| `fire_version`   | integer    | Incremented when schedule changes                                   |
| `relative_to_id` | integer    | Foreign key to contacts_contactfield (date field to base timing on) |
| `offset`         | integer    | Offset from relative_to date                                        |
| `unit`           | char(1)    | 'M' (Minutes), 'H' (Hours), 'D' (Days), 'W' (Weeks)                 |
| `delivery_hour`  | integer    | Hour of day to deliver (-1 for same hour as date)                   |
| `flow_id`        | integer    | Foreign key to flows_flow (if type=F)                               |
| `translations`   | jsonb      | Message translations by language (if type=M)                        |
| `base_language`  | varchar(3) | Base language for message (if type=M)                               |
| `start_mode`     | char(1)    | 'I' (Interrupt), 'S' (Skip), 'P' (Passive)                          |
| `is_active`      | boolean    | Whether event is active                                             |
| `created_on`     | timestamp  | When event was created                                              |

**Example:**

- **relative_to**: "birthday" field
- **offset**: -7
- **unit**: 'D' (Days)
- **delivery_hour**: 9
- **Result**: Send message 7 days before birthday at 9am

**Key Relationships:**

- Many-to-One with `campaigns_campaign`
- Many-to-One with `contacts_contactfield`
- Many-to-One with `flows_flow` (if flow event)

---

## Channel Tables

### Channels (`channels_channel`)

Communication channels for sending/receiving messages.

| Column         | Type         | Description                                                  |
| -------------- | ------------ | ------------------------------------------------------------ |
| `id`           | integer      | Primary key                                                  |
| `uuid`         | uuid         | Unique identifier                                            |
| `org_id`       | integer      | Foreign key to orgs_org                                      |
| `channel_type` | varchar(3)   | Channel type code (e.g., 'WAC', 'TW', 'TG')                  |
| `name`         | varchar(64)  | Channel name                                                 |
| `address`      | varchar(255) | Channel address (phone number, username, etc.)               |
| `country`      | varchar(2)   | ISO country code                                             |
| `config`       | jsonb        | Channel configuration                                        |
| `schemes`      | text[]       | Supported URN schemes                                        |
| `role`         | varchar(4)   | Roles: S (Send), R (Receive), C (Call), A (Answer), U (USSD) |
| `log_policy`   | char(1)      | 'N' (None), 'E' (Errors), 'A' (All)                          |
| `tps`          | integer      | Transactions per second limit                                |
| `is_active`    | boolean      | Whether channel is active                                    |
| `is_enabled`   | boolean      | Whether channel is enabled for sending                       |
| `created_on`   | timestamp    | When channel was created                                     |
| `modified_on`  | timestamp    | Last modification time                                       |
| `last_seen`    | timestamp    | Last sync time (Android channels)                            |

**Common Channel Types:**

- **WAC**: WhatsApp Cloud API
- **TW**: Twilio
- **TG**: Telegram
- **FBA**: Facebook Messenger
- **IG**: Instagram
- **A**: Android (direct phone connection)

**Key Relationships:**

- One-to-Many with `msgs_msg` (messages through channel)
- One-to-Many with `channels_channelevent` (channel events)
- One-to-Many with `contacts_contacturn` (URN affinities)

---

### Channel Events (`channels_channelevent`)

Non-message events from channels (calls, opt-ins, etc.)

| Column           | Type        | Description                        |
| ---------------- | ----------- | ---------------------------------- |
| `id`             | integer     | Primary key                        |
| `uuid`           | uuid        | Unique identifier                  |
| `org_id`         | integer     | Foreign key to orgs_org            |
| `channel_id`     | integer     | Foreign key to channels_channel    |
| `contact_id`     | integer     | Foreign key to contacts_contact    |
| `contact_urn_id` | integer     | Foreign key to contacts_contacturn |
| `event_type`     | varchar(16) | Type of event (see below)          |
| `status`         | char(1)     | 'P' (Pending), 'H' (Handled)       |
| `extra`          | jsonb       | Additional event data              |
| `occurred_on`    | timestamp   | When event occurred                |
| `created_on`     | timestamp   | When event was recorded            |

**Event Types:**

- **mo_call**: Incoming call
- **mo_miss**: Missed incoming call
- **mt_call**: Outgoing call
- **mt_miss**: Missed outgoing call
- **new_conversation**: New conversation started
- **referral**: User came via referral
- **optin**: User opted in
- **optout**: User opted out
- **stop_contact**: Contact asked to stop
- **welcome_message**: Welcome message trigger

---

## Ticketing Tables

### Tickets (`tickets_ticket`)

Support tickets for human-agent interaction with contacts.

| Column             | Type      | Description                                   |
| ------------------ | --------- | --------------------------------------------- |
| `id`               | integer   | Primary key                                   |
| `uuid`             | uuid      | Unique identifier                             |
| `org_id`           | integer   | Foreign key to orgs_org                       |
| `contact_id`       | integer   | Foreign key to contacts_contact               |
| `topic_id`         | integer   | Foreign key to tickets_topic                  |
| `assignee_id`      | integer   | Foreign key to auth_user (assigned agent)     |
| `status`           | char(1)   | 'O' (Open), 'C' (Closed)                      |
| `opened_on`        | timestamp | When ticket was opened                        |
| `opened_in_id`     | integer   | Foreign key to flows_flow (if opened in flow) |
| `opened_by_id`     | integer   | User who opened (if manual)                   |
| `replied_on`       | timestamp | When first reply was sent                     |
| `closed_on`        | timestamp | When ticket was closed                        |
| `modified_on`      | timestamp | Last modification time                        |
| `last_activity_on` | timestamp | Last activity (for sorting)                   |

**Key Relationships:**

- Many-to-One with `contacts_contact`
- Many-to-One with `tickets_topic`
- Many-to-One with auth_user (assignee)
- One-to-Many with `tickets_ticketevent` (ticket history)
- One-to-Many with `msgs_msg` (messages in ticket conversation)

---

### Ticket Events (`tickets_ticketevent`)

History of ticket state changes.

| Column          | Type      | Description                                                                                 |
| --------------- | --------- | ------------------------------------------------------------------------------------------- |
| `id`            | integer   | Primary key                                                                                 |
| `org_id`        | integer   | Foreign key to orgs_org                                                                     |
| `ticket_id`     | integer   | Foreign key to tickets_ticket                                                               |
| `contact_id`    | integer   | Foreign key to contacts_contact                                                             |
| `event_type`    | char(1)   | 'O' (Opened), 'A' (Assigned), 'N' (Note), 'T' (Topic Changed), 'C' (Closed), 'R' (Reopened) |
| `note`          | text      | Note text (if event_type=N)                                                                 |
| `topic_id`      | integer   | New topic (if event_type=T)                                                                 |
| `assignee_id`   | integer   | New assignee (if event_type=A)                                                              |
| `created_on`    | timestamp | When event occurred                                                                         |
| `created_by_id` | integer   | User who created event                                                                      |

---

### Topics (`tickets_topic`)

Categories for organizing tickets.

| Column       | Type        | Description                       |
| ------------ | ----------- | --------------------------------- |
| `id`         | integer     | Primary key                       |
| `uuid`       | uuid        | Unique identifier                 |
| `org_id`     | integer     | Foreign key to orgs_org           |
| `name`       | varchar(64) | Topic name                        |
| `is_default` | boolean     | Whether this is the default topic |
| `is_system`  | boolean     | Whether this is a system topic    |
| `is_active`  | boolean     | Whether topic is active           |
| `created_on` | timestamp   | When topic was created            |

**Key Relationships:**

- One-to-Many with `tickets_ticket`
- Many-to-Many with `tickets_team` (teams that can access this topic)

---

### Teams (`tickets_team`)

Groups of agent users organized by topic access.

| Column       | Type         | Description                        |
| ------------ | ------------ | ---------------------------------- |
| `id`         | integer      | Primary key                        |
| `uuid`       | uuid         | Unique identifier                  |
| `org_id`     | integer      | Foreign key to orgs_org            |
| `name`       | varchar(128) | Team name                          |
| `all_topics` | boolean      | Whether team can access all topics |
| `is_default` | boolean      | Whether this is the default team   |
| `is_system`  | boolean      | Whether this is a system team      |
| `is_active`  | boolean      | Whether team is active             |
| `created_on` | timestamp    | When team was created              |

**Key Relationships:**

- Many-to-Many with `tickets_topic` (via tickets_team_topics)
- One-to-Many with orgs_orgmembership (team members)

---

## Automation Tables

### Triggers (`triggers_trigger`)

Automated flow starters based on events.

| Column         | Type         | Description                                           |
| -------------- | ------------ | ----------------------------------------------------- |
| `id`           | integer      | Primary key                                           |
| `org_id`       | integer      | Foreign key to orgs_org                               |
| `trigger_type` | char(1)      | Type of trigger (see below)                           |
| `flow_id`      | integer      | Foreign key to flows_flow                             |
| `channel_id`   | integer      | Foreign key to channels_channel (if channel-specific) |
| `keywords`     | text[]       | Keywords to match (if type=K)                         |
| `match_type`   | char(1)      | 'F' (First word), 'O' (Only word)                     |
| `referrer_id`  | varchar(255) | Referrer ID (if type=R)                               |
| `schedule_id`  | integer      | Foreign key to schedules_schedule (if type=S)         |
| `priority`     | integer      | Priority (higher = more specific = runs first)        |
| `is_archived`  | boolean      | Whether trigger is archived                           |
| `is_active`    | boolean      | Whether trigger is active                             |
| `created_on`   | timestamp    | When trigger was created                              |

**Trigger Types:**

- **K (Keyword)**: Message starts with keyword
- **S (Schedule)**: Scheduled time
- **V (Inbound Call)**: Incoming call
- **M (Missed Call)**: Missed call
- **N (New Conversation)**: New conversation
- **R (Referral)**: Referral
- **T (Closed Ticket)**: Ticket closed
- **C (Catch All)**: Catch-all for unhandled messages
- **I (Opt In)**: Opt-in event
- **O (Opt Out)**: Opt-out event

**Key Relationships:**

- Many-to-One with `flows_flow`
- Many-to-One with `channels_channel`
- Many-to-One with `schedules_schedule`
- Many-to-Many with `contacts_contactgroup` (groups/exclude_groups)

---

### Schedules (`schedules_schedule`)

Scheduling configuration for recurring events.

| Column                  | Type       | Description                                                              |
| ----------------------- | ---------- | ------------------------------------------------------------------------ |
| `id`                    | integer    | Primary key                                                              |
| `org_id`                | integer    | Foreign key to orgs_org                                                  |
| `repeat_period`         | char(1)    | 'O' (Never/Once), 'D' (Daily), 'W' (Weekly), 'M' (Monthly), 'Y' (Yearly) |
| `repeat_hour_of_day`    | integer    | Hour to fire (0-23)                                                      |
| `repeat_minute_of_hour` | integer    | Minute to fire (0-59)                                                    |
| `repeat_day_of_month`   | integer    | Day of month (1-31, for monthly)                                         |
| `repeat_days_of_week`   | varchar(7) | Days of week (MTWRFSU, for weekly)                                       |
| `is_paused`             | boolean    | Whether schedule is paused                                               |
| `last_fire`             | timestamp  | Last time schedule fired                                                 |
| `next_fire`             | timestamp  | Next scheduled fire time                                                 |

**Key Relationships:**

- One-to-One with `msgs_broadcast` (scheduled broadcasts)
- One-to-One with `triggers_trigger` (scheduled triggers)

---

### Globals (`globals_global`)

Global variables accessible in flows and messages.

| Column        | Type        | Description                                         |
| ------------- | ----------- | --------------------------------------------------- |
| `id`          | integer     | Primary key                                         |
| `uuid`        | uuid        | Unique identifier                                   |
| `org_id`      | integer     | Foreign key to orgs_org                             |
| `key`         | varchar(36) | Variable key (lowercase, alphanumeric + underscore) |
| `name`        | varchar(36) | Display name                                        |
| `value`       | text        | Global value                                        |
| `is_active`   | boolean     | Whether global is active                            |
| `created_on`  | timestamp   | When global was created                             |
| `modified_on` | timestamp   | Last modification time                              |

**Usage:**
Globals can be referenced in flows and messages using `@globals.key_name` syntax.

---

## Template Tables

### Templates (`templates_template`)

Message templates with variable substitution, primarily used for WhatsApp Business API.

| Column                | Type         | Description                              |
| --------------------- | ------------ | ---------------------------------------- |
| `id`                  | integer      | Primary key                              |
| `uuid`                | uuid         | Unique identifier                        |
| `org_id`              | integer      | Foreign key to orgs_org                  |
| `name`                | varchar(512) | Template name                            |
| `base_translation_id` | integer      | Foreign key to base template translation |
| `is_active`           | boolean      | Whether template is active               |
| `created_on`          | timestamp    | When template was created                |
| `modified_on`         | timestamp    | Last modification time                   |

**Key Relationships:**

- One-to-Many with `templates_templatetranslation` (translations in different languages)
- Referenced by flows via template dependencies

---

### Template Translations (`templates_templatetranslation`)

Language and channel-specific versions of templates.

| Column           | Type        | Description                                                      |
| ---------------- | ----------- | ---------------------------------------------------------------- |
| `id`             | integer     | Primary key                                                      |
| `template_id`    | integer     | Foreign key to templates_template                                |
| `channel_id`     | integer     | Foreign key to channels_channel                                  |
| `locale`         | varchar(6)  | Language locale (e.g., 'eng', 'eng-US')                          |
| `status`         | char(1)     | 'P' (Pending), 'A' (Approved), 'R' (Rejected), 'U' (Unsupported) |
| `content`        | text        | Template content with variable placeholders                      |
| `variable_count` | integer     | Number of variables in template                                  |
| `namespace`      | varchar(36) | WhatsApp namespace                                               |
| `external_id`    | varchar(64) | External ID from channel provider                                |
| `is_active`      | boolean     | Whether translation is active                                    |

**Key Relationships:**

- Many-to-One with `templates_template`
- Many-to-One with `channels_channel`

---

## AI & Classifier Tables

### Classifiers (`classifiers_classifier`)

NLU/AI classifiers for intent recognition and entity extraction.

| Column            | Type         | Description                                  |
| ----------------- | ------------ | -------------------------------------------- |
| `id`              | integer      | Primary key                                  |
| `uuid`            | uuid         | Unique identifier                            |
| `org_id`          | integer      | Foreign key to orgs_org                      |
| `name`            | varchar(255) | Classifier name                              |
| `classifier_type` | varchar(16)  | Type of classifier (wit, bothub, luis, etc.) |
| `config`          | jsonb        | Classifier configuration and credentials     |
| `is_active`       | boolean      | Whether classifier is active                 |
| `created_on`      | timestamp    | When classifier was created                  |
| `modified_on`     | timestamp    | Last modification time                       |

**Common Classifier Types:**

- **wit**: Wit.ai
- **bothub**: Bothub
- **luis**: Microsoft LUIS

**Key Relationships:**

- One-to-Many with `classifiers_intent` (intents this classifier recognizes)
- Referenced by flows via classifier dependencies

---

### Intents (`classifiers_intent`)

Intent definitions for classifiers.

| Column          | Type         | Description                           |
| --------------- | ------------ | ------------------------------------- |
| `id`            | integer      | Primary key                           |
| `classifier_id` | integer      | Foreign key to classifiers_classifier |
| `name`          | varchar(64)  | Intent name                           |
| `external_id`   | varchar(255) | External ID from classifier provider  |
| `is_active`     | boolean      | Whether intent is active              |
| `created_on`    | timestamp    | When intent was created               |

**Key Relationships:**

- Many-to-One with `classifiers_classifier`

---

## Common Query Patterns

### Get all messages for a contact

```sql
SELECT
    m.id,
    m.text,
    m.direction,
    m.status,
    m.created_on,
    c.name as channel_name
FROM msgs_msg m
LEFT JOIN channels_channel c ON m.channel_id = c.id
WHERE m.contact_id = {contact_id}
  AND m.visibility = 'V'
ORDER BY m.created_on DESC;
```

### Get flow run statistics with detailed status breakdown

```sql
SELECT
    f.name as flow_name,
    f.uuid as flow_uuid,
    fr.status,
    COUNT(*) as run_count,
    COUNT(DISTINCT fr.contact_id) as unique_contacts,
    AVG(EXTRACT(EPOCH FROM (fr.exited_on - fr.created_on))/60) as avg_duration_minutes,
    COUNT(CASE WHEN fr.responded THEN 1 END) as responded_count,
    MIN(fr.created_on) as first_run,
    MAX(fr.created_on) as last_run
FROM flows_flowrun fr
JOIN flows_flow f ON fr.flow_id = f.id
WHERE fr.created_on >= NOW() - INTERVAL '30 days'
  AND fr.exited_on IS NOT NULL
  AND f.is_active = TRUE
GROUP BY f.id, f.name, f.uuid, fr.status
ORDER BY run_count DESC;
```

### Get detailed flow run results

```sql
-- Extract specific result values from flow runs
SELECT
    f.name as flow_name,
    c.name as contact_name,
    fr.status,
    fr.results->>'result_key' as result_value,
    fr.created_on,
    fr.exited_on,
    EXTRACT(EPOCH FROM (fr.exited_on - fr.created_on))/60 as duration_minutes
FROM flows_flowrun fr
JOIN flows_flow f ON fr.flow_id = f.id
JOIN contacts_contact c ON fr.contact_id = c.id
WHERE f.uuid = 'flow-uuid-here'
  AND fr.results IS NOT NULL
  AND fr.created_on >= NOW() - INTERVAL '7 days'
ORDER BY fr.created_on DESC;
```

### Get campaign event performance

```sql
SELECT
    c.name as campaign_name,
    ce.event_type,
    COUNT(DISTINCT cf.contact_id) as contacts_scheduled,
    AVG(ce.offset) as avg_offset
FROM campaigns_campaign c
JOIN campaigns_campaignevent ce ON c.id = ce.campaign_id
LEFT JOIN contacts_contactfire cf ON cf.scope LIKE 'C:' || ce.id || '%'
WHERE c.is_archived = FALSE
GROUP BY c.name, ce.event_type;
```

### Get contact engagement metrics

```sql
SELECT
    c.id,
    c.name,
    c.created_on,
    c.last_seen_on,
    COUNT(DISTINCT m.id) as message_count,
    COUNT(DISTINCT fr.id) as flow_run_count,
    COUNT(DISTINCT t.id) as ticket_count
FROM contacts_contact c
LEFT JOIN msgs_msg m ON c.id = m.contact_id
  AND m.created_on >= NOW() - INTERVAL '90 days'
LEFT JOIN flows_flowrun fr ON c.id = fr.contact_id
  AND fr.created_on >= NOW() - INTERVAL '90 days'
LEFT JOIN tickets_ticket t ON c.id = t.contact_id
WHERE c.org_id = {org_id}
  AND c.is_active = TRUE
  AND c.status = 'A'
GROUP BY c.id
ORDER BY message_count DESC;
```

### Get broadcast effectiveness

```sql
SELECT
    b.id,
    b.created_on,
    b.contact_count,
    b.status,
    COUNT(m.id) as messages_sent,
    COUNT(CASE WHEN m.status IN ('S', 'D', 'R') THEN 1 END) as messages_delivered,
    COUNT(CASE WHEN m.status = 'F' THEN 1 END) as messages_failed
FROM msgs_broadcast b
LEFT JOIN msgs_msg m ON b.id = m.broadcast_id
WHERE b.org_id = {org_id}
  AND b.created_on >= NOW() - INTERVAL '30 days'
GROUP BY b.id
ORDER BY b.created_on DESC;
```

---

## Important Notes

### UUID Fields

Most tables use UUIDs as unique identifiers for API access and exports. The `id` field is the internal integer primary key used for database relationships.

### Timestamps

All timestamps are stored in UTC. Use the org's timezone from `orgs_org.timezone` to convert to local time.

### Soft Deletes

Most tables use `is_active` for soft deletes rather than actually deleting rows. Always filter by `is_active = TRUE` unless you specifically want to include deleted items.

### JSONB Fields

Fields like `config`, `fields`, `results`, and `extra` use PostgreSQL's JSONB type for flexible schema storage. You can query these using PostgreSQL's JSON operators:

- `->` for object field access
- `->>` for text result
- `@>` for containment
- `?` for key existence

Example:

```sql
-- Find contacts with a specific field value
SELECT * FROM contacts_contact
WHERE fields @> '{"field_uuid": {"text": "value"}}'::jsonb;
```

### Foreign Key Naming

Most foreign keys follow the pattern `tablename_id` (e.g., `org_id`, `contact_id`). Some many-to-many relationships use junction tables (e.g., `contacts_contactgroup_contacts`).

### Count Tables

Many tables have associated count tables (e.g., `orgs_orgcount`, `contacts_contactgroupcount`) that maintain aggregated counts for performance. These are updated by database triggers and background tasks.

---

## Database Indexes

RapidPro includes numerous indexes optimized for common query patterns. Key indexes include:

- **Contact lookups**: By org, status, modified_on
- **Message retrieval**: By org, contact, created_on, status
- **Flow runs**: By flow, contact, status, modified_on
- **Tickets**: By org, status, last_activity_on
- **URN lookups**: By identity + org (unique), scheme

When writing custom queries, use `EXPLAIN ANALYZE` to ensure you're using appropriate indexes.

---

This schema represents a mature messaging platform with comprehensive tracking of contact interactions, automated workflows, campaign management, and support ticketing. The design emphasizes:

1. **Scalability**: Proper indexing and partitioning strategies
2. **Flexibility**: JSONB fields for variable data
3. **Auditability**: Comprehensive timestamps and modification tracking
4. **Multi-tenancy**: Org-level isolation
5. **Extensibility**: Custom fields and dynamic groups

For building dashboards, focus on the relationships between:

- **Contacts** ↔ **Messages** ↔ **Channels** (engagement metrics)
- **Contacts** ↔ **Flow Runs** ↔ **Flows** (automation effectiveness)
- **Campaigns** ↔ **Campaign Events** ↔ **Contacts** (campaign performance)
- **Tickets** ↔ **Agents** ↔ **Topics** (support metrics)
- **Templates** ↔ **Channels** ↔ **Messages** (template usage)
- **Classifiers** ↔ **Flows** (AI/NLU integration)

## Additional Analytics Queries

### Flow engagement by group

```sql
SELECT
    cg.name as group_name,
    f.name as flow_name,
    COUNT(DISTINCT fr.contact_id) as unique_participants,
    COUNT(*) as total_runs,
    COUNT(CASE WHEN fr.status = 'C' THEN 1 END) as completed_runs,
    COUNT(CASE WHEN fr.status = 'X' THEN 1 END) as expired_runs,
    AVG(CASE WHEN fr.exited_on IS NOT NULL THEN
        EXTRACT(EPOCH FROM (fr.exited_on - fr.created_on))/60
    END) as avg_duration_minutes
FROM flows_flowrun fr
JOIN flows_flow f ON fr.flow_id = f.id
JOIN contacts_contact c ON fr.contact_id = c.id
JOIN contacts_contactgroup_contacts cgc ON c.id = cgc.contact_id
JOIN contacts_contactgroup cg ON cgc.contactgroup_id = cg.id
WHERE fr.created_on >= NOW() - INTERVAL '30 days'
  AND cg.group_type IN ('M', 'Q')
  AND cg.is_active = TRUE
GROUP BY cg.id, cg.name, f.id, f.name
ORDER BY total_runs DESC;
```

### Campaign effectiveness

```sql
SELECT
    c.name as campaign_name,
    ce.event_type,
    cf.name as trigger_field,
    CASE ce.unit
        WHEN 'M' THEN 'Minutes'
        WHEN 'H' THEN 'Hours'
        WHEN 'D' THEN 'Days'
        WHEN 'W' THEN 'Weeks'
    END as time_unit,
    ce.offset as time_offset,
    COUNT(DISTINCT fs.id) as flow_starts_triggered,
    SUM(fs.contact_count) as total_contacts_reached
FROM campaigns_campaign c
JOIN campaigns_campaignevent ce ON c.id = ce.campaign_id
JOIN contacts_contactfield cf ON ce.relative_to_id = cf.id
LEFT JOIN flows_flowstart fs ON fs.flow_id = ce.flow_id
    AND fs.start_type = 'T'
    AND fs.created_on >= NOW() - INTERVAL '90 days'
WHERE c.is_archived = FALSE
  AND ce.is_active = TRUE
GROUP BY c.id, c.name, ce.id, ce.event_type, cf.name, ce.unit, ce.offset
ORDER BY c.name, ce.offset;
```

### Template usage and approval status

```sql
SELECT
    t.name as template_name,
    ch.name as channel_name,
    tt.locale,
    tt.status as approval_status,
    tt.variable_count,
    COUNT(DISTINCT m.id) as times_used,
    MIN(m.created_on) as first_used,
    MAX(m.created_on) as last_used
FROM templates_template t
JOIN templates_templatetranslation tt ON t.id = tt.template_id
JOIN channels_channel ch ON tt.channel_id = ch.id
LEFT JOIN msgs_msg m ON m.text LIKE '%' || t.name || '%'
    AND m.channel_id = ch.id
    AND m.created_on >= NOW() - INTERVAL '90 days'
WHERE t.is_active = TRUE
  AND tt.is_active = TRUE
GROUP BY t.id, t.name, ch.name, tt.locale, tt.status, tt.variable_count
ORDER BY times_used DESC;
```
