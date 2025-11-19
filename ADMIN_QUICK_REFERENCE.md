# Admin Panel - Quick Reference Guide

## Visual Status Indicators Cheat Sheet

### Service Health Colors
| Status | Color | Meaning | Action |
|--------|-------|---------|--------|
| up | Green | Service running | None needed |
| down | Red | Service stopped | Investigate, restart |
| unknown | Gray | Cannot detect | Check logs |

### Resource Thresholds
| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| CPU (app) | < 50% | 50-75% | > 75% |
| CPU (sys) | < 70% | 70-85% | > 85% |
| RAM | < 60% | 60-80% | > 80% |
| Disk | < 80% | 80-90% | > 90% |

### Crawler Status States
| Status | Icon | Meaning |
|--------|------|---------|
| Waiting to start | Gray | No crawler running |
| Scanning (5) | Blue | 5 pages being crawled |
| Queued (12) | Yellow | 12 pages waiting |
| Done | Green | All completed |
| Errors | Red | Some failed |

---

## Common Tasks and Steps

### Task: Check System Health
1. Go to "Services" status card
2. Verify MongoDB, Redis, Qdrant show "up" (green)
3. Check "Overall" status = healthy
4. Check Resources: CPU, RAM within normal ranges
5. If anything red: Click to view error details

### Task: Monitor Crawling Progress
1. Go to "Crawling" card at top
2. Read status: Scanning/Queued/Done
3. Watch progress bar fill up
4. Monitor page counters: X / Y pages
5. Check notes for issues: "Indexing in progress"
6. View recent URLs being crawled

### Task: View Activity Statistics
1. Find "User activity" section
2. Hover over date points to see exact count
3. Read summary: Total requests, per-day average
4. Check date range covered
5. Click "Export CSV" to download data

### Task: Access Crawler Logs
1. Click "?" button in Crawler Launch card
2. Log panel opens above form
3. View filtered crawler entries
4. Search with Ctrl+F for specific errors
5. Click copy icon to copy all logs
6. Press Escape to close

### Task: Create Manual Backup
1. Go to "Backups" section (Super Admin only)
2. Verify OAuth token is saved (green status)
3. Click "Create backup now"
4. Watch status: Running → Completed
5. Check "Operations log" for backup path
6. Backup appears in recent operations list

### Task: Restore from Backup
1. Go to "Backups" section (Super Admin only)
2. Find backup in "Operations log"
3. Click "Use" button OR manually enter path
4. Click "Restore" button
5. Wait for operation to complete
6. **Warning**: Current data will be overwritten!

### Task: Diagnose Service Issues
1. Check "Services" card - which is red?
2. Note the failing service (MongoDB/Redis/Qdrant)
3. Go to "Logs (last 200)" section
4. Search for service name (Ctrl+F)
5. Look for ERROR or FAILED messages
6. Check resource metrics: CPU/RAM/Disk
7. Review error messages for clues

### Task: Monitor Performance
1. Watch CPU and RAM metrics
2. Compare to baseline (check historical logs)
3. If trending up: Investigate resource hogs
4. Check crawler logs for inefficient operations
5. Review statistics for traffic spikes
6. Plan resource scaling if needed

### Task: Export Statistics for Report
1. Go to "User activity" section
2. Click "Export CSV" button
3. File downloads: request-stats-{project}.csv
4. Open in Excel or Google Sheets
5. Create charts and analysis
6. Include in monthly reports

---

## Quick Diagnostics

### "Crawler is stuck on 'Scanning'"
```
Check:
- Is CPU at 100%? → Reduce concurrent tasks
- Is RAM at 90%+? → Restart, check for leak
- Are URLs failing? → Check logs for pattern
- Is LLM down? → Check "LLM" section status
```

### "LLM shows unavailable"
```
Check:
- MongoDB status → must be "up"
- Check Ollama base URL in LLM section
- Try "Ping" button → verify connectivity
- Check "Logs" for OllamaError messages
- Verify Ollama server is running
```

### "Backup failed"
```
Check:
- Is token saved? → Red status = generate new token
- Internet connectivity? → Can you reach Yandex.Disk?
- Disk space? → Free up space, check logs
- Token expired? → Generate fresh token from Yandex
```

### "System running slow"
```
Check in order:
1. CPU > 80%? → Reduce load, increase resources
2. RAM > 85%? → Restart service, check for leak
3. Services down? → Restart them
4. Disk full? → Delete old logs, backups
5. High latency logs? → Check network
```

### "Services keep going down"
```
Check:
- Out of memory? → Increase RAM allocation
- Out of disk? → Free space (40GB minimum)
- Resource limits hit? → Increase container limits
- Network issues? → Check connectivity
- Check logs for repeated errors
```

---

## API Endpoints Reference (for logs/debugging)

### Crawler Status
```
GET /api/v1/crawler/status?project={project_name}
Returns: queued, in_progress, done, failed, last_url, last_crawl_iso
```

