#!/usr/bin/env python3
"""
knowledge_base.db のテーブル構造を確認するスクリプト
"""
import sqlite3
from pathlib import Path

def check_database_structure(db_path="knowledge_base.db"):
    """データベースの構造を詳しく調査"""
    
    if not Path(db_path).exists():
        print(f"エラー: {db_path} が見つかりません")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📊 DATABASE STRUCTURE ANALYSIS")
    print("=" * 80)
    
    # 1. 全テーブルの一覧
    print("\n### 1. テーブル一覧")
    print("-" * 40)
    cursor.execute("""
        SELECT name, type, sql 
        FROM sqlite_master 
        WHERE type IN ('table', 'view')
        ORDER BY type, name
    """)
    tables = cursor.fetchall()
    
    for table_name, table_type, create_sql in tables:
        print(f"\n📁 {table_name} ({table_type})")
        if 'VIRTUAL TABLE' in create_sql:
            print("   ⚡ 仮想テーブル (FTS5)")
        else:
            print("   📝 通常テーブル")
    
    # 2. 各テーブルの詳細構造
    print("\n" + "=" * 80)
    print("### 2. 各テーブルの詳細構造")
    print("-" * 40)
    
    for table_name, table_type, create_sql in tables:
        print(f"\n🔍 {table_name}")
        print("-" * 40)
        
        # テーブル作成SQL
        print("CREATE文:")
        print(create_sql)
        print()
        
        # カラム情報（仮想テーブル以外）
        if 'VIRTUAL TABLE' not in create_sql:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print("カラム構造:")
            print(f"{'ID':<5} {'名前':<20} {'型':<15} {'NULL':<6} {'デフォルト':<15} {'PK'}")
            print("-" * 80)
            for col in columns:
                cid, name, dtype, notnull, default, pk = col
                null_str = "NO" if notnull else "YES"
                pk_str = "PK" if pk else ""
                default_str = str(default) if default else ""
                print(f"{cid:<5} {name:<20} {dtype:<15} {null_str:<6} {default_str:<15} {pk_str}")
        
        # レコード数
        try:
            if table_type == 'table':
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"\nレコード数: {count}")
        except:
            print(f"\nレコード数: 取得できません")
    
    # 3. インデックス一覧
    print("\n" + "=" * 80)
    print("### 3. インデックス一覧")
    print("-" * 40)
    cursor.execute("""
        SELECT name, tbl_name, sql 
        FROM sqlite_master 
        WHERE type = 'index' AND sql IS NOT NULL
        ORDER BY tbl_name, name
    """)
    indexes = cursor.fetchall()
    
    for idx_name, table_name, create_sql in indexes:
        print(f"\n📍 {idx_name} (on {table_name})")
        print(f"   {create_sql}")
    
    # 4. トリガー一覧
    print("\n" + "=" * 80)
    print("### 4. トリガー一覧")
    print("-" * 40)
    cursor.execute("""
        SELECT name, tbl_name, sql 
        FROM sqlite_master 
        WHERE type = 'trigger'
        ORDER BY tbl_name, name
    """)
    triggers = cursor.fetchall()
    
    for trigger_name, table_name, create_sql in triggers:
        print(f"\n⚡ {trigger_name} (on {table_name})")
        print(f"   目的: snippetsテーブルの変更をFTSテーブルに反映")
    
    # 5. FTSテーブルの説明
    print("\n" + "=" * 80)
    print("### 5. FTS（全文検索）テーブルの説明")
    print("-" * 40)
    print("""
FTSテーブルについて:
- snippets_fts は全文検索用の仮想テーブルです
- SQLite FTS5 (Full-Text Search) エンジンを使用
- snippetsテーブルのテキストデータのインデックスを保持
- 高速な全文検索を可能にします

関連テーブル:
- snippets_fts_* : FTS5が内部的に作成する補助テーブル
  - snippets_fts_data: 実際の全文検索インデックスデータ
  - snippets_fts_idx: インデックス構造
  - snippets_fts_content: コンテンツ参照（使用されない場合もある）
  - snippets_fts_docsize: ドキュメントサイズ情報
  - snippets_fts_config: FTS設定情報

これらは自動的に管理されるため、直接操作する必要はありません。
    """)
    
    # 6. データ重複チェック
    print("\n" + "=" * 80)
    print("### 6. データ重複チェック")
    print("-" * 40)
    
    # snippetsテーブルの重複チェック
    cursor.execute("""
        SELECT title, category, COUNT(*) as count
        FROM snippets
        GROUP BY title, category
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    
    if duplicates:
        print("⚠️  重複データが見つかりました:")
        for title, category, count in duplicates:
            print(f"   - '{title}' (カテゴリ: {category}): {count}件")
    else:
        print("✅ snippetsテーブルに重複データはありません")
    
    conn.close()
    
    # 7. 推奨事項
    print("\n" + "=" * 80)
    print("### 7. 推奨事項")
    print("-" * 40)
    print("""
1. FTS関連テーブル（snippets_fts_*）は自動管理されるため触らない
2. データの追加・更新・削除は snippets テーブルに対してのみ行う
3. トリガーが自動的にFTSインデックスを更新
4. 検索時はFTSテーブルを使用すると高速（ただし現在は無効化中）
5. バックアップ時は snippets, categories, search_history テーブルのみで十分
    """)

if __name__ == "__main__":
    check_database_structure()