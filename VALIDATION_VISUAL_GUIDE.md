# Form Validation Visual Reference Guide

## Error Message Flow Diagram

```
USER ACTION
    ↓
┌───────────────────────────────────────────┐
│  FRONTEND VALIDATION                      │
│  - Required fields                        │
│  - Format check (URL, email, etc.)        │
│  - Duplicate check (project name)         │
└───────────────┬───────────────────────────┘
                ↓
        ┌───────────────┐
        │ Validation    │
        │ Passes?       │
        └───┬────────┬──┘
            YES      NO
            │        │
            ↓        ↓
    ┌──────────┐  ┌─────────────────────────┐
    │ Submit   │  │ SHOW ERROR              │
    │ to API   │  │ - Red border (if input) │
    └──┬───────┘  │ - Status message        │
       ↓          │ - Auto-dismiss (3-6s)   │
    ┌──────┐      └──────────┬──────────────┘
    │ API  │                  ↓
    │ Call │          USER EDITS FORM
    └──┬───┘          & RETRIES
       ↓              
   ┌─────────┐
   │ Success?│
   └─┬───┬───┘
     YES NO
     │   │
     ↓   ↓
┌────────────────────────────────────┐
│ SHOW SUCCESS / FAIL MESSAGE        │
│ - 2-6s timeout                     │
│ - Refresh UI data if success       │
│ - Preserve form if fail            │
└────────────────────────────────────┘
```

## Error Styling Guide

### Red Border Warning (Duplicate Project ID)

```
BEFORE (Valid)
┌─────────────────────┐
│ projectName         │ ← Blue/gray border, normal
└─────────────────────┘

AFTER (Duplicate)
╔═════════════════════╗
║ projectName         ║ ← Red border + shadow
╚═════════════════════╝
⚠️  "Project identifier already exists"
```

### Status Message Display

```
┌─────────────────────────────────────┐
│         Form / Card Section          │
├─────────────────────────────────────┤
│  [Form fields...]                   │
├─────────────────────────────────────┤
│  [Status message - muted gray]       │ ← Auto-clears in 3-6 sec
│  ✓ Saved                             │   or stays if persistent
│  ✗ Error message                     │
└─────────────────────────────────────┘
```

## Modal Dialog Validation Flow

```
┌────────────────────────────────────────┐
│        New Project Modal               │
├────────────────────────────────────────┤
│  Project Identifier:                   │
│  ┌──────────────────────────────────┐  │
│  │ [input field]                    │  │
│  └──────────────────────────────────┘  │
│                                        │
│  (Other optional fields...)            │
│                                        │
├────────────────────────────────────────┤
│  [Status message - if error]           │
│  [Create button] [Cancel button]       │
└────────────────────────────────────────┘
         On Create Click:
              ↓
    Validate + Submit
              ↓
    ┌─────────────────┐
    │ Success?        │
    └────┬────────┬───┘
         YES      NO
         │        │
         ↓        ↓
      Close   Show error
      Modal   in footer
      &       (stays visible)
      Reload
      UI
```

## Crawler Progress Display

```
WAITING STATE:
┌───────────────────────────────┐
│ Crawler Launch                │
│ ☐▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬ 0%        │
│ Waiting to start              │
│ 0 / 0 pages                   │
└───────────────────────────────┘

RUNNING STATE:
┌───────────────────────────────┐
│ Crawler Launch                │
│ ░░░░░░░░▮▮▮▬▬▬▬▬▬▬▬▬▬▬ 40%    │
│ Scanning (15 pages)           │
│ 40 / 100 pages · errors: 2    │
│ Last URL: https://example.com │ ← Clickable link
└───────────────────────────────┘

COMPLETE STATE:
┌───────────────────────────────┐
│ Crawler Launch                │
│ ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮ 100%    │
│ Done                          │
│ 100 / 100 pages               │
└───────────────────────────────┘
```

## Integration Status States

### Telegram Integration Example

