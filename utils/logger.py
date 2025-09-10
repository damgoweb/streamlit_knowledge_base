"""
ログ設定モジュール
アプリケーション全体のログ設定を管理
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import os

# プロジェクトルートからのimport
sys.path.append(str(Path(__file__).parent.parent))
from config import LOGGING_CONFIG


def setup_logger(name: str) -> logging.Logger:
    """
    ロガーのセットアップ
    
    Args:
        name: ロガー名
        
    Returns:
        設定済みのロガーインスタンス
    """
    logger = logging.getLogger(name)
    
    # 既にハンドラが設定されている場合はスキップ
    if logger.handlers:
        return logger
    
    # ログレベル設定
    log_level = getattr(logging, LOGGING_CONFIG['level'], logging.INFO)
    logger.setLevel(log_level)
    
    # フォーマッタ
    formatter = logging.Formatter(LOGGING_CONFIG['format'])
    
    # コンソールハンドラ（常に追加）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラ（ローカル環境のみ）
    log_file = LOGGING_CONFIG.get('file')
    if log_file is not None:
        try:
            # ログディレクトリ作成
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ローテーティングファイルハンドラ
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=LOGGING_CONFIG.get('max_bytes', 10485760),
                backupCount=LOGGING_CONFIG.get('backup_count', 5),
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # ファイルハンドラの作成に失敗してもアプリは続行
            logger.warning(f"Failed to create file handler: {e}")
    
    # 親ロガーへの伝播を防ぐ
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    ロガーインスタンスを取得
    
    Args:
        name: ロガー名
        
    Returns:
        ロガーインスタンス
    """
    return logging.getLogger(name)


# アプリケーション共通ロガー
app_logger = setup_logger('knowledge_base')


# ログレベル変更用のユーティリティ関数
def set_log_level(level: str):
    """
    ログレベルを動的に変更
    
    Args:
        level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    app_logger.setLevel(log_level)
    for handler in app_logger.handlers:
        handler.setLevel(log_level)