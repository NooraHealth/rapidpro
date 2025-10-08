#!/usr/bin/env python3
"""
Example script to analyze exported channel logs.

Usage:
    python analyze_logs.py logs.csv
    python analyze_logs.py logs.json
"""

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def analyze_csv(file_path):
    """Analyze CSV log file"""
    try:
        import pandas as pd
    except ImportError:
        print("Error: pandas is required for CSV analysis. Install with: pip install pandas")
        return

    print(f"Loading {file_path}...")
    df = pd.read_csv(file_path)
    
    print("\n" + "="*60)
    print("CHANNEL LOGS ANALYSIS")
    print("="*60)
    
    # Basic statistics
    print(f"\nTotal Logs: {len(df)}")
    print(f"Date Range: {df['created_on'].min()} to {df['created_on'].max()}")
    
    # Error analysis
    error_logs = df[df['is_error'] == True]
    print(f"\nError Logs: {len(error_logs)} ({len(error_logs)/len(df)*100:.1f}%)")
    
    # Log type breakdown
    print("\nLog Type Distribution:")
    print(df['type'].value_counts().to_string())
    
    # Performance statistics
    print(f"\nElapsed Time Statistics (ms):")
    print(f"  Average: {df['elapsed_ms'].mean():.2f}ms")
    print(f"  Median: {df['elapsed_ms'].median():.2f}ms")
    print(f"  Min: {df['elapsed_ms'].min()}ms")
    print(f"  Max: {df['elapsed_ms'].max()}ms")
    print(f"  95th percentile: {df['elapsed_ms'].quantile(0.95):.2f}ms")
    
    # Slowest requests
    print("\nTop 10 Slowest Requests:")
    slowest = df.nlargest(10, 'elapsed_ms')[['log_uuid', 'type', 'elapsed_ms', 'is_error', 'created_on']]
    print(slowest.to_string(index=False))
    
    # Organizations
    if 'org_id' in df.columns:
        print("\nOrganization Distribution:")
        print(df['org_id'].value_counts().to_string())
    
    # Channels
    if 'channel_uuid' in df.columns:
        unique_channels = df['channel_uuid'].nunique()
        print(f"\nUnique Channels: {unique_channels}")
    
    # Error analysis
    if len(error_logs) > 0:
        print("\nError Types:")
        print(error_logs['type'].value_counts().to_string())
        
        # Parse error messages if available
        if 'errors' in df.columns:
            error_messages = []
            for errors_str in error_logs['errors'].dropna():
                try:
                    errors = json.loads(errors_str)
                    for err in errors:
                        error_messages.append(err.get('message', 'Unknown'))
                except:
                    pass
            
            if error_messages:
                print("\nMost Common Error Messages:")
                for msg, count in Counter(error_messages).most_common(10):
                    print(f"  {count:4d}x - {msg[:80]}")
    
    # Hourly distribution
    df['hour'] = pd.to_datetime(df['created_on']).dt.hour
    print("\nLogs by Hour of Day:")
    hourly = df.groupby('hour').size()
    for hour, count in hourly.items():
        bar = '█' * int(count / hourly.max() * 40)
        print(f"  {hour:02d}:00 - {count:5d} {bar}")


