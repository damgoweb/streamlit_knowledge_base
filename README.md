# 🧠 個人用ナレッジベース

開発作業で頻繁に使用するコマンドやコードスニペットを一元管理し、素早く検索・参照できるWebアプリケーションです。

## 🌟 特徴

- **スニペット管理**: コマンドやコードを整理して保存
- **高速検索**: キーワードやカテゴリで素早く検索
- **カテゴリ分類**: Docker、Git、SQL、Linux、Python、設定など
- **使用頻度追跡**: よく使うスニペットを把握
- **お気に入り機能**: 重要なスニペットをマーク
- **クラウド対応**: Supabaseによるデータ同期

## 🚀 デモ

[Streamlit Cloudでデモを見る](https://your-app-url.streamlit.app)

## 📋 必要要件

- Python 3.8以上
- Supabaseアカウント（無料プランでOK）

## 🛠️ セットアップ

### 1. Supabaseプロジェクトの準備

1. [Supabase](https://supabase.com)でプロジェクトを作成
2. SQL Editorで[データベース初期化スクリプト](docs/supabase_setup.sql)を実行
3. Settings > APIから認証情報を取得

### 2. ローカル環境のセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/knowledge-base.git
cd knowledge-base

# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
# .envファイルを編集してSupabase認証情報を設定
```

### 3. アプリケーションの起動

```bash
streamlit run app.py
```

## 🌐 Streamlit Cloudへのデプロイ

1. このリポジトリをFork
2. [Streamlit Cloud](https://streamlit.io/cloud)でアカウント作成
3. 「New app」からリポジトリを選択
4. Secretsに以下を設定:
   ```toml
   SUPABASE_URL = "your-supabase-url"
   SUPABASE_ANON_KEY = "your-anon-key"
   ```

## 📁 プロジェクト構造

```
knowledge_base/
├── app.py                 # メインアプリケーション
├── config.py             # 設定ファイル
├── requirements.txt      # 依存パッケージ
├── database/            # データベース関連
│   ├── db_factory.py    # DBファクトリー
│   ├── db_manager.py    # SQLite管理（ローカル用）
│   └── supabase_manager.py  # Supabase管理（クラウド用）
├── repository/          # リポジトリ層
│   └── snippet_repo.py  # スニペットリポジトリ
├── services/           # サービス層
│   └── snippet_service.py  # ビジネスロジック
├── ui/                 # UI層
│   ├── components.py   # UIコンポーネント
│   └── pages.py       # ページ定義
└── utils/             # ユーティリティ
    ├── logger.py      # ログ設定
    └── validators.py  # バリデータ
```

## 🔧 主な機能

### スニペット管理
- タイトル、コード内容、カテゴリ、タグで整理
- 構文ハイライト対応（Python、Bash、SQL等）
- 説明文やメモの追加

### 検索機能
- キーワード検索
- カテゴリフィルター
- タグ検索
- お気に入りフィルター

### 統計・分析
- スニペット総数
- カテゴリ別集計
- 使用頻度ランキング
- 最近使用したスニペット

### データ管理
- インポート/エクスポート（JSON形式）
- バックアップ機能
- データ同期（Supabase）

## 🤝 貢献

プルリクエストは歓迎です！大きな変更の場合は、まずissueを開いて変更内容について議論してください。

## 📄 ライセンス

[MIT License](LICENSE)

## 👤 作者

Your Name - [@yourtwitter](https://twitter.com/yourtwitter)

## 🙏 謝辞

- [Streamlit](https://streamlit.io/)
- [Supabase](https://supabase.com/)
- すべてのコントリビューター
