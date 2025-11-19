# Admin Panel Monitoring, Backup, and Maintenance Features - User Documentation

## Overview
The admin panel provides comprehensive monitoring, maintenance, and backup capabilities for managing the SiteLLM platform. This documentation covers key features for administrators to monitor system health, manage backups, and track user activity.

---

## 1. MONITORING DASHBOARD

### Status Overview Cards
The dashboard displays four main status cards at the top:

#### Project Card
- **Displays**: Currently selected project name
- **Shows**: Whether a project is selected or not
- **Purpose**: Quick reference for which project you're working with
- **Action**: Click to change project selection

#### Crawling Card
- **Status Values**:
  - Waiting to start
  - Scanning (with active count)
  - Queued (with pending count)
  - Done
  - Errors
- **Displays**: Progress percentage, page counters (X / Y pages), error count
- **Additional Info**:
  - Last crawl timestamp (ISO format)
  - Recent URLs being crawled
  - Notes about current state (e.g., "Indexing in progress")

#### LLM Insights Card
- **States**:
  - "LLM available · {count} docs" - System is ready
  - "LLM unavailable" - Connection issue detected
- **Shows**: Number of documents indexed in MongoDB
- **Action when unavailable**: Click "Check connection" link

#### Build Card
- **Fill Percentage**: Vector store capacity (0-100%)
- **Details**:
  - MongoDB documents count
  - Qdrant vector points count
- **Purpose**: Monitor knowledge base storage and vector indexing

---

## 2. RESOURCE MONITORING

### CPU Monitoring
**Two metrics tracked:**
- **CPU (app)**: Percentage of CPU used by the SiteLLM application
- **CPU (sys)**: System-wide CPU usage percentage

**What's normal:**
- App CPU: 5-20% during light activity, up to 50-70% during active crawling/indexing
- Sys CPU: Should not exceed 80-90% for reliable operation

**When to be concerned:**
- App CPU consistently above 80% = increase resources or reduce concurrent tasks
- Sys CPU above 95% = system bottleneck, may need to restart services or upgrade

### Memory (RAM) Monitoring
**Display format**: `{used}/{total} MB ({percentage}%)`

**Example**: `1024/4096 MB (25%)`

**What's normal:**
- 30-60% of available RAM for typical operations
- 60-80% during large document processing

**When to take action:**
- Over 85% usage = slow operations, possible memory leaks
- Over 95% usage = critical, service may crash or become unresponsive

### RSS (Resident Set Size)
- **Shows**: Actual memory being used by Python process
- **Normal range**: 200-800 MB depending on workload
- **High values** (>1.5 GB) may indicate memory leak

### GPU Information
- **Display**: GPU model and availability status
- **Shows**: "–" if no GPU detected
- **Typical values**:
  - "NVIDIA RTX 3080 (10GB)" - GPU available
  - "–" - No GPU or not configured

### Python Version
- **Shows**: Python interpreter version (e.g., "Python 3.11.5")
- **Purpose**: Verify compatibility and identify environment

---

## 3. SERVICE HEALTH

### Service Status Indicators
Three critical services are monitored:

#### MongoDB
- **Status**: "up" (green) or "down" (red)
- **Purpose**: Main database for documents and project data
- **If down**: 
  - Crawler cannot save results
  - Knowledge base operations fail
  - User data is inaccessible

#### Redis
- **Status**: "up" (green) or "down" (red)
- **Purpose**: Cache and session management
- **If down**: 
  - Sessions may be lost
  - Performance degradation
  - LLM queue processing affected

#### Qdrant
- **Status**: "up" (green) or "down" (red)
- **Purpose**: Vector database for semantic search
- **If down**: 
  - LLM cannot retrieve knowledge base
  - Search and RAG features fail

#### Overall Status
- **Shows**: Composite health status
- **Values**:
  - "healthy" - All services operational
  - "degraded" - One or more services down
  - "unknown" - Cannot determine status

### Service Health Troubleshooting

**If a service shows "down":**

1. **Check service logs** in the "Logs (last 200)" section
2. **Refresh status** - Click the refresh button to verify status hasn't recovered
3. **Common causes**:
   - Service process crashed
   - Network connectivity issue
   - Port conflict
   - Insufficient resources

