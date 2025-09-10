"""
スニペットリポジトリ
データベースへのCRUD操作を担当
"""
from typing import Optional, List, Tuple
from datetime import datetime
import time
from pathlib import Path
import sys

# プロジェクトルートからのimport
sys.path.append(str(Path(__file__).parent.parent))
from database.models import Snippet, Category, SearchResult, DatabaseError, NotFoundError
from database.db_manager import DatabaseManager
from config import SEARCH_CONFIG
from utils.logger import app_logger


class SnippetRepository:
    """
    スニペットのCRUD操作を担当するリポジトリクラス
    データベースとのやり取りを抽象化
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        SnippetRepositoryの初期化
        
        Args:
            db_manager: DatabaseManagerインスタンス
        """
        self.db_manager = db_manager
        self.logger = app_logger
    
    def create(self, snippet: Snippet) -> int:
        """
        新しいスニペットを作成
        
        Args:
            snippet: 作成するSnippetオブジェクト
            
        Returns:
            作成されたスニペットのID
        """
        try:
            query = '''
                INSERT INTO snippets 
                (title, content, category, tags, description, language, 
                 created_at, updated_at, usage_count, is_favorite)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            now = datetime.now()
            params = (
                snippet.title,
                snippet.content,
                snippet.category,
                snippet.tags,
                snippet.description,
                snippet.language,
                now,
                now,
                snippet.usage_count,
                int(snippet.is_favorite)
            )
            
            with self.db_manager.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                snippet_id = cursor.lastrowid
                conn.commit()
                
            self.logger.info(f"Created snippet with id: {snippet_id}")
            return snippet_id
            
        except Exception as e:
            self.logger.error(f"Failed to create snippet: {e}")
            raise DatabaseError(f"スニペット作成エラー: {e}")
    
    def read(self, snippet_id: int) -> Optional[Snippet]:
        """
        IDでスニペットを取得
        
        Args:
            snippet_id: スニペットID
            
        Returns:
            Snippetオブジェクト（見つからない場合はNone）
        """
        try:
            query = "SELECT * FROM snippets WHERE id = ?"
            rows = self.db_manager.execute_query(query, (snippet_id,))
            
            if not rows:
                return None
            
            row = rows[0]
            return self._row_to_snippet(row)
            
        except Exception as e:
            self.logger.error(f"Failed to read snippet {snippet_id}: {e}")
            raise DatabaseError(f"スニペット取得エラー: {e}")
    
    def update(self, snippet: Snippet) -> bool:
        """
        スニペットを更新
        
        Args:
            snippet: 更新するSnippetオブジェクト（IDが必須）
            
        Returns:
            更新成功の可否
        """
        if not snippet.id:
            raise ValueError("更新にはIDが必要です")
        
        try:
            query = '''
                UPDATE snippets 
                SET title = ?, content = ?, category = ?, tags = ?, 
                    description = ?, language = ?, updated_at = ?, 
                    usage_count = ?, is_favorite = ?
                WHERE id = ?
            '''
            
            params = (
                snippet.title,
                snippet.content,
                snippet.category,
                snippet.tags,
                snippet.description,
                snippet.language,
                datetime.now(),
                snippet.usage_count,
                int(snippet.is_favorite),
                snippet.id
            )
            
            affected_rows = self.db_manager.execute_update(query, params)
            
            if affected_rows == 0:
                raise NotFoundError(f"Snippet with id {snippet.id} not found")
            
            self.logger.info(f"Updated snippet with id: {snippet.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update snippet {snippet.id}: {e}")
            raise DatabaseError(f"スニペット更新エラー: {e}")
    
    def delete(self, snippet_id: int) -> bool:
        """
        スニペットを削除
        
        Args:
            snippet_id: 削除するスニペットのID
            
        Returns:
            削除成功の可否
        """
        try:
            query = "DELETE FROM snippets WHERE id = ?"
            affected_rows = self.db_manager.execute_update(query, (snippet_id,))
            
            if affected_rows == 0:
                raise NotFoundError(f"Snippet with id {snippet_id} not found")
            
            self.logger.info(f"Deleted snippet with id: {snippet_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete snippet {snippet_id}: {e}")
            raise DatabaseError(f"スニペット削除エラー: {e}")
    
    def list_all(self, limit: int = 100, offset: int = 0, 
                 order_by: str = "updated_at DESC") -> List[Snippet]:
        """
        全スニペットを取得
        
        Args:
            limit: 取得件数の上限
            offset: オフセット
            order_by: ソート順
            
        Returns:
            Snippetオブジェクトのリスト
        """
        try:
            # SQLインジェクション対策：order_byを検証
            valid_orders = {
                "updated_at DESC": "updated_at DESC",
                "updated_at ASC": "updated_at ASC",
                "created_at DESC": "created_at DESC",
                "created_at ASC": "created_at ASC",
                "usage_count DESC": "usage_count DESC",
                "title ASC": "title ASC"
            }
            order_by = valid_orders.get(order_by, "updated_at DESC")
            
            query = f'''
                SELECT * FROM snippets 
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            '''
            
            rows = self.db_manager.execute_query(query, (limit, offset))
            return [self._row_to_snippet(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to list snippets: {e}")
            raise DatabaseError(f"スニペット一覧取得エラー: {e}")
    
    def search(self, keyword: str = "", category: str = None, 
              tags: str = None, limit: int = 100) -> SearchResult:
        """
        スニペットを検索（FTSを使わない簡易版）
        
        Args:
            keyword: 検索キーワード
            category: カテゴリフィルタ
            tags: タグフィルタ
            limit: 結果の上限数
            
        Returns:
            SearchResultオブジェクト
        """
        start_time = time.time()
        
        try:
            # 検索条件の構築
            conditions = []
            params = []
            
            # キーワード検索（通常のLIKE検索）
            if keyword and len(keyword) >= SEARCH_CONFIG.get('min_keyword_length', 2):
                conditions.append('''
                    (title LIKE ? OR content LIKE ? OR 
                     tags LIKE ? OR description LIKE ?)
                ''')
                keyword_param = f'%{keyword}%'
                params.extend([keyword_param] * 4)
            
            # カテゴリフィルタ
            if category and category != "すべて":
                conditions.append("category = ?")
                params.append(category)
            
            # タグフィルタ
            if tags:
                tag_conditions = []
                for tag in tags.split(','):
                    tag = tag.strip()
                    if tag:
                        tag_conditions.append("tags LIKE ?")
                        params.append(f'%{tag}%')
                if tag_conditions:
                    conditions.append(f"({' OR '.join(tag_conditions)})")
            
            # クエリ構築
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f'''
                SELECT *
                FROM snippets 
                WHERE {where_clause}
                ORDER BY usage_count DESC, updated_at DESC
                LIMIT ?
            '''
            
            params.append(limit)
            
            # 検索実行
            rows = self.db_manager.execute_query(query, params)
            snippets = [self._row_to_snippet(row) for row in rows]
            
            # 検索履歴を保存
            if keyword:
                self._save_search_history(keyword, len(snippets))
            
            search_time = time.time() - start_time
            
            return SearchResult(
                snippets=snippets,
                total_count=len(snippets),
                search_time=search_time,
                query=keyword,
                category_filter=category
            )
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            # エラーでも空の結果を返す
            return SearchResult(
                snippets=[],
                total_count=0,
                search_time=0,
                query=keyword,
                category_filter=category
            )
    
    def search_by_category(self, category: str, limit: int = 100) -> List[Snippet]:
        """
        カテゴリでスニペットを検索
        
        Args:
            category: カテゴリ名
            limit: 取得件数の上限
            
        Returns:
            Snippetオブジェクトのリスト
        """
        try:
            query = '''
                SELECT * FROM snippets 
                WHERE category = ?
                ORDER BY usage_count DESC, updated_at DESC
                LIMIT ?
            '''
            
            rows = self.db_manager.execute_query(query, (category, limit))
            return [self._row_to_snippet(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Category search failed: {e}")
            raise DatabaseError(f"カテゴリ検索エラー: {e}")
    
    def get_most_used(self, limit: int = 5) -> List[Snippet]:
        """
        よく使うスニペットを取得
        
        Args:
            limit: 取得件数
            
        Returns:
            Snippetオブジェクトのリスト
        """
        try:
            query = '''
                SELECT * FROM snippets 
                WHERE usage_count > 0
                ORDER BY usage_count DESC
                LIMIT ?
            '''
            
            rows = self.db_manager.execute_query(query, (limit,))
            return [self._row_to_snippet(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to get most used snippets: {e}")
            raise DatabaseError(f"使用頻度取得エラー: {e}")
    
    def get_favorites(self) -> List[Snippet]:
        """
        お気に入りスニペットを取得
        
        Returns:
            Snippetオブジェクトのリスト
        """
        try:
            query = '''
                SELECT * FROM snippets 
                WHERE is_favorite = 1
                ORDER BY updated_at DESC
            '''
            
            rows = self.db_manager.execute_query(query)
            return [self._row_to_snippet(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to get favorites: {e}")
            raise DatabaseError(f"お気に入り取得エラー: {e}")
    
    def increment_usage(self, snippet_id: int) -> bool:
        """
        使用回数をインクリメント
        
        Args:
            snippet_id: スニペットID
            
        Returns:
            更新成功の可否
        """
        try:
            query = '''
                UPDATE snippets 
                SET usage_count = usage_count + 1
                WHERE id = ?
            '''
            
            affected_rows = self.db_manager.execute_update(query, (snippet_id,))
            
            if affected_rows == 0:
                raise NotFoundError(f"Snippet with id {snippet_id} not found")
            
            self.logger.info(f"Incremented usage for snippet {snippet_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to increment usage: {e}")
            raise DatabaseError(f"使用回数更新エラー: {e}")
    
    def toggle_favorite(self, snippet_id: int) -> bool:
        """
        お気に入り状態を切り替え
        
        Args:
            snippet_id: スニペットID
            
        Returns:
            新しいお気に入り状態
        """
        try:
            # 現在の状態を取得
            snippet = self.read(snippet_id)
            if not snippet:
                raise NotFoundError(f"Snippet with id {snippet_id} not found")
            
            # 状態を反転
            new_state = not snippet.is_favorite
            
            query = '''
                UPDATE snippets 
                SET is_favorite = ?
                WHERE id = ?
            '''
            
            self.db_manager.execute_update(query, (int(new_state), snippet_id))
            
            self.logger.info(f"Toggled favorite for snippet {snippet_id}: {new_state}")
            return new_state
            
        except Exception as e:
            self.logger.error(f"Failed to toggle favorite: {e}")
            raise DatabaseError(f"お気に入り更新エラー: {e}")
    
    def get_categories_with_count(self) -> List[Category]:
        """
        カテゴリとスニペット数を取得
        
        Returns:
            Categoryオブジェクトのリスト
        """
        try:
            query = '''
                SELECT c.*, COUNT(s.id) as snippet_count
                FROM categories c
                LEFT JOIN snippets s ON c.name = s.category
                GROUP BY c.id
                ORDER BY c.display_order
            '''
            
            rows = self.db_manager.execute_query(query)
            categories = []
            
            for row in rows:
                category = Category(
                    id=row['id'],
                    name=row['name'],
                    icon=row['icon'],
                    display_order=row['display_order'],
                    snippet_count=row['snippet_count']
                )
                categories.append(category)
            
            return categories
            
        except Exception as e:
            self.logger.error(f"Failed to get categories: {e}")
            raise DatabaseError(f"カテゴリ取得エラー: {e}")
    
    def _row_to_snippet(self, row: dict) -> Snippet:
        """
        データベース行をSnippetオブジェクトに変換
        
        Args:
            row: データベース行
            
        Returns:
            Snippetオブジェクト
        """
        return Snippet(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            category=row['category'],
            tags=row['tags'],
            description=row['description'],
            language=row['language'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            usage_count=row['usage_count'],
            is_favorite=bool(row['is_favorite'])
        )
    
    def _save_search_history(self, query: str, result_count: int):
        """
        検索履歴を保存
        
        Args:
            query: 検索クエリ
            result_count: 結果件数
        """
        try:
            insert_query = '''
                INSERT INTO search_history (query, result_count)
                VALUES (?, ?)
            '''
            self.db_manager.execute_update(insert_query, (query, result_count))
        except Exception as e:
            # 検索履歴の保存失敗は警告レベル
            self.logger.warning(f"Failed to save search history: {e}")