# Admin Panel Documentation Index

## Overview

This directory contains comprehensive user documentation for the SiteLLM admin panel monitoring, backup, and maintenance features. Three documents are provided:

1. **ADMIN_MONITORING_DOCUMENTATION.md** - Complete feature guide
2. **ADMIN_QUICK_REFERENCE.md** - Quick lookup and troubleshooting
3. **ADMIN_DOCUMENTATION_INDEX.md** - This index file

---

## Document Quick Links

### For Users Starting Out
Begin with: **ADMIN_QUICK_REFERENCE.md**
- Visual status indicator reference
- Common task walkthroughs
- Quick diagnostic flowcharts

### For Comprehensive Understanding
Study: **ADMIN_MONITORING_DOCUMENTATION.md**
- In-depth feature explanations
- What you see and what actions you can take
- Best practices and maintenance procedures
- Detailed troubleshooting guides

### For Specific Tasks
Use both documents:
- Look up task steps in Quick Reference
- Deep dive into details in Full Documentation

---

## Document Contents Summary

### ADMIN_MONITORING_DOCUMENTATION.md (721 lines)

**Sections:**
1. Monitoring Dashboard - Status cards, real-time updates
2. Resource Monitoring - CPU, RAM, GPU, Python version
3. Service Health - MongoDB, Redis, Qdrant status
4. Statistics and Analytics - Charts, export, interpretation
5. Logs Management - Crawler logs, system logs, troubleshooting
6. Backup Configuration - Scheduling, tokens, Yandex.Disk
7. LLM Management - Model configuration, servers, installation
8. Feedback Review - Viewing and acting on user feedback
9. Crawler Management - Progress, counters, actions
10. Status Interpretation - Green/Yellow/Red status meanings
11. Maintenance Best Practices - Daily, weekly, monthly tasks
12. Troubleshooting Checklist - Common issues and solutions
13. Accessing Features - Role-based feature visibility
14. Keyboard Shortcuts - Quick navigation
15. Data Retention - Cleanup and archival policies

---

### ADMIN_QUICK_REFERENCE.md (374 lines)

**Sections:**
1. Visual Status Indicators - Color coding reference
2. Resource Thresholds - Good/Warning/Critical ranges
3. Common Tasks and Steps - 8 detailed walkthroughs
4. Quick Diagnostics - 5 troubleshooting flowcharts
5. API Endpoints Reference - Key API routes
6. Keyboard Shortcuts - Complete list
7. Multi-Service Dependency Map - Service relationships
8. Log Levels Reference - DEBUG, INFO, WARNING, ERROR, CRITICAL
9. Typical Metric Ranges - Normal values by scenario
10. Backup File Naming - Format and examples
11. Common Status Messages - Explanations and actions
12. Data Interpretation Examples - What patterns mean
13. File Paths - Log and backup location references
14. Emergency Contact Checklist - Information to gather

---

## Feature Coverage Map

| Feature | Full Doc | Quick Ref | Coverage |
|---------|----------|-----------|----------|
| Monitoring Dashboard | Sec 1-3 | Sec 1-2 | Complete |
| Resource Metrics | Sec 2 | Sec 2 | Complete |
| Service Health | Sec 3 | Sec 1 | Complete |
| Statistics | Sec 4 | - | Detailed |
| Crawler Logs | Sec 5 | Sec 4 | Complete |
| System Logs | Sec 5 | Sec 4 | Complete |
| Backup Config | Sec 6 | Sec 3,14 | Complete |
| LLM Management | Sec 7 | Sec 3 | Detailed |
| Feedback | Sec 8 | - | Documented |
| Crawler Monitoring | Sec 9 | Sec 3,4 | Complete |
| Troubleshooting | Sec 12 | Sec 4 | Complete |
| Best Practices | Sec 11 | Sec 3 | Complete |

---

## How to Use These Documents

### Scenario 1: First Time Learning
1. Read ADMIN_QUICK_REFERENCE.md sections 1-2
2. Review typical metric ranges (Sec 8)
3. Study dependency map (Sec 6)
4. Then read ADMIN_MONITORING_DOCUMENTATION.md overview

### Scenario 2: Responding to Alert
1. Check Quick Reference status indicators (Sec 1)
2. Use Quick Diagnostics (Sec 4) for your issue
3. Refer to Full Documentation troubleshooting (Sec 12)
4. Implement recommended actions

### Scenario 3: Setting Up Backups
1. Full Documentation Sec 6: Backup Configuration
2. Quick Reference Sec 14: Backup naming convention
3. Full Documentation Sec 11: Best practices
4. Quick Reference Sec 3: Step-by-step guide

### Scenario 4: Regular Maintenance
1. Check Full Documentation Sec 11: Maintenance schedule
2. Use Quick Reference typical ranges (Sec 8)
3. Compare current metrics to baseline
4. Review logs for patterns

### Scenario 5: Emergency Issue
1. Immediately check resource metrics
2. Use Quick Reference Sec 4: Quick Diagnostics
3. Check logs using Sec 4 in both documents
4. Follow Full Documentation troubleshooting procedures
5. Gather information from Quick Reference Sec 14

---

## Key Definitions