4. **Recovery steps**:
   - Restart the service via Docker/Kubernetes
   - Check disk space and available memory
   - Review service-specific logs
   - Contact infrastructure team if persistent

---

## 4. STATISTICS AND ANALYTICS

### User Activity Graph

**Display**: Interactive line chart showing requests over time

**Time Period**: Last 14 days by default (configured in stats.js, line 10: `STATS_DAYS = 14`)

**Reading the Graph:**
- **X-axis**: Date (ISO format, e.g., "2025-01-15")
- **Y-axis**: Number of requests
- **Line**: Shows request trend
- **Hover tooltip**: Shows exact date and request count when hovering over a point
- **Grid lines**: Reference markers for easier reading

### Statistics Summary
Shows two key metrics:

1. **Total Requests**: Sum of all requests in the period
   - Example: "Total 4,250 requests"

2. **Per Day Average**: Total divided by number of days
   - Example: "per day 303.6"

### Time Period Information
- **Subtitle shows**: Actual date range covered
  - Example: "2025-01-01 — 2025-01-14"
- **Updates when**: New data is loaded or date range changes

### Exporting Data

**Export to CSV:**
1. Click the "Export CSV" button
2. File downloads as: `request-stats-{project-name}.csv`
3. Can be opened in Excel, Google Sheets, or any spreadsheet software

**CSV Format:**
- Column 1: Date (ISO format)
- Column 2: Request count
- One row per day

**Use cases:**
- Trend analysis
- Performance reports
- Integration with analytics tools
- Creating custom charts

### Refreshing Statistics
- Click "Refresh" button to fetch latest data
- Automatic updates occur every 5 seconds while panel is visible
- Status message shows "Loading…" during fetch

---

## 5. LOGS MANAGEMENT

### Crawler Logs

**Access**: Click the "?" button in the Crawler Launch section

**Display**:
- Pre-formatted log output
- Filtered to show crawler-related entries only
- Last 400 log lines shown
- Auto-scrolls to show newest entries

**Log Entry Format**: Each line shows:
- Timestamp
- Log level (INFO, ERROR, WARNING)
- Module name
- Message

**Reading Crawler Logs:**
- **INFO**: Normal operation messages
- **ERROR**: Something failed (URL not found, timeout, etc.)
- **WARNING**: Potential issues (slow response, retry attempts)

**Common Log Messages:**
- "Crawling started" - Crawler initialization
- "Processing URL: {url}" - Currently crawling a page
- "Indexed X documents" - Progress indicator
- "Error processing {url}: {reason}" - Individual page failure
- "Crawl completed: {count} pages, {errors} errors" - Final summary

**Crawler Log Actions:**
- **Copy**: Click copy icon to copy all logs to clipboard
- **Refresh**: Manually fetch latest logs
- **Close**: Hide the log panel (or press Escape)

### System Logs

**Access**: "Logs (last 200)" section at bottom of dashboard

**Display**:
- All system and application logs
- Shows last 200 lines (configurable via input field: 50-1000)
- Auto-updated every 5 seconds

**Log Sources Include:**
- Python application logs
- API request/response logs
- Background job processing
- Service integration logs
- Error stack traces

**Filter logs**: Use browser's Find function (Ctrl+F / Cmd+F) to search

**Copy System Logs:**
1. Click "Copy" button below the logs
2. Logs are copied to clipboard
3. Paste into support ticket or external system

**Monitoring Log Volume:**
- Log output is capped at 200 lines to prevent memory issues
- Older logs are automatically removed
- Adjust line limit if you need more history (up to 1000)

### Log Troubleshooting

**Identifying Issues from Logs:**
1. Search for "ERROR" or "FAILED" keywords
2. Check timestamps to correlate with problems
3. Look for repeated patterns indicating systemic issues
4. Check resource metrics (CPU/RAM) around error timestamps

**Common Issues and Log Signatures:**
- **Connection timeout**: "ConnectionError" or "timeout" messages
- **Out of memory**: "MemoryError" or RAM showing >95%
- **Database issues**: "MongoError" or "ConnectionPoolError"
- **LLM issues**: "OllamaError" or "model not found"

---

## 6. BACKUP CONFIGURATION (Super Admin Only)

**Important**: Backup features are only visible to Super Admin users. Regular admins will not see this section.

### Backup Schedule Configuration

