#!/bin/bash

# AI Video Generator - Async Mode Startup Script
# このスクリプトは、非同期処理対応のアプリケーションを起動します

echo "🚀 AI Video Generator - Async Mode"
echo "=================================="
echo ""

# 環境変数の確認
if [ ! -f .env ]; then
    echo "❌ .env ファイルが見つかりません"
    echo "   .env.example をコピーして .env を作成してください"
    exit 1
fi

# Redisの確認
echo "🔍 Redisの接続を確認中..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis接続OK"
else
    echo "❌ Redisに接続できません"
    echo "   以下のコマンドでRedisを起動してください:"
    echo "   - macOS: brew services start redis"
    echo "   - Linux: sudo systemctl start redis-server"
    echo "   - Docker: docker run -d --name redis -p 6379:6379 redis:7-alpine"
    exit 1
fi

# ディレクトリの作成
echo "📁 ディレクトリを作成中..."
mkdir -p uploads outputs frames logs

# Supabaseの確認
echo "🗄 Supabase設定を確認中..."
if grep -q "xxxxxxxxxxxxx" .env; then
    echo "⚠️  警告: Supabaseの設定が必要です"
    echo "   SUPABASE_SETUP.md を参照してSupabaseをセットアップしてください"
    echo "   (モックモードで起動します)"
fi

echo ""
echo "🎬 アプリケーションを起動します..."
echo ""

# tmux または screen が使えるか確認
if command -v tmux &> /dev/null; then
    echo "📺 tmuxを使用してセッションを起動します"
    echo "   セッション名: ai-video-async"
    echo ""
    echo "   各ペインの役割:"
    echo "   - ペイン 0: Flask Webサーバー"
    echo "   - ペイン 1: Celery Worker"
    echo "   - ペイン 2: Flower監視ダッシュボード"
    echo ""

    # tmuxセッションを作成
    tmux new-session -d -s ai-video-async

    # ペイン0: Flask
    tmux send-keys -t ai-video-async:0.0 'source venv/bin/activate 2>/dev/null || true' C-m
    tmux send-keys -t ai-video-async:0.0 'python app_async.py' C-m

    # ペイン1を作成: Celery Worker
    tmux split-window -h -t ai-video-async:0
    tmux send-keys -t ai-video-async:0.1 'source venv/bin/activate 2>/dev/null || true' C-m
    tmux send-keys -t ai-video-async:0.1 'sleep 3' C-m
    tmux send-keys -t ai-video-async:0.1 'celery -A async_tasks.celery_app worker --loglevel=info --concurrency=2' C-m

    # ペイン2を作成: Flower
    tmux split-window -v -t ai-video-async:0.1
    tmux send-keys -t ai-video-async:0.2 'source venv/bin/activate 2>/dev/null || true' C-m
    tmux send-keys -t ai-video-async:0.2 'sleep 5' C-m
    tmux send-keys -t ai-video-async:0.2 'celery -A async_tasks.celery_app flower --port=5555' C-m

    # セッションにアタッチ
    echo "✅ 起動完了！"
    echo ""
    echo "📍 アクセス先:"
    echo "   - Webアプリ: http://localhost:5000"
    echo "   - Flower監視: http://localhost:5555"
    echo ""
    echo "💡 tmuxコマンド:"
    echo "   - デタッチ: Ctrl+B → D"
    echo "   - アタッチ: tmux attach -t ai-video-async"
    echo "   - 終了: tmux kill-session -t ai-video-async"
    echo ""

    sleep 2
    tmux attach -t ai-video-async

else
    echo "⚠️  tmuxが見つかりません。個別に起動してください:"
    echo ""
    echo "ターミナル1 (Flask):"
    echo "  python app_async.py"
    echo ""
    echo "ターミナル2 (Celery Worker):"
    echo "  celery -A async_tasks.celery_app worker --loglevel=info --concurrency=2"
    echo ""
    echo "ターミナル3 (Flower - オプション):"
    echo "  celery -A async_tasks.celery_app flower --port=5555"
    echo ""
fi