```
NO PROJECT SELECTED:
┌──────────────────────────────────┐
│ Telegram bot                     │
│                                  │
│ [Bot Token field - disabled]     │
│ ☐ Auto-start on launch           │
│ Status: —                        │
│ Select a project to manage bot   │
│                                  │
│ [Buttons - all disabled]         │
└──────────────────────────────────┘

PROJECT SELECTED (NO CONFIG):
┌──────────────────────────────────┐
│ Telegram bot                     │
│                                  │
│ [Bot Token field]                │
│ ☐ Auto-start on launch           │
│ Status: —                        │
│ Save token and start the bot     │
│                                  │
│ [Save] [Start] [Stop-disabled]   │
└──────────────────────────────────┘

WITH TOKEN (RUNNING):
┌──────────────────────────────────┐
│ Telegram bot                     │
│                                  │
│ [Bot Token - "Token saved"]      │
│ ☑ Auto-start on launch           │
│ Status: Running                  │
│ Token: ••••••••••                │
│ Auto-start: Enabled              │
│                                  │
│ [Save] [Start-disabled] [Stop]   │
│ Saved ← (2.4s timeout)           │
└──────────────────────────────────┘

ERROR STATE:
┌──────────────────────────────────┐
│ Telegram bot                     │
│                                  │
│ Status: Stopped                  │
│ Token: ••••••••••                │
│ Last error: Invalid token format │
│                                  │
│ ✗ Failed to start                │
└──────────────────────────────────┘
```

## Mail Integration Hint States

```
STATE 1: NOT CONFIGURED
┌─────────────────────────────────────────┐
│ Mail Connector                          │
│ ☐ Enable integration                    │
│                                         │
│ IMAP Host: [empty]                      │
│ IMAP Port: [empty]                      │
│ SMTP Host: [empty]                      │
│ SMTP Port: [empty]                      │
│ ⓘ Specify IMAP/SMTP parameters so...    │
└─────────────────────────────────────────┘

STATE 2: CONFIGURED, DISABLED
┌─────────────────────────────────────────┐
│ Mail Connector                          │
│ ☐ Enable integration                    │
│                                         │
│ IMAP Host: imap.example.com             │
│ IMAP Port: 993                          │
│ SMTP Host: smtp.example.com             │
│ SMTP Port: 587                          │
│ ⓘ Parameters saved, but disabled.       │
│   Enable to activate.                   │
└─────────────────────────────────────────┘

STATE 3: CONFIGURED, ENABLED
┌─────────────────────────────────────────┐
│ Mail Connector                          │
│ ☑ Enable integration                    │
│                                         │
│ IMAP Host: imap.example.com             │
│ IMAP Port: 993                          │
│ SMTP Host: smtp.example.com             │
│ SMTP Port: 587                          │
│ ⓘ Integration is active. Assistants     │
│   can send and read emails.             │
└─────────────────────────────────────────┘
```

## Input Type Validation Examples

### Email Input
```
VALID:
user@example.com          ✓ Accepted
contact@domain.co.uk      ✓ Accepted

INVALID:
user@example              ✗ Browser error: "Invalid email"
user example@example.com  ✗ Browser error: "Invalid email"
@example.com              ✗ Browser error: "Invalid email"
```

### URL Input
```
VALID:
https://example.com       ✓ Accepted
http://example.com/path   ✓ Accepted

INVALID:
example.com               ✗ Browser error: "Invalid URL"
ftp://example.com         ✗ Browser error: "Invalid URL"
/path/only                ✗ Browser error: "Invalid URL"
```

### Number Input (with min/max)
```
For field: min="1" max="1000"

VALID:
1, 50, 500, 1000         ✓ Accepted

INVALID:
0                        ✗ Browser spinner prevents
1001                     ✗ Browser spinner prevents
abc                      ✗ Browser spinner prevents
```

### Time Input
```
VALID:
03:00   →  03:00         ✓ Accepted
23:59   →  23:59         ✓ Accepted

OUT OF RANGE:
24:00   →  Auto-clamp to 23:00
99:99   →  Auto-clamp to 23:59
```

## Keyboard Navigation

```
TAB FLOW (Project Form):
┌──────────────────────────────┐
│ Identifier → Title → Domain  │
│     ↓         ↓       ↓      │
│   Model → Prompt → Buttons   │
│     ↓         ↓       ↓      │
│  [Focus loops...]            │
└──────────────────────────────┘

ESC KEY (Modals):
Modal visible
    ↓
  ESC pressed
    ↓
  Close modal
  Clear error messages
  Reset form
```

## Project Form State Transitions

