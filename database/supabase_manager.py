"""
Supabase管理クラス
PostgreSQL（Supabase）への接続、クエリ実行を担当
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Any, Dict
from contextlib import contextmanager
import json
import logging

# Supabaseインポート（バージョン互換性対応）
try:
    from supabase import create_client, Client
except ImportError:
    from supabase.client import create_client, Client

# プロジェクトルートからのimport
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_CONFIG, CATEGORIES
from utils.logger import app_logger


class SupabaseManager:
    """
    Supabase接続とクエリ管理
    
    db_manager.pyのインターフェースと互換性を保ちながら
    Supabaseへの接続を提供
    """
    
    def __init__(self):
        """
        SupabaseManagerの初期化
        """
        self.logger = app_logger
        
        # Supabase接続情報を取得
        self.supabase_url = None
        self.supabase_key = None
        
        # 1. Streamlit secretsから取得を試みる（優先）
        try:
            import streamlit as st
            self.supabase_url = st.secrets.get('SUPABASE_URL')
            self.supabase_key = st.secrets.get('SUPABASE_ANON_KEY')
            if self.supabase_url and self.supabase_key:
                self.logger.info("Using Streamlit secrets for Supabase connection")
        except Exception as e:
            self.logger.debug(f"Streamlit secrets not available: {e}")
        
        # 2. 環境変数から取得を試みる
        if not self.supabase_url or not self.supabase_key:
            self.supabase_url = os.environ.get('SUPABASE_URL')
            self.supabase_key = os.environ.get('SUPABASE_ANON_KEY')
            if self.supabase_url and self.supabase_key:
                self.logger.info("Using environment variables for Supabase connection")
        
        # 3. 接続情報が取得できない場合はエラー
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables or Streamlit secrets.\n"
                "See: https://docs.streamlit.io/library/advanced-features/secrets-management"
            )
        
        # Supabaseクライアント初期化（エラーハンドリング付き）
        self._initialize_client()
        
        # データベース初期化
        self.init_database()
        self.logger.info("SupabaseManager initialized successfully")
    
    def _initialize_client(self):
        """
        Supabaseクライアントを初期化（バージョン互換性対応）
        """
        try:
            # 標準的な初期化を試みる
            self.client = create_client(self.supabase_url, self.supabase_key)
            self.logger.debug("Supabase client initialized with standard method")
        except TypeError as e:
            # TypeErrorの場合、パラメータ名を明示的に指定
            if 'proxy' in str(e):
                self.logger.warning("Proxy parameter not supported, retrying without it")
                try:
                    # 直接Clientクラスを使用
                    from supabase.client import Client as SupabaseClient
                    self.client = SupabaseClient(self.supabase_url, self.supabase_key)
                    self.logger.debug("Supabase client initialized with Client class directly")
                except Exception as retry_error:
                    self.logger.error(f"Failed to initialize client: {retry_error}")
                    raise ValueError(f"Cannot initialize Supabase client: {retry_error}")
            else:
                raise ValueError(f"Unexpected error initializing Supabase client: {e}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Supabase client: {e}")
            raise ValueError(f"Supabase initialization error: {e}")
    
    def get_connection(self):
        """
        互換性のためのメソッド（Supabaseではクライアントを返す）
        """
        return self.client
    
    @contextmanager
    def get_db(self):
        """
        コンテキストマネージャーとして接続を提供（互換性のため）
        """
        try:
            yield self.client
        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
            raise DatabaseError(f"データベース操作エラー: {e}")
    
    def init_database(self):
        """
        データベースの初期化
        初期カテゴリデータを挿入
        """
        try:
            # カテゴリデータの初期化
            existing_categories = self.client.table('categories').select('name').execute()
            existing_names = {cat['name'] for cat in existing_categories.data}
            
            for category in CATEGORIES:
                if category['name'] not in existing_names:
                    self.client.table('categories').insert({
                        'name': category['name'],
                        'icon': category['icon'],
                        'display_order': category['order']
                    }).execute()
            
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"データベース初期化エラー: {e}")
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict]:
        """
        SELECTクエリを実行（SQLite互換インターフェース）
        
        注意: Supabaseでは直接SQLを実行できないため、
        クエリパターンを解析してSupabase APIを使用
        """
        try:
            # シンプルなSELECTクエリのパターンマッチング
            if "SELECT * FROM snippets" in query:
                result = self._execute_snippets_query(query, params)
            elif "SELECT * FROM categories" in query:
                result = self.client.table('categories').select('*').order('display_order').execute()
            elif "SELECT * FROM search_history" in query:
                result = self.client.table('search_history').select('*').order('searched_at', desc=True).execute()
            else:
                # より複雑なクエリはRPCを使用
                result = self._execute_rpc_query(query, params)
            
            # sqlite3.Row風の辞書リストを返す
            return result.data if hasattr(result, 'data') else result
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {query}, params: {params}, error: {e}")
            raise DatabaseError(f"クエリ実行エラー: {e}")
    
    def _execute_snippets_query(self, query: str, params: Tuple) -> Any:
        """
        snippetsテーブルのクエリを実行
        """
        query_builder = self.client.table('snippets').select('*')
        
        # WHERE句の解析
        if "WHERE" in query:
            if "category = ?" in query and params:
                query_builder = query_builder.eq('category', params[0])
            elif "is_favorite = ?" in query and params:
                query_builder = query_builder.eq('is_favorite', bool(params[0]))
        
        # ORDER BY句の解析
        if "ORDER BY" in query:
            if "updated_at DESC" in query:
                query_builder = query_builder.order('updated_at', desc=True)
            elif "usage_count DESC" in query:
                query_builder = query_builder.order('usage_count', desc=True)
            elif "created_at DESC" in query:
                query_builder = query_builder.order('created_at', desc=True)
        
        # LIMIT句の解析
        if "LIMIT" in query:
            import re
            limit_match = re.search(r'LIMIT (\d+)', query)
            if limit_match:
                query_builder = query_builder.limit(int(limit_match.group(1)))
        
        return query_builder.execute()
    
    def _execute_rpc_query(self, query: str, params: Tuple) -> List[Dict]:
        """
        複雑なクエリをRPC関数経由で実行
        """
        # 統計情報などの集計クエリ用
        if "COUNT(*)" in query:
            table_name = self._extract_table_name(query)
            if table_name:
                result = self.client.table(table_name).select('*', count='exact').execute()
                return [{'count': result.count}]
        
        return []
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """
        SQLクエリからテーブル名を抽出
        """
        import re
        match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        return match.group(1) if match else None
    
    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """
        INSERT/UPDATE/DELETEクエリを実行
        """
        try:
            affected_rows = 0
            
            if query.upper().startswith("INSERT"):
                affected_rows = self._execute_insert(query, params)
            elif query.upper().startswith("UPDATE"):
                affected_rows = self._execute_update_query(query, params)
            elif query.upper().startswith("DELETE"):
                affected_rows = self._execute_delete(query, params)
            
            return affected_rows
            
        except Exception as e:
            self.logger.error(f"Update execution failed: {query}, params: {params}, error: {e}")
            raise DatabaseError(f"更新クエリ実行エラー: {e}")
    
    def _execute_insert(self, query: str, params: Tuple) -> int:
        """
        INSERTクエリを実行
        """
        if "snippets" in query:
            # パラメータの順序は元のSQLiteクエリに依存
            data = {
                'title': params[0],
                'content': params[1],
                'category': params[2],
                'tags': params[3] if len(params) > 3 else None,
                'description': params[4] if len(params) > 4 else None,
                'language': params[5] if len(params) > 5 else 'text',
            }
            result = self.client.table('snippets').insert(data).execute()
            return len(result.data)
        
        elif "search_history" in query:
            data = {
                'query': params[0],
                'result_count': params[1] if len(params) > 1 else 0
            }
            result = self.client.table('search_history').insert(data).execute()
            return len(result.data)
        
        return 0
    
    def _execute_update_query(self, query: str, params: Tuple) -> int:
        """
        UPDATEクエリを実行
        """
        import re
        
        if "snippets" in query:
            # UPDATE snippets SET ... WHERE id = ?
            id_match = re.search(r'WHERE\s+id\s*=\s*\?', query, re.IGNORECASE)
            if id_match and params:
                snippet_id = params[-1]  # 最後のパラメータがID
                
                # SET句の解析
                if "usage_count = usage_count + 1" in query:
                    # 使用回数のインクリメント
                    current = self.client.table('snippets').select('usage_count').eq('id', snippet_id).execute()
                    if current.data:
                        new_count = current.data[0]['usage_count'] + 1
                        result = self.client.table('snippets').update({'usage_count': new_count}).eq('id', snippet_id).execute()
                        return len(result.data)
                else:
                    # 通常の更新
                    data = {
                        'title': params[0],
                        'content': params[1],
                        'category': params[2],
                        'tags': params[3] if len(params) > 3 else None,
                        'description': params[4] if len(params) > 4 else None,
                        'language': params[5] if len(params) > 5 else 'text',
                    }
                    result = self.client.table('snippets').update(data).eq('id', snippet_id).execute()
                    return len(result.data)
        
        return 0
    
    def _execute_delete(self, query: str, params: Tuple) -> int:
        """
        DELETEクエリを実行
        """
        import re
        
        if "snippets" in query:
            id_match = re.search(r'WHERE\s+id\s*=\s*\?', query, re.IGNORECASE)
            if id_match and params:
                result = self.client.table('snippets').delete().eq('id', params[0]).execute()
                return len(result.data)
        
        return 0
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """
        複数のINSERT/UPDATEを一括実行
        """
        affected_rows = 0
        for params in params_list:
            affected_rows += self.execute_update(query, params)
        return affected_rows
    
    def search_snippets(self, keyword: str) -> List[Dict]:
        """
        全文検索の実装（シンプルな検索関数を使用）
        """
        try:
            # Supabaseの検索RPC関数を呼び出す（search_snippets_simple使用）
            result = self.client.rpc('search_snippets_simple', {'keyword': keyword}).execute()
            
            # データが返ってきた場合はそのまま返す
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            # フォールバック検索
            return self._fallback_search(keyword)
    
    def _fallback_search(self, keyword: str) -> List[Dict]:
        """
        フォールバック検索（基本的なLIKE検索）
        """
        try:
            search_pattern = f"%{keyword}%"
            result = self.client.table('snippets').select('*').ilike('title', search_pattern).execute()
            title_results = result.data
            
            result = self.client.table('snippets').select('*').ilike('content', search_pattern).execute()
            content_results = result.data
            
            # 重複を除いて結合
            seen_ids = set()
            combined_results = []
            
            for item in title_results + content_results:
                if item['id'] not in seen_ids:
                    seen_ids.add(item['id'])
                    combined_results.append(item)
            
            return combined_results
            
        except Exception as e:
            self.logger.error(f"Fallback search failed: {e}")
            return []
    
    def backup_database(self, backup_name: Optional[str] = None) -> str:
        """
        データベースのバックアップ（JSONエクスポート）
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if not backup_name:
                backup_name = f"knowledge_base_backup_{timestamp}.json"
            
            # データを取得
            snippets = self.client.table('snippets').select('*').execute()
            categories = self.client.table('categories').select('*').execute()
            
            backup_data = {
                'timestamp': timestamp,
                'snippets': snippets.data,
                'categories': categories.data
            }
            
            # JSONファイルとして保存
            backup_path = Path('backups') / backup_name
            backup_path.parent.mkdir(exist_ok=True)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.info(f"Database backed up to: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            raise DatabaseError(f"バックアップエラー: {e}")
    
    def restore_database(self, backup_path: str) -> bool:
        """
        バックアップからデータベースを復元
        """
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # スニペットを復元
            if 'snippets' in backup_data:
                for snippet in backup_data['snippets']:
                    # IDを除外して挿入
                    snippet_data = {k: v for k, v in snippet.items() if k != 'id'}
                    self.client.table('snippets').upsert(snippet_data).execute()
            
            self.logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            raise DatabaseError(f"復元エラー: {e}")
    
    def get_table_info(self, table_name: str) -> List[dict]:
        """
        テーブル情報を取得（簡易実装）
        """
        # Supabaseではテーブル構造の取得が制限されているため、
        # 既知のスキーマを返す
        if table_name == 'snippets':
            return [
                {'name': 'id', 'type': 'INTEGER'},
                {'name': 'title', 'type': 'TEXT'},
                {'name': 'content', 'type': 'TEXT'},
                {'name': 'category', 'type': 'TEXT'},
                {'name': 'tags', 'type': 'TEXT'},
                {'name': 'description', 'type': 'TEXT'},
                {'name': 'language', 'type': 'TEXT'},
                {'name': 'created_at', 'type': 'TIMESTAMP'},
                {'name': 'updated_at', 'type': 'TIMESTAMP'},
                {'name': 'usage_count', 'type': 'INTEGER'},
                {'name': 'is_favorite', 'type': 'BOOLEAN'},
            ]
        return []
    
    def vacuum(self):
        """
        データベースの最適化（Supabaseでは不要なのでパス）
        """
        self.logger.info("Vacuum operation skipped for Supabase")
        pass


# カスタム例外クラス（互換性のため）
class DatabaseError(Exception):
    """データベース関連のエラー"""
    pass