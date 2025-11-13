# AI動画生成システム - 非同期処理版

Celery + Redis + Supabase による本格的な非同期処理を実装したAI動画生成システムです。

## 🚀 主な機能

- **非同期タスク処理**: Celeryによる分散タスクキュー
- **リアルタイム進捗管理**: Supabaseによるタスク状態管理
- **自動リトライ**: タスク失敗時の自動再試行
- **タスク履歴**: 過去のタスク実行履歴を保存
- **ポーリング更新**: フロントエンドでの進捗リアルタイム表示
- **監視ダッシュボード**: Flowerによるタスク監視

## 📋 システム構成

```
┌─────────────────┐
│   Frontend      │  ← ポーリングで進捗確認
│  (Browser UI)   │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│  Flask Web App  │  ← タスク投入、API提供
│  (app_async.py) │
└────────┬────────┘
         │
         ├─→ Supabase (PostgreSQL)
         │   └─ タスク履歴管理
         │
         └─→ Redis
             └─ Celeryブローカー
                    │
                    ↓
            ┌───────────────┐
            │ Celery Worker │  ← 非同期タスク実行
            │ (async_tasks) │
            └───────────────┘
                    │
                    ↓
            ┌───────────────┐
            │  Google Veo   │  ← AI動画生成
            └───────────────┘
```

## 🛠 セットアップ手順

### 1. Supabaseのセットアップ

`SUPABASE_SETUP.md` を参照して、Supabaseプロジェクトを作成してください。

### 2. 環境変数の設定

`.env` ファイルを編集して、以下の情報を設定してください：

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Google API
GOOGLE_API_KEY=your-google-api-key

# その他はデフォルトのまま
```

### 3. 依存パッケージのインストール

```bash
# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# パッケージをインストール
pip install -r requirements.txt
```

### 4. Redisのインストールと起動

#### macOS
```bash
brew install redis
brew services start redis
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

#### Docker
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 5. アプリケーションの起動

#### ローカル環境

**ターミナル1: Flask Webサーバー**
```bash
python app_async.py
```

**ターミナル2: Celery Worker**
```bash
celery -A async_tasks.celery_app worker --loglevel=info
```

**ターミナル3: Flower (監視ダッシュボード) - オプション**
```bash
celery -A async_tasks.celery_app flower --port=5555
```

#### Docker Compose

```bash
# 起動
docker-compose up -d

# ログ確認
docker-compose logs -f

# 停止
docker-compose down
```

## 📖 使用方法

### Webインターフェース

1. ブラウザで http://localhost:5000 にアクセス
2. 画像をアップロード
3. プロンプトを入力
4. 「動画生成開始」ボタンをクリック
5. 進捗バーで状態を確認
6. 完了後、動画をダウンロード

### API使用例

#### タスクの作成

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "veo_generate",
    "params": {
      "image_path": "uploads/test.jpg",
      "prompt": "A serene mountain landscape",
      "duration": 8
    }
  }'
```

レスポンス:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "celery_task_id": "abc123...",
  "status": "Task submitted successfully"
}
```

#### タスク状態の確認

```bash
curl http://localhost:5000/api/tasks/550e8400-e29b-41d4-a716-446655440000
```

レスポンス:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 45,
  "current_step": "動画生成中...",
  "created_at": "2025-01-15T10:30:00Z",
  "result_url": null
}
```

#### タスクのキャンセル

```bash
curl -X POST http://localhost:5000/api/tasks/550e8400.../cancel
```

## 🔍 監視とデバッグ

### Flower ダッシュボード

http://localhost:5555 にアクセス

- アクティブなタスク
- ワーカーの状態
- タスク実行履歴
- パフォーマンスメトリクス

### Supabase ダッシュボード

https://app.supabase.com でプロジェクトにアクセス

- タスクテーブルの確認
- SQLクエリの実行
- リアルタイムログ

### ログ確認

```bash
# アプリケーションログ
tail -f logs/app.log

# Celeryワーカーログ (Docker)
docker-compose logs -f celery_worker

# Redis監視
redis-cli monitor
```

## 🗂 ファイル構成

```
yc-realty/
├── app_async.py            # Flask Webアプリケーション
├── async_tasks.py          # Celery非同期タスク定義
├── celery_app.py           # Celery設定
├── supabase_client.py      # Supabaseクライアント
├── veo_generator.py        # Veo API統合
├── frame_editor.py         # フレーム処理
├── requirements.txt        # Python依存パッケージ
├── .env                    # 環境変数
├── docker-compose.yml      # Docker Compose設定
├── Dockerfile              # Dockerイメージ定義
├── SUPABASE_SETUP.md       # Supabaseセットアップガイド
├── templates/
│   └── async_video_ui.html # フロントエンドUI
├── uploads/                # アップロードファイル
├── outputs/                # 生成動画
└── frames/                 # 抽出フレーム
```

## 🐛 トラブルシューティング

### Redisに接続できない

```bash
# Redis起動確認
redis-cli ping
# 出力: PONG

# Redis起動
brew services start redis  # macOS
sudo systemctl start redis-server  # Linux
```

### Celeryワーカーが起動しない

```bash
# Celeryワーカーの確認
celery -A async_tasks.celery_app inspect active

# ワーカーを再起動
docker-compose restart celery_worker
```

### Supabase接続エラー

1. `.env` ファイルの `SUPABASE_URL` と `SUPABASE_SERVICE_KEY` を確認
2. Supabase Dashboardで接続情報を再確認
3. ネットワーク接続を確認

### タスクがタイムアウトする

`celery_app.py` でタイムアウト時間を調整:

```python
task_soft_time_limit=1800,  # 30分
task_time_limit=2400,        # 40分
```

## 📊 パフォーマンス

### タスクの並列実行数

Celery Workerの並列度を調整:

```bash
celery -A async_tasks.celery_app worker --concurrency=4
```

### メモリ管理

Workerのタスク実行数を制限:

```python
# celery_app.py
worker_max_tasks_per_child=10
```

## 🔐 セキュリティ

- `.env` ファイルは `.gitignore` に追加
- `SECRET_KEY` は本番環境で必ず変更
- `SUPABASE_SERVICE_KEY` は慎重に管理
- Row Level Security (RLS) を有効化推奨

## 📝 ライセンス

MIT License

## 🤝 サポート

問題が発生した場合は、以下を確認してください：

1. `SUPABASE_SETUP.md` の手順を実行したか
2. `.env` ファイルが正しく設定されているか
3. Redisが起動しているか
4. Celery Workerが起動しているか
5. ログファイルにエラーがないか

---

**作成日**: 2025-11-13
**バージョン**: 1.0
**技術スタック**: Flask + Celery + Redis + Supabase + Google Veo
