а# Admin Panel Form Validation, Error Messages, and User Feedback Analysis

## Overview
This document provides a comprehensive analysis of all form validation rules, error messages, and user feedback patterns used in the SiteLLM Vertebro admin panel.

---

## 1. INPUT VALIDATION RULES

### 1.1 Project Identifier (Name) Validation

**Field:** `projectName` / `projectModalName`
**Validation Rules:**
- Required: YES
- Format: English characters only (lowercase)
- Min length: 1 character
- Max length: No explicit max (implementation allows any valid string)
- Special characters: NOT allowed
- Spaces: Converted to underscores or removed
- Duplicate check: Prevents creating projects with same identifier

**Normalization Logic:**
```javascript
// Location: projects.js, line 101-110
const safeNormalizeProjectName = (value) => {
  if (typeof globalThis.normalizeProjectName === 'function') {
    try {
      return globalThis.normalizeProjectName(value);
    } catch (error) {
      console.error('normalizeProjectName_failed', error);
    }
  }
  return typeof value === 'string' ? value.trim().toLowerCase() : '';
};
```

**User Feedback:**
- Empty identifier: Shows "projectsEnterIdentifier" message (3 sec timeout)
- Duplicate identifier: Shows input-warning class with "projectsIdentifierExists" message
- Warning styling: Red border (rgba(248, 113, 113, 0.8)) with shadow

**Example Error:**
```
Message: "Enter project identifier (project name in English)"
Duration: 3000ms
Display: Status label under form
```

---

### 1.2 Domain Name Validation

**Field:** `projectDomain` / `projectModalDomain`
**Validation Rules:**
- Required: NO (optional)
- Format: Valid URL required
- Must include protocol: http:// or https://
- Auto-correction: If no protocol provided, adds https://