```
┌─────────────────────────────┐
│   No Project Selected       │
├─────────────────────────────┤
│  All fields disabled        │
│  No data shown              │
│  "Select a project..."      │
└──────────┬──────────────────┘
           │
        Select
        Project
           │
           ↓
┌─────────────────────────────┐
│   Project Selected          │
├─────────────────────────────┤
│  Fields populated with data │
│  Can edit and save          │
│  Admin section visible      │
│  Integrations loaded        │
└──────────┬──────────────────┘
           │
      Save Form
           │
           ↓
      Validation
           ↓
      ┌─────────┐
      │ Pass?   │
      └─┬─────┬─┘
        YES   NO
        │     │
        ↓     ↓
      API   Show
      Call  Error
        │     │
        ↓     ↓
      Update Keep
      UI   State
      &
      Clear
      Form
```

## Error Recovery Path

```
┌─────────────────┐
│  ERROR SHOWN    │ ← "Failed to save"
└────────┬────────┘
         │
    ┌────┴────────────────────────┐
    │ User Action                 │
    └────┬───────────┬───┬────────┘
         │           │   │
         ↓           ↓   ↓
    Retry       Edit    Reload
    Same       Field    Page
         │           │   │
         ↓           ↓   ↓
      API        Resubmit Fresh
      Call       Form   State
         │           │   │
         ↓           ↓   ↓
      Success   Success Success
      or        or     (loses
      Failure   Failure data)
```

## Storage Format Display

```
COMPACT FORMAT:
Text: 150 KB
Files: 24 MB
Contexts: 512 KB
Redis: 8 MB

EXPANDED FORMAT:
Texts: 150 KB · Files: 24 MB · Contexts: 512 KB · Redis: 8 MB
```

## Token Lifecycle

```
USER NEVER ENTERS TOKEN:
┌─────────────────────────────┐
│ Telegram Token              │
│ ┌─────────────────────────┐ │
│ │ "Token saved"           │ │ ← Placeholder
│ │ (field disabled?)       │ │
│ └─────────────────────────┘ │
│ (Can't edit without new)    │
└─────────────────────────────┘

USER ENTERS NEW TOKEN:
┌─────────────────────────────┐
│ Telegram Token              │
│ ┌─────────────────────────┐ │
│ │ •••••••••••••••••••     │ │ ← Masked input
│ │ (type=password)         │ │
│ └─────────────────────────┘ │
│ [Save Token Button]         │
└─────────────────────────────┘
         ↓
    Click Save
         ↓
    ┌─────────────┐
    │ Transmit to │
    │ Backend API │
    └─────────────┘
         ↓
    ┌─────────────────────────────┐
    │ Backend:                    │
    │ - Hash/encrypt token        │
    │ - Store in database         │
    │ - Return success            │
    └─────────────────────────────┘
         ↓
    ┌─────────────────────────────┐
    │ Frontend:                   │
    │ - Clear input field         │
    │ - Show "Token saved"        │
    │ - Disable further editing   │
    └─────────────────────────────┘
```

## Message Timeout Progression

```
MESSAGE LIFECYCLE:

t=0ms:   "Saving..."              ← Set immediately
         (user sees message)

t=2000ms: "Saved"                 ← Replace with success
         (if success)

t=2000ms+: [Snapshot check]
           If still "Saved":
              Clear to "—"

TOTAL VISIBLE: ~2 seconds


PERSISTENT MESSAGE (No Timeout):

t=0ms:   "Crawler started"
         (persistent)
         
[User watches progress bar update]

t=30min: Stop crawler clicked
         "Stopping..."
         
[Message stays until API responds]
```

## Accessibility Structure

```
HTML STRUCTURE (With ARIA):

<label>
  Project Identifier
  <input aria-label="Project identifier in English"
         aria-required="true"
         aria-invalid="false">
</label>

<span role="status" aria-live="polite">
  ← Error/success messages here
     Screen readers announce changes
</span>

<form role="form">
  <fieldset>
    <legend>Project Settings</legend>
    ← Groups related fields
  </fieldset>
</form>
```

## Service Health Indicator

```
┌──────────────────────────────┐
│ Services                     │
├──────────────────────────────┤
│ ● Mongo: up                  │ ← Green (ok)
│ ○ Redis: down                │ ← Red (failed)
│ ○ Qdrant: down               │ ← Red (failed)
│                              │
│ Status: degraded             │ ← Overall status
└──────────────────────────────┘

HOVER OVER RED:
Shows tooltip with error message:
"Connection refused: 127.0.0.1:6379"
```

