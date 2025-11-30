#!/usr/bin/env python3
"""Refactor project structure - move files to apps/ and packages/."""
import os
import subprocess
import shutil
from pathlib import Path

def run_cmd(cmd):
    """Run command and return success status."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠️  {result.stderr.strip()}")
        return False
    print(f"  ✓")
    return True

def move_file(src, dst):
    """Move file using git mv if in repo, otherwise regular move."""
    if not Path(src).exists():
        return False
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    return run_cmd(["git", "mv", src, dst])

def move_dir_contents(src_dir, dst_dir):
    """Move all files from src_dir to dst_dir, skipping __pycache__."""
    if not Path(src_dir).exists():
        return
    Path(dst_dir).mkdir(parents=True, exist_ok=True)
    
    for item in Path(src_dir).iterdir():
        if item.name == '__pycache__' or item.name.startswith('.'):
            continue
        dst = Path(dst_dir) / item.name
        move_file(str(item), str(dst))

print("=== Starting structure refactoring ===\n")

# Create directories
print("Creating directory structure...")
dirs = [
    "apps/admin", "apps/api", "apps/worker", 
    "apps/bots/telegram", "apps/bots/vk", "apps/bots/max",
    "packages/core", "packages/backend", "packages/connectors",
    "packages/knowledge", "packages/utils", "packages/common", "packages/crawler"
]
for d in dirs:
    Path(d).mkdir(parents=True, exist_ok=True)
print("✓ Directories created\n")

# Move entry points
print("Moving application entry points...")
move_file("app.py", "apps/admin/main.py")
move_file("api.py", "apps/api/main.py")
move_file("worker.py", "apps/worker/main.py")

# Move admin files
print("\nMoving admin files...")
move_dir_contents("admin", "apps/admin")

# Move api files
print("\nMoving api files...")
move_dir_contents("api", "apps/api")

# Move bot files
print("\nMoving bot files...")
move_dir_contents("tg_bot", "apps/bots/telegram")
move_dir_contents("vk_bot", "apps/bots/vk")
move_dir_contents("max_bot", "apps/bots/max")

# Move core modules
print("\nMoving core modules...")
core_files = ["models.py", "mongo.py", "settings.py", "vectors.py", "textnorm.py", "yallm.py"]
for f in core_files:
    move_file(f, f"packages/core/{f}")
move_dir_contents("core", "packages/core")

# Move packages
print("\nMoving packages...")
move_dir_contents("backend", "packages/backend")
move_dir_contents("connectors", "packages/connectors")
move_dir_contents("integrations", "packages/connectors/integrations")
move_dir_contents("knowledge", "packages/knowledge/knowledge")
move_dir_contents("knowledge_service", "packages/knowledge/knowledge_service")
move_dir_contents("retrieval", "packages/knowledge/retrieval")
move_dir_contents("crawler", "packages/crawler")
move_dir_contents("observability", "packages/utils/observability")
move_dir_contents("backup", "packages/utils/backup")
move_dir_contents("safety", "packages/utils/safety")
move_dir_contents("app_modules", "packages/common/app_modules")

# Create __init__.py files
print("\nCreating __init__.py files...")
init_dirs = [
    "apps", "apps/admin", "apps/api", "apps/worker", "apps/bots",
    "apps/bots/telegram", "apps/bots/vk", "apps/bots/max",
    "packages", "packages/core", "packages/backend", "packages/connectors",
    "packages/knowledge", "packages/utils", "packages/common", "packages/crawler"
]
for d in init_dirs:
    init_file = Path(d) / "__init__.py"
    if not init_file.exists():
        init_file.touch()
        run_cmd(["git", "add", str(init_file)])
print("✓ __init__.py files created\n")

# Clean up empty directories
print("Cleaning up empty directories...")
old_dirs = ["admin", "api", "tg_bot", "vk_bot", "max_bot", "core", "backend", 
            "connectors", "integrations", "knowledge", "knowledge_service", 
            "retrieval", "crawler", "observability", "backup", "safety", "app_modules"]
for d in old_dirs:
    if Path(d).exists():
        try:
            if not any(Path(d).iterdir()):  # Only remove if empty
                Path(d).rmdir()
                print(f"  ✓ Removed empty {d}/")
        except:
            print(f"  ⚠️  Could not remove {d}/ (not empty or other issue)")

print("\n=== Refactoring complete ===")
print("\nNext steps:")
print("1. Update imports with: python3 scripts/refactor_imports.py")
print("2. Update Dockerfile and compose.yaml")
print("3. Update pyproject.toml package discovery")
print("4. Run tests")