**URL Building Logic:**
```javascript
// Location: projects.js, line 162-179
const buildTargetUrl = (raw) => {
  if (!raw) return null;
  let candidate = String(raw).trim();
  if (!candidate) return null;
  if (!/^https?:\/\//i.test(candidate)) {
    candidate = `https://${candidate}`;
  }
  try {
    const parsed = new URL(candidate);
    if (!parsed.hostname) return null;
    if (!parsed.pathname) parsed.pathname = '/';
    return parsed.toString();
  } catch (error) {
    console.warn('[projects:buildTargetUrl:fail]', { input: raw, error });
    return null;
  }
};
```

**User Feedback:**
- Invalid domain for AI prompt: "promptAiInvalidDomain" (4 sec timeout)
- Styling: Gradient background (rgba(96, 165, 250, 0.32)) with blue border
- Hint text: "Paste full URL, for example https://example.com"

---

### 1.3 Crawler URL Validation

**Field:** `url` (Start URL in crawler form)
**Validation Rules:**
- Required: YES
- Format: Valid URL (HTML5 input type="url")
- Must include protocol: http:// or https://
- Empty check: Requires project selection first

**Validation Logic:**
```javascript
// Location: crawler.js, line 467-504
const handleCrawlerSubmit = async (event) => {
  if (!form) return;
  event.preventDefault();
  const payload = {
    start_url: document.getElementById('url')?.value,
    max_depth: Number(document.getElementById('depth')?.value),
    max_pages: Number(document.getElementById('pages')?.value),
  };
  if (!global.currentProject) {
    launchMsg.textContent = translate('crawlerSelectProject', 'Select a project');
    launchMsg.style.color = 'var(--danger)';
    return;
  }
};
```

**User Feedback:**
- No project selected: "Select a project" (red text, no timeout)
- Start failures: "Failed to start crawler" (red text)
- Success: "Crawler started" (normal text)

---

### 1.4 Crawler Parameters Validation

**Depth Field:**
- Type: number
- Min: 1
- Max: No explicit limit (defaults to 2)
- Input validation: HTML5 number input

**Pages Field:**
- Type: number
- Min: 1
- Max: No explicit limit (defaults to 100)
- Input validation: HTML5 number input

---

### 1.5 Email Format Validation

**Field:** `projectMailFrom` / `projectMailUsername`
**Validation Rules:**
- Required: NO (optional for mail integration)
- Format: Valid email format for "From" field
- Type attribute: HTML5 input type="email"
- Port validation: 1-65535

**Mail Port Fields:**
```javascript
// IMAP Port: projectMailImapPort
// SMTP Port: projectMailSmtpPort
const portValue = parseInt(projectMailImapPortInput.value, 10);
payload.mail_imap_port = Number.isFinite(portValue) ? portValue : null;
```

**Constraints:**
- IMAP SSL: Default enabled (checkbox)
- IMAP Port: Default 993 (suggested)
- SMTP TLS: Default enabled (checkbox)
- SMTP Port: Default 587 (suggested)

---

### 1.6 Token Format Requirements

**Telegram Token Field (`projectTelegramToken`):**
- Type: password input (masked)
- Required: YES (if Telegram integration enabled)
- Format: Alphanumeric (Telegram bot token format)
- Storage: NOT stored in form, only in backend
- Placeholder when saved: "Token saved"

**MAX Token Field (`projectMaxToken`):**
- Type: password input (masked)
- Required: YES (if MAX integration enabled)
- Format: Alphanumeric/Special characters
- Storage: NOT stored, only backend persistent
- Placeholder when saved: "Token saved"

**VK Token Field (`projectVkToken`):**
- Type: password input (masked)
- Format: VK access token format
- Storage: Backend only

**Bitrix Webhook Field (`projectBitrixWebhook`):**
- Type: URL input
- Format: Valid Bitrix24 webhook URL
- Example: https://example.bitrix24.ru/rest/1/xxxxxxxxx/
- Storage: Backend stored

**Backup OAuth Token (`backupToken`):**
- Type: password input
- Required: YES (if backup enabled)
- Format: OAuth token from cloud provider
- Display: Masked, not visible after saving

---

### 1.7 File Upload Validation

**Knowledge Base Files (`kbNewFile`):**
- Type: multiple file accept
- Accepted formats: Not explicitly restricted in HTML
- File size limits: Server-side enforced
- Multiple: YES

**Q&A Import File (`kbQaFile`):**
- Type: file input
- Accepted formats: `.xlsx, .xlsm, .xltx, .xltm, .csv`
- Required: YES (for import action)
- Expected columns: "Question" and "Answer"

**Voice Training Files (`voiceSampleInput`):**
- Type: file input (audio)
- Accepted formats: audio/* (all audio formats)
- Capture: microphone enabled
- Multiple: YES
- Min files: 3+ samples recommended

---

### 1.8 File Size Limits

**Knowledge Base:**
- Storage display: Shows formatted bytes (KB, MB, GB)
- Formatting function: `formatBytes(value)` in ui-utils.js
- Display format: Shows storage breakdown (Text/Files/Contexts/Redis)

**Voice Samples:**
- Min samples: 3+ recommended for training
- Status message: "Upload at least {min} samples. Remaining: {remaining}."
- Error on insufficient samples: Training blocked until minimum reached

---

### 1.9 Numeric Range Limits

**Backup Time Settings:**
```javascript
// Location: backup.js, line 85-101
const formatBackupTimeValue = (hour, minute) => {
  const safeHour = Math.max(0, Math.min(23, Number.isFinite(Number(hour)) ? Number(hour) : 0));
  const safeMinute = Math.max(0, Math.min(59, Number.isFinite(Number(minute)) ? Number(minute) : 0));
  return `${String(safeHour).padStart(2, '0')}:${String(safeMinute).padStart(2, '0')}`;
};
```

**Hour Range:** 0-23
**Minute Range:** 0-59
**Default:** 3:00 AM

**Knowledge Base Limit:**
- Min: 10
- Max: 1000
- Default: 1000
- Field: `kbLimit`

---

### 1.10 Date/Time Format Requirements

**Backup Time Field:**
- Input type: time (HTML5)
- Format: HH:MM (24-hour)
- Constraints: 00:00 - 23:59
- Default: 03:00

**Timestamp Display:**
```javascript
// Location: ui-utils.js, line 25-35
const formatTimestamp = (value) => {
  if (value === null || value === undefined) return '—';
  let timestamp = Number(value);
  if (!Number.isFinite(timestamp)) return '—';
  if (timestamp < 1e11) {
    timestamp *= 1000;
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString();
};
```

---

### 1.11 Special Character Validation

**Project Name (Identifier):**
- Allowed: a-z, 0-9
- NOT allowed: Spaces, special characters, uppercase
- Auto-conversion: Uppercase → lowercase, trim whitespace

**Domain Field:**
- Allowed: RFC 3986 compliant URLs
- Special handling: Auto-prepends https:// if missing

**Mail Configuration:**
- Hostnames: Standard domain format (imap.example.com, smtp.example.com)
- No validation of actual connectivity at form level
- Validation happens on save/test

---

## 2. ERROR MESSAGES

### 2.1 Error Message Formats and Triggers

**Standard Error Display Pattern:**
```javascript
// Using statusLabel elements
statusLabel.textContent = translateKey('errorKey');
// Timeout auto-clear: 3000-6000ms
setTimeout(() => {
  if (statusLabel.textContent === expectedMessage) {
    statusLabel.textContent = '';
  }
}, 3000);
```

**Error Display Methods:**

1. **Status Labels (Inline):**
   - Location: Muted text below forms
   - Examples: `projectStatus`, `launchMsg`, `crawlerActionStatus`
   - Auto-dismiss: YES (timeout: 2-6 seconds)
   - Color: Red (--danger) for critical errors

2. **Input Warning Styling:**
   - Applied to: Project identifier field
   - Styling: Input border turns red + shadow
   - Class: `.input-warning`
   - CSS: `border-color: rgba(248, 113, 113, 0.8)`

3. **Console Logging:**
   - All errors logged with context
   - Format: `error_type`, error object
   - Example: `console.error('crawler_start_failed', error)`

---

### 2.2 Validation Error Messages

**Project Creation:**

| Error | Message Key | Trigger | Display | Timeout |
|-------|-------------|---------|---------|---------|
| Empty name | `projectsEnterIdentifier` | No project name | Status label | 3000ms |
| Duplicate name | `projectsIdentifierExists` | Name exists | Input warning + Status label | Until cleared |
| No permission | `projectsNoPermission` | User not admin | Status label | 3000ms |
| Save failed | `projectsSaveFailed` | API error | Status label | 4000ms |

**Crawler Start:**

| Error | Message Key | Trigger | Display | Timeout |
|-------|-------------|---------|---------|---------|
| No project | `crawlerSelectProject` | Project not selected | Launch message (red) | No timeout |
| Start failed | `crawlerStartFailed` | API/network error | Launch message (red) | No timeout |
| Stop failed | `crawlerStopFailed` | Stop operation error | Launch message (red) | No timeout |

**URL/Domain Validation:**

| Error | Message Key | Trigger | Display | Timeout |
|-------|-------------|---------|---------|---------|
| Invalid domain (AI) | `promptAiInvalidDomain` | Bad domain for prompt generation | Status label | 4000ms |
| Empty domain (crawler) | None explicit | Start URL empty | Browser validation | N/A |

---

### 2.3 How Errors Are Displayed

**Modal Dialogs:**
```html
<div id="projectModal" class="modal-backdrop">
  <div class="modal">
    <div class="modal-header">...</div>
    <form id="projectModalForm">
      <div class="modal-body">...</div>
      <div class="modal-footer">
        <span class="muted" id="projectModalStatus"></span>
      </div>
    </form>
  </div>
</div>
```

**Modal Status Display:**
- Element: `.muted` span in modal-footer
- Update method: `projectModalStatus.textContent = message`
- Dismissal: Manual (form reset), or auto on successful submission
- Styling: Muted text color

**Inline Form Errors:**
- Display location: After form fields
- Styling: Muted text (gray) or warning class (red)
- Examples: `projectStatus`, `launchMsg`, `crawlerActionStatus`

**Toast Notifications (CSS-ready, may be used):**
```css
/* Defined in ui-elements.css, lines 178-212 */
.toast { ... }
.toast-success { background: rgba(34, 197, 94, 0.9); color: #052e16; }
.toast-error { background: rgba(239, 68, 68, 0.9); color: #1f0a0a; }
.toast-info { background: rgba(59, 130, 246, 0.9); color: #0b1220; }
```

---

### 2.4 How to Dismiss Errors

**Automatic Dismissal:**
- Status messages: Auto-clear after 2-6 seconds
- Mechanism: `setTimeout()` with snapshot check
- Reset: `statusLabel.textContent = '—'` or `''`

**Manual Dismissal:**
- Modal errors: Click Cancel or X button
- Form reset: Clicking Reset button
- New action: Starting new operation clears previous message

**Error State Clearing:**
```javascript
// Clear on modal close
const closeProjectModal = () => {
  toggleProjectModalVisibility(false);
  modalPromptAiHandler?.abort?.();
  modalPromptAiHandler?.reset?.();
  if (projectModalStatus) projectModalStatus.textContent = '';
};

// Clear on new operation
setProjectStatus(t('projectsSaving'));
// Message will auto-dismiss after timeout
```

---

## 3. SUCCESS MESSAGES

### 3.1 Success Confirmation Displays

**Save Operations:**
```javascript
setProjectStatus(t('projectsSaved'), 2000);
// Message: "Saved" or "Changes saved"
// Duration: 2000ms (auto-dismiss)
// Display: Status label
```

**Action Completions:**

| Action | Message Key | Display | Timeout |
|--------|-------------|---------|---------|
| Project saved | `projectsSaved` | Status label | 2000ms |
| Crawler started | `crawlerStarted` | Launch message | Persistent (cleared on stop) |
| Crawler stopped | `crawlerStopping` | Launch message | Persistent |
| Telegram saved | `projectsSaved` | Integration message | 2400ms |
| Telegram started | `integrationActionStarted` | Integration message | 2400ms |
| Telegram stopped | `integrationActionStopped` | Integration message | 2400ms |
| Backup reset | `crawlerActionReset` | Crawler action status | 2000ms |
| Duplicates removed | `crawlerActionDedup` | Crawler action status | 2000ms |
| Logs copied | `logCopySuccess` | Crawler action status | 2000ms |

---

### 3.2 When Success Messages Appear

**Project Management:**
- After form submission completes
- After project deletion confirms
- Immediately after database write succeeds

**Crawler Operations:**
- Start: After API returns 200 OK
- Stop: After API returns 200 OK
- Reset/Dedup: After API returns 200 OK

**Integration Actions:**
- Token save: After API call succeeds
- Start/Stop bot: After API call succeeds
- Status update: On successful status fetch

---

### 3.3 Auto-Dismiss Behavior

**Standard Timeout Pattern:**
```javascript
const setStatus = (message, timeoutMs = 0) => {
  statusLabel.textContent = message || '—';
  if (timeoutMs > 0) {
    const snapshot = statusLabel.textContent;
    setTimeout(() => {
      if (statusLabel && statusLabel.textContent === snapshot) {
        statusLabel.textContent = '—';
      }
    }, timeoutMs);
  }
};
```

**Timeout Durations by Operation:**
- 2000ms: Successful saves, quick actions
- 2400ms: Integration operations
- 3000ms: Error messages, validation failures
- 4000ms: Longer operations, deletion confirmations
- 6000ms: Critical errors
- No timeout: Crawler progress (persistent), critical status

---

## 4. LOADING STATES

### 4.1 Loading Indicators

**Text-Based Loading:**
```javascript
launchMsg.textContent = translate('crawlerStarting', 'Starting…');
crawlerActionStatus.textContent = translate('crawlerActionProcessing', 'Processing…');
infoLabel.textContent = translate('integrationStatusUpdating', 'Updating status…');
```

**Loading States by Operation:**

| Operation | Loading Text | Element | Auto-clear |
|-----------|--------------|---------|-----------|
| Crawler start | "Starting…" | launchMsg | Yes (on complete) |
| Crawler stop | "Stopping…" | launchMsg | Yes (on complete) |
| Action processing | "Processing…" | crawlerActionStatus | Yes (2000ms) |
| Status update | "Updating status…" | infoLabel | Yes (on data) |
| Logs loading | "Loading…" | crawlerLogsOutput | Yes (on fetch complete) |
| AI prompt generation | "Generating prompt…" | promptAiStatus | Yes (on complete) |

---

### 4.2 When Loading Indicators Appear

**Crawler Operations:**
- Appear: On form submit
- Disappear: When API responds or errors

**Integration Status:**
- Appear: When loading project status
- Disappear: When status data received or error

**AI Prompt Generation:**
- Appear: On "Generate with AI" button click
- Disappear: When prompt received or cancelled

**Logs Fetching:**
- Appear: On logs refresh click
- Disappear: When logs loaded

---

### 4.3 Text During Processing

**AI Prompt Generation States:**
```javascript
// Initial state
setStatus(t('promptAiStart')); // "Generating prompt…"

// Success
setStatus(t('promptAiReady'), 2000); // "Prompt ready"

// Error
setStatus(t('promptAiError', { message }), 4000); // "Error: {message}"

// Interrupted by user input
setStatus(t('projectsStoppedByInput')); // "Stopped by input"
```

**Progress Display Format:**
```javascript
// Crawler progress
crawlerProgressCounters.textContent = translate(
  'crawlerProgressCounters',
  '{completed} / {total} pages',
  { completed: 45, total: 100 }
);
// Output: "45 / 100 pages" or "45 / 100 pages · errors: 5"
```

---

## 5. FIELD REQUIREMENTS AND DEFAULTS

### 5.1 Required vs Optional Fields

**Project Form - REQUIRED:**
- Project Identifier (projectName)
- LLM Model (projectModel) - if available
- Initial Prompt (projectPrompt) - recommended but not enforced

**Project Form - OPTIONAL:**
- Title (projectTitle)
- Domain (projectDomain)
- Admin login (projectAdminUsername)
- Admin password (projectAdminPassword)
- Voice model (projectVoiceModel)
- Widget URL (projectWidgetUrl)

**Crawler Form - REQUIRED:**
- Start URL (url)
- Project selection (global.currentProject)

**Crawler Form - OPTIONAL:**
- Depth (defaults to 2)
- Pages (defaults to 100)
- Collect books (checkbox, defaults to false)
- Collect Medesk links (checkbox, defaults to false)

**Mail Integration - OPTIONAL:**
- All fields optional
- Integration enabled via checkbox
- If enabled, suggested: IMAP/SMTP host, port, credentials

---

### 5.2 Default Values

**Crawler Defaults:**
```javascript
depth: 2 // min="1", defaults in HTML
pages: 100 // min="1", defaults in HTML
```

**Backup Time:**
```javascript
const DEFAULT_BACKUP_TIME = '03:00'; // 3 AM
hour: 3, minute: 0
```

**Mail Configuration Defaults:**
```javascript
imapSsl: true // checked
smtpTls: true // checked
imapPort: '' // placeholder "993"
smtpPort: '' // placeholder "587"
```

**Knowledge Base:**
```javascript
kbLimit: 1000 // min="10", max="1000"
```

**Project Features:**
```javascript
llm_emotions_enabled: true // checked
llm_voice_enabled: true // checked
knowledge_image_caption_enabled: true // checked
debug_info_enabled: true // checked
llm_sources_enabled: false // unchecked
debug_enabled: false // unchecked
```

---

### 5.3 Placeholder Text Meanings

**Start URL:**
- `placeholder="https://example.com"`
- Meaning: Full URL format with protocol required

**Project Name/Identifier:**
- `placeholder="mmvs"`
- Meaning: Example project slug (lowercase, no spaces)

**Project Title:**
- `placeholder="Project name"`
- Meaning: Human-readable project title, any format allowed

**Project Domain:**
- `placeholder="https://example.com"`
- Meaning: Full domain URL

**Domain Hint:**
- "Paste full URL, for example https://example.com"
- Auto-corrects if protocol missing

**Mail Configuration:**
```
IMAP Host: "imap.example.com"
IMAP Port: "993"
SMTP Host: "smtp.example.com"
SMTP Port: "587"
Username: "user@example.com"
Sender: "support@example.com"
Password: "Password" or "Password saved"
```

---

### 5.4 Help Text and Tooltips

**Field Hints:**

| Field | Hint | Display |
|-------|------|---------|
| Domain (Project) | "Paste full URL, for example https://example.com" | Always visible |
| Mail Integration | "Specify IMAP/SMTP parameters so assistant can work with email." | Always visible, updates dynamically |
| Bitrix Webhook | "Webhook is used for model requests and stored on the server." | Always visible, updates on change |
| Backup Folder | "Name of folder in cloud storage for backups" | Placeholder text |
| Backup Token | "OAuth token from your cloud provider" | Placeholder text |
| Telegram Token | "Enter token" or "Token saved" | Dynamic placeholder |
| Voice Training | "Upload 3+ clean voice clips to teach assistant to speak like project." | Summary text |

**Dynamic Hints (Updated on Toggle):**

```javascript
// Emotions enabled hint
projectEmotionsHint.textContent = enabled
  ? t('projectsEmotionsOnHint')
  : t('projectsEmotionsOffHint');

// Voice enabled hint
projectVoiceHint.textContent = enabled
  ? t('projectsWidgetVoiceHintOn')
  : t('projectsWidgetVoiceHintOff');
projectVoiceModelInput.disabled = !enabled;

// Mail integration hint
hintLabel.textContent = enabled
  ? t('integrationMailHintActive')
  : t('integrationMailHintConfiguredButDisabled');
```

**Mail Integration Hint States:**
1. Not configured: "Specify IMAP/SMTP parameters…"
2. Configured, disabled: "Parameters saved, but integration is disabled…"
3. Configured, enabled: "Integration is active. Assistant can send and read emails."

---

## 6. FORM SUBMISSION BEHAVIOR

### 6.1 Submission Flow

**Project Form Submission:**
```javascript
projectForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  // 1. Validate project name
  const name = projectNameInput.value.trim().toLowerCase();
  if (!name) {
    setProjectStatus(t('projectsEnterIdentifier'), 3000);
    return;
  }
  
  // 2. Collect form data
  const payload = {
    name,
    title: projectTitleInput.value.trim() || null,
    domain: projectDomainInput.value.trim() || null,
    // ... more fields
  };
  
  // 3. Set status and submit
  setProjectStatus(t('projectsSaving'));
  try {
    const resp = await fetch('/api/v1/admin/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'same-origin',
    });
    
    // 4. Handle response
    if (!resp.ok) {
      setProjectStatus(t('projectsSaveFailed'), 4000);
      return;
    }
    
    // 5. Update UI and fetch fresh data
    currentProject = name;
    await fetchProjects();
    await fetchProjectStorage();
    setProjectStatus(t('projectsSaved'), 2000);
    
  } catch (error) {
    console.error(error);
    setProjectStatus(t('projectsSaveError'), 4000);
  }
});
```

---

### 6.2 Validation Order

**Project Form:**
1. Project name not empty
2. Normalize name (lowercase, trim)
3. Check for duplicates against projectsCache
4. Validate optional fields (URL parsing for domain)
5. Collect all field values
6. Submit to API
7. API validates server-side

**Crawler Form:**
1. Check project selected
2. Validate start URL format (HTML5 input type="url")
3. Parse depth and pages as numbers
4. Submit form data to API
5. API validates parameters

**Modal Form (Project Creation):**
1. Check permission: `adminSession.can_manage_projects`
2. Validate project name
3. Check for duplicate identifier
4. Validate optional fields
5. Submit to API

---

### 6.3 What Happens on Success

**Project Saved:**
- UI shows "Saved" (2 sec timeout)
- Project list refreshed
- Project storage fetched
- Knowledge base reloaded
- Status polling reset
- Form remains populated with latest data

**Crawler Started:**
- Progress bar initializes
- Status updates: "Scanning" or "Queued"
- Launch message: "Crawler started"
- Counters begin updating
- Progress tracking activates

**Integration Action (Telegram/MAX/VK):**
- Status updated from API
- Token cleared from UI
- Button states updated (disabled/enabled)
- Info message shows result
- Auto-dismiss after 2.4 seconds

---

### 6.4 What to Do on Failure

**On Form Validation Failure:**
1. Message displayed (red, muted text)
2. Form remains populated
3. Focus may be set to problematic field
4. User can fix and resubmit
5. Message auto-dismisses after 3-6 seconds

**On API Error:**
1. Error message shown: "Failed to save" or specific error
2. Form data preserved
3. No state changes applied
4. User can retry submission
5. Console logs error details for debugging

**Recovery Actions:**
- Reload page to refresh state
- Clear browser storage: `localStorage.removeItem('admin_project')`
- Check browser console for error details
- Verify network connectivity
- Check server status (/health endpoint)

---

## 7. SPECIAL VALIDATIONS

### 7.1 Password Strength Requirements

**Admin Project Password:**
- No explicit strength requirements in frontend
- Type: password input (masked)
- Min length: Not enforced frontend
- Server-side: Backend may enforce

**Backup OAuth Token:**
- Format: Token string (no validation pattern shown)
- Storage: Server-side only (not shown in UI after save)
- Requirement: Must be valid OAuth token for cloud provider

**Telegram/MAX/VK Tokens:**
- Format: Bot token or access token format
- Min length: Platform-specific (not validated frontend)
- Validation: Happens on start/save action
- Error handling: Shows "Last error" if token invalid

---

### 7.2 Character Limits

**Project Identifier:**
- No explicit max shown
- Practical limit: Any valid string
- Should be URL-safe (lowercase, alphanumeric)

**Project Title:**
- No limit shown
- Any text allowed
- Can contain special characters, emoji

**Initial Prompt (Textarea):**
- No explicit limit
- Large text supported (rows="3" shown)
- Resize: vertical (resize:vertical)

**Mail Signature (Textarea):**
- No limit
- rows="3" default
- Resize: vertical

**Knowledge Base Content:**
- No explicit limit
- Displayed with min-height:120px

**Crawler Logs:**
- Max display: 200 lines (configurable)
- Can adjust with logLimit input (min=50, max=1000)

---

### 7.3 Numeric Range Limits (Summary)

| Field | Min | Max | Default | Notes |
|-------|-----|-----|---------|-------|
| Crawl Depth | 1 | None | 2 | Integer |
| Crawl Pages | 1 | None | 100 | Integer |
| IMAP Port | 1 | 65535 | 993 | Valid port range |
| SMTP Port | 1 | 65535 | 587 | Valid port range |
| KB Limit | 10 | 1000 | 1000 | Documents to fetch |
| Backup Hour | 0 | 23 | 3 | 24-hour format |
| Backup Minute | 0 | 59 | 0 | 60-minute format |
| Log Lines | 50 | 1000 | 200 | Display limit |

---

### 7.4 Date/Time Format Requirements

**Backup Time Input:**
- Type: HTML5 `<input type="time">`
- Format: HH:MM (24-hour)
- Parsing logic handles edge cases
- Auto-correction: Values outside range clamped to valid range

**Timestamp Normalization:**
```javascript
// Auto-detects seconds vs milliseconds
if (timestamp < 1e11) {
  timestamp *= 1000; // seconds to ms
}
```

---

## 8. COMPREHENSIVE VALIDATION SUMMARY TABLE

| Validation Type | Field(s) | Required | Format | Error Handling | User Message |
|-----------------|----------|----------|--------|----------------|--------------|
| **Identifiers** | projectName | YES | lowercase, no spaces | Warning class, status message | "Enter identifier" |
| **URLs** | projectDomain, url | CONDITIONAL | Valid URL with protocol | Parsing, auto-correction | "Invalid URL" (implicit) |
| **Email** | projectMailFrom, projectMailUsername | NO | Email format | HTML5 validation | Browser native message |
| **Ports** | imapPort, smtpPort | NO | 1-65535 | parseInt, clamp | None (silent correction) |
| **Numbers** | depth, pages, kbLimit | NO | Positive integers | HTML5 number input | Browser native message |
| **Time** | backupTime | NO | HH:MM 24-hour | Parsing, clamp | Auto-correction |
| **Tokens** | telegramToken, maxToken, vkToken | CONDITIONAL | Alphanumeric | Stored backend, no frontend validation | "Token invalid" (after action) |
| **Passwords** | projectAdminPassword, projectMailPassword | OPTIONAL | Any string | No frontend validation | None |
| **Files** | kbNewFile, kbQaFile, voiceSampleInput | OPTIONAL | Format-specific | Client accept attribute + server validation | Browser native message |
| **Domain | projectDomain | OPTIONAL | Valid URL | URL() parsing constructor | "Invalid domain" (for AI) |
| **Duplicates** | projectName | CHECK | Against projectsCache | Input-warning class | "Identifier exists" |

---

## 9. INTEGRATION VALIDATION PATTERNS

### 9.1 Telegram Integration

**Validation Flow:**
1. Check if project selected
2. Get/validate token (if provided)
3. Auto-start checkbox state
4. Submit to `/api/v1/admin/projects/{project}/telegram/start`

**Error States:**
- No project: "Select a project" message
- Invalid token: "Last error: {error_details}" in info
- Connection failed: Status shows error message

**Success States:**
- Token saved: Button state updates
- Bot running: Status shows "Running"
- Auto-start set: Checkbox state persists

---

### 9.2 Mail Integration

**Validation Flow:**
1. Check IMAP/SMTP hosts provided
2. Validate port numbers (1-65535)
3. Check SSL/TLS settings
4. Validate email addresses (type="email")
5. Store password on save (backend only)
6. Update hint based on state

**Hint State Machine:**
```
State 1: No config
  ↓ Hint: "Specify IMAP/SMTP..."
  
State 2: Config, integration disabled
  ↓ Hint: "Configured but disabled..."
  
State 3: Config, integration enabled
  ↓ Hint: "Integration active..."
```

---

### 9.3 Bitrix Integration

**Validation Flow:**
1. Check webhook URL format
2. Validate against Bitrix24 URL pattern
3. Toggle integration enabled/disabled
4. Update hint based on state

**Hint State Machine:**
```
State 1: No webhook
  ↓ Hint: "Webhook is used for requests..."
  
State 2: Webhook, disabled
  ↓ Hint: "Saved but disabled..."
  
State 3: Webhook, enabled
  ↓ Hint: "Integration active..."
```

---

## 10. GLOBAL FEEDBACK MECHANISM

### 10.1 Status Message Update Pattern

**Common Pattern:**
```javascript
// Set message with optional timeout
function setStatus(message, timeoutMs = 0) {
  statusEl.textContent = message || '—';
  if (timeoutMs > 0) {
    const snapshot = statusEl.textContent;
    setTimeout(() => {
      if (statusEl && statusEl.textContent === snapshot) {
        statusEl.textContent = '—';
      }
    }, timeoutMs);
  }
}

// Usage
setStatus('Saving...'); // Persistent
setStatus('Saved', 2000); // Auto-dismiss after 2 sec
setStatus('Error', 4000); // Auto-dismiss after 4 sec
```

### 10.2 Styling Classes

**Warning/Error Styling:**
```css
.input-warning {
  border-color: rgba(248, 113, 113, 0.8) !important;
  box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.22);
}

