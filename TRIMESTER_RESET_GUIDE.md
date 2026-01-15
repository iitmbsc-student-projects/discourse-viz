# Trimester Reset Implementation Guide

## Overview

This document explains the trimester-based full data recalculation system implemented in `discourse-viz`. The system automatically resets and recalculates all data from scratch on trimester start dates (Jan 1, May 1, Sep 1) to discover new courses and capture new users.

---

## Architecture: Two-Job Scheduler

The system uses **two separate APScheduler jobs** that run at different times:

### Job 1: Full System Reset (Trimester Starts Only)
- **Trigger**: `cron(month='1,5,9', day='1', hour=3, minute=30)`
- **Dates**: Jan 1, May 1, Sep 1 at 3:30 AM
- **Function**: `data_loader.full_system_reset()`
- **Action**: Complete system recalculation from scratch (equivalent to app restart)
- **Duration**: ~30 minutes
- **Max Instances**: 1 (prevents concurrent execution)
- **Coalesce**: True (skips missed runs if overlapping)

### Job 2: Incremental Daily Refresh (All Other Days)
- **Trigger**: `cron(day='*', hour=3, minute=15)`
- **Dates**: Every day at 3:15 AM except trimester start dates
- **Function**: `data_loader.refresh_all_data()`
- **Action**: Fetch only NEW data since last refresh (incremental delta)
- **Duration**: 5-15 minutes (depending on activity)
- **Max Instances**: 1 (prevents concurrent execution)
- **Coalesce**: True (skips missed runs if overlapping)
- **Safety Check**: Exits early if accidentally triggered on trimester start date

---

## Data Flow: Full System Reset

### Step 0: Backup Current State
```
Before attempting reset, backup:
├── user_actions_dictionaries (all courses, all trimesters)
├── df_map_category_to_id (course ID mapping)
├── id_username_mapping (user ID mapping)
└── last_refresh_date
```

**Why**: Allows graceful fallback if any subsequent step fails. Users can continue accessing old data while developers investigate.

### Step 1: Reload Course Mappings (Query #107)
- Fetches all courses from Discourse
- Identifies new courses added since last trimester
- Filters out irrelevant categories
- Identifies uncategorized courses

### Step 2: Reload User Mappings (Query #108)
- Fetches all users from Discourse
- Captures new users enrolled in the system
- Updates global user ID-username mapping

### Step 3: Rebuild All User Actions Data
- For each trimester (current + 2 previous):
  - For each course:
    - Query #103: Fetch ALL user actions for the trimester
    - Create raw_metrics, unnormalized_scores, log_normalized_scores
  - Query #102: Fetch overall engagement metrics
  - Aggregate and calculate platform-wide scores

### Step 4: Finalize Reset
- Update `last_refresh_date` to current date
- Set `user_actions_loaded = True` (system ready)
- Set `system_reset_failed = False`
- Log completion

---

## Failure Handling: Graceful Degradation

If any step fails during reset:

### Automatic Fallback (Recommendation Implemented)
```
1. RESTORE BACKUP
   └─ Restore all backed-up state
   
2. ALLOW OLD DATA ACCESS
   └─ Set user_actions_loaded = True
   └─ Users see old data (no downtime)
   
3. FLAG THE ISSUE
   ├─ Set system_reset_failed = True
   ├─ Set system_reset_failure_reason = error message
   └─ Indicates to frontend/monitoring that issue exists
   
4. ALERT DEVELOPER
   └─ Call _alert_developer_of_reset_failure()
   └─ Sends notification (email/g-chat/Slack)
   └─ No time pressure (developers investigate at their pace)
   
5. RETRY ON NEXT TRIMESTER
   └─ System will attempt reset again next trimester start
   └─ No cascade failures or partial state corruption
```

### Why This Approach?
- **User Experience**: Users get old data instead of loading message/downtime
- **Developer Efficiency**: No time pressure to fix immediately
- **System Stability**: No partial state corruption
- **Observability**: Issue is clearly flagged for monitoring systems

---

## Configuration: Implementing Developer Alerts

The placeholder function `_alert_developer_of_reset_failure()` needs implementation for your notification system.

### Option 1: Google Chat Webhook
```python
def _alert_developer_of_reset_failure(error_message):
    import requests
    import os
    
    webhook_url = os.environ.get('GOOGLE_CHAT_WEBHOOK_URL')
    message = {
        'text': f'🚨 ALERT: Full System Reset Failed\n\n'
                f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
                f'Trimester: {get_current_trimester()}\n'
                f'Error: {error_message}\n\n'
                f'Action Required: Check logs at discourse-viz server\n'
                f'Fallback: Users can access previous trimester data'
    }
    requests.post(webhook_url, json=message)
```

### Option 2: Email via SMTP
```python
def _alert_developer_of_reset_failure(error_message):
    import smtplib
    from email.mime.text import MIMEText
    
    sender = os.environ.get('EMAIL_SENDER')
    recipients = os.environ.get('EMAIL_RECIPIENTS').split(',')
    
    msg = MIMEText(f"Reset failed: {error_message}")
    msg['Subject'] = "🚨 discourse-viz: Trimester Reset Failed"
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender, os.environ.get('EMAIL_PASSWORD'))
        server.sendmail(sender, recipients, msg.as_string())
```

