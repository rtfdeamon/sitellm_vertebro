import os
import re

MAPPINGS = [
    (r'^from models\b', 'from packages.core.models'),
    (r'^import models\b', 'from packages.core import models'),
    (r'^from mongo\b', 'from packages.core.mongo'),
    (r'^import mongo\b', 'from packages.core import mongo'),
    (r'^from settings\b', 'from packages.core.settings'),
    (r'^import settings\b', 'from packages.core import settings'),
    (r'^from vectors\b', 'from packages.core.vectors'),
    (r'^import vectors\b', 'from packages.core import vectors'),
    (r'^from textnorm\b', 'from packages.core.textnorm'),
    (r'^import textnorm\b', 'from packages.core import textnorm'),
    (r'^from yallm\b', 'from packages.core.yallm'),
    (r'^import yallm\b', 'from packages.core import yallm'),
    (r'^from core\b', 'from packages.core'),
    (r'^import core\b', 'from packages import core'),
    (r'^from backend\b', 'from packages.backend'),
    (r'^import backend\b', 'from packages import backend'),
    (r'^from connectors\b', 'from packages.connectors'),
    (r'^import connectors\b', 'from packages import connectors'),
    (r'^from knowledge\b', 'from packages.knowledge'),
    (r'^import knowledge\b', 'from packages import knowledge'),
    (r'^from observability\b', 'from packages.utils.observability'),
    (r'^import observability\b', 'from packages.utils import observability'),
    (r'^from backup\b', 'from packages.utils.backup'),
    (r'^import backup\b', 'from packages.utils import backup'),
    (r'^from safety\b', 'from packages.utils.safety'),
    (r'^import safety\b', 'from packages.utils import safety'),
    (r'^from app_modules\b', 'from packages.common.app_modules'),
    (r'^import app_modules\b', 'from packages.common import app_modules'),
    (r'^from crawler\b', 'from packages.crawler'),
    (r'^import crawler\b', 'from packages import crawler'),
    # Fix api imports
    (r'^from api\b', 'from apps.api'),
    (r'^import api\b', 'from apps import api'),
    # Fix worker imports
    (r'^from worker\b', 'from apps.worker.main'),
    (r'^import worker\b', 'from apps.worker import main as worker'),
]

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    new_content = content
    for pattern, replacement in MAPPINGS:
        # Handle multi-line imports? No, regex usually works line by line or on full text.
        # We use multiline flag for anchors.
        new_content = re.sub(pattern, replacement, new_content, flags=re.MULTILINE)
    
    if new_content != content:
        print(f"Updating {filepath}")
        with open(filepath, 'w') as f:
            f.write(new_content)

def main():
    for root, dirs, files in os.walk('.'):
        if '.git' in root or '.venv' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                process_file(os.path.join(root, file))

if __name__ == '__main__':
    main()
