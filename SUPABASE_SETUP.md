# Supabase セットアップガイド

## 1. Supabaseプロジェクトの作成

1. [Supabase](https://supabase.com) にアクセスしてログイン
2. "New Project" をクリック
3. 以下の情報を入力:
   - Project name: `ai-video-editor`
   - Database Password: **強力なパスワードを設定（メモしておく）**
   - Region: `Northeast Asia (Tokyo)` を推奨
4. "Create new project" をクリック

## 2. データベーススキーマの作成

プロジェクトが作成されたら:

1. 左サイドバーの **SQL Editor** をクリック
2. 以下のSQLを貼り付けて実行:

```sql
-- タスクステータスの列挙型
CREATE TYPE task_status AS ENUM (
    'pending',
    'running',
    'success',
    'failed',
    'cancelled',
    'retry'
);

-- タスクタイプの列挙型
CREATE TYPE task_type AS ENUM (
    'veo_generate',
    'frame_extract',
    'generate_video_from_image',
    'video_edit'
);

-- タスク管理テーブル
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    celery_task_id VARCHAR(36) UNIQUE,

    -- ユーザー情報
    user_id VARCHAR(100),

    -- タスク情報
    task_type task_type NOT NULL,
    status task_status DEFAULT 'pending',

    -- 進捗情報
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    current_step VARCHAR(200),

    -- パラメータ（JSON形式）
    params JSONB NOT NULL,

    -- 結果
    result_path VARCHAR(500),
    result_url VARCHAR(500),
    result_metadata JSONB,

    -- エラー情報
    error_message TEXT,
    error_type VARCHAR(100),
    retry_count INTEGER DEFAULT 0,

    -- タイムスタンプ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 実行時間（秒）
    duration_seconds DOUBLE PRECISION
);

-- インデックス作成（パフォーマンス向上）
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_celery_task_id ON tasks(celery_task_id);

-- updated_at 自動更新トリガー
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE
    ON tasks FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- アップロードファイル管理テーブル
CREATE TABLE uploaded_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100),

    -- ファイル情報
    original_filename VARCHAR(500),
    stored_filename VARCHAR(500) UNIQUE,
    file_path VARCHAR(500),
    file_size BIGINT,
    mime_type VARCHAR(100),

    -- メタデータ
    width INTEGER,
    height INTEGER,
    duration DOUBLE PRECISION,
    frame_count INTEGER,

    -- タイムスタンプ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_uploaded_files_user_id ON uploaded_files(user_id);

-- ユーザーセッション管理テーブル
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) UNIQUE NOT NULL,

    -- 編集中のデータ
    current_video_id UUID REFERENCES uploaded_files(id),
    frames_data JSONB,

    -- タイムスタンプ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_sessions_session_id ON user_sessions(session_id);
```

3. "Run" をクリックして実行
4. 成功メッセージを確認

## 3. API認証情報の取得

1. 左サイドバーの **Settings** → **API** をクリック
2. 以下の情報をコピー:
   - **Project URL**: `https://xxxxxxxxxxxxx.supabase.co`
   - **anon public**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - **service_role**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (Show to revealをクリック)

## 4. .env ファイルに追加

プロジェクトルートの `.env` ファイルに以下を追加:

```bash
# Supabase設定
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...（anon public key）
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...（service_role key）
```

## 5. Row Level Security（RLS）の設定（オプション）

本番環境ではRLSを有効化してセキュリティを強化することを推奨します。

SQL Editorで以下を実行:

```sql
-- RLSの有効化
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- ポリシーの作成（サービスロールは全アクセス可能）
CREATE POLICY "Service role can do anything on tasks"
    ON tasks FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role can do anything on files"
    ON uploaded_files FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role can do anything on sessions"
    ON user_sessions FOR ALL
    USING (true)
    WITH CHECK (true);
```

## 6. テストクエリで確認

SQL Editorで以下を実行して、テーブルが正しく作成されたか確認:

```sql
-- テーブル一覧
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';

-- tasksテーブルの構造確認
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tasks';
```

## 完了！

これでSupabaseのセットアップが完了しました。
次のステップ: Redis と Celery のセットアップに進んでください。
