"""
個人用ナレッジベース - メインアプリケーション
Streamlitを使用したWebインターフェース
"""
import streamlit as st
from pathlib import Path
import sys
import os

# .envファイルから環境変数を読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# プロジェクトルートをパスに追加
current_dir = Path(__file__).parent
if current_dir.name == 'knowledge_base':
    sys.path.append(str(current_dir))
else:
    knowledge_base_dir = current_dir / 'knowledge_base'
    if knowledge_base_dir.exists():
        sys.path.append(str(knowledge_base_dir))

try:
    # DB Factoryを使用してマネージャーを取得
    from database.db_factory import get_db_manager_instance
    from repository.snippet_repo import SnippetRepository
    from services.snippet_service import SnippetService
    from ui.components import UIComponents
    from ui.pages import Pages
    from config import APP_CONFIG, UI_CONFIG
    from utils.logger import app_logger
except ImportError as e:
    st.error(f"""
    モジュールのインポートに失敗しました: {e}
    
    ディレクトリ構造を確認してください:
    ```
    knowledge_base/
    ├── app.py (このファイル)
    ├── config.py
    ├── database/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── db_manager.py
    │   ├── supabase_manager.py
    │   └── db_factory.py
    ├── repository/
    │   ├── __init__.py
    │   └── snippet_repo.py
    ├── services/
    │   ├── __init__.py
    │   └── snippet_service.py
    ├── ui/
    │   ├── __init__.py
    │   ├── components.py
    │   └── pages.py
    └── utils/
        ├── __init__.py
        ├── logger.py
        └── validators.py
    ```
    
    環境変数の設定:
    - SUPABASE_URL: {os.environ.get('SUPABASE_URL', '未設定')}
    - SUPABASE_ANON_KEY: {'設定済み' if os.environ.get('SUPABASE_ANON_KEY') else '未設定'}
    """)
    sys.exit(1)


