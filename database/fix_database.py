#!/usr/bin/env python3
"""
データベースのFTSテーブルを修正するスクリプト
"""
import sqlite3
import sys
from pathlib import Path

# データベースパス
db_path = Path("knowledge_base.db")

if not db_path.exists():
    print(f"エラー: {db_path} が見つかりません")
    sys.exit(1)

print("データベースの修正を開始します...")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 現在のテーブル構造を確認
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"現在のテーブル: {[t[0] for t in tables]}")
    
    # FTSテーブルを削除して再作成
    print("FTSテーブルを再構築します...")
    
    # 既存のトリガーを削除
    cursor.execute("DROP TRIGGER IF EXISTS snippets_fts_insert;")
    cursor.execute("DROP TRIGGER IF EXISTS snippets_fts_update;")
    cursor.execute("DROP TRIGGER IF EXISTS snippets_fts_delete;")
    
    # FTSテーブルを削除
    cursor.execute("DROP TABLE IF EXISTS snippets_fts;")
    
    # FTSテーブルを再作成（修正版）
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS snippets_fts USING fts5(
            title, 
            content, 
            tags, 
            description
        )
    ''')
    
    # 既存のデータをFTSテーブルに挿入
    cursor.execute('''
        INSERT INTO snippets_fts(rowid, title, content, tags, description)
        SELECT id, title, content, tags, description FROM snippets
    ''')
    
    # トリガーを再作成（INSERT時）
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS snippets_fts_insert 
        AFTER INSERT ON snippets BEGIN
            INSERT INTO snippets_fts(rowid, title, content, tags, description)
            VALUES (new.id, new.title, new.content, new.tags, new.description);
        END
    ''')
    
    # トリガーを再作成（UPDATE時）
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
    
    # トリガーを再作成（DELETE時）
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS snippets_fts_delete 
        AFTER DELETE ON snippets BEGIN
            DELETE FROM snippets_fts WHERE rowid = old.id;
        END
    ''')
    
    conn.commit()
    print("✅ FTSテーブルの再構築が完了しました")
    
    # テスト：FTSテーブルの動作確認
    cursor.execute("SELECT COUNT(*) FROM snippets_fts")
    count = cursor.fetchone()[0]
    print(f"FTSテーブルのレコード数: {count}")
    
    conn.close()
    print("✅ データベースの修正が完了しました")
    
except Exception as e:
    print(f"エラー: {e}")
    sys.exit(1)
    sys.exit(1)