.ok { color: var(--success); font-weight: 600; }
.bad { color: var(--danger); font-weight: 600; }
```

**Status Colors:**
- Success: Green (var(--success))
- Error: Red (var(--danger))
- Info: Muted gray (var(--text-muted))

---

## 11. CREDENTIAL SECURITY PATTERNS

### 11.1 Token Handling

**Never Displayed:**
- Telegram tokens
- MAX tokens
- VK tokens
- Mail passwords
- Backup OAuth tokens

**Display After Save:**
- Placeholder changes: "Enter token" → "Token saved"
- Token cleared from input field
- Backend stores encrypted/hashed version

**Submission Without Viewing:**
```javascript
// User enters token, submits form
const token = tokenInput.value.trim(); // from password input (masked)
payload.token = token; // Only sent to API
tokenInput.value = ''; // Cleared immediately after
```

### 11.2 Password Field Handling

**Admin Password:**
- Type: password (masked input)
- Not displayed after save
- Placeholder: "Leave empty to keep unchanged"
- Only sent if user enters new password

**Mail Password:**
- Type: password (masked input)
- Backend stores encrypted
- Not displayed or transmitted with get request
- Placeholder: "Password saved" or "Password"

---

## 12. FORM STATE PRESERVATION

### 12.1 Data Persistence

**LocalStorage:**
```javascript
// Save selected project
if (currentProject) {
  localStorage.setItem('admin_project', currentProject);
} else {
  localStorage.removeItem('admin_project');
}

