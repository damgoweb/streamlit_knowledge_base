"""
データベース管理クラス
SQLiteデータベースの接続、初期化、トランザクション管理を担当
"""
import sqlite3
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Any
from contextlib import contextmanager
import logging

# プロジェクトルートからのimport
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_CONFIG, CATEGORIES
from utils.logger import app_logger


class DatabaseManager:
    """
    データベース接続とトランザクション管理
    
    SQLiteデータベースへの接続、テーブル作成、
    バックアップ、トランザクション管理を行う
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        DatabaseManagerの初期化
        
        Args:
            db_path: データベースファイルのパス（Noneの場合はconfig.pyから取得）
        """
        self.db_path = db_path or DATABASE_CONFIG['db_path']
        self.backup_dir = DATABASE_CONFIG['backup_dir']
        self.logger = app_logger
        
        # データベースディレクトリが存在しない場合は作成
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # バックアップディレクトリが存在しない場合は作成
        if DATABASE_CONFIG['auto_backup']:
            Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
        
        # データベース初期化
        self.init_database()
        self.logger.info(f"DatabaseManager initialized with db_path: {self.db_path}")
    
    def get_connection(self) -> sqlite3.Connection:
        """
        データベース接続を取得
        
        Returns:
            sqlite3.Connection: データベース接続オブジェクト
        """
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=10.0,  # タイムアウト10秒
                isolation_level=None  # 自動コミットモード
            )
            # Row Factoryを設定（辞書形式でのアクセスを可能に）
            conn.row_factory = sqlite3.Row
            # 外部キー制約を有効化
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise DatabaseError(f"データベース接続エラー: {e}")
    
    @contextmanager
    def get_db(self):
        """
        コンテキストマネージャーとしてデータベース接続を提供
        
        Usage:
            with db_manager.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
        """
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        """
        データベースの初期化
        必要なテーブルとインデックスを作成
        """
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                # snippetsテーブル作成
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS snippets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        category TEXT NOT NULL,
                        tags TEXT,
                        description TEXT,
                        language TEXT DEFAULT 'text',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        usage_count INTEGER DEFAULT 0,
                        is_favorite INTEGER DEFAULT 0,
                        CHECK (language IN ('text', 'bash', 'python', 'sql', 
                                          'javascript', 'yaml', 'json', 
                                          'dockerfile', 'conf', 'xml'))
                    )
                ''')
                
                # categoriesテーブル作成
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        icon TEXT DEFAULT '📁',
                        display_order INTEGER DEFAULT 0
                    )
                ''')
                
                # search_historyテーブル作成
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS search_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT NOT NULL,
                        searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        result_count INTEGER DEFAULT 0
                    )
                ''')
                
                # インデックス作成
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_snippets_category 
                    ON snippets(category)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_snippets_usage 
                    ON snippets(usage_count DESC)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_snippets_updated 
                    ON snippets(updated_at DESC)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_snippets_favorite 
                    ON snippets(is_favorite DESC)
                ''')
                
                # 全文検索用の仮想テーブル（FTS5）
                cursor.execute('''
                    CREATE VIRTUAL TABLE IF NOT EXISTS snippets_fts USING fts5(
                        title, content, tags, description,
                        content=snippets,
                        content_rowid=id
                    )
                ''')
                
                # FTS用のトリガー（INSERT時）
                cursor.execute('''
                    CREATE TRIGGER IF NOT EXISTS snippets_fts_insert 
                    AFTER INSERT ON snippets BEGIN
                        INSERT INTO snippets_fts(rowid, title, content, tags, description)
                        VALUES (new.id, new.title, new.content, new.tags, new.description);
                    END
                ''')
                
                # FTS用のトリガー（UPDATE時）
                cursor.execute('''
                    CREATE TRIGGER IF NOT EXISTS snippets_fts_update 
                    AFTER UPDATE ON snippets BEGIN
                        UPDATE snippets_fts 
                        SET title = new.title, 
                            content = new.content,
                            tags = new.tags,
                            description = new.description
                        WHERE rowid = new.id;
                    END
                ''')
                
                # FTS用のトリガー（DELETE時）
                cursor.execute('''
                    CREATE TRIGGER IF NOT EXISTS snippets_fts_delete 
                    AFTER DELETE ON snippets BEGIN
                        DELETE FROM snippets_fts WHERE rowid = old.id;
                    END
                ''')
                
                # 初期カテゴリデータの挿入
                self._init_categories(cursor)
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"データベース初期化エラー: {e}")
    
    def _init_categories(self, cursor: sqlite3.Cursor):
        """
        初期カテゴリデータを挿入
        
        Args:
            cursor: SQLiteカーソル
        """
        for category in CATEGORIES:
            cursor.execute('''
                INSERT OR IGNORE INTO categories (name, icon, display_order)
                VALUES (?, ?, ?)
            ''', (category['name'], category['icon'], category['order']))
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """
        SELECTクエリを実行
        
        Args:
            query: SQL文
            params: パラメータのタプル
            
        Returns:
            クエリ結果のリスト
        """
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Query execution failed: {query}, params: {params}, error: {e}")
            raise DatabaseError(f"クエリ実行エラー: {e}")
    
    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """
        INSERT/UPDATE/DELETEクエリを実行
        
        Args:
            query: SQL文
            params: パラメータのタプル
            
        Returns:
            影響を受けた行数
        """
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN")
                cursor.execute(query, params)
                affected_rows = cursor.rowcount
                conn.commit()
                return affected_rows
        except sqlite3.Error as e:
            self.logger.error(f"Update execution failed: {query}, params: {params}, error: {e}")
            raise DatabaseError(f"更新クエリ実行エラー: {e}")
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """
        複数のINSERT/UPDATEを一括実行
        
        Args:
            query: SQL文
            params_list: パラメータのタプルのリスト
            
        Returns:
            影響を受けた行数
        """
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN")
                cursor.executemany(query, params_list)
                affected_rows = cursor.rowcount
                conn.commit()
                return affected_rows
        except sqlite3.Error as e:
            self.logger.error(f"Batch execution failed: {query}, error: {e}")
            raise DatabaseError(f"バッチ実行エラー: {e}")
    
    def backup_database(self, backup_name: Optional[str] = None) -> str:
        """
        データベースのバックアップを作成
        
        Args:
            backup_name: バックアップファイル名（Noneの場合は自動生成）
            
        Returns:
            バックアップファイルのパス
        """
        try:
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"knowledge_base_backup_{timestamp}.db"
            
            backup_path = Path(self.backup_dir) / backup_name
            
            # SQLiteのバックアップAPI使用
            with self.get_db() as source_conn:
                with sqlite3.connect(backup_path) as backup_conn:
                    source_conn.backup(backup_conn)
            
            self.logger.info(f"Database backed up to: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            raise DatabaseError(f"バックアップエラー: {e}")
    
    def restore_database(self, backup_path: str) -> bool:
        """
        バックアップからデータベースを復元
        
        Args:
            backup_path: バックアップファイルのパス
            
        Returns:
            復元成功の可否
        """
        try:
            if not Path(backup_path).exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # 現在のDBをバックアップ
            temp_backup = self.backup_database("temp_before_restore.db")
            
            try:
                # バックアップから復元
                shutil.copy2(backup_path, self.db_path)
                self.logger.info(f"Database restored from: {backup_path}")
                return True
            except Exception as e:
                # 復元失敗時は元に戻す
                shutil.copy2(temp_backup, self.db_path)
                raise e
                
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            raise DatabaseError(f"復元エラー: {e}")
    
    def get_table_info(self, table_name: str) -> List[dict]:
        """
        テーブル情報を取得
        
        Args:
            table_name: テーブル名
            
        Returns:
            カラム情報のリスト
        """
        query = f"PRAGMA table_info({table_name})"
        rows = self.execute_query(query)
        return [dict(row) for row in rows]
    
    def vacuum(self):
        """
        データベースの最適化（VACUUM）を実行
        不要な領域を解放し、データベースファイルを圧縮
        """
        try:
            with self.get_db() as conn:
                conn.execute("VACUUM")
                self.logger.info("Database vacuumed successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Vacuum failed: {e}")
            raise DatabaseError(f"最適化エラー: {e}")


# カスタム例外クラス
class DatabaseError(Exception):
    """データベース関連のエラー"""
    pass