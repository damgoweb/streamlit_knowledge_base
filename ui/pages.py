"""
ページ定義
各画面のレイアウトと機能を実装
"""
import streamlit as st
import json
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# プロジェクトルートからのimport
sys.path.append(str(Path(__file__).parent.parent))
from services.snippet_service import SnippetService
from ui.components import UIComponents
from config import APP_CONFIG
from utils.logger import app_logger


class Pages:
    """
    各ページの定義と描画
    """
    
    def __init__(self, service: SnippetService, ui: UIComponents):
        """
        Pagesの初期化
        
        Args:
            service: SnippetServiceインスタンス
            ui: UIComponentsインスタンス
        """
        self.service = service
        self.ui = ui
        self.logger = app_logger
    
    def render_search_page(self):
        """検索・閲覧ページの描画"""
        st.header("🔍 検索・閲覧")
        
        # 検索ボックス
        self.ui.render_search_box()
        
        st.divider()
        
        # 検索実行
        if st.session_state.search_query or st.session_state.selected_category != "すべて":
            # 検索実行
            category = None if st.session_state.selected_category == "すべて" else st.session_state.selected_category
            
            result = self.service.search_snippets(
                query=st.session_state.search_query,
                category=category,
                page=st.session_state.page_number,
                per_page=APP_CONFIG['page_size']
            )
            
            # 検索結果サマリー
            if result.has_results():
                st.caption(result.get_summary())
            
            # スニペット一覧表示
            self.ui.render_snippet_list(
                snippets=result.snippets,
                total_count=result.total_count,
                page=st.session_state.page_number,
                per_page=APP_CONFIG['page_size']
            )
        else:
            # 全件表示
            snippets, total_count = self.service.list_snippets(
                page=st.session_state.page_number,
                per_page=APP_CONFIG['page_size'],
                order_by=st.session_state.sort_by
            )
            
            st.caption(f"📚 登録済みスニペット")
            
            self.ui.render_snippet_list(
                snippets=snippets,
                total_count=total_count,
                page=st.session_state.page_number,
                per_page=APP_CONFIG['page_size']
            )
    
    def render_favorites_page(self):
        """お気に入りページの描画"""
        st.header("⭐ お気に入り")
        
        # お気に入りスニペット取得
        favorites = self.service.get_favorites()
        
        if favorites:
            st.caption(f"お気に入り登録: {len(favorites)}件")
            
            for snippet in favorites:
                self.ui.render_snippet_card(snippet)
        else:
            st.info("お気に入りに登録されたスニペットはありません")
            st.caption("スニペットカードの ☆ ボタンでお気に入りに追加できます")
    
    def render_statistics_page(self):
        """統計ページの描画"""
        st.header("📊 統計情報")
        
        # 統計情報取得
        stats = self.service.get_statistics()
        
        # サマリーカード
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "総スニペット数",
                stats.total_snippets,
                help="登録されている全スニペット数"
            )
        
        with col2:
            st.metric(
                "カテゴリ数",
                stats.total_categories,
                help="使用中のカテゴリ数"
            )
        
        with col3:
            st.metric(
                "総使用回数",
                stats.total_usage,
                help="全スニペットの累計使用回数"
            )
        
        with col4:
            avg_usage = stats.total_usage / stats.total_snippets if stats.total_snippets > 0 else 0
            st.metric(
                "平均使用回数",
                f"{avg_usage:.1f}",
                help="スニペットあたりの平均使用回数"
            )
        
        st.divider()
        
        # よく使うスニペットTOP5
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 よく使うスニペット TOP5")
            
            if stats.most_used_snippets:
                for i, snippet in enumerate(stats.most_used_snippets, 1):
                    st.write(f"{i}. **{snippet.title}** ({snippet.usage_count}回)")
                    st.caption(f"　　カテゴリ: {snippet.category}")
            else:
                st.info("使用履歴がありません")
        
        with col2:
            st.subheader("📂 カテゴリ別分布")
            
            if stats.category_distribution:
                # データフレーム作成
                df = pd.DataFrame(
                    list(stats.category_distribution.items()),
                    columns=['カテゴリ', 'スニペット数']
                )
                df = df.sort_values('スニペット数', ascending=False)
                
                # バーチャート表示
                st.bar_chart(df.set_index('カテゴリ'))
            else:
                st.info("データがありません")
        
        st.divider()
        
        # 最近追加されたスニペット
        st.subheader("🆕 最近追加されたスニペット")
        
        if stats.recent_snippets:
            for snippet in stats.recent_snippets:
                created = snippet.created_at
                if isinstance(created, str):
                    created = datetime.fromisoformat(created)
                
                st.write(f"• **{snippet.title}**")
                st.caption(f"　カテゴリ: {snippet.category} | 追加日: {created.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.info("スニペットがありません")
    
    def render_manage_page(self):
        """管理ページの描画"""
        st.header("⚙️ スニペット管理")
        
        # 編集モード
        if st.session_state.edit_snippet_id:
            snippet = self.service.get_snippet(st.session_state.edit_snippet_id)
            if snippet:
                self.ui.render_edit_form(snippet)
            else:
                st.error("スニペットが見つかりません")
                st.session_state.edit_snippet_id = None
        else:
            # スニペット選択
            snippets, total_count = self.service.list_snippets(
                page=1,
                per_page=1000  # 管理画面では全件取得
            )
            
            if snippets:
                st.subheader("編集・削除するスニペットを選択")
                
                # スニペット選択
                snippet_options = {
                    f"{s.title} ({s.category})": s.id 
                    for s in snippets
                }
                
                selected = st.selectbox(
                    "スニペット選択",
                    options=list(snippet_options.keys()),
                    label_visibility="collapsed"
                )
                
                if selected:
                    snippet_id = snippet_options[selected]
                    snippet = next((s for s in snippets if s.id == snippet_id), None)
                    
                    if snippet:
                        # プレビュー
                        st.subheader("プレビュー")
                        self.ui.render_snippet_card(snippet, show_actions=False)
                        
                        # アクションボタン
                        col1, col2, col3 = st.columns([1, 1, 3])
                        
                        with col1:
                            if st.button("✏️ 編集", use_container_width=True, type="primary"):
                                st.session_state.edit_snippet_id = snippet_id
                                st.rerun()
                        
                        with col2:
                            if st.button("🗑️ 削除", use_container_width=True, type="secondary"):
                                success, message = self.service.delete_snippet(snippet_id)
                                if success:
                                    st.session_state.success_message = message
                                    st.rerun()
                                else:
                                    st.error(message)
            else:
                st.info("管理するスニペットがありません")
    
    def render_import_dialog(self):
        """インポートダイアログの描画"""
        st.header("📥 スニペットのインポート")
        
        # ファイル形式選択
        format_type = st.radio(
            "ファイル形式",
            options=["JSON", "CSV"],
            horizontal=True
        )
        
        # ファイルアップロード
        uploaded_file = st.file_uploader(
            "ファイルを選択",
            type=["json", "csv"],
            help="エクスポートしたスニペットファイルを選択してください"
        )
        
        if uploaded_file is not None:
            # ファイル内容読み取り
            content = uploaded_file.read().decode('utf-8')
            
            # プレビュー
            with st.expander("ファイル内容プレビュー"):
                if format_type == "JSON":
                    try:
                        data = json.loads(content)
                        st.json(data)
                    except:
                        st.error("JSONファイルの解析に失敗しました")
                else:
                    st.text(content[:1000])  # 最初の1000文字
            
            # インポート実行
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("📥 インポート実行", type="primary"):
                    success, message, count = self.service.import_snippets(
                        data=content,
                        format=format_type.lower()
                    )
                    
                    if success:
                        st.session_state.success_message = message
                        st.session_state.show_import = False
                        st.rerun()
                    else:
                        st.error(message)
            
            with col2:
                if st.button("❌ キャンセル"):
                    st.session_state.show_import = False
                    st.rerun()
        
        else:
            # 使い方説明
            st.info("""
            ### インポートの使い方
            1. エクスポートしたJSON/CSVファイルを選択
            2. ファイル内容をプレビューで確認
            3. 「インポート実行」をクリック
            
            **注意事項:**
            - 同じタイトルとカテゴリのスニペットは重複としてスキップされます
            - CSVファイルはUTF-8エンコーディングである必要があります
            """)
            
            if st.button("❌ 閉じる"):
                st.session_state.show_import = False
                st.rerun()
    
    def render_export_dialog(self):
        """エクスポートダイアログの描画"""
        st.header("📤 スニペットのエクスポート")
        
        # エクスポート形式選択
        format_type = st.radio(
            "エクスポート形式",
            options=["JSON", "CSV"],
            horizontal=True,
            help="JSONは完全なデータ、CSVは表形式での出力"
        )
        
        # エクスポート実行
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("📤 エクスポート実行", type="primary"):
                success, message, data = self.service.export_snippets(
                    format=format_type.lower()
                )
                
                if success:
                    # ダウンロードボタン表示
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"snippets_export_{timestamp}.{format_type.lower()}"
                    
                    st.success(message)
                    
                    st.download_button(
                        label=f"💾 {filename} をダウンロード",
                        data=data,
                        file_name=filename,
                        mime="application/json" if format_type == "JSON" else "text/csv"
                    )
                    
                    # プレビュー
                    with st.expander("エクスポート内容プレビュー"):
                        if format_type == "JSON":
                            st.json(json.loads(data))
                        else:
                            st.text(data[:2000])  # 最初の2000文字
                else:
                    st.error(message)
        
        with col2:
            if st.button("❌ 閉じる"):
                st.session_state.show_export = False
                st.rerun()
        
        # 説明
        st.info("""
        ### エクスポートについて
        - **JSON形式**: すべてのデータを含む完全なバックアップ
        - **CSV形式**: Excel等で編集可能な表形式
        
        エクスポートしたファイルは、インポート機能で読み込むことができます。
        """)