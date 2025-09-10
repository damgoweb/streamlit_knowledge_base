"""
データベースファクトリー
環境に応じて適切なデータベースマネージャーを返す
"""
import os
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_CONFIG


def get_database_manager():
    """
    環境に応じて適切なデータベースマネージャーを返す
    
    Returns:
        DatabaseManager or SupabaseManager: データベースマネージャーインスタンス
    """
    db_type = DATABASE_CONFIG.get('db_type', 'sqlite')
    
    if db_type == 'supabase':
        from database.supabase_manager import SupabaseManager
        return SupabaseManager()
    else:
        from database.db_manager import DatabaseManager
        return DatabaseManager()


# シングルトンインスタンス
_db_manager_instance = None


def get_db_manager_instance():
    """
    データベースマネージャーのシングルトンインスタンスを取得
    
    Returns:
        DatabaseManager or SupabaseManager: データベースマネージャーインスタンス
    """
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = get_database_manager()
    return _db_manager_instance