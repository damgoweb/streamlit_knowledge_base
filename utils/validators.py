"""
バリデーションユーティリティ
入力値の検証とサニタイズを担当
"""
import re
from typing import Optional, Tuple, List
from pathlib import Path
import sys

# プロジェクトルートからのimport
sys.path.append(str(Path(__file__).parent.parent))
from config import CATEGORIES, LANGUAGES


class SnippetValidator:
    """
    スニペット関連のバリデーションクラス
    """
    
    # 最大文字数の定義
    MAX_TITLE_LENGTH = 200
    MAX_CONTENT_LENGTH = 50000  # 約50KB
    MAX_TAGS_LENGTH = 500
    MAX_DESCRIPTION_LENGTH = 1000
    MIN_TITLE_LENGTH = 1
    MIN_CONTENT_LENGTH = 1
    
    # 危険な文字のパターン
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # スクリプトタグ
        r'javascript:',                 # JavaScriptプロトコル
        r'on\w+\s*=',                  # イベントハンドラ
    ]
    
    def validate_title(self, title: str) -> Tuple[bool, str]:
        """
        タイトルのバリデーション
        
        Args:
            title: タイトル
            
        Returns:
            (is_valid, error_message)のタプル
        """
        if not title or not title.strip():
            return False, "タイトルは必須です"
        
        title = title.strip()
        
        if len(title) < self.MIN_TITLE_LENGTH:
            return False, f"タイトルは{self.MIN_TITLE_LENGTH}文字以上必要です"
        
        if len(title) > self.MAX_TITLE_LENGTH:
            return False, f"タイトルは{self.MAX_TITLE_LENGTH}文字以内で入力してください"
        
        # 特殊文字のチェック（基本的な文字は許可）
        if not self._is_valid_text(title):
            return False, "タイトルに使用できない文字が含まれています"
        
        return True, ""
    
    def validate_content(self, content: str) -> Tuple[bool, str]:
        """
        コンテンツのバリデーション
        
        Args:
            content: コンテンツ
            
        Returns:
            (is_valid, error_message)のタプル
        """
        if not content or not content.strip():
            return False, "コンテンツは必須です"
        
        content = content.strip()
        
        if len(content) < self.MIN_CONTENT_LENGTH:
            return False, f"コンテンツは{self.MIN_CONTENT_LENGTH}文字以上必要です"
        
        if len(content) > self.MAX_CONTENT_LENGTH:
            return False, f"コンテンツは{self.MAX_CONTENT_LENGTH}文字以内で入力してください"
        
        return True, ""
    
    def validate_category(self, category: str) -> Tuple[bool, str]:
        """
        カテゴリのバリデーション
        
        Args:
            category: カテゴリ
            
        Returns:
            (is_valid, error_message)のタプル
        """
        if not category or not category.strip():
            return False, "カテゴリは必須です"
        
        category = category.strip()
        
        # 定義済みカテゴリのチェック
        valid_categories = [cat['name'] for cat in CATEGORIES]
        if category not in valid_categories:
            return False, f"無効なカテゴリです。使用可能: {', '.join(valid_categories)}"
        
        return True, ""
    
    def validate_tags(self, tags: Optional[str]) -> Tuple[bool, str]:
        """
        タグのバリデーション
        
        Args:
            tags: タグ（カンマ区切り）
            
        Returns:
            (is_valid, error_message)のタプル
        """
        if not tags:
            return True, ""  # タグはオプション
        
        if len(tags) > self.MAX_TAGS_LENGTH:
            return False, f"タグは{self.MAX_TAGS_LENGTH}文字以内で入力してください"
        
        # 各タグのバリデーション
        tag_list = [tag.strip() for tag in tags.split(',')]
        
        for tag in tag_list:
            if tag and not self._is_valid_tag(tag):
                return False, f"タグ '{tag}' に使用できない文字が含まれています"
        
        if len(tag_list) > 20:
            return False, "タグは20個以内で指定してください"
        
        return True, ""
    
    def validate_description(self, description: Optional[str]) -> Tuple[bool, str]:
        """
        説明のバリデーション
        
        Args:
            description: 説明
            
        Returns:
            (is_valid, error_message)のタプル
        """
        if not description:
            return True, ""  # 説明はオプション
        
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            return False, f"説明は{self.MAX_DESCRIPTION_LENGTH}文字以内で入力してください"
        
        if not self._is_valid_text(description, allow_newlines=True):
            return False, "説明に使用できない文字が含まれています"
        
        return True, ""
    
    def validate_language(self, language: str) -> Tuple[bool, str]:
        """
        言語のバリデーション
        
        Args:
            language: 言語
            
        Returns:
            (is_valid, error_message)のタプル
        """
        if language not in LANGUAGES:
            return False, f"無効な言語です。使用可能: {', '.join(LANGUAGES)}"
        
        return True, ""
    
    def validate_snippet(self, 
                        title: str,
                        content: str,
                        category: str,
                        tags: Optional[str] = None,
                        description: Optional[str] = None,
                        language: str = "text") -> Tuple[bool, str]:
        """
        スニペット全体のバリデーション
        
        Args:
            title: タイトル
            content: コンテンツ
            category: カテゴリ
            tags: タグ
            description: 説明
            language: 言語
            
        Returns:
            (is_valid, error_message)のタプル
        """
        # タイトル検証
        is_valid, error_msg = self.validate_title(title)
        if not is_valid:
            return False, error_msg
        
        # コンテンツ検証
        is_valid, error_msg = self.validate_content(content)
        if not is_valid:
            return False, error_msg
        
        # カテゴリ検証
        is_valid, error_msg = self.validate_category(category)
        if not is_valid:
            return False, error_msg
        
        # タグ検証
        is_valid, error_msg = self.validate_tags(tags)
        if not is_valid:
            return False, error_msg
        
        # 説明検証
        is_valid, error_msg = self.validate_description(description)
        if not is_valid:
            return False, error_msg
        
        # 言語検証
        is_valid, error_msg = self.validate_language(language)
        if not is_valid:
            return False, error_msg
        
        return True, ""
    
    def sanitize_input(self, 
                      text: str,
                      allow_newlines: bool = False,
                      allow_html: bool = False) -> str:
        """
        入力値をサニタイズ
        
        Args:
            text: サニタイズ対象のテキスト
            allow_newlines: 改行を許可するか
            allow_html: HTMLタグを許可するか
            
        Returns:
            サニタイズされたテキスト
        """
        if not text:
            return ""
        
        # 前後の空白を削除
        text = text.strip()
        
        # HTMLタグを除去（許可されていない場合）
        if not allow_html:
            text = self._remove_html_tags(text)
        
        # 危険なパターンを除去
        for pattern in self.DANGEROUS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 改行の処理
        if not allow_newlines:
            text = text.replace('\n', ' ').replace('\r', ' ')
            # 連続する空白を1つに
            text = re.sub(r'\s+', ' ', text)
        
        # NULL文字を除去
        text = text.replace('\x00', '')
        
        return text
    
    def _is_valid_text(self, text: str, allow_newlines: bool = False) -> bool:
        """
        テキストが有効な文字のみを含むかチェック
        
        Args:
            text: チェック対象のテキスト
            allow_newlines: 改行を許可するか
            
        Returns:
            有効な場合True
        """
        # 基本的な文字（英数字、日本語、一般的な記号）を許可
        if allow_newlines:
            pattern = r'^[\w\s\-_.,:;!?@#$%^&*()\[\]{}<>/\\|`~\'"=+\n\r\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]+$'
        else:
            pattern = r'^[\w\s\-_.,:;!?@#$%^&*()\[\]{}<>/\\|`~\'"=+\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]+$'
        
        return bool(re.match(pattern, text))
    
    def _is_valid_tag(self, tag: str) -> bool:
        """
        タグが有効な文字のみを含むかチェック
        
        Args:
            tag: チェック対象のタグ
            
        Returns:
            有効な場合True
        """
        # タグは英数字、日本語、ハイフン、アンダースコアのみ許可
        pattern = r'^[\w\-_\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]+$'
        return bool(re.match(pattern, tag))
    
    def _remove_html_tags(self, text: str) -> str:
        """
        HTMLタグを除去
        
        Args:
            text: 処理対象のテキスト
            
        Returns:
            HTMLタグが除去されたテキスト
        """
        # HTMLタグを除去（簡易版）
        clean = re.sub('<.*?>', '', text)
        return clean