**Enable/Disable Backups:**
- Check "Enable daily backup" to activate automatic backups
- When disabled, backups only run manually

**Backup Time:**
- **Format**: HH:MM (24-hour format)
- **Default**: 03:00 (3 AM)
- **Recommended**: Off-peak hours when system is less loaded

**Timezone Selection:**
- Dropdown with Russian timezone options (UTC, Europe/Moscow, Asia/Vladivostok, etc.)
- Choose timezone matching your organization's location
- Backup time is interpreted in selected timezone

**Examples:**
- Set 02:00 UTC for 2 AM UTC
- Set 23:00 Europe/Moscow for 11 PM Moscow time

### Yandex.Disk Configuration

**Remote Folder:**
- Where backups are stored on Yandex.Disk
- Default: "sitellm-backups"
- Can create subfolders: "backups/production" or "backups/2025"
- Must have write permissions in folder

**OAuth Token:**
1. Generate token from Yandex.Disk settings
2. Paste token in "OAuth token" field
3. Click "Save" to store securely on server
4. Token is never displayed after saving (security measure)

**Token Status:**
- Green "Token saved" = Ready to backup
- Red "Token missing" = Cannot perform backups
- Click "Delete" to remove saved token

### Manual Backup Actions

**Create Backup Now:**
1. Ensure token is saved
2. Click "Create backup now" button
3. Status updates to show backup is running
4. Can take 5-30 minutes depending on data size
5. Progress shown in "Operations log" section

**Refresh Status:**
- Click "Refresh status" to check backup progress
- Updates job list and current status
- Happens automatically every 5 seconds during active operations

**Backup Duration:**
- Small databases (< 100 MB): 5-10 minutes
- Medium databases (100 MB - 1 GB): 10-20 minutes
- Large databases (> 1 GB): 20-45 minutes
- Network speed affects duration

### Restore from Backup

**Restore Process:**
1. Locate backup path from "Operations log" section
2. Click "Use" button on desired backup to auto-fill path
3. Or manually enter path: `/sitellm-backups/backup_2025-01-15_03-00.archive.gz`
4. Click "Restore" button
5. System restores data from backup (this is destructive - replaces current data)

**Restore Duration:**
- Similar to backup time
- Cannot be cancelled once started

**Warning**:
- Restoring overwrites current data
- Keep data frozen during restore operation
- Verify backup integrity before restoring in production

### Operations Log

**Shows**:
- History of recent backup and restore operations
- Up to 6 most recent jobs displayed

**For Each Operation:**
- **Operation type**: "Backup" or "Restore"
- **Status**: "Running", "Queued", "Completed", or "Failed"
- **Remote path**: Where backup is stored
- **Timestamp**: When operation was created
- **Error message**: If operation failed

**Job Actions:**
- **Use for Restore**: Sets backup path to restore field
- **Copy Path**: Copies backup path to clipboard

**Status Indicators:**
- Highlighted in blue = currently active operation
- Green checkmark = successful completion
- Red text = error occurred

### Backup Status Summary

**Shows current state:**
- "Backup scheduled for 03:00" = enabled and waiting
- "Backup queued" = queued in job processor
- "Backup running" = currently in progress
- "Last run: 2025-01-15 03:15" = when last backup started
- "Last success: 2025-01-15 03:28" = when last successful backup completed

**Understanding Status:**
- Last run may be recent but still "running"
- Success timestamp lags behind if backup took time
- "Never" = no backups have been run yet

---

## 7. LLM MANAGEMENT

### Current LLM Configuration

**Displays:**
- **Model**: Currently selected model name (e.g., "yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest")
- **Backend**: Type of LLM service (e.g., "Ollama", "OpenAI", "Local")
- **Device**: Hardware running the model (e.g., "GPU: NVIDIA RTX 3080", "CPU")

### Ollama Configuration

**Ollama Base URL:**
- Default: `http://host.docker.internal:11434` (Docker container access)
- For local: `http://localhost:11434`
- For remote: `http://192.168.1.10:11434`

**Model Name:**
- Full model identifier including version tag
- Example: `yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest`
- Format: `{provider}/{model-name}:{tag}`

