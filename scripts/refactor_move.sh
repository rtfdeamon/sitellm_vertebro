#!/bin/bash

move_if_exists() {
    if [ -e "$1" ]; then
        echo "Moving $1 to $2"
        git mv "$1" "$2"
    fi
}

move_contents() {
    if [ -d "$1" ]; then
        echo "Moving contents of $1 to $2"
        for f in "$1"/*; do
            if [[ "$f" != *"__pycache__"* ]] && [ -e "$f" ]; then
                git mv "$f" "$2"
            fi
        done
    fi
}

mkdir -p apps/admin apps/api apps/worker apps/bots/telegram apps/bots/vk apps/bots/max
mkdir -p packages/core packages/backend packages/connectors packages/knowledge packages/utils packages/common packages/crawler

move_if_exists app.py apps/admin/main.py
move_contents admin apps/admin/

move_if_exists api.py apps/api/main.py
move_contents api apps/api/

move_if_exists worker.py apps/worker/main.py

move_contents tg_bot apps/bots/telegram/
move_contents vk_bot apps/bots/vk/
move_contents max_bot apps/bots/max/

move_if_exists models.py packages/core/
move_if_exists mongo.py packages/core/
move_if_exists settings.py packages/core/
move_if_exists vectors.py packages/core/
move_if_exists textnorm.py packages/core/
move_if_exists yallm.py packages/core/
move_contents core packages/core/

move_contents backend packages/backend/
move_contents connectors packages/connectors/
move_if_exists integrations packages/connectors/

move_contents knowledge packages/knowledge/
move_if_exists knowledge_service packages/knowledge/
move_if_exists retrieval packages/knowledge/

move_if_exists observability packages/utils/
move_if_exists backup packages/utils/
move_if_exists safety packages/utils/

move_if_exists app_modules packages/common/

move_contents crawler packages/crawler/