### System Health
```
GET /health
Returns: mongo (bool), redis (bool), qdrant (bool), status (string)
```

### Statistics
```
GET /api/v1/admin/stats/requests?project={project}&start={date}&end={date}
Returns: Array of {date, count} for each day
```

### Logs
```
GET /api/v1/admin/logs?limit={lines}
Returns: Array of log lines, filtered to last N lines
```

### Backup Status
```
GET /api/v1/backup/status?limit={count}
Returns: settings, activeJob, jobs list
```

---

## Keyboard Shortcuts Reminder

| Key | Action |
|-----|--------|
| Escape | Close crawler logs |
| Ctrl+F | Search logs |
| Ctrl+C | Copy selected |
| Ctrl+A | Select all |

---

## Multi-Service Dependency Map

```
User Requests
    ↓
    ├─→ Redis (sessions, cache)
    │   ├─→ MongoDB (documents)
    │   └─→ Qdrant (vectors)
    │
    ├─→ Crawler (processes URLs)
    │   ├─→ MongoDB (stores results)
    │   └─→ LLM (indexes content)
    │
    └─→ LLM (answers questions)
        ├─→ MongoDB (loads docs)
        ├─→ Qdrant (searches vectors)
        └─→ Ollama (runs model)

All require: Disk space, CPU, RAM, Network
```

---

## Log Levels Quick Reference

| Level | Color | Meaning | Examples |
|-------|-------|---------|----------|
| DEBUG | Gray | Detailed info | function entry/exit |
| INFO | Blue | Normal operation | "Process started" |
| WARNING | Yellow | Potential issue | "Slow response" |
| ERROR | Red | Something failed | "Cannot connect to DB" |
| CRITICAL | Bright Red | System failing | "Out of memory" |

---

## Typical Metric Ranges

### After System Restart
```
CPU: 5-10%
RAM: 20-30%
Services: all "up"
Disk: >40% free
```

### During Light Activity
```
CPU: 15-25%
RAM: 40-50%
Services: all "up"
Disk: >30% free
```

### During Heavy Crawling
```
CPU: 60-80%
RAM: 70-85%
Services: all "up"
Disk: >15% free
```

### Critical Warning
```
CPU: >85%
RAM: >90%
Services: any "down"
Disk: <10% free
```

---

## Backup File Naming Convention

```
Backup format: backup_{YYYY-MM-DD}_{HH-MM}.archive.gz
Examples:
- backup_2025-01-15_03-00.archive.gz
- backup_2025-01-20_02-30.archive.gz
```

---

## Common Status Messages Explained

### Crawler Notes
| Message | Meaning | Action |
|---------|---------|--------|
| "Indexing in progress" | LLM processing results | Wait for completion |
| "LLM unavailable" | Ollama/LLM not responding | Check LLM section |
| "Errors detected" | Some URLs failed | Check logs for failures |
| "Last URL: {url}" | Current page being crawled | Check if URL is hanging |

### Backup Status
| Message | Meaning | Action |
|---------|---------|--------|
| "Never" | No backups run | Run backup or enable schedule |
| "Backup running" | In progress | Wait, check progress |
| "Backup completed" | Success | Can restore if needed |
| "Failed: {error}" | Backup failed | Check error, retry |

### Service Health
| Status | Meaning | Action |
|--------|---------|--------|
| "healthy" | All services up | Normal operation |
| "degraded" | Some services down | Check which, restart |
| "unknown" | Cannot determine | Check connectivity, logs |

---

## Data Interpretation Examples

### Statistics Graph
```
If graph shows:
↗ Steep upward trend → Increased user activity
↘ Downward trend → Decreased usage
▬ Flat line → Consistent usage
↱ Spike then drop → Brief traffic surge
```

### Resource Usage Pattern
```
CPU spikes every hour:
→ Scheduled background job

RAM increasing over days:
→ Possible memory leak

Disk growing daily:
→ Logs/cache not cleaned
```

### Service Status Pattern
```
All services down simultaneously:
→ Network issue or hardware failure

Only Redis down:
→ Process crash or configuration issue

Intermittent ups/downs:
→ Service unstable or resource constrained
```

---

## File Paths in UI

### Backup Paths
- Local: `/backups/`, `/data/backups/`
- Remote: `/sitellm-backups/backup_*.archive.gz`

### Log Locations (in UI)
- Crawler logs: Last 400 lines from `/var/log/sitellm/crawler.log`
- System logs: Last 200 lines from `/var/log/sitellm/app.log`

### Configuration Locations
- Ollama default: `http://host.docker.internal:11434`
- Backup default folder: `sitellm-backups`

---

## Emergency Contact Checklist

When contacting support, include:
1. Screenshot of dashboard showing red/yellow status
2. Copy of relevant logs (use "Copy logs" button)
3. Current resource metrics (CPU, RAM, Disk)
4. Recent changes made (new crawler, backup, etc.)
5. Time when issue started
6. Steps you've already taken