def analyze_json(file_path):
    """Analyze JSON log file"""
    print(f"Loading {file_path}...")
    with open(file_path, 'r') as f:
        logs = json.load(f)
    
    print("\n" + "="*60)
    print("CHANNEL LOGS ANALYSIS")
    print("="*60)
    
    # Basic statistics
    print(f"\nTotal Logs: {len(logs)}")
    
    if not logs:
        print("No logs to analyze!")
        return
    
    # Date range
    dates = [log['created_on'] for log in logs if 'created_on' in log]
    if dates:
        print(f"Date Range: {min(dates)} to {max(dates)}")
    
    # Error analysis
    error_logs = [log for log in logs if log.get('is_error', False)]
    print(f"\nError Logs: {len(error_logs)} ({len(error_logs)/len(logs)*100:.1f}%)")
    
    # Log type breakdown
    log_types = Counter(log.get('type', 'unknown') for log in logs)
    print("\nLog Type Distribution:")
    for log_type, count in log_types.most_common():
        print(f"  {log_type:20s}: {count:5d} ({count/len(logs)*100:.1f}%)")
    
    # Performance statistics
    elapsed_times = [log.get('elapsed_ms', 0) for log in logs]
    if elapsed_times:
        elapsed_times.sort()
        print(f"\nElapsed Time Statistics (ms):")
        print(f"  Average: {sum(elapsed_times)/len(elapsed_times):.2f}ms")
        print(f"  Median: {elapsed_times[len(elapsed_times)//2]:.2f}ms")
        print(f"  Min: {min(elapsed_times)}ms")
        print(f"  Max: {max(elapsed_times)}ms")
        print(f"  95th percentile: {elapsed_times[int(len(elapsed_times)*0.95)]:.2f}ms")
    
    # Slowest requests
    slowest_logs = sorted(logs, key=lambda x: x.get('elapsed_ms', 0), reverse=True)[:10]
    print("\nTop 10 Slowest Requests:")
    print(f"{'UUID':<38} {'Type':<20} {'Elapsed':<10} {'Error':<6} {'Created On'}")
    print("-" * 110)
    for log in slowest_logs:
        print(f"{log.get('log_uuid', 'N/A'):<38} "
              f"{log.get('type', 'N/A'):<20} "
              f"{log.get('elapsed_ms', 0):<10}ms "
              f"{'Yes' if log.get('is_error') else 'No':<6} "
              f"{log.get('created_on', 'N/A')}")
    
    # Organizations
    org_ids = Counter(log.get('org_id') for log in logs if 'org_id' in log)
    if org_ids:
        print("\nOrganization Distribution:")
        for org_id, count in org_ids.most_common():
            print(f"  Org {org_id}: {count} logs")
    
    # Channels
    channel_uuids = set(log.get('channel_uuid') for log in logs if 'channel_uuid' in log)
    if channel_uuids:
        print(f"\nUnique Channels: {len(channel_uuids)}")
    
    # Error analysis
    if error_logs:
        print("\nError Types:")
        error_types = Counter(log.get('type', 'unknown') for log in error_logs)
        for error_type, count in error_types.most_common():
            print(f"  {error_type:20s}: {count:5d}")
        
        # Error messages
        error_messages = []
        for log in error_logs:
            if 'errors' in log:
                for err in log['errors']:
                    error_messages.append(err.get('message', 'Unknown'))
        
        if error_messages:
            print("\nMost Common Error Messages:")
            for msg, count in Counter(error_messages).most_common(10):
                print(f"  {count:4d}x - {msg[:80]}")
    
    # Hourly distribution
    hours = []
    for log in logs:
        try:
            dt = datetime.fromisoformat(log['created_on'].replace('Z', '+00:00'))
            hours.append(dt.hour)
        except:
            pass
    
    if hours:
        hourly = Counter(hours)
        print("\nLogs by Hour of Day:")
        max_count = max(hourly.values())
        for hour in range(24):
            count = hourly.get(hour, 0)
            bar = '█' * int(count / max_count * 40) if count > 0 else ''
            print(f"  {hour:02d}:00 - {count:5d} {bar}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <logs.csv|logs.json>")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    
    if not file_path.exists():
        print(f"Error: File {file_path} not found")
        sys.exit(1)
    
    if file_path.suffix == '.csv':
        analyze_csv(file_path)
    elif file_path.suffix == '.json':
        analyze_json(file_path)
    else:
        print(f"Error: Unsupported file type {file_path.suffix}")
        print("Supported types: .csv, .json")
        sys.exit(1)


if __name__ == '__main__':
    main()

