#!/usr/bin/env python3
"""
Migrate task files to new format with YAML frontmatter.
"""
import os
import re
from pathlib import Path
from datetime import date

TASKS_DIR = Path(__file__).parent.parent / "tasks"

def extract_id_from_filename(filename: str) -> int:
    """Extract task ID from filename like '23-breakpoints-system.md'"""
    match = re.match(r'^(\d+)-', filename)
    if match:
        return int(match.group(1))
    return 0

def extract_title(content: str) -> str:
    """Extract title from '# Task XX: Title' or '# Task XX - Title'"""
    match = re.search(r'^# Task \d+[:\-]\s*(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Fallback: first heading
    match = re.search(r'^# (.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Untitled"

def extract_priority(content: str) -> str:
    """Extract priority from '**Приоритет:** P1 (HIGH)'"""
    match = re.search(r'\*\*Приоритет:\*\*\s*(.+?)(?:\n|$)', content)
    if match:
        prio = match.group(1).strip().lower()
        if 'p1' in prio or 'high' in prio or 'высок' in prio:
            return 'high'
        elif 'p2' in prio or 'medium' in prio or 'средн' in prio:
            return 'medium'
        elif 'p3' in prio or 'low' in prio or 'низк' in prio:
            return 'low'
        elif 'critical' in prio or 'критич' in prio:
            return 'critical'
    return 'medium'

def extract_estimate(content: str) -> str:
    """Extract estimate from '**Оценка:** 3h' or '**Оценка:** 3-5 дней'"""
    match = re.search(r'\*\*Оценка:\*\*\s*(.+?)(?:\n|$)', content)
    if match:
        return match.group(1).strip()
    return ''

def extract_dependencies(content: str) -> list:
    """Extract dependencies from '**Зависимости:** Task 22, Task 23'"""
    match = re.search(r'\*\*Зависимости:\*\*\s*(.+?)(?:\n|$)', content)
    if match:
        deps_str = match.group(1).strip()
        if 'нет' in deps_str.lower() or deps_str == '-':
            return []
        # Find all Task XX references
        task_refs = re.findall(r'Task\s*(\d+)', deps_str)
        return [f"T{t}" for t in task_refs]
    return []

def extract_tags(content: str, title: str) -> list:
    """Generate tags based on content"""
    tags = []
    title_lower = title.lower()
    content_lower = content.lower()

    if 'frontend' in title_lower or 'frontend' in content_lower[:500]:
        tags.append('frontend')
    if 'backend' in title_lower or 'backend' in content_lower[:500]:
        tags.append('backend')
    if 'api' in title_lower:
        tags.append('api')
    if 'workflow' in title_lower:
        tags.append('workflow')
    if 'test' in title_lower:
        tags.append('testing')
    if 'refactor' in title_lower:
        tags.append('refactoring')
    if 'fix' in title_lower or 'bug' in title_lower:
        tags.append('bugfix')

    return tags

def generate_slug(filename: str) -> str:
    """Generate slug from filename"""
    # Remove number prefix and .md extension
    slug = re.sub(r'^\d+-', '', filename)
    slug = slug.replace('.md', '')
    return slug

def create_frontmatter(task_id: int, title: str, priority: str, estimate: str,
                       dependencies: list, tags: list, status: str) -> str:
    """Create YAML frontmatter"""
    today = date.today().isoformat()
    deps_str = str(dependencies) if dependencies else '[]'
    tags_str = str(tags) if tags else '[]'

    return f"""---
id: T{task_id}
title: "{title}"
status: {status}
priority: {priority}
created: {today}
updated: {today}
tags: {tags_str}
depends_on: {deps_str}
estimate: "{estimate}"
branch: ""
---

"""

def remove_old_metadata(content: str) -> str:
    """Remove old metadata lines from content"""
    lines = content.split('\n')
    new_lines = []
    skip_next_empty = False

    for line in lines:
        # Skip old metadata lines
        if line.startswith('**Приоритет:**'):
            skip_next_empty = True
            continue
        if line.startswith('**Оценка:**'):
            skip_next_empty = True
            continue
        if line.startswith('**Зависимости:**'):
            skip_next_empty = True
            continue
        if line.startswith('**Блокирует:**'):
            skip_next_empty = True
            continue
        if line.startswith('**Phase:**'):
            skip_next_empty = True
            continue

        # Skip empty line after metadata
        if skip_next_empty and line.strip() == '':
            skip_next_empty = False
            continue

        skip_next_empty = False
        new_lines.append(line)

    return '\n'.join(new_lines)

def migrate_task_file(filepath: Path, status: str) -> tuple[str, str]:
    """Migrate a single task file. Returns (old_name, new_name)"""
    filename = filepath.name

    # Skip non-task files
    if filename in ['README.md', '00-PLAN.md', 'REFACTORING.md']:
        return None, None

    with open(filepath, 'r') as f:
        content = f.read()

    task_id = extract_id_from_filename(filename)
    if task_id == 0:
        print(f"  Skipping {filename} - no ID found")
        return None, None

    title = extract_title(content)
    priority = extract_priority(content)
    estimate = extract_estimate(content)
    dependencies = extract_dependencies(content)
    tags = extract_tags(content, title)
    slug = generate_slug(filename)

    # Create new content
    frontmatter = create_frontmatter(task_id, title, priority, estimate,
                                      dependencies, tags, status)
    cleaned_content = remove_old_metadata(content)
    new_content = frontmatter + cleaned_content

    # New filename
    new_filename = f"T{task_id}-{slug}.md"
    new_filepath = filepath.parent / new_filename

    # Write new file
    with open(new_filepath, 'w') as f:
        f.write(new_content)

    # Remove old file if different name
    if new_filepath != filepath:
        os.remove(filepath)

    return filename, new_filename

def main():
    print("Migrating task files to new format...")

    # Migrate todo/
    todo_dir = TASKS_DIR / "todo"
    print(f"\n=== Migrating {todo_dir} ===")
    for filepath in sorted(todo_dir.glob("*.md")):
        old, new = migrate_task_file(filepath, "todo")
        if old:
            print(f"  {old} -> {new}")

    # Migrate done/
    done_dir = TASKS_DIR / "done"
    print(f"\n=== Migrating {done_dir} ===")
    for filepath in sorted(done_dir.glob("*.md")):
        old, new = migrate_task_file(filepath, "done")
        if old:
            print(f"  {old} -> {new}")

    print("\nMigration complete!")

if __name__ == "__main__":
    main()
