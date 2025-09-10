"""
データモデル定義
スニペット、カテゴリ、検索結果のデータクラス
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import json


@dataclass
class Snippet:
    """
    スニペット（コード断片）のデータモデル
    
    Attributes:
        id: スニペットの一意識別子
        title: スニペットのタイトル
        content: コード/コマンドの内容
        category: カテゴリ（Docker, Git, SQL等）
        tags: タグ（カンマ区切りの文字列）
        description: 説明文
        language: 構文ハイライト用の言語指定
        created_at: 作成日時
        updated_at: 更新日時
        usage_count: 使用回数
        is_favorite: お気に入りフラグ
    """
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    category: str = ""
    tags: Optional[str] = None
    description: Optional[str] = None
    language: str = "text"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    usage_count: int = 0
    is_favorite: bool = False
    
    def __post_init__(self):
        """データ初期化後の処理"""
        # 日時文字列をdatetimeオブジェクトに変換
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'tags': self.tags,
            'description': self.description,
            'language': self.language,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'usage_count': self.usage_count,
            'is_favorite': self.is_favorite
        }
    
    def to_json(self) -> str:
        """JSON形式に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Snippet':
        """辞書からインスタンスを生成"""
        return cls(**data)
    
    @classmethod
    def from_db_row(cls, row: tuple, columns: List[str]) -> 'Snippet':
        """データベースの行データからインスタンスを生成"""
        data = dict(zip(columns, row))
        return cls.from_dict(data)
    
    def get_tags_list(self) -> List[str]:
        """タグをリスト形式で取得"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',')]
    
    def set_tags_from_list(self, tags_list: List[str]):
        """リストからタグを設定"""
        self.tags = ', '.join(tags_list) if tags_list else None
    
    def validate(self) -> tuple[bool, str]:
        """
        バリデーション
        
        Returns:
            (is_valid, error_message)のタプル
        """
        if not self.title:
            return False, "タイトルは必須です"
        if len(self.title) > 200:
            return False, "タイトルは200文字以内で入力してください"
        if not self.content:
            return False, "コンテンツは必須です"
        if not self.category:
            return False, "カテゴリは必須です"
        if self.language not in ['text', 'bash', 'python', 'sql', 'javascript', 
                                 'yaml', 'json', 'dockerfile', 'conf', 'xml']:
            return False, "無効な言語が指定されています"
        return True, ""


@dataclass
class Category:
    """
    カテゴリのデータモデル
    
    Attributes:
        id: カテゴリID
        name: カテゴリ名
        icon: 表示用アイコン（絵文字）
        display_order: 表示順序
        snippet_count: このカテゴリのスニペット数
    """
    id: Optional[int] = None
    name: str = ""
    icon: str = "📁"
    display_order: int = 0
    snippet_count: int = 0
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'display_order': self.display_order,
            'snippet_count': self.snippet_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Category':
        """辞書からインスタンスを生成"""
        return cls(**data)
    
    def get_display_name(self) -> str:
        """アイコン付きの表示名を取得"""
        return f"{self.icon} {self.name}"


@dataclass
class SearchResult:
    """
    検索結果のデータモデル
    
    Attributes:
        snippets: 検索結果のスニペットリスト
        total_count: 総件数
        search_time: 検索にかかった時間（秒）
        query: 検索クエリ
        category_filter: カテゴリフィルタ
    """
    snippets: List[Snippet] = field(default_factory=list)
    total_count: int = 0
    search_time: float = 0.0
    query: str = ""
    category_filter: Optional[str] = None
    
    def has_results(self) -> bool:
        """検索結果があるかどうか"""
        return self.total_count > 0
    
    def get_summary(self) -> str:
        """検索結果のサマリーを取得"""
        if not self.has_results():
            return "検索結果が見つかりませんでした"
        
        summary = f"検索結果: {self.total_count}件"
        if self.query:
            summary += f" (キーワード: {self.query})"
        if self.category_filter:
            summary += f" [カテゴリ: {self.category_filter}]"
        summary += f" - {self.search_time:.3f}秒"
        return summary


@dataclass
class Statistics:
    """
    統計情報のデータモデル
    
    Attributes:
        total_snippets: 総スニペット数
        total_categories: 総カテゴリ数
        total_usage: 総使用回数
        most_used_snippets: よく使うスニペット上位
        category_distribution: カテゴリ別分布
    """
    total_snippets: int = 0
    total_categories: int = 0
    total_usage: int = 0
    most_used_snippets: List[Snippet] = field(default_factory=list)
    category_distribution: dict = field(default_factory=dict)
    recent_snippets: List[Snippet] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            'total_snippets': self.total_snippets,
            'total_categories': self.total_categories,
            'total_usage': self.total_usage,
            'most_used_snippets': [s.to_dict() for s in self.most_used_snippets],
            'category_distribution': self.category_distribution,
            'recent_snippets': [s.to_dict() for s in self.recent_snippets]
        }


# エラー定義
class DatabaseError(Exception):
    """データベース関連のエラー"""
    pass


class ValidationError(Exception):
    """バリデーションエラー"""
    pass


class NotFoundError(Exception):
    """リソースが見つからないエラー"""
    pass