### Status Colors
- **Green ("up")**: Service operational, all good
- **Red ("down")**: Service not responding, immediate action needed
- **Yellow**: Warning level, monitor closely
- **Gray ("unknown")**: Cannot determine status

### Resource Levels
- **Normal**: System operating efficiently
- **Warning**: Approaching limits, monitor closely
- **Critical**: System under stress, action required
- **Overload**: Performance degradation imminent

### Crawler States
- **Waiting to start**: No crawler running, ready to start
- **Scanning**: Pages being actively crawled
- **Queued**: Pages discovered, waiting to be processed
- **Done**: All pages successfully completed
- **Errors**: Some pages failed to process

---

## Quick Navigation

### By Feature
- [Status Monitoring](ADMIN_MONITORING_DOCUMENTATION.md#1-monitoring-dashboard)
- [Resource Usage](ADMIN_MONITORING_DOCUMENTATION.md#2-resource-monitoring)
- [Service Health](ADMIN_MONITORING_DOCUMENTATION.md#3-service-health)
- [Statistics](ADMIN_MONITORING_DOCUMENTATION.md#4-statistics-and-analytics)
- [Logs](ADMIN_MONITORING_DOCUMENTATION.md#5-logs-management)
- [Backups](ADMIN_MONITORING_DOCUMENTATION.md#6-backup-configuration-super-admin-only)
- [LLM](ADMIN_MONITORING_DOCUMENTATION.md#7-llm-management)

### By Task
- [Check System Health](ADMIN_QUICK_REFERENCE.md#task-check-system-health)
- [Monitor Crawling](ADMIN_QUICK_REFERENCE.md#task-monitor-crawling-progress)
- [View Statistics](ADMIN_QUICK_REFERENCE.md#task-view-activity-statistics)
- [Access Logs](ADMIN_QUICK_REFERENCE.md#task-access-crawler-logs)
- [Create Backup](ADMIN_QUICK_REFERENCE.md#task-create-manual-backup)
- [Restore Backup](ADMIN_QUICK_REFERENCE.md#task-restore-from-backup)
- [Export Data](ADMIN_QUICK_REFERENCE.md#task-export-statistics-for-report)

### By Issue
- [Crawler Stuck](ADMIN_QUICK_REFERENCE.md#scenario-crawler-is-stuck-on-scanning)
- [LLM Down](ADMIN_QUICK_REFERENCE.md#scenario-llm-shows-unavailable)
- [Backup Failed](ADMIN_QUICK_REFERENCE.md#scenario-backup-failed)
- [System Slow](ADMIN_QUICK_REFERENCE.md#scenario-system-running-slow)
- [Services Down](ADMIN_QUICK_REFERENCE.md#scenario-services-keep-going-down)

---

## Code Analysis Details

The documentation is based on analysis of:

### Primary Source Files
- `admin/js/crawler.js` - Crawler monitoring, progress, logs
- `admin/js/stats.js` - Statistics dashboard and export
- `admin/js/backup.js` - Backup operations and scheduling
- `admin/index.html` - UI structure and components

### API Endpoints Documented
- `/api/v1/crawler/status` - Crawling progress
- `/health` - Service health check
- `/api/v1/admin/logs` - Log retrieval
- `/api/v1/admin/stats/requests` - Statistics data
- `/api/v1/backup/*` - Backup operations

### Features Analyzed
1. Real-time status monitoring (2-5 second updates)
2. Resource usage tracking (CPU, RAM, GPU)
3. Service health indicators
4. Interactive statistics with export
5. Log management and filtering
6. Backup scheduling and execution
7. LLM configuration and management
8. User feedback collection

---

## Important Notes

### Super Admin Features
The following features are restricted to Super Admin users:
- Backup configuration and scheduling
- Token management
- Restore operations
- All other features visible to regular admins

### Browser Compatibility
- Works with modern browsers (Chrome, Firefox, Safari, Edge)
- Requires JavaScript enabled
- Responsive design for desktop and tablet
- Touch-friendly controls for mobile

### Data Privacy
- Tokens are stored server-side, never displayed in UI
- Logs can be exported for support tickets
- Statistics are project-specific
- Session data expires after 24 hours

### Performance
- Auto-updates every 2-5 seconds
- Configurable log limits (50-1000 lines)
- Canvas-based charts for smooth animation
- Efficient polling to minimize server load

---

## Updates and Changes

This documentation is current as of November 2025 and reflects:
- Admin panel UI as of commit 8beaa68
- Latest feature set including backup improvements
- Security enhancements for token handling
- Recent performance optimizations

For the most current version, refer to the main documentation repository.

---

## Support and Questions

If documentation is unclear or missing information:
1. Check both documents for related sections
2. Review code comments in source files
3. Refer to API endpoints section for technical details
4. Include relevant logs when seeking help

---

## Document Metadata

| Property | Value |
|----------|-------|
| Created | November 19, 2025 |
| Version | 1.0 |
| Coverage | Monitoring, Backup, Maintenance |
| Scope | User documentation |
| Target | Admin users and Super Admins |
| Pages | ~1,100 total across all documents |
| Sections | 30+ detailed sections |