// Restore on page load
const saved = localStorage.getItem('admin_project');
```

**Form Population:**
```javascript
// When project selected, populate all fields
projectNameInput.value = project.name;
projectTitleInput.value = project.title || '';
projectDomainInput.value = project.domain || '';
projectPromptInput.value = project.llm_prompt || '';
// ... all other fields
```

**Temporary Cache (Session):**
- `projectsCache`: All projects data
- `projectStorageCache`: Storage stats
- Updated on fetch/save operations

---

## 13. ACCESSIBILITY AND USER EXPERIENCE

### 13.1 Aria Labels and Data Attributes

**Project Name Input:**
- No explicit aria-label in current code
- Should have: aria-label="Project identifier" or data-i18n-aria-label

**Language Selection:**
```html
<select id="adminLanguage" aria-label="Language" data-i18n-aria-label="languageLabel"></select>
```

**Tab Management:**
- Knowledge base tabs use role="tab", aria-selected, aria-controls
- Proper tab index management

---

### 13.2 Focus Management

**Modal Opening:**
```javascript
const openProjectModal = () => {
  resetProjectModal();
  toggleProjectModalVisibility(true);
  projectModalName?.focus(); // Set initial focus
};
```

**Keyboard Navigation:**
- ESC key closes modals
- Form submission with Enter key supported
- Tab through form fields in order

---

## 14. ERROR RECOVERY AND DEBUGGING

### 14.1 Error Logging

**Pattern Used:**
```javascript
console.error('operation_name_failed', {
  error,
  context: 'additional_info'
});