class SearchValidator:
    """
    検索クエリのバリデーションクラス
    """
    
    MAX_QUERY_LENGTH = 100
    MIN_QUERY_LENGTH = 2
    
    def validate_search_query(self, query: str) -> Tuple[bool, str]:
        """
        検索クエリのバリデーション
        
        Args:
            query: 検索クエリ
            
        Returns:
            (is_valid, error_message)のタプル
        """
        if not query:
            return True, ""  # 空のクエリは許可（全件表示）
        
        query = query.strip()
        
        if query and len(query) < self.MIN_QUERY_LENGTH:
            return False, f"検索キーワードは{self.MIN_QUERY_LENGTH}文字以上必要です"
        
        if len(query) > self.MAX_QUERY_LENGTH:
            return False, f"検索キーワードは{self.MAX_QUERY_LENGTH}文字以内で入力してください"
        
        # SQLインジェクション対策
        dangerous_sql_patterns = [
            r';\s*DROP',
            r';\s*DELETE',
            r';\s*UPDATE',
            r';\s*INSERT',
            r'--',
            r'/\*.*\*/',
            r'UNION\s+SELECT',
            r'OR\s+1\s*=\s*1',
        ]
        
        for pattern in dangerous_sql_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return False, "検索クエリに使用できない文字が含まれています"
        
        return True, ""
    
    def sanitize_search_query(self, query: str) -> str:
        """
        検索クエリをサニタイズ
        
        Args:
            query: 検索クエリ
            
        Returns:
            サニタイズされたクエリ
        """
        if not query:
            return ""
        
        # 前後の空白を削除
        query = query.strip()
        
        # 特殊文字をエスケープ（SQLite FTS5用）
        # FTS5の特殊文字: " * ( ) 
        query = query.replace('"', '""')
        query = query.replace("'", "''")
        
        # 連続する空白を1つに
        query = re.sub(r'\s+', ' ', query)
        
        return query


class FileValidator:
    """
    ファイル関連のバリデーションクラス
    """
    
    # 許可するファイル拡張子
    ALLOWED_EXTENSIONS = {
        'import': ['.json', '.csv'],
        'export': ['.json', '.csv']
    }
    
    # 最大ファイルサイズ（10MB）
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    def validate_import_file(self, 
                           filename: str,
                           file_size: int) -> Tuple[bool, str]:
        """
        インポートファイルのバリデーション
        
        Args:
            filename: ファイル名
            file_size: ファイルサイズ（バイト）
            
        Returns:
            (is_valid, error_message)のタプル
        """
        # ファイル名チェック
        if not filename:
            return False, "ファイル名が指定されていません"
        
        # 拡張子チェック
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS['import']:
            allowed = ', '.join(self.ALLOWED_EXTENSIONS['import'])
            return False, f"サポートされていないファイル形式です。使用可能: {allowed}"
        
        # ファイルサイズチェック
        if file_size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            return False, f"ファイルサイズが大きすぎます。最大: {max_mb}MB"
        
        return True, ""