**Save & Ping:**
1. Enter Ollama base URL and model name
2. Click "Save" to update configuration
3. Click "Ping" to verify connection
4. Ping result shows:
   - Success: Green checkmark, connection time
   - Failure: Red error, connection details

### Ollama Model Catalog

**Installed Models:**
- Lists models currently downloaded on Ollama server
- Shows model size and parameters
- Ready to use immediately

**Popular Models:**
- Recommended models for different use cases
- Organized by category (General, Chat, Code, etc.)
- Click to install

**Installation Progress:**
- Shows models being downloaded
- Status: "Pending", "Installing…", "Installed", "Installation failed"
- Can take 5-60 minutes depending on model size

**Installing a Model:**
1. Find model in Popular list
2. Click model name or "Install" button
3. Status shows as "Pending" then "Installing…"
4. View progress in "Installation" section
5. Refresh page to see latest status

**Installation Failures:**
- Check disk space: Models require 5-20 GB
- Check network: Ollama downloads from hub
- Verify Ollama is running: Check backend availability
- Try installing again: Temporary network issues

### Ollama Servers Management

**Add Server to Cluster:**

1. **Identifier**: Unique name (e.g., "gpu-server-01", "cpu-backup")
2. **URL**: Full Ollama API endpoint (e.g., `http://10.0.1.5:11434`)
3. **Enabled**: Toggle to activate/deactivate without removing
4. Click "Add" button

**Server Health:**
- Green "up" = Server responding and ready
- Red "down" = Cannot connect to server
- Automatically checked every 10 seconds

**Server Status Display:**
- Lists all servers in cluster
- Shows model availability on each server
- Indicates which server is primary

**Load Balancing:**
- System automatically distributes requests across healthy servers
- Disabled servers are skipped
- Failed requests retry on other servers

**Use Cases for Multiple Servers:**
- **High availability**: Multiple servers for redundancy
- **Load distribution**: Spread requests across multiple GPUs
- **Specialization**: Different servers for different models
- **Failover**: Backup server takes over if primary fails

---

## 8. FEEDBACK REVIEW

### User Feedback List

**Display**: All feedback submitted by users

**For Each Feedback:**
- **User question/feedback**: Full text submitted
- **Timestamp**: When feedback was received
- **Status**: New/Reviewed/Archived
- **Project**: Which project feedback is for

**Reading Feedback:**
- Review for patterns in user complaints
- Identify features users are asking for
- Find bugs reported by users
- Understand user satisfaction level

### Acting on Feedback

**Steps:**
1. Read feedback carefully
2. Determine type: Bug report, feature request, or complaint
3. **For bugs**: 
   - Verify in staging environment
   - Check logs for related errors
   - Create ticket in bug tracking system
4. **For features**:
   - Evaluate feasibility
   - Estimate effort
   - Add to product roadmap if approved
5. Mark as reviewed to avoid duplicate processing

**Recording Outcomes:**
- Add notes to issue tracking system
- Reference feedback ID for traceability
- Notify user of actions taken (if contact available)

---

## 9. CRAWLER MANAGEMENT MONITORING

### Crawler Progress Display

**Progress Bar**:
- Visual representation of crawling progress
- Percentage complete: `(done / total) * 100`
- Updates every 1-2 seconds during crawling

**Status Text**:
- **Waiting to start**: No crawler running
- **Scanning (X)**: X pages currently being processed
- **Queued (X)**: X pages waiting to be crawled
- **Done**: All pages successfully crawled
- **Errors**: Failures detected during crawl

**Page Counters**: "X / Y pages"
- X = Successfully crawled pages
- Y = Total pages discovered
- Including errors: "X / Y pages · errors: Z"

### Crawler Progress Notes

**Information displayed**:
- "Indexing in progress or errors detected; see counters" = Processing found documents
- "LLM unavailable — queue processing paused" = LLM service down
- Last URL being crawled
- Custom backend notes about crawler state

**Interpreting Notes:**
- If indexing note shows: Crawler found content, LLM is processing
- If LLM paused note: Wait for LLM to come back online
- Check logs for detailed error information

### Crawler Status Counters

**Queued**: Pages waiting to be crawled
- Increases when new URLs discovered
- Decreases as pages are processed

**In Progress**: Pages currently being crawled
- Usually 1-5 depending on concurrency setting
- Indicates system is actively working

