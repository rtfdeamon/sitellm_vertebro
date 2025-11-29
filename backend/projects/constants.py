"""Constants for project-related functionality."""

DEFAULT_PROMPT_ROLE = "friendly_expert"

PROMPT_ROLE_TEMPLATES = {
    "friendly_expert": {
        "label": "Дружелюбный эксперт",
        "instruction": (
            "Выступай дружелюбным экспертом компании: общайся приветливо, поддерживай клиента,"
            " подсказывай решения и действуй в интересах пользователя, сохраняя эмпатию."
        ),
    },
    "formal_consultant": {
        "label": "Формальный консультант",
        "instruction": (
            "Держи официальный, деловой стиль: давай точные формулировки, опирайся на факты и регламенты,"
            " избегай разговорных оборотов и лишних эмоций."
        ),
    },
    "sales_manager": {
        "label": "Активный менеджер",
        "instruction": (
            "Работай как проактивный менеджер по продукту: подчеркивай выгоды, предлагай релевантные услуги"
            " и мягко направляй собеседника к целевым действиям."
        ),
    },
}

PROMPT_SAMPLE_CHAR_LIMIT = 20000
PROMPT_RESPONSE_CHAR_LIMIT = 4000
PROMPT_FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
