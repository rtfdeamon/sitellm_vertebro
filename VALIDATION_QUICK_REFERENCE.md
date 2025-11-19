# Form Validation Quick Reference Guide

## Quick Lookup Tables

### Input Fields Validation Matrix

| Field Name | Type | Required | Format | Error Message | Timeout |
|------------|------|----------|--------|---------------|---------|
| Project ID | text | YES | lowercase, no spaces | "Enter identifier" | 3000ms |
| Project Title | text | NO | Any text | None | N/A |
| Domain | URL | NO | Full URL (https://) | "Invalid domain" (AI only) | 4000ms |
| Crawler URL | URL | YES | Valid URL | Browser native | N/A |
| Depth | number | NO | 1+ | None (HTML5) | N/A |
| Pages | number | NO | 1+ | None (HTML5) | N/A |
| KB Limit | number | NO | 10-1000 | None | N/A |
| IMAP Host | text | NO | Domain format | None | N/A |
| IMAP Port | number | NO | 1-65535 | None | N/A |
| SMTP Host | text | NO | Domain format | None | N/A |
| SMTP Port | number | NO | 1-65535 | None | N/A |
| Mail From | email | NO | Email format | Browser native | N/A |
| Mail Username | text | NO | Any text | None | N/A |
| Backup Time | time | NO | HH:MM | Auto-corrected | N/A |
| Telegram Token | password | COND | Alphanumeric | "Last error: {msg}" | After action |
| Bitrix Webhook | URL | NO | Full URL | None (checked on use) | N/A |

### Error Display Methods

**Method 1: Status Labels (Most Common)**
- Elements: `projectStatus`, `launchMsg`, `crawlerActionStatus`, etc.
- Display: Muted text below forms
- Auto-dismiss: YES (2-6 seconds)
- Styling: Red (.bad) or muted

**Method 2: Input Warning Class**
- Applied to: Project identifier field
- Styling: Red border + shadow
- Trigger: Duplicate project name
- Clear: Auto when field edited

**Method 3: Placeholder Updates**
- Elements: Token input fields
- Before save: "Enter token"
- After save: "Token saved"
- Never shows actual token

**Method 4: Dynamic Hints**
- Locations: Mail, Bitrix, Voice, etc.
- Update: On checkbox/field changes
- Examples: Integration status hints

### Message Timeouts by Category

| Timeout | Use Case | Examples |
|---------|----------|----------|
| 2000ms | Quick success | Saved, Copied, Reset |
| 2400ms | Integration actions | Telegram start/stop |
| 3000ms | Validation errors | Empty field, no project |
| 4000ms | Complex errors | AI generation failed |
| 6000ms | Critical errors | Network failure |
| No timeout | Persistent status | Crawler progress |

### Feature Toggles & Defaults

| Feature | Default | When Disabled | When Enabled |
|---------|---------|---------------|--------------|
| Emotions | ON | "Responses less warm" | "Warm responses" |
| Voice | ON | Voice model disabled | Voice model active |
| Captions | ON | No image captions | Auto-caption images |
| Sources | OFF | No source links | Show source links |
| Debug | OFF | No debug output | Detailed debug info |
| Mail | OFF | Email disabled | Send/receive emails |
| Backup | OFF | No backups | Scheduled backups |

### Required Configurations by Feature

**Telegram Bot:**
- Token: Required
- Auto-start: Optional checkbox
- Project: Required (select first)

**Mail Integration:**
- IMAP Host: Recommended
- SMTP Host: Recommended
- Port: Auto-filled (993, 587)
- Username: Recommended
- Password: Set once, not displayed

**Bitrix24:**
- Webhook URL: Required format
- Enable toggle: Required to activate

**Voice Training:**
- Audio files: 3+ minimum
- Format: Any audio/* supported
- Training: Starts after upload

## Common Workflows

### Create New Project
1. Click "Add project" button
2. Enter project ID (lowercase, no spaces)
3. Fill optional: Title, Domain, Model, Prompt
4. Click "Create"
5. Confirm "Saved" message appears

### Validate Project Settings
1. Select project from dropdown
2. Fill form fields
3. Click "Save"
4. Check for "Saved" message (2 sec)
5. On error: Check console (F12), retry

### Enable Mail Integration
1. Scroll to Mail Connector section
2. Toggle "Enable integration"
3. Fill IMAP/SMTP hosts and ports
4. Enter credentials
5. Click "Save" (password saved server-side)
6. Hint updates to "Integration is active"

### Start Crawler
1. Select project (required)
2. Enter Start URL
3. Set Depth (default 2) and Pages (default 100)
4. Click "Start"
5. Watch progress bar update
6. Counters show: "{done} / {total} pages"

### Handle Validation Error
1. Read error message
2. Identify problematic field
3. Fix the value
4. Submit again (or auto-retry)
5. Message auto-dismisses after timeout

## CSS Classes for Styling

```css
.ok { color: green; font-weight: 600; }
.bad { color: red; font-weight: 600; }
.input-warning { border: red; box-shadow: red glow; }
.muted { color: gray; font-size: smaller; }
.modal-backdrop { Fixed overlay, z-index: 2100; }
.toast-success { Green background, dark text; }
.toast-error { Red background, dark text; }
```

## Key JavaScript Functions

**Set Status Message:**
```javascript
setProjectStatus('Message', 3000); // Auto-dismiss after 3 sec
```

**Validate URL:**
```javascript
buildTargetUrl(raw); // Auto-adds https://, parses, validates
```

**Format Bytes:**
```javascript
formatBytes(1024000); // Returns "977 KB"
```

**Format Timestamp:**
```javascript
formatTimestamp(1700400000); // Returns locale string
```

**Translate Message:**
```javascript
t('projectsSaved'); // Returns translated "Saved"
t('message', { variable: 'value' }); // With parameters
```

## Status Indicators

### Crawler Progress Display
- Progress bar: 0-100% filled (green)
- Status text: "Waiting", "Scanning", "Queued", "Done", "Errors"
- Counter: "{done} / {total} pages"
- Last URL: Clickable link to most recent page

### Integration Status Display
- Status label: "Running" or "Stopped" or "—"
- Info text: Token preview, auto-start status, last error
- Buttons: Disabled unless project selected
- Token field: Masked input, cleared after save

### Service Health
- Color coded: Green (ok), Red (down), Gray (unknown)
- Services: Mongo, Redis, Qdrant, Overall status
- Updates: Auto-polling every ~5 seconds

## File Upload Constraints

| File Type | Accepted | Multiple | Max Count | Min Count |
|-----------|----------|----------|-----------|-----------|
| Knowledge | Any | YES | Unlimited | N/A |
| Q&A Excel | .xlsx, .csv | NO | 1 | 1 |
| Voice | audio/* | YES | Unlimited | 3+ |

## Browser Native Validations

- Email fields: HTML5 type="email" (browser shows error)
- URL fields: HTML5 type="url" (browser shows error)
- Number fields: HTML5 type="number" with min/max (browser spinner)
- Time field: HTML5 type="time" (browser time picker)
- Required fields: HTML5 required attribute

## Internationalization Keys

**Errors:**
- projectsEnterIdentifier
- projectsIdentifierExists
- projectsSaveFailed
- crawlerSelectProject
- promptAiInvalidDomain

**Success:**
- projectsSaved
- crawlerStarted
- integrationActionStarted

**Status:**
- projectsSaving
- crawlerStarting
- integrationStatusUpdating

## Credential Handling Security

1. Tokens stored in `<input type="password">` (masked)
2. Never logged to console
3. Never displayed in UI after save
4. Only transmitted to backend via POST
5. Backend encrypts/hashes before storage
6. On form load: Shows "Token saved" placeholder only

## Debug Tips

**Check What Went Wrong:**
1. Open browser console: F12 or Cmd+Option+J
2. Look for errors starting with operation name:
   - `crawler_start_failed`
   - `project_save_failed`
   - `telegram_action_failed`
3. Check Network tab for failed API calls
4. Verify response status: 200 OK, 400/401/403/500 errors

**Common Issues:**
| Problem | Solution |
|---------|----------|
| "Select a project" | Choose project from dropdown first |
| "Invalid domain" | Ensure URL starts with http:// or https:// |
| "Identifier exists" | Project name already taken |
| "Failed to save" | Check server logs, network connectivity |
| Token won't save | Check token format, valid for service |
| Mail not working | Verify host/port/credentials, test connectivity |

## File Locations (For Development)

- HTML: `/admin/index.html`
- CSS: `/admin/css/*.css`
- JS Validation: `/admin/js/projects.js`, `/admin/js/crawler.js`
- Integrations: `/admin/js/integrations/*.js`
- i18n: `/admin/js/i18n-static.js`
- Utils: `/admin/js/ui-utils.js`