class KnowledgeBaseApp:
    """
    メインアプリケーションクラス
    """
    
    def __init__(self):
        """アプリケーションの初期化"""
        self.logger = app_logger
        self.init_services()
        self.init_session_state()
        self.ui = UIComponents(self.service)
        self.pages = Pages(self.service, self.ui)
    
    def init_services(self):
        """サービス層の初期化"""
        try:
            # データベース層の初期化（Factory経由）
            self.db_manager = get_db_manager_instance()
            
            # リポジトリ層の初期化
            self.repository = SnippetRepository(self.db_manager)
            
            # サービス層の初期化
            self.service = SnippetService(self.repository)
            
            # 環境情報をログ出力
            env = APP_CONFIG.get('environment', 'unknown')
            self.logger.info(f"Services initialized successfully (Environment: {env})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            st.error(f"""
            アプリケーションの初期化に失敗しました: {e}
            
            考えられる原因:
            1. Supabase接続情報が設定されていない
            2. データベース接続に失敗
            3. 必要なテーブルが存在しない
            
            確認事項:
            - 環境変数 SUPABASE_URL と SUPABASE_ANON_KEY が設定されているか
            - Supabaseプロジェクトでテーブルが作成されているか
            """)
            st.stop()
    
    def init_session_state(self):
        """セッション状態の初期化"""
        # 初期値の設定
        defaults = {
            'current_page': 'search',           # 現在のページ
            'search_query': '',                 # 検索クエリ
            'selected_category': 'すべて',      # 選択中のカテゴリ
            'view_mode': 'list',               # 表示モード
            'sort_by': 'updated_at DESC',      # ソート順
            'edit_snippet_id': None,           # 編集中のスニペットID
            'show_statistics': False,          # 統計表示フラグ
            'page_number': 1,                  # ページ番号
            'success_message': None,           # 成功メッセージ
            'error_message': None,             # エラーメッセージ
            'show_export': False,              # エクスポート画面表示
            'show_import': False,              # インポート画面表示
        }
        
        # セッション状態に存在しないキーを初期化
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def run(self):
        """アプリケーションのメイン実行"""
        # ページ設定
        st.set_page_config(
            page_title=APP_CONFIG['app_name'],
            page_icon="🧠",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # カスタムCSS
        self.apply_custom_css()
        
        # ヘッダー
        self.render_header()
        
        # メッセージ表示
        self.show_messages()
        
        # サイドバー
        self.render_sidebar()
        
        # メインコンテンツ
        self.render_main_content()
    
    def apply_custom_css(self):
        """カスタムCSSの適用"""
        st.markdown("""
        <style>
        /* メインコンテナの幅調整 */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        
        /* スニペットカードのスタイル */
        .snippet-card {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            border: 1px solid #dee2e6;
        }
        
        /* コードブロックのスタイル */
        .stCodeBlock {
            border-radius: 8px;
        }
        
        /* ボタンのスタイル */
        .stButton > button {
            border-radius: 4px;
            transition: all 0.3s;
        }
        
        /* 成功メッセージ */
        .success-message {
            padding: 0.75rem;
            border-radius: 4px;
            background-color: #d1e7dd;
            border: 1px solid #badbcc;
            color: #0f5132;
        }
        
        /* エラーメッセージ */
        .error-message {
            padding: 0.75rem;
            border-radius: 4px;
            background-color: #f8d7da;
            border: 1px solid #f5c2c7;
            color: #842029;
        }
        
        /* 統計カード */
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def render_header(self):
        """ヘッダーの描画"""
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col2:
            st.title(APP_CONFIG['app_name'])
            caption = f"Version {APP_CONFIG['version']} - よく使うコマンドやコードを素早く検索・管理"
            
            # 環境表示
            if UI_CONFIG.get('show_environment', False):
                env = APP_CONFIG.get('environment', 'unknown')
                env_emoji = "☁️" if env == 'cloud' else "💻"
                caption += f" {env_emoji} {env.upper()}"
            
            st.caption(caption)
    
    def show_messages(self):
        """メッセージの表示"""
        # 成功メッセージ
        if st.session_state.success_message:
            st.success(st.session_state.success_message)
            st.session_state.success_message = None
        
        # エラーメッセージ
        if st.session_state.error_message:
            st.error(st.session_state.error_message)
            st.session_state.error_message = None
    
    def render_sidebar(self):
        """サイドバーの描画"""
        with st.sidebar:
            st.header("📝 新規登録")
            
            # スニペット登録フォーム
            self.ui.render_register_form()
            
            st.divider()
            
            # ナビゲーション
            st.header("🗂️ メニュー")
            
            # ページ選択
            pages = {
                'search': '🔍 検索・閲覧',
                'favorites': '⭐ お気に入り',
                'statistics': '📊 統計',
                'manage': '⚙️ 管理'
            }
            
            for page_key, page_name in pages.items():
                if st.button(
                    page_name,
                    key=f"nav_{page_key}",
                    use_container_width=True,
                    type="primary" if st.session_state.current_page == page_key else "secondary"
                ):
                    st.session_state.current_page = page_key
                    st.session_state.page_number = 1
            
            st.divider()
            
            # ツール
            st.header("🛠️ ツール")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 インポート", use_container_width=True):
                    st.session_state.show_import = True
            
            with col2:
                if st.button("📤 エクスポート", use_container_width=True):
                    st.session_state.show_export = True
            
            # バックアップ（環境に応じて表示）
            if APP_CONFIG.get('environment') != 'cloud':
                if st.button("💾 バックアップ", use_container_width=True):
                    try:
                        backup_path = self.db_manager.backup_database()
                        st.success(f"バックアップ完了: {Path(backup_path).name}")
                    except Exception as e:
                        st.error(f"バックアップ失敗: {e}")
    
    def render_main_content(self):
        """メインコンテンツの描画"""
        # インポート/エクスポートダイアログ
        if st.session_state.show_import:
            self.pages.render_import_dialog()
        elif st.session_state.show_export:
            self.pages.render_export_dialog()
        else:
            # 通常のページ表示
            if st.session_state.current_page == 'search':
                self.pages.render_search_page()
            elif st.session_state.current_page == 'favorites':
                self.pages.render_favorites_page()
            elif st.session_state.current_page == 'statistics':
                self.pages.render_statistics_page()
            elif st.session_state.current_page == 'manage':
                self.pages.render_manage_page()


def main():
    """メイン関数"""
    app = KnowledgeBaseApp()
    app.run()


if __name__ == "__main__":
    main()