**Done**: Successfully processed pages
- Increases steadily during successful crawl
- Should be largest counter at end

**Failed**: Pages that had errors
- Should remain small if system is healthy
- Check logs to understand failures
- Common failures: 404, timeout, robots.txt

---

## 10. QUICK REFERENCE: STATUS INTERPRETATION

### Green (OK) Status
- Service shows "up"
- CPU usage < 70%
- RAM usage < 80%
- No errors in last 50 logs
- Crawler running smoothly

### Yellow (Warning) Status
- Service intermittent connection
- CPU usage 70-85%
- RAM usage 80-90%
- Occasional errors (< 5 per minute)
- Crawler slowing down

### Red (Critical) Status
- Service shows "down"
- CPU usage > 85%
- RAM usage > 90%
- Frequent errors (> 10 per minute)
- Crawler unable to proceed
- **Action required immediately**

---

## 11. MAINTENANCE BEST PRACTICES

### Daily Checks
- Monitor resource usage: CPU, RAM, disk
- Check service health: all services should be "up"
- Review error logs for patterns
- Verify backups completed successfully

### Weekly Tasks
- Export statistics to analyze trends
- Review user feedback and act on critical issues
- Check crawler logs for repeated failure patterns
- Verify backup restoration works (test restore to staging)

### Monthly Actions
- Clean up old logs (keep last 30 days)
- Archive old statistics
- Update documentation with any configuration changes
- Review resource consumption trends
- Plan capacity upgrades if needed

### Emergency Procedures

**Service Down:**
1. Check resource metrics (is system out of RAM/CPU?)
2. Review logs (what error caused crash?)
3. Restart service via Docker/Kubernetes
4. Monitor for 5 minutes to ensure stability
5. If continues failing: check health, backup, restore from previous backup

**Data Corruption:**
1. Stop all operations (disable crawler, new uploads)
2. Create manual backup of current state
3. Restore from latest known-good backup
4. Verify data integrity after restore
5. Document incident

**Backup Failure:**
1. Check network connectivity to Yandex.Disk
2. Verify OAuth token is still valid
3. Check disk space on local server
4. Try manual backup
5. If persistent: check service logs, contact infrastructure team

---

## 12. TROUBLESHOOTING CHECKLIST

| Issue | Check | Fix |
|-------|-------|-----|
| Crawling slow | CPU, RAM, service health | Reduce max_pages, wait for resources to free |
| LLM unavailable | Check "LLM" section, MongoDB status | Restart LLM service, verify Ollama running |
| Backup failed | Network, token, disk space | Refresh token, check connectivity, free disk space |
| High memory usage | Check RSS and RAM % in Resources | Restart app, reduce batch size, investigate memory leak |
| Service down | Check individual service status | Check logs, restart service, verify network |
| Lost data | Check last successful backup | Restore from backup, notify users of data loss |

---

## 13. ACCESSING FEATURES

### For Regular Admins:
- Monitoring Dashboard: Full access
- Resource Monitoring: Full access
- Service Health: Full access
- Statistics: Full access
- Logs Management: Full access
- Crawler Management: Full access
- LLM Management: Full access
- Feedback Review: Full access
- **Backup Configuration: NOT VISIBLE** (requires Super Admin)

### For Super Admins:
- All features fully accessible
- Backup Configuration: Full access
- Token management: Full access
- Restore operations: Full access

---

## 14. KEYBOARD SHORTCUTS

- **Escape**: Close crawler logs panel
- **Ctrl/Cmd + F**: Search logs
- **Ctrl/Cmd + A**: Select all log text
- **Ctrl/Cmd + C**: Copy selected text
- **Click on date point in stats**: View detailed stats for that date (hover functionality)

---

## 15. DATA RETENTION AND CLEANUP

### Automatic Cleanup
- Log files: Last 200 lines retained automatically
- Statistics: 14-day window retained (older data available via archive)
- Backup operations log: Last 6 operations shown
- Session data: 24-hour expiration

### Manual Cleanup
- Export statistics before 14-day retention expires
- Archive crawler logs manually if needed
- Delete old backups from Yandex.Disk to free storage

### Recommended Retention
- Logs: 30 days minimum
- Statistics: 1 year minimum
- Backups: Keep at least 2 weeks' worth
- Operation logs: Keep for compliance (30-90 days)