### Option 3: Slack Webhook
```python
def _alert_developer_of_reset_failure(error_message):
    import requests
    
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    message = {
        'text': ':warning: *Full System Reset Failed*',
        'attachments': [{
            'color': 'danger',
            'fields': [
                {'title': 'Time', 'value': datetime.now().isoformat(), 'short': True},
                {'title': 'Trimester', 'value': get_current_trimester(), 'short': True},
                {'title': 'Error', 'value': error_message, 'short': False},
                {'title': 'Fallback', 'value': 'Users accessing previous trimester data', 'short': False}
            ]
        }]
    }
    requests.post(webhook_url, json=message)
```

---

## Monitoring: Checking Reset Status

### In Your Code
```python
from core import data_loader

# Check reset status
status = data_loader.get_system_reset_status()
if status['reset_failed']:
    logger.warning(f"Reset failed: {status['failure_reason']}")
    # Take action (e.g., show alert to users, trigger manual investigation)
```

### In Frontend
```javascript
// Check system health
fetch('/api/system-status')
  .then(r => r.json())
  .then(data => {
    if (data.reset_failed) {
      showAlert(`System using old data: ${data.failure_reason}`);
    }
  });
```

### In Logs
```
========================================
TRIMESTER START DETECTED - INITIATING FULL SYSTEM RESET
========================================
Step 0/4: Backing up current system state...
Current system state backed up successfully

Step 1/4: Reloading course category mappings (Query #107)...
Course mappings reloaded | courses: 45

Step 2/4: Reloading user ID mappings (Query #108)...
User mappings reloaded | users: 3200

Step 3/4: Rebuilding all user actions data from scratch...
User actions data rebuilt | trimesters: ['t1-2026', 't3-2025', 't2-2025']

Step 4/4: Finalizing reset...
Last refresh date updated | date: 01-01-2026

========================================
FULL SYSTEM RESET COMPLETED SUCCESSFULLY
========================================
```

---

## Implementation Details

### Global Variables
```python
# Current data
user_actions_dictionaries = {}
df_map_category_to_id = None
id_username_mapping = None
user_actions_loaded = False
last_refresh_date = "dd-mm-yyyy"

# Backup for fallback on failure
_backup_user_actions_dictionaries = None
_backup_df_map_category_to_id = None
_backup_id_username_mapping = None
_backup_last_refresh_date = None

# Reset failure tracking
system_reset_failed = False
system_reset_failure_reason = None
```

### Key Functions

#### `is_trimester_start_today()`
Checks if today is Jan 1, May 1, or Sep 1. Used by both APScheduler jobs to coordinate execution.

#### `full_system_reset()`
Performs complete data recalculation from scratch. Includes 4-step process with backup/restore mechanism.

#### `refresh_all_data()`
Performs incremental daily refresh. Includes safety check to skip execution on trimester start dates.

#### `_backup_current_state()`
Creates deep copy of all global data structures before reset attempt.

#### `_restore_from_backup()`
Restores all backed-up state if reset fails.

#### `_alert_developer_of_reset_failure(error_message)`
PLACEHOLDER: Implement this with your notification system (email/g-chat/Slack).

#### `get_system_reset_status()`
Returns dict with reset failure status. Use this to check system health in routes/frontend.

---

## Testing

### Simulate Trimester Reset
To test without waiting for actual trimester date:

```python
# Temporarily modify is_trimester_start_today() in utils.py
def is_trimester_start_today():
    return True  # Force reset to run

# Then call:
from core import data_loader
data_loader.full_system_reset()

# Check logs and verify:
# ✓ Backup created
# ✓ All queries executed
# ✓ Data reloaded successfully
# ✓ user_actions_loaded set to True
```

### Test Failure Fallback
To test backup/restore mechanism:

```python
# Modify load_user_actions_dictionaries() temporarily to raise error:
def load_user_actions_dictionaries():
    raise Exception("Simulated API failure")

# Then call reset:
data_loader.full_system_reset()

# Verify in logs:
# ✓ Backup created
# ✓ Error caught
# ✓ Backup restored
# ✓ user_actions_loaded set to True (allows old data access)
# ✓ system_reset_failed set to True
# ✓ Developer alerted
```

---

## Troubleshooting

### Reset Keeps Failing
1. Check logs: `grep "FULL SYSTEM RESET" app.log`
2. Look for specific error: Check `system_reset_failure_reason`
3. Verify API connectivity: Test Query #107, #108, #103, #102
4. Check disk space: Deep copying data requires temporary memory
5. Review error timestamp: Multiple failures indicate systematic issue

### Users Stuck on Old Data
1. Check `get_system_reset_status()` - confirms reset failure
2. Wait for next trimester or manually trigger reset
3. For immediate fix: Restart app to trigger `init_minimal_data()`

### New Courses Not Appearing
1. Verify course was added to Discourse
2. Check if it's in excluded categories (see `load_df_map_category_to_id()`)
3. If within excluded categories, modify `irrelevant_categories` list
4. Wait for next trimester reset or manually add to constants

---

## Summary

| Aspect | Details |
|--------|---------|
| **Trimester Dates** | Jan 1, May 1, Sep 1 (3:30 AM) |
| **Reset Time** | ~30 minutes |
| **Failure Handling** | Automatic backup/restore, users see old data |
| **Developer Alert** | Implement `_alert_developer_of_reset_failure()` |
| **Fallback** | Previous trimester data accessible during investigation |
| **Retry** | Automatic on next trimester start date |
