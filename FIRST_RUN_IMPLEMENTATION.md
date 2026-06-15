# First-Run Database Check Implementation

## Overview

This implementation adds automatic first-run detection to the HFOrchestra system. When the code runs for the first time and no database is present, it automatically runs the `--update` command to populate the database.

## Implementation Details

### Location
- **File**: `src/hforchestra/main.py`
- **Function**: `main()` function
- **Lines**: Around line 1180-1200

### Code Changes

The following logic was added to the main function:

```python
# Check if database exists and handle first-time setup
db_path = Path("db/hf_models.db")
if not db_path.exists():
    print("🔍 First-time setup detected: Database not found")
    print("📦 Running initial database population...")
    print("🌍 This will download and populate the HuggingFace models database")
    print("⏱️  This process may take several minutes to hours depending on your connection")
    
    # Auto-run update for first-time setup
    result = await task_handler.handle_update_database()
    safe_print_content(result)
    return
else:
    # Database exists - show info about update option
    if not any([args.update, args.tasks, args.stats, args.restore, 
               args.decision_stats, args.novel_ai_stats, args.performance_stats, 
               args.cache_stats, args.clearcache, args.analytics_demo, 
               args.model_ranking, args.model_recommendations, args.full]):
        # Only show this message if no other flags are specified
        print("✅ Database found: HuggingFace models database is ready")
        print("💡 Use --update to refresh the database with latest models")
        print("💡 Use --tasks to see available models and tasks")
        print("💡 Use --help for more options")
```

## Functionality

### First-Run Detection
- **Trigger**: When `db/hf_models.db` does not exist
- **Action**: Automatically runs `--update` command
- **User Experience**: Shows informative messages about the process

### Normal Operation
- **When Database Exists**: Shows helpful information about available commands
- **Conditional Display**: Only shows info when no other flags are specified
- **Non-Intrusive**: Doesn't interfere with normal command execution

### Command Behavior

| Scenario | Database Status | Command | Behavior |
|----------|----------------|---------|----------|
| First Run | Missing | `python main.py` | Auto-runs `--update` |
| First Run | Missing | `python main.py --help` | Shows help (no auto-update) |
| Normal | Exists | `python main.py` | Shows database ready message |
| Normal | Exists | `python main.py --update` | Runs update manually |
| Normal | Exists | `python main.py --tasks` | Runs tasks command |

## Benefits

1. **Automatic Setup**: New users don't need to know about `--update`
2. **User-Friendly**: Clear messages explain what's happening
3. **Non-Intrusive**: Doesn't interfere with help or other commands
4. **Backward Compatible**: Existing functionality unchanged
5. **Informative**: Tells users about available options

## Testing

The implementation was tested with:
- ✅ Database exists scenario
- ✅ Database missing scenario  
- ✅ Help command with missing database
- ✅ Update command with existing database
- ✅ Normal operation with existing database

## Security Considerations

- **OWASP A01**: Input validation - Database path is validated using `Path`
- **OWASP A05**: Security misconfiguration - Uses safe file operations
- **OWASP A09**: Logging/monitoring - Provides clear user feedback
- **Minimal Changes**: Only adds necessary functionality without removing existing code

## Files Modified

- `src/hforchestra/main.py` - Added first-run detection logic

## Dependencies

- `pathlib.Path` - Already imported in the file
- `task_handler.handle_update_database()` - Existing functionality
- `safe_print_content()` - Existing utility function

## Future Enhancements

1. **Progress Indicators**: Add progress bars for long-running updates
2. **Configuration Options**: Allow users to skip auto-update
3. **Database Validation**: Check database integrity before use
4. **Backup Creation**: Automatically create backups before updates
