import os
from pathlib import Path

# プロジェクトルートディレクトリ
BASE_DIR = Path(__file__).resolve().parent

# 環境判定（Streamlit CloudではSUPABASE_URLが設定されている）
IS_CLOUD = os.environ.get('SUPABASE_URL') is not None

# データベース設定
if IS_CLOUD:
    # Streamlit Cloud環境（Supabase使用）
    DATABASE_CONFIG = {
        'db_type': 'supabase',
        'backup_dir': BASE_DIR / 'backups',
        'auto_backup': True,
        'backup_interval_hours': 24
    }
else:
    # ローカル環境（SQLite使用）
    DATABASE_CONFIG = {
        'db_type': 'sqlite',
        'db_path': BASE_DIR / 'knowledge_base.db',
        'backup_dir': BASE_DIR / 'backups',
        'auto_backup': True,
        'backup_interval_hours': 24
    }

# アプリケーション設定
APP_CONFIG = {
    'app_name': '🧠 個人用ナレッジベース',
    'version': '2.0.0',  # Supabase対応版
    'page_size': 20,  # ページネーション
    'max_search_results': 100,
    'enable_cache': True,
    'environment': 'cloud' if IS_CLOUD else 'local'
}

# カテゴリ設定
CATEGORIES = [
    {'name': 'Docker', 'icon': '🐳', 'order': 1},
    {'name': 'Git', 'icon': '📚', 'order': 2},
    {'name': 'SQL', 'icon': '🗄️', 'order': 3},
    {'name': 'Linux', 'icon': '🐧', 'order': 4},
    {'name': 'Python', 'icon': '🐍', 'order': 5},
    {'name': '設定', 'icon': '⚙️', 'order': 6},
    {'name': 'その他', 'icon': '📝', 'order': 99}
]

# 言語設定（構文ハイライト用）
LANGUAGES = [
    'text', 'bash', 'python', 'sql', 'javascript', 
    'yaml', 'json', 'dockerfile', 'conf', 'xml'
]

# ログ設定
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': BASE_DIR / 'app.log' if not IS_CLOUD else None,  # Cloudでは標準出力のみ
    'max_bytes': 10485760,  # 10MB
    'backup_count': 5
}

# UI設定
UI_CONFIG = {
    'theme': 'light',  # light/dark
    'show_statistics': True,
    'enable_shortcuts': True,
    'confirm_delete': True,
    'show_environment': True  # 環境表示
}

# 検索設定
SEARCH_CONFIG = {
    'min_keyword_length': 2,
    'enable_fuzzy_search': False,
    'search_fields': ['title', 'content', 'tags', 'description'],
    'boost_title': 2.0,  # タイトルマッチの重み
    'boost_tags': 1.5    # タグマッチの重み
}