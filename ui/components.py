"""
UIコンポーネント
再利用可能なUI部品を定義
"""
import streamlit as st
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import sys

# プロジェクトルートからのimport
sys.path.append(str(Path(__file__).parent.parent))
from database.models import Snippet, Category, SearchResult
from services.snippet_service import SnippetService
from config import CATEGORIES, LANGUAGES
from utils.logger import app_logger


class UIComponents:
    """
    再利用可能なUIコンポーネント
    """
    
    def __init__(self, service: SnippetService):
        """
        UIComponentsの初期化
        
        Args:
            service: SnippetServiceインスタンス
        """
        self.service = service
        self.logger = app_logger
    
    def render_register_form(self):
        """スニペット登録フォームの描画"""
        with st.form("register_form", clear_on_submit=True):
            # タイトル
            title = st.text_input(
                "タイトル *",
                placeholder="例: Docker コンテナ一覧表示",
                help="スニペットを識別するタイトル"
            )
            
            # カテゴリ
            categories = [cat['name'] for cat in CATEGORIES]
            category = st.selectbox(
                "カテゴリ *",
                options=categories,
                help="スニペットのカテゴリを選択"
            )
            
            # 言語
            language = st.selectbox(
                "言語/形式",
                options=LANGUAGES,
                index=LANGUAGES.index("bash") if "bash" in LANGUAGES else 0,
                help="構文ハイライト用の言語を選択"
            )
            
            # タグ
            tags = st.text_input(
                "タグ（カンマ区切り）",
                placeholder="例: container, list, ps",
                help="検索用のタグをカンマ区切りで入力"
            )
            
            # 説明
            description = st.text_area(
                "説明",
                placeholder="使い方や注意点など",
                height=80,
                help="スニペットの説明や使用方法"
            )
            
            # コンテンツ
            content = st.text_area(
                "コード/コマンド *",
                placeholder="docker ps -a",
                height=150,
                help="実際のコードやコマンド"
            )
            
            # 送信ボタン
            submitted = st.form_submit_button(
                "💾 保存",
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                if title and content and category:
                    # スニペット追加
                    success, message, snippet_id = self.service.add_snippet(
                        title=title,
                        content=content,
                        category=category,
                        tags=tags,
                        description=description,
                        language=language
                    )
                    
                    if success:
                        st.session_state.success_message = message
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("必須項目（*）を入力してください")
    
    def render_snippet_card(self, snippet: Snippet, show_actions: bool = True):
        """
        スニペットカードの描画
        
        Args:
            snippet: Snippetオブジェクト
            show_actions: アクションボタンを表示するか
        """
        with st.container():
            # カードヘッダー
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # タイトルとお気に入り
                title_text = snippet.title
                if snippet.is_favorite:
                    title_text = f"⭐ {title_text}"
                st.subheader(title_text)
            
            with col2:
                # カテゴリとタグ
                category_icon = next(
                    (cat['icon'] for cat in CATEGORIES if cat['name'] == snippet.category),
                    "📁"
                )
                st.caption(f"{category_icon} {snippet.category}")
            
            with col3:
                # 使用回数
                st.caption(f"使用: {snippet.usage_count}回")
            
            # 説明
            if snippet.description:
                st.caption(snippet.description)
            
            # タグ
            if snippet.tags:
                tags_html = " ".join([
                    f'<span style="background-color: #e3f2fd; padding: 2px 8px; '
                    f'border-radius: 12px; margin-right: 4px; font-size: 0.8em;">'
                    f'#{tag}</span>'
                    for tag in snippet.get_tags_list()
                ])
                st.markdown(tags_html, unsafe_allow_html=True)
            
            # コンテンツ
            st.code(snippet.content, language=snippet.language)
            
            # アクションボタン
            if show_actions:
                col1, col2, col2_5, col3, col4, col5 = st.columns([1, 1, 1, 1, 1, 3])
                
                with col1:
                    if st.button("👁️ 表示", key=f"view_{snippet.id}"):
                        self.service.increment_usage(snippet.id)
                        st.session_state.success_message = "使用回数を更新しました"
                        st.rerun()
                
                with col2:
                    # コピーボタン - コピー用のテキストエリアを表示
                    if st.button("📋 コピー", key=f"copy_{snippet.id}"):
                        # セッション状態でコピーモードを管理
                        copy_key = f"show_copy_{snippet.id}"
                        st.session_state[copy_key] = not st.session_state.get(copy_key, False)
                        if st.session_state[copy_key]:
                            self.service.increment_usage(snippet.id)
                        st.rerun()
                
                with col2_5:
                    # お気に入りトグル
                    is_fav = "⭐" if snippet.is_favorite else "☆"
                    if st.button(is_fav, key=f"fav_{snippet.id}"):
                        success, new_state = self.service.toggle_favorite(snippet.id)
                        if success:
                            msg = "お気に入りに追加しました" if new_state else "お気に入りから削除しました"
                            st.session_state.success_message = msg
                            st.rerun()
                
                with col3:
                    if st.button("✏️ 編集", key=f"edit_{snippet.id}"):
                        st.session_state.edit_snippet_id = snippet.id
                        st.session_state.current_page = 'manage'
                        st.rerun()
                
                with col4:
                    if st.button("🗑️ 削除", key=f"delete_{snippet.id}", type="secondary"):
                        # 削除確認用のセッション状態を設定
                        if f"confirm_delete_{snippet.id}" not in st.session_state:
                            st.session_state[f"confirm_delete_{snippet.id}"] = True
                            st.rerun()
            
            # コピー用テキストエリア表示
            if show_actions and st.session_state.get(f"show_copy_{snippet.id}", False):
                st.info("📋 下記のテキストを選択してコピーしてください（Ctrl+A → Ctrl+C）")
                st.text_area(
                    "コピー用",
                    value=snippet.content,
                    height=100,
                    key=f"copy_text_{snippet.id}",
                    label_visibility="collapsed"
                )
                if st.button("閉じる", key=f"close_copy_{snippet.id}"):
                    st.session_state[f"show_copy_{snippet.id}"] = False
                    st.rerun()
            
            # 削除確認
            if show_actions and f"confirm_delete_{snippet.id}" in st.session_state:
                if st.session_state[f"confirm_delete_{snippet.id}"]:
                    st.warning("本当に削除しますか？")
                    col1, col2, col3 = st.columns([1, 1, 3])
                    with col1:
                        if st.button("はい", key=f"confirm_yes_{snippet.id}", type="primary"):
                            success, message = self.service.delete_snippet(snippet.id)
                            if success:
                                st.session_state.success_message = message
                                del st.session_state[f"confirm_delete_{snippet.id}"]
                                st.rerun()
                            else:
                                st.error(message)
                    with col2:
                        if st.button("いいえ", key=f"confirm_no_{snippet.id}"):
                            del st.session_state[f"confirm_delete_{snippet.id}"]
                            st.rerun()
            
            st.divider()
    
    def render_snippet_list(self, 
                           snippets: List[Snippet],
                           total_count: int,
                           page: int = 1,
                           per_page: int = 20):
        """
        スニペット一覧の描画
        
        Args:
            snippets: スニペットリスト
            total_count: 総件数
            page: 現在のページ
            per_page: 1ページあたりの件数
        """
        if not snippets:
            st.info("📭 スニペットが見つかりません")
            return
        
        # 件数とページ情報
        total_pages = (total_count + per_page - 1) // per_page
        st.caption(f"全 {total_count} 件 - ページ {page}/{total_pages}")
        
        # スニペット表示
        for snippet in snippets:
            self.render_snippet_card(snippet)
        
        # ページネーション
        if total_pages > 1:
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
            
            with col2:
                if page > 1:
                    if st.button("◀ 前へ", use_container_width=True):
                        st.session_state.page_number = page - 1
                        st.rerun()
            
            with col3:
                st.write(f"{page} / {total_pages}")
            
            with col4:
                if page < total_pages:
                    if st.button("次へ ▶", use_container_width=True):
                        st.session_state.page_number = page + 1
                        st.rerun()
    
    def render_search_box(self):
        """検索ボックスの描画"""
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            # 検索クエリ入力
            query = st.text_input(
                "🔍 キーワード検索",
                value=st.session_state.search_query,
                placeholder="検索したいキーワードを入力...",
                label_visibility="collapsed"
            )
            st.session_state.search_query = query
        
        with col2:
            # カテゴリフィルタ
            categories = ["すべて"] + [cat['name'] for cat in CATEGORIES]
            category = st.selectbox(
                "カテゴリ",
                options=categories,
                index=categories.index(st.session_state.selected_category),
                label_visibility="collapsed"
            )
            st.session_state.selected_category = category
        
        with col3:
            # ソート順
            sort_options = {
                "updated_at DESC": "更新日時 ↓",
                "updated_at ASC": "更新日時 ↑",
                "usage_count DESC": "使用回数 ↓",
                "created_at DESC": "作成日時 ↓",
                "title ASC": "タイトル ↑"
            }
            sort_by = st.selectbox(
                "並び順",
                options=list(sort_options.keys()),
                format_func=lambda x: sort_options[x],
                index=list(sort_options.keys()).index(st.session_state.sort_by),
                label_visibility="collapsed"
            )
            st.session_state.sort_by = sort_by
        
        # 検索ボタン
        if st.button("🔍 検索", use_container_width=True, type="primary"):
            st.session_state.page_number = 1
            st.rerun()
    
    def render_edit_form(self, snippet: Snippet):
        """
        スニペット編集フォームの描画
        
        Args:
            snippet: 編集対象のSnippet
        """
        st.subheader(f"✏️ スニペット編集: {snippet.title}")
        
        with st.form("edit_form"):
            # タイトル
            title = st.text_input(
                "タイトル *",
                value=snippet.title
            )
            
            # カテゴリ
            categories = [cat['name'] for cat in CATEGORIES]
            category_index = categories.index(snippet.category) if snippet.category in categories else 0
            category = st.selectbox(
                "カテゴリ *",
                options=categories,
                index=category_index
            )
            
            # 言語
            language_index = LANGUAGES.index(snippet.language) if snippet.language in LANGUAGES else 0
            language = st.selectbox(
                "言語/形式",
                options=LANGUAGES,
                index=language_index
            )
            
            # タグ
            tags = st.text_input(
                "タグ（カンマ区切り）",
                value=snippet.tags or ""
            )
            
            # 説明
            description = st.text_area(
                "説明",
                value=snippet.description or "",
                height=80
            )
            
            # コンテンツ
            content = st.text_area(
                "コード/コマンド *",
                value=snippet.content,
                height=200
            )
            
            # ボタン
            col1, col2, col3 = st.columns([1, 1, 3])
            
            with col1:
                submitted = st.form_submit_button(
                    "💾 更新",
                    type="primary",
                    use_container_width=True
                )
            
            with col2:
                cancel = st.form_submit_button(
                    "❌ キャンセル",
                    use_container_width=True
                )
            
            if submitted:
                success, message = self.service.update_snippet(
                    snippet_id=snippet.id,
                    title=title,
                    content=content,
                    category=category,
                    tags=tags,
                    description=description,
                    language=language
                )
                
                if success:
                    st.session_state.success_message = message
                    st.session_state.edit_snippet_id = None
                    st.rerun()
                else:
                    st.error(message)
            
            if cancel:
                st.session_state.edit_snippet_id = None
                st.rerun()