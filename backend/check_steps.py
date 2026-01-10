#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

# Get all workflow steps for video_id=1
cursor.execute('''
    SELECT id, video_id, step_type, status, created_at, generation_time_seconds
    FROM workflow_steps
    WHERE video_id = 1
    ORDER BY id
''')

steps = cursor.fetchall()
print(f"\nTotal steps for video_id=1: {len(steps)}\n")
print(f"{'ID':<5} {'Video':<7} {'Step Type':<15} {'Status':<20} {'Gen Time':<10}")
print("=" * 75)
for step in steps:
    step_id, video_id, step_type, status, created_at, gen_time = step
    gen_time_str = f"{gen_time:.1f}s" if gen_time else "N/A"
    print(f"{step_id:<5} {video_id:<7} {step_type:<15} {status:<20} {gen_time_str:<10}")

# Check for duplicate step types
cursor.execute('''
    SELECT step_type, COUNT(*) as count
    FROM workflow_steps
    WHERE video_id = 1
    GROUP BY step_type
    HAVING count > 1
''')

duplicates = cursor.fetchall()
if duplicates:
    print("\n⚠️  DUPLICATES FOUND:")
    for step_type, count in duplicates:
        print(f"  - {step_type}: {count} instances")

conn.close()
