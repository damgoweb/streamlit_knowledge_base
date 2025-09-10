"""
スニペットサービス
ビジネスロジックとバリデーションを担当
"""
import json
import csv
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import sys
from io import StringIO

# プロジェクトルートからのimport
sys.path.append(str(Path(__file__).parent.parent))
from database.models import Snippet, Category, SearchResult, Statistics, ValidationError, NotFoundError
from repository.snippet_repo import SnippetRepository
from database.db_manager import DatabaseManager
from utils.validators import SnippetValidator
from config import APP_CONFIG, SEARCH_CONFIG
from utils.logger import app_logger


class SnippetService:
    """
    ビジネスロジック層
    リポジトリ層の上位に位置し、バリデーション、
    複雑なビジネスロジック、データ変換などを担当
    """
    
    def __init__(self, repository: SnippetRepository):
        """
        SnippetServiceの初期化
        
        Args:
            repository: SnippetRepositoryインスタンス
        """
        self.repository = repository
        self.validator = SnippetValidator()
        self.logger = app_logger
    
    def add_snippet(self, 
                   title: str, 
                   content: str, 
                   category: str,
                   tags: Optional[str] = None,
                   description: Optional[str] = None,
                   language: str = "text") -> Tuple[bool, str, Optional[int]]:
        """
        スニペットを追加（バリデーション付き）
        
        Args:
            title: タイトル
            content: コンテンツ
            category: カテゴリ
            tags: タグ（カンマ区切り）
            description: 説明
            language: 言語
            
        Returns:
            (success, message, snippet_id)のタプル
        """
        try:
            # 入力値のサニタイズ
            title = self.validator.sanitize_input(title)
            content = self.validator.sanitize_input(content, allow_newlines=True)
            category = self.validator.sanitize_input(category)
            
            if tags:
                tags = self.validator.sanitize_input(tags)
            if description:
                description = self.validator.sanitize_input(description, allow_newlines=True)
            
            # バリデーション
            is_valid, error_msg = self.validator.validate_snippet(
                title=title,
                content=content,
                category=category,
                language=language
            )
            
            if not is_valid:
                return False, error_msg, None
            
            # タグの正規化
            if tags:
                tags = self._normalize_tags(tags)
            
            # Snippetオブジェクト作成
            snippet = Snippet(
                title=title,
                content=content,
                category=category,
                tags=tags,
                description=description,
                language=language
            )
            
            # データベースに保存
            snippet_id = self.repository.create(snippet)
            
            self.logger.info(f"Added snippet: {title} (ID: {snippet_id})")
            return True, "スニペットを追加しました", snippet_id
            
        except Exception as e:
            self.logger.error(f"Failed to add snippet: {e}")
            return False, f"追加に失敗しました: {str(e)}", None
    
    def get_snippet(self, snippet_id: int) -> Optional[Snippet]:
        """
        スニペットを取得
        
        Args:
            snippet_id: スニペットID
            
        Returns:
            Snippetオブジェクト（見つからない場合はNone）
        """
        try:
            snippet = self.repository.read(snippet_id)
            if snippet:
                # 使用回数をインクリメント
                self.repository.increment_usage(snippet_id)
            return snippet
        except Exception as e:
            self.logger.error(f"Failed to get snippet {snippet_id}: {e}")
            return None
    
    def update_snippet(self,
                      snippet_id: int,
                      title: str,
                      content: str,
                      category: str,
                      tags: Optional[str] = None,
                      description: Optional[str] = None,
                      language: str = "text") -> Tuple[bool, str]:
        """
        スニペットを更新
        
        Args:
            snippet_id: 更新対象のID
            title: タイトル
            content: コンテンツ
            category: カテゴリ
            tags: タグ
            description: 説明
            language: 言語
            
        Returns:
            (success, message)のタプル
        """
        try:
            # 既存のスニペットを取得
            existing = self.repository.read(snippet_id)
            if not existing:
                return False, "スニペットが見つかりません"
            
            # 入力値のサニタイズ
            title = self.validator.sanitize_input(title)
            content = self.validator.sanitize_input(content, allow_newlines=True)
            category = self.validator.sanitize_input(category)
            
            if tags:
                tags = self.validator.sanitize_input(tags)
                tags = self._normalize_tags(tags)
            if description:
                description = self.validator.sanitize_input(description, allow_newlines=True)
            
            # バリデーション
            is_valid, error_msg = self.validator.validate_snippet(
                title=title,
                content=content,
                category=category,
                language=language
            )
            
            if not is_valid:
                return False, error_msg
            
            # 更新用のSnippetオブジェクト作成
            updated_snippet = Snippet(
                id=snippet_id,
                title=title,
                content=content,
                category=category,
                tags=tags,
                description=description,
                language=language,
                created_at=existing.created_at,
                usage_count=existing.usage_count,
                is_favorite=existing.is_favorite
            )
            
            # データベースを更新
            self.repository.update(updated_snippet)
            
            self.logger.info(f"Updated snippet: {snippet_id}")
            return True, "スニペットを更新しました"
            
        except Exception as e:
            self.logger.error(f"Failed to update snippet {snippet_id}: {e}")
            return False, f"更新に失敗しました: {str(e)}"
    
    def delete_snippet(self, snippet_id: int) -> Tuple[bool, str]:
        """
        スニペットを削除
        
        Args:
            snippet_id: 削除対象のID
            
        Returns:
            (success, message)のタプル
        """
        try:
            self.repository.delete(snippet_id)
            self.logger.info(f"Deleted snippet: {snippet_id}")
            return True, "スニペットを削除しました"
        except NotFoundError:
            return False, "スニペットが見つかりません"
        except Exception as e:
            self.logger.error(f"Failed to delete snippet {snippet_id}: {e}")
            return False, f"削除に失敗しました: {str(e)}"
    
    def list_snippets(self, 
                     page: int = 1,
                     per_page: Optional[int] = None,
                     order_by: str = "updated_at DESC") -> Tuple[List[Snippet], int]:
        """
        スニペット一覧を取得（ページネーション対応）
        
        Args:
            page: ページ番号（1から開始）
            per_page: 1ページあたりの件数
            order_by: ソート順
            
        Returns:
            (スニペットリスト, 総件数)のタプル
        """
        try:
            if per_page is None:
                per_page = APP_CONFIG['page_size']
            
            offset = (page - 1) * per_page
            
            # 総件数を取得
            all_snippets = self.repository.list_all(limit=10000, offset=0)
            total_count = len(all_snippets)
            
            # ページ分のデータを取得
            snippets = self.repository.list_all(
                limit=per_page,
                offset=offset,
                order_by=order_by
            )
            
            return snippets, total_count
            
        except Exception as e:
            self.logger.error(f"Failed to list snippets: {e}")
            return [], 0
    
    def search_snippets(self, 
                       query: str = "",
                       category: Optional[str] = None,
                       tags: Optional[str] = None,
                       page: int = 1,
                       per_page: Optional[int] = None) -> SearchResult:
        """
        高度な検索（複数条件、ランキング）
        
        Args:
            query: 検索クエリ
            category: カテゴリフィルタ
            tags: タグフィルタ
            page: ページ番号
            per_page: 1ページあたりの件数
            
        Returns:
            SearchResultオブジェクト
        """
        try:
            # 検索クエリの正規化
            if query:
                query = self.validator.sanitize_input(query)
                
                # 最小文字数チェック
                if len(query) < SEARCH_CONFIG['min_keyword_length']:
                    return SearchResult(
                        snippets=[],
                        total_count=0,
                        search_time=0,
                        query=query,
                        category_filter=category
                    )
            
            # リポジトリで検索実行
            result = self.repository.search(
                keyword=query,
                category=category,
                tags=tags,
                limit=APP_CONFIG['max_search_results']
            )
            
            # ページネーション適用
            if per_page is None:
                per_page = APP_CONFIG['page_size']
            
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            result.snippets = result.snippets[start_idx:end_idx]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return SearchResult(
                snippets=[],
                total_count=0,
                search_time=0,
                query=query,
                category_filter=category
            )
    
    def increment_usage(self, snippet_id: int) -> bool:
        """
        使用回数をインクリメント
        
        Args:
            snippet_id: スニペットID
            
        Returns:
            成功の可否
        """
        try:
            return self.repository.increment_usage(snippet_id)
        except Exception as e:
            self.logger.error(f"Failed to increment usage for {snippet_id}: {e}")
            return False
    
    def toggle_favorite(self, snippet_id: int) -> Tuple[bool, bool]:
        """
        お気に入り状態を切り替え
        
        Args:
            snippet_id: スニペットID
            
        Returns:
            (成功の可否, 新しい状態)のタプル
        """
        try:
            new_state = self.repository.toggle_favorite(snippet_id)
            return True, new_state
        except Exception as e:
            self.logger.error(f"Failed to toggle favorite for {snippet_id}: {e}")
            return False, False
    
    def get_statistics(self) -> Statistics:
        """
        統計情報を取得
        
        Returns:
            Statisticsオブジェクト
        """
        try:
            # 全スニペット取得
            all_snippets = self.repository.list_all(limit=10000)
            
            # カテゴリ別統計
            categories = self.repository.get_categories_with_count()
            category_dist = {
                cat.name: cat.snippet_count 
                for cat in categories
            }
            
            # よく使うスニペットTOP5
            most_used = self.repository.get_most_used(limit=5)
            
            # 最近のスニペット
            recent = self.repository.list_all(
                limit=5,
                order_by="created_at DESC"
            )
            
            # 総使用回数
            total_usage = sum(s.usage_count for s in all_snippets)
            
            return Statistics(
                total_snippets=len(all_snippets),
                total_categories=len(categories),
                total_usage=total_usage,
                most_used_snippets=most_used,
                category_distribution=category_dist,
                recent_snippets=recent
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return Statistics()
    
    def export_snippets(self, format: str = 'json') -> Tuple[bool, str, Optional[str]]:
        """
        スニペットをエクスポート
        
        Args:
            format: エクスポート形式（'json' or 'csv'）
            
        Returns:
            (success, message, data)のタプル
        """
        try:
            snippets = self.repository.list_all(limit=10000)
            
            if format == 'json':
                data = self._export_to_json(snippets)
            elif format == 'csv':
                data = self._export_to_csv(snippets)
            else:
                return False, "サポートされていない形式です", None
            
            self.logger.info(f"Exported {len(snippets)} snippets to {format}")
            return True, f"{len(snippets)}件のスニペットをエクスポートしました", data
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return False, f"エクスポートに失敗しました: {str(e)}", None
    
    def import_snippets(self, data: str, format: str = 'json') -> Tuple[bool, str, int]:
        """
        スニペットをインポート
        
        Args:
            data: インポートデータ
            format: データ形式（'json' or 'csv'）
            
        Returns:
            (success, message, imported_count)のタプル
        """
        try:
            if format == 'json':
                snippets = self._import_from_json(data)
            elif format == 'csv':
                snippets = self._import_from_csv(data)
            else:
                return False, "サポートされていない形式です", 0
            
            imported_count = 0
            errors = []
            
            for snippet_data in snippets:
                try:
                    # バリデーション
                    is_valid, error_msg = self.validator.validate_snippet(
                        title=snippet_data.get('title', ''),
                        content=snippet_data.get('content', ''),
                        category=snippet_data.get('category', ''),
                        language=snippet_data.get('language', 'text')
                    )
                    
                    if not is_valid:
                        errors.append(f"{snippet_data.get('title', 'Unknown')}: {error_msg}")
                        continue
                    
                    # Snippetオブジェクト作成
                    snippet = Snippet(
                        title=snippet_data['title'],
                        content=snippet_data['content'],
                        category=snippet_data['category'],
                        tags=snippet_data.get('tags'),
                        description=snippet_data.get('description'),
                        language=snippet_data.get('language', 'text')
                    )
                    
                    # 重複チェック（タイトルとカテゴリで判定）
                    existing = self.repository.search(
                        keyword=snippet.title,
                        category=snippet.category
                    )
                    
                    if existing.snippets and any(
                        s.title == snippet.title for s in existing.snippets
                    ):
                        errors.append(f"{snippet.title}: 既に存在します")
                        continue
                    
                    # インポート実行
                    self.repository.create(snippet)
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"インポートエラー: {str(e)}")
            
            message = f"{imported_count}件のスニペットをインポートしました"
            if errors:
                message += f"\n警告: {len(errors)}件のエラー"
                for error in errors[:5]:  # 最初の5件のみ表示
                    message += f"\n- {error}"
            
            self.logger.info(f"Imported {imported_count} snippets")
            return True, message, imported_count
            
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            return False, f"インポートに失敗しました: {str(e)}", 0
    
    def get_categories(self) -> List[Category]:
        """
        カテゴリ一覧を取得
        
        Returns:
            Categoryオブジェクトのリスト
        """
        try:
            return self.repository.get_categories_with_count()
        except Exception as e:
            self.logger.error(f"Failed to get categories: {e}")
            return []
    
    def get_favorites(self) -> List[Snippet]:
        """
        お気に入りスニペットを取得
        
        Returns:
            Snippetオブジェクトのリスト
        """
        try:
            return self.repository.get_favorites()
        except Exception as e:
            self.logger.error(f"Failed to get favorites: {e}")
            return []
    
    def _normalize_tags(self, tags: str) -> str:
        """
        タグを正規化
        
        Args:
            tags: タグ文字列
            
        Returns:
            正規化されたタグ文字列
        """
        if not tags:
            return ""
        
        # カンマで分割して各タグをトリム
        tag_list = [tag.strip() for tag in tags.split(',')]
        # 空のタグを除去
        tag_list = [tag for tag in tag_list if tag]
        # 重複を除去
        tag_list = list(dict.fromkeys(tag_list))
        # カンマ区切りで結合
        return ', '.join(tag_list)
    
    def _export_to_json(self, snippets: List[Snippet]) -> str:
        """
        JSON形式でエクスポート
        
        Args:
            snippets: スニペットリスト
            
        Returns:
            JSON文字列
        """
        export_data = {
            'version': APP_CONFIG['version'],
            'exported_at': datetime.now().isoformat(),
            'total_count': len(snippets),
            'snippets': [s.to_dict() for s in snippets]
        }
        
        return json.dumps(export_data, ensure_ascii=False, indent=2)
    
    def _export_to_csv(self, snippets: List[Snippet]) -> str:
        """
        CSV形式でエクスポート
        
        Args:
            snippets: スニペットリスト
            
        Returns:
            CSV文字列
        """
        output = StringIO()
        fieldnames = ['title', 'content', 'category', 'tags', 
                     'description', 'language', 'usage_count']
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for snippet in snippets:
            writer.writerow({
                'title': snippet.title,
                'content': snippet.content,
                'category': snippet.category,
                'tags': snippet.tags or '',
                'description': snippet.description or '',
                'language': snippet.language,
                'usage_count': snippet.usage_count
            })
        
        return output.getvalue()
    
    def _import_from_json(self, data: str) -> List[Dict]:
        """
        JSON形式からインポート
        
        Args:
            data: JSON文字列
            
        Returns:
            スニペットデータのリスト
        """
        import_data = json.loads(data)
        
        if 'snippets' in import_data:
            return import_data['snippets']
        elif isinstance(import_data, list):
            return import_data
        else:
            raise ValueError("Invalid JSON format")
    
    def _import_from_csv(self, data: str) -> List[Dict]:
        """
        CSV形式からインポート
        
        Args:
            data: CSV文字列
            
        Returns:
            スニペットデータのリスト
        """
        input_data = StringIO(data)
        reader = csv.DictReader(input_data)
        
        snippets = []
        for row in reader:
            snippets.append({
                'title': row.get('title', ''),
                'content': row.get('content', ''),
                'category': row.get('category', ''),
                'tags': row.get('tags', ''),
                'description': row.get('description', ''),
                'language': row.get('language', 'text')
            })
        
        return snippets