console.warn('operation_name_unexpected', error);
```

**Logged Operations:**
- Project creation/update/deletion
- Crawler start/stop
- Integration actions
- File uploads
- Backup operations
- LLM operations

---

### 14.2 User Debugging Steps

1. Check browser console (F12) for error details
2. Look for HTTP error codes in network tab
3. Verify server health: Check /health endpoint
4. Reload page (Ctrl+R) to refresh state
5. Clear localStorage if session corrupt: `localStorage.clear()`
6. Check network connectivity

---

## 15. TRANSLATION/INTERNATIONALIZATION KEYS

### Error Message Keys:
- `projectsEnterIdentifier`: "Enter project identifier"
- `projectsIdentifierExists`: "Project identifier already exists"
- `projectsSaveFailed`: "Failed to save project"
- `projectsSaveError`: "Save error"
- `projectsLoadFailed`: "Failed to load projects"
- `crawlerSelectProject`: "Select a project"
- `crawlerStartFailed`: "Failed to start crawler"
- `crawlerStopFailed`: "Failed to stop crawler"
- `promptAiInvalidDomain`: "Invalid domain for AI prompt generation"
- `integrationStatusError`: "Status error"
- `integrationActionFailed`: "Action failed"

### Success Message Keys:
- `projectsSaved`: "Saved"
- `crawlerStarted`: "Crawler started"
- `integrationActionStarted`: "Started"
- `integrationActionStopped`: "Stopped"

### Status Message Keys:
- `projectsSaving`: "Saving..."
- `crawlerStarting`: "Starting..."
- `crawlerActionProcessing`: "Processing..."
- `integrationStatusUpdating`: "Updating status..."

---

## Summary

The admin panel implements a comprehensive validation and feedback system:

1. **Validation**: Mix of HTML5 native validation, frontend logic, and server-side enforcement
2. **Error Display**: Status labels, warning styling, console logging
3. **User Feedback**: Auto-dismissing messages (2-6 sec), persistent loading states, dynamic hints
4. **Field Requirements**: Clear optional/required marking, sensible defaults
5. **Security**: Tokens masked, passwords encrypted server-side, credentials never displayed
6. **UX**: Dynamic hint updates, form state preservation, keyboard navigation support
7. **Accessibility**: ARIA labels, tab management, focus handling
8. **Internationalization**: All messages use i18n keys for translation support

