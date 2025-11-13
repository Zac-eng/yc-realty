# クイックスタートガイド 🚀

非同期処理対応のAI動画生成システムをすぐに試すための最短手順です。

## 📝 最低限必要な手順（5分）

### 1. Redisのインストールと起動

```bash
# macOS
brew install redis
brew services start redis

# または Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 2. パッケージのインストール

```bash
# 仮想環境を作成（初回のみ）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# パッケージをインストール
pip install -r requirements.txt
```

### 3. Supabaseのセットアップ（オプション）

**Supabaseなしでも動作します（モックモード）**

Supabaseを使用する場合は `SUPABASE_SETUP.md` を参照してください。

### 4. 起動

#### 方法A: 自動起動スクリプト（推奨）

```bash
./start_async.sh
```

#### 方法B: Docker Compose

```bash
docker-compose up -d
```

#### 方法C: 手動起動

**ターミナル1: Flask**
```bash
python app_async.py
```

**ターミナル2: Celery Worker**
```bash
celery -A async_tasks.celery_app worker --loglevel=info --concurrency=2
```

**ターミナル3: Flower（オプション）**
```bash
celery -A async_tasks.celery_app flower --port=5555
```

## 🌐 アクセス先

- **Webアプリ**: http://localhost:5000
- **Flower監視**: http://localhost:5555

## 🎬 使い方

1. ブラウザで http://localhost:5000 を開く
2. 画像をアップロード
3. プロンプトを入力（例: "A serene mountain landscape at sunset"）
4. 「動画生成開始」ボタンをクリック
5. 進捗バーで状態を確認
6. 完了後、動画をダウンロード

## ⚙️ 設定ファイル

### `.env` の最低限の設定

```bash
# Google AI API（必須）
GOOGLE_API_KEY=your-google-api-key-here

# Supabase（オプション - なければモックモード）
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# その他はデフォルトのまま
```

## 🔍 動作確認

### Redisの確認
```bash
redis-cli ping
# 出力: PONG
```

### Celery Workerの確認
```bash
celery -A async_tasks.celery_app inspect active
```

### ヘルスチェック
```bash
curl http://localhost:5000/health
```

## 🐛 よくある問題

### Redisに接続できない

```bash
# Redisが起動しているか確認
redis-cli ping

# 起動していなければ
brew services start redis  # macOS
```

### Celery Workerが起動しない

```bash
# 仮想環境が有効か確認
which python
# /path/to/venv/bin/python と表示されればOK

# 有効でなければ
source venv/bin/activate
```

### モジュールが見つからない

```bash
# パッケージを再インストール
pip install -r requirements.txt
```

## 📚 次のステップ

- `README_ASYNC.md`: 詳細なドキュメント
- `SUPABASE_SETUP.md`: Supabaseのセットアップ手順
- 提供されたガイドドキュメント: 完全な実装ガイド

## 🎯 システム要件

- Python 3.9以上
- Redis 7以上
- 2GB以上のRAM
- Google AI API Key

## 💡 ヒント

- Supabaseなしでも動作します（モックモード）
- 初回は Supabaseなしで試してみるのがおすすめ
- 本番環境では Supabase を使用することを推奨

---

問題が発生した場合は、`README_ASYNC.md` のトラブルシューティングセクションを確認してください。
