# Integration Setup Guide - Complete Documentation

Complete step-by-step instructions for configuring all integrations in the admin panel.

---

## TABLE OF CONTENTS

1. [Telegram Bot Integration](#telegram-bot-integration)
2. [VK (VKontakte) Bot Integration](#vk-bot-integration)
3. [MAX Bot Integration](#max-bot-integration)
4. [Bitrix24 Integration](#bitrix24-integration)
5. [Mail Connector (IMAP/SMTP)](#mail-connector-integration)

---

## TELEGRAM BOT INTEGRATION

### 1. Prerequisites

**External Accounts/Services Needed:**
- Telegram account (free, create at https://telegram.org)
- Access to BotFather on Telegram (official bot for creating bots)
- A chat or group where the bot will be used

**Credentials to Obtain:**
- **Bot Token**: Unique authentication key from BotFather
- Format: Long alphanumeric string (example: `123456789:ABCdefGHIjklmnoPQRstuvWXYZabcdefg`)

**Where to Get Bot Token:**

1. Open Telegram and search for **@BotFather**
2. Start the bot (`/start`)
3. Create new bot (`/newbot`)
4. Follow prompts:
   - Enter a name for your bot
   - Enter a username (must end with "bot", e.g., `myproject_bot`)
5. BotFather will respond with your **Bot Token**
6. Copy the token exactly as shown

### 2. Step-by-Step Configuration

**Location in Admin Panel:**
- Navigate to Projects → Select your project → Telegram bot section (in project extensions)

**Fields to Fill:**

| Field | Required | Format | Example | Notes |
|-------|----------|--------|---------|-------|
| **Bot Token** | Yes | 88+ character string | `123456789:ABCdefGHIjklmnoPQRstuvWXYZ` | Password field (hidden) |
| **Auto-start on launch** | No | Checkbox | Checked/Unchecked | Auto-starts bot when system launches |

**Configuration Steps:**

1. **Enter Bot Token**
   - Click the "Bot Token" password field
   - Paste the token from BotFather
   - Leave field empty to use previously saved token

2. **Set Auto-start (Optional)**
   - Check "Auto-start on launch" to automatically start the bot when your project launches
   - Useful for production setups

3. **Save Configuration**
   - Click **Save** button
   - You should see "Saved" message
   - Status will show "Token saved" in placeholder

### 3. Testing and Verification

**How to Test:**

1. **Start the Bot**
   - Click **Start** button in admin panel
   - Status should change to "Running"
   - Message appears: "Started"

2. **Test on Telegram**
   - Send any message to your bot on Telegram
   - Bot should respond with AI-generated answer
   - Check if responses appear in your project

3. **Success Indicators:**
   - Status: **Running** (green or highlighted)
   - No error messages in logs
   - Bot replies to messages immediately
   - Assistant's knowledge base is accessible

**What Success Looks Like:**

```
Status: Running
Auto-start: Enabled
Token: •••• (preview shown)
```

**Common Error Messages and Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| "HTTP 401" | Invalid token | Verify token from BotFather, ensure exact copy |
| "HTTP 404" | Token format wrong | Check token length, no spaces at start/end |
| "Connection timeout" | Bot server down | Try again, check internet connection |
| "Token not set" | No token configured | Enter token and click Save before Start |
| "Last error: [error text]" | Telegram API issue | Check project prompt, knowledge base |

### 4. Bot Management

**Starting the Bot:**
- Click **Start** button
- If token not yet saved, token field is required
- Bot will begin accepting messages immediately
- Auto-start flag is remembered

**Stopping the Bot:**
- Click **Stop** button
- Bot will stop processing new messages
- Existing conversations end gracefully

**Checking Bot Status:**
- Look at **Status** label
- Shows: "Running" or "Stopped"
- Shows token preview (first/last characters)
- Shows auto-start setting

**What "Auto-start" Means:**
- When enabled: Bot automatically starts when project loads/restarts
- When disabled: Must manually click Start after project restart
- Useful for: Always-on production bots
- Warning: Requires valid token to be saved first

**Troubleshooting Steps:**

1. **Bot doesn't respond**
   - Verify status is "Running" in admin
   - Test with simple message
   - Check project prompt is not empty
   - Check knowledge base has content (if required)

2. **Token error appears**
   - Get fresh token from BotFather
   - Remove spaces before/after token
   - Save and try Start again

3. **Bot stops unexpectedly**
   - Check if auto-start is enabled
   - Look for errors in project logs
   - Restart the bot manually

---

## VK BOT INTEGRATION

### 1. Prerequisites

**External Accounts/Services Needed:**
- VK (VKontakte) account
- VK community (group) where bot will operate
- Access to VK Community Settings

**Credentials to Obtain:**
- **Access Token**: Authentication token from VK API
- Format: Long alphanumeric string (example: `vk1.a.abc123def456...`)

**Where to Get Access Token:**

1. Log into VK and navigate to your community/group
2. Go to **Settings** → **API Usage** (or **API tokens**)
3. Create a new token with:
   - **Permissions**: messages, groups
   - **Lifetime**: unlimited (recommended)
4. Copy the generated token

Alternative method (VK App API):
1. Visit https://vk.com/dev
2. Create new app
3. Go to **Settings** → **API tokens**
4. Generate token for your community

### 2. Step-by-Step Configuration

**Location in Admin Panel:**
- Navigate to Projects → Select your project → VK bot section (in project extensions)

**Fields to Fill:**

| Field | Required | Format | Example | Notes |
|-------|----------|--------|---------|-------|
| **Access Token** | Yes | 88+ character string | `vk1.a.abc123def456...` | Password field (hidden) |
| **Auto-start on launch** | No | Checkbox | Checked/Unchecked | Auto-starts bot when system launches |

**Configuration Steps:**

1. **Enter Access Token**
   - Click the "Access Token" password field
   - Paste the token from VK API
   - Ensure no spaces at beginning/end

2. **Set Auto-start (Optional)**
   - Check "Auto-start on launch" to auto-start on project restart
   - Good for production use

3. **Save Configuration**
   - Click **Save** button
   - Confirmation: "Saved" message appears
   - Token preview shown if successful

### 3. Testing and Verification

**How to Test:**

1. **Start the Bot**
   - Click **Start** button
   - Status changes to "Running"

2. **Test in VK Community**
   - Send message to community chat or bot
   - Bot should respond with assistant answer
   - Check timing (should be < 5 seconds)

3. **Success Indicators:**
   - Status: **Running**
   - Messages processed instantly
   - No timeout errors
   - Responses use project knowledge base

**Common Error Messages:**

| Error | Cause | Solution |
|-------|-------|----------|
| "HTTP 401" | Invalid token | Get fresh token from VK API |
| "Token not set" | No token configured | Enter token and Save first |
| "Connection refused" | VK API down | Wait 5 minutes, try again |
| "Invalid token format" | Malformed token | Verify token from VK settings |

### 4. Bot Management

**Starting the Bot:**
- Click **Start** button
- Accepts messages from community immediately

**Stopping the Bot:**
- Click **Stop** button
- No longer processes messages

**Checking Status:**
- **Status** label shows: "Running" or "Stopped"
- Shows token availability
- Shows auto-start setting

---

## MAX BOT INTEGRATION

### 1. Prerequisites

**External Accounts/Services Needed:**
- MAX platform account (Russian chat platform)
- Access to MAX bot settings

**Credentials to Obtain:**
- **Access Token**: From MAX bot dashboard
- Format: Alphanumeric string similar to Telegram

**Where to Get Token:**

1. Log into MAX platform
2. Go to Bot Settings/API
3. Generate or copy existing bot token
4. Use in admin panel

### 2. Step-by-Step Configuration

**Location in Admin Panel:**
- Projects → Select project → MAX bot section

**Fields to Fill:**

| Field | Required | Format | Example | Notes |
|-------|----------|--------|---------|-------|
| **Access Token** | Yes | String | `max_bot_token_here` | Password field |
| **Auto-start on launch** | No | Checkbox | Checked/Unchecked | Auto-start setting |

**Configuration Steps:**

1. **Enter Access Token**
   - Click "Access Token" field
   - Paste token from MAX dashboard
   - No spaces before/after

2. **Optional: Enable Auto-start**
   - Check if you want automatic startup

3. **Save Configuration**
   - Click **Save**
   - "Saved" confirmation appears

### 3. Testing and Verification

**How to Test:**
1. Click **Start** button
2. Send test message in MAX app
3. Bot should respond

**Success Indicators:**
- Status: "Running"
- Instant message processing
- No errors in log

---

## BITRIX24 INTEGRATION

### 1. Prerequisites

**External Accounts/Services Needed:**
- Bitrix24 account (free or paid)
- Admin access to Bitrix24 portal
- Bitrix24 CRM access

**Credentials to Obtain:**
- **Webhook URL**: Special URL created in Bitrix24
- Format: `https://[company].bitrix24.ru/rest/[number]/[key]/`
- Example: `https://example.bitrix24.ru/rest/1/a1b2c3d4e5f6g7h8i9j0/`

**Where to Get Webhook URL:**

1. Log into Bitrix24 portal as administrator
2. Navigate to **CRM** → **Leads** (or desired module)
3. Go to **Integration** → **REST API** (or **Webhooks**)
4. Click **Create new webhook**
5. Configure webhook:
   - **Event**: Select relevant events (lead creation, etc.)
   - **URL**: Copy the generated webhook URL
6. Copy complete webhook URL

**Permissions Needed:**
- CRM module access (at minimum)
- Ability to create/modify webhooks
- API access enabled (usually default)

### 2. Step-by-Step Configuration

**Location in Admin Panel:**
- Projects → Select project → Bitrix24 section

**Fields to Fill:**

| Field | Required | Format | Example | Notes |
|-------|----------|--------|---------|-------|
| **Webhook URL** | Yes | Full URL | `https://example.bitrix24.ru/rest/1/abc123/` | Must end with / |
| **Activate integration** | No | Checkbox | Checked/Unchecked | Enables/disables integration |

**Configuration Steps:**

1. **Enter Webhook URL**
   - Click "Webhook URL" field
   - Paste exact URL from Bitrix24
   - Must include trailing slash: `/`
   - Do NOT add any extra parameters

2. **Enable Integration (Optional)**
   - Check "Activate integration" to enable
   - Webhook is stored server-side (secure)
   - LLM can make requests to your Bitrix24

3. **Save**
   - Webhook is automatically saved
   - Check status message at bottom

### 3. Testing and Verification

**How to Test:**

1. **Webhook Validation**
   - Once URL entered, hover over it
   - System automatically validates format
   - Should show: "Integration is active"

2. **Manual Test (Advanced)**
   - Use your project's LLM to query Bitrix24
   - Example: "What leads do we have?"
   - LLM should retrieve data from Bitrix24

3. **Success Indicators:**
   - Hint text shows: "Integration is active"
   - Webhook URL is properly formatted
   - No error messages
   - LLM can access Bitrix24 data

**Common Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid URL format" | Missing / at end | Add trailing slash: `url/` |
| "Connection refused" | Wrong domain | Verify correct Bitrix24 domain |
| "Webhook not found" | Token changed in Bitrix | Get fresh webhook URL |
| "Integration disabled" | Checkbox unchecked | Check "Activate integration" |

### 4. How to Enable/Disable Integration

**Enable:**
- Check the "Activate integration" checkbox
- Hint changes to: "Integration is active"

**Disable:**
- Uncheck the "Activate integration" checkbox
- Webhook remains saved, but not used

### 5. Creating Webhook in Bitrix24

**Step-by-step in Bitrix24:**

1. Open your Bitrix24 portal
2. Go to **CRM** section
3. Find **Leads** → **Settings** or **Integration**
4. Look for **REST API**, **Webhooks**, or **API Settings**
5. Click **Create webhook** or **Generate token**
6. Configure:
   - Name: "AI Assistant Bot"
   - Event: Choose (Lead creation, update, etc.) or All events
7. Copy the generated URL (looks like: `https://xxx.bitrix24.ru/rest/1/abc123/`)
8. Paste in admin panel

---

## MAIL CONNECTOR INTEGRATION

### 1. Prerequisites

**External Accounts/Services Needed:**
- Email account (Gmail, Outlook, corporate email, etc.)
- Access to email settings and security settings
- For Gmail: app password or OAuth enabled
- For Outlook: app password or OAuth enabled

**Credentials to Obtain:**

For **Gmail (Google Workspace)**:
- Email: your@gmail.com
- **App Password**: Generate from Security settings (not your main password)
  - Go to: https://myaccount.google.com/security
  - Enable 2-factor authentication if not already
  - Generate app password (select Mail + Windows Computer)
  - Get 16-character password

For **Outlook/Microsoft 365**:
- Email: your@outlook.com or corporate email
- **App Password**: Generate from Account security
  - Go to: https://account.microsoft.com/security/
  - Create app password (new device)
  - Get generated password

For **Corporate/Hosted Email**:
- Email address: user@company.com
- Ask your IT department for:
  - IMAP host
  - SMTP host
  - Port numbers
  - Username (often email)
  - Password or app password

**Server Details for Common Providers:**

**Gmail/Google:**
```
IMAP Host: imap.gmail.com
IMAP Port: 993
IMAP SSL: Enabled (checked)
SMTP Host: smtp.gmail.com
SMTP Port: 587
SMTP STARTTLS: Enabled (checked)
Username: your@gmail.com
Password: [app password - 16 chars]
```

**Outlook/Microsoft 365:**
```
IMAP Host: outlook.office365.com
IMAP Port: 993
IMAP SSL: Enabled (checked)
SMTP Host: smtp.office365.com
SMTP Port: 587
SMTP STARTTLS: Enabled (checked)
Username: your@outlook.com
Password: [app password]
```

**Yandex Mail:**
```
IMAP Host: imap.yandex.com
IMAP Port: 993
IMAP SSL: Enabled (checked)
SMTP Host: smtp.yandex.com
SMTP Port: 465
SMTP STARTTLS: Not enabled (unchecked)
SMTP SSL: Enabled (uses port 465)
Username: yourname
Password: [app password or main password]
```

**Mail.ru:**
```
IMAP Host: imap.mail.ru
IMAP Port: 993
IMAP SSL: Enabled (checked)
SMTP Host: smtp.mail.ru
SMTP Port: 465
SMTP STARTTLS: Not enabled (unchecked)
Username: yourname@mail.ru
Password: [password]
```

### 2. Step-by-Step Configuration

**Location in Admin Panel:**
- Projects → Select project → Mail connector section (at bottom)

**Fields to Fill:**

| Field | Required | Format | Example | Notes |
|-------|----------|--------|---------|-------|
| **Enable integration** | No | Checkbox | Checked/Unchecked | Must enable to use |
| **IMAP host** | If enabled | Hostname | `imap.gmail.com` | Domain only, no protocol |
| **IMAP port** | If enabled | Number 1-65535 | `993` | Usually 993 (SSL) or 143 |
| **IMAP SSL** | If enabled | Checkbox | Checked | Should be checked (secure) |
| **SMTP host** | If enabled | Hostname | `smtp.gmail.com` | Domain only, no protocol |
| **SMTP port** | If enabled | Number 1-65535 | `587` | Usually 587 (TLS) or 465 (SSL) |
| **SMTP STARTTLS** | If enabled | Checkbox | Checked | Use TLS (port 587) or uncheck for SSL (port 465) |
| **Username** | If enabled | Email or username | `your@gmail.com` | Often your email address |
| **Password** | If enabled | String | `[app password]` | App password, not main password |
| **Sender (From)** | If enabled | Email address | `support@company.com` | Email address to send from |
| **Email signature** | No | Text | `Best regards, Team` | Appended to outgoing emails |

**Configuration Steps for Gmail:**

1. **Prepare Gmail Account**
   - Go to https://myaccount.google.com/security
   - Enable 2-Step Verification if not enabled
   - Go to App passwords (near bottom)
   - Select "Mail" and "Windows Computer"
   - Google generates 16-character password
   - Copy this password (spaces will be shown)

2. **Fill IMAP Settings**
   - **IMAP host**: `imap.gmail.com`
   - **IMAP port**: `993`
   - **IMAP SSL**: Check ✓
   - Hint appears: "IMAP configured"

3. **Fill SMTP Settings**
   - **SMTP host**: `smtp.gmail.com`
   - **SMTP port**: `587`
   - **SMTP STARTTLS**: Check ✓ (NOT SSL on port 587)
   - Hint updates: "SMTP configured"

4. **Fill Credentials**
   - **Username**: `your@gmail.com`
   - **Password**: Paste 16-character app password (without spaces)
   - **Sender (From)**: `your@gmail.com` or custom address

5. **Optional: Add Signature**
   - **Email signature**: Type custom signature
   - Example: "AI Assistant - Support Team"
   - Appended to all sent emails

6. **Enable Integration**
   - Check "Enable integration" checkbox
   - Status changes to: "Integration is active"

7. **Save**
   - Admin panel auto-saves changes
   - No explicit Save button needed

### 3. SSL/TLS Configuration Explained

**IMAP SSL/TLS:**
- **Checked (SSL)**: Port 993 - Encrypted from start (secure, recommended)
- **Unchecked (PLAIN)**: Port 143 - Unencrypted (not recommended, rare)

**SMTP Configuration:**
- **Port 587 + STARTTLS (checked)**: Starts plain, upgrades to TLS
  - Used by: Gmail, Office365, most providers
- **Port 465 + STARTTLS (unchecked)**: Full SSL from start
  - Used by: Some mail servers
- **Port 25**: Unencrypted, deprecated (never use)

**How to Decide:**
1. Check provider's documentation for recommended ports
2. Gmail/Office365: Use 587 + STARTTLS (TLS checkbox checked)
3. Some others: Use 465 + SSL (TLS checkbox unchecked)
4. When unsure: Try 587 with STARTTLS first

### 4. Testing Email Sending/Receiving

**Testing IMAP (Receiving):**

1. **Auto-test on Save**
   - When you fill all IMAP fields, admin panel validates connection
   - Check hint text for confirmation

2. **Manual Test**
   - Go to your email account
   - Send a test email to the account
   - Wait 1 minute
   - Use project chat to ask: "What's my latest email?"
   - Assistant should retrieve and summarize it

3. **Success Indicators:**
   - No timeout errors
   - Hint shows: "Integration is active"
   - Assistant can summarize recent emails

**Testing SMTP (Sending):**

1. **Prepare**
   - Fill all SMTP fields
   - Include recipient email address in knowledge base or project prompt

2. **Manual Test**
   - Use project chat to ask: "Send an email to support@test.com saying test"
   - Check target inbox after 10-30 seconds
   - Should receive email from configured sender

3. **Success Indicators:**
   - Email arrives in inbox
   - From address matches "Sender" field
   - Signature appended (if configured)
   - No bounce/rejection

### 5. Port Numbers Reference

**Quick Reference Table:**

| Email Provider | IMAP Host | IMAP Port | SMTP Host | SMTP Port | SMTP TLS | Notes |
|---|---|---|---|---|---|---|
| Gmail | imap.gmail.com | 993 | smtp.gmail.com | 587 | Yes | Use app password |
| Office365 | outlook.office365.com | 993 | smtp.office365.com | 587 | Yes | Use app password |
| Outlook | imap-mail.outlook.com | 993 | smtp-mail.outlook.com | 587 | Yes | Legacy |
| Yandex | imap.yandex.com | 993 | smtp.yandex.com | 465 | No | No STARTTLS |
| Mail.ru | imap.mail.ru | 993 | smtp.mail.ru | 465 | No | No STARTTLS |
| Yahoo | imap.mail.yahoo.com | 993 | smtp.mail.yahoo.com | 587 | Yes | Use app password |
| AOL | imap.aol.com | 993 | smtp.aol.com | 587 | Yes | Use app password |
| Custom/Corporate | Ask IT | Varies | Ask IT | Varies | Ask IT | Use provided credentials |

### 6. Troubleshooting Email Integration

**Connection Issues:**

| Problem | Cause | Solution |
|---------|-------|----------|
| "Connection timeout" | Server unreachable | Check host name, verify port |
| "Connection refused" | Port blocked | Try alternate port (993 vs 143) |
| "Invalid hostname" | Typo in host | Double-check from provider docs |

**Authentication Issues:**

| Problem | Cause | Solution |
|---------|-------|----------|
| "Login failed" | Wrong password | Use app password, not main password |
| "Invalid credentials" | Username format wrong | Try email format or username only |
| "Account locked" | Multiple failed attempts | Wait 10 minutes, try again |

**Configuration Issues:**

| Problem | Cause | Solution |
|---------|-------|----------|
| "Emails not received" | IMAP not enabled | Check IMAP port and SSL setting |
| "Cannot send emails" | SMTP misconfigured | Verify port matches TLS setting |
| "Signature not added" | Signature field empty | Add text to signature field |

**Testing Connection:**

1. Fill all required fields
2. Look for hint message at bottom:
   - Green/positive: "Integration is active"
   - Orange/warning: "Parameters saved but disabled"
   - Red/error: "Could not connect"

3. If error persists:
   - Verify credentials with provider
   - Check firewall/network access
   - Try connecting from different network
   - Contact provider support

### 7. Security Best Practices

**Password Security:**
- Never use main account password
- Always use app-specific passwords
- Store passwords securely
- Change passwords periodically

**Data Privacy:**
- Webhook stored server-side (not visible in UI after save)
- Passwords encrypted in database
- IMAP/SMTP connections use TLS
- Never share credentials in screenshots

---

## GENERAL TROUBLESHOOTING

### Projects Status Checks

1. **Select Project First**
   - All integrations require selecting a project
   - If no project selected:
     - Integrations show "—" (dash)
     - All buttons disabled
     - Hint: "Select a project to manage..."

2. **Check Project Permissions**
   - Must be project admin or super admin
   - Cannot configure integrations without proper access

3. **Network Connectivity**
   - Ensure stable internet connection
   - Check firewall allows outbound connections
   - Verify proxy settings if behind corporate proxy

### API Response Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Integration working |
| 400 | Bad request | Check field format |
| 401 | Unauthorized | Check token/credentials |
| 404 | Not found | Check webhook URL, project name |
| 500 | Server error | Retry, check logs |
| Timeout | No response | Check connection, try again |

### Checking Admin Panel Logs

1. In browser, press **F12** (Developer Tools)
2. Go to **Console** tab
3. Look for errors starting with:
   - `telegram_` - Telegram bot errors
   - `vk_` - VK bot errors
   - `max_` - MAX bot errors
   - `bitrix_` - Bitrix integration errors
   - `mail_` - Mail connector errors

### Project Data Storage

Mail/Bitrix configurations stored in project:
- Not visible in plain text after save
- Accessible only via admin panel
- Can be modified anytime
- Passwords encrypted in database

---

## FREQUENTLY ASKED QUESTIONS

**Q: How do I reset integration settings?**
A: Clear the token/URL field and click Save. Settings will be removed.

**Q: Can I use multiple integrations with one project?**
A: Yes! All integrations are independent. You can configure Telegram, Mail, and Bitrix simultaneously.

**Q: What happens if I restart the system with auto-start enabled?**
A: Bot automatically starts when project loads. Useful for production setups.

**Q: Is my token/password stored safely?**
A: Yes, all credentials encrypted in database. Never visible after save.

**Q: Can I test integration without enabling it?**
A: Telegram/VK/MAX: Yes, click Start/Stop buttons. Mail/Bitrix: Check field hints for validation.

**Q: What if the bot stops responding?**
A: Check status in admin panel, verify knowledge base has content, restart bot with Stop → Start.

---

## INTEGRATION QUICK LINKS

**Telegram Bot Setup:**
1. Get token from @BotFather → https://telegram.org/
2. Paste in admin panel
3. Click Save → Start

**VK Bot Setup:**
1. Get token from VK API → https://vk.com/dev
2. Paste in admin panel
3. Click Save → Start

**MAX Bot Setup:**
1. Get token from MAX dashboard
2. Paste in admin panel
3. Click Save → Start

**Bitrix24 Setup:**
1. Create webhook in Bitrix24 portal
2. Copy webhook URL
3. Paste in admin panel
4. Check "Activate integration"

**Mail Connector Setup:**
1. Get app password from email provider
2. Fill IMAP/SMTP settings
3. Add credentials and sender email
4. Check "Enable integration"

