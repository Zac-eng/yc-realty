"""
Supabase Client
データベース接続とヘルパー関数
"""
from supabase import create_client, Client
from typing import Dict, List, Optional
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Supabaseデータベースクライアント"""

    def __init__(self):
        """クライアントを初期化"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_SERVICE_KEY')  # サービスロールを使用

        if not self.url or not self.key:
            logger.warning("Supabase credentials not configured. Using mock mode.")
            self.client = None
            self.mock_mode = True
        else:
            try:
                self.client: Client = create_client(self.url, self.key)
                self.mock_mode = False
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.client = None
                self.mock_mode = True

    def create_task(self, task_data: Dict) -> Dict:
        """
        タスクを作成

        Args:
            task_data: タスクデータ

        Returns:
            作成されたタスク
        """
        if self.mock_mode:
            # モックモード: ダミーデータを返す
            import uuid
            task_data['id'] = str(uuid.uuid4())
            task_data['created_at'] = datetime.utcnow().isoformat()
            task_data['updated_at'] = datetime.utcnow().isoformat()
            logger.info(f"[MOCK] Created task: {task_data['id']}")
            return task_data

        try:
            response = self.client.table('tasks').insert(task_data).execute()
            task = response.data[0] if response.data else None
            logger.info(f"Created task: {task['id']}")
            return task
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        タスクを取得

        Args:
            task_id: タスクID

        Returns:
            タスク情報
        """
        if self.mock_mode:
            logger.warning(f"[MOCK] Getting task: {task_id}")
            return {
                'id': task_id,
                'status': 'pending',
                'progress': 0,
                'created_at': datetime.utcnow().isoformat()
            }

        try:
            response = self.client.table('tasks').select('*').eq('id', task_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    def update_task(self, task_id: str, update_data: Dict) -> Dict:
        """
        タスクを更新

        Args:
            task_id: タスクID
            update_data: 更新データ

        Returns:
            更新されたタスク
        """
        if self.mock_mode:
            logger.info(f"[MOCK] Updated task {task_id}: {update_data}")
            task = self.get_task(task_id)
            task.update(update_data)
            task['updated_at'] = datetime.utcnow().isoformat()
            return task

        try:
            update_data['updated_at'] = datetime.utcnow().isoformat()

            # duration_secondsを計算（started_atとcompleted_atがある場合）
            if 'completed_at' in update_data and 'started_at' not in update_data:
                # 既存のタスクからstarted_atを取得
                existing_task = self.get_task(task_id)
                if existing_task and existing_task.get('started_at'):
                    started = datetime.fromisoformat(existing_task['started_at'].replace('Z', '+00:00'))
                    completed = datetime.fromisoformat(update_data['completed_at'].replace('Z', '+00:00'))
                    update_data['duration_seconds'] = (completed - started).total_seconds()

            response = self.client.table('tasks').update(update_data).eq('id', task_id).execute()
            task = response.data[0] if response.data else None
            logger.debug(f"Updated task {task_id}")
            return task
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            raise

    def get_user_tasks(self, user_id: str, limit: int = 50, status: str = None) -> List[Dict]:
        """
        ユーザーのタスク一覧を取得

        Args:
            user_id: ユーザーID
            limit: 取得件数
            status: ステータスでフィルタ（オプション）

        Returns:
            タスクリスト
        """
        if self.mock_mode:
            logger.warning(f"[MOCK] Getting tasks for user: {user_id}")
            return []

        try:
            query = self.client.table('tasks').select('*').eq('user_id', user_id)

            if status:
                query = query.eq('status', status)

            response = query.order('created_at', desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to get user tasks: {e}")
            return []

    def delete_old_tasks(self, days: int = 30) -> int:
        """
        古いタスクを削除（クリーンアップ）

        Args:
            days: この日数より古いタスクを削除

        Returns:
            削除されたタスク数
        """
        if self.mock_mode:
            logger.info(f"[MOCK] Would delete tasks older than {days} days")
            return 0

        try:
            from datetime import timedelta
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            response = self.client.table('tasks').delete().lt('created_at', cutoff_date).execute()
            deleted_count = len(response.data) if response.data else 0
            logger.info(f"Deleted {deleted_count} old tasks")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete old tasks: {e}")
            return 0

    def get_task_statistics(self, user_id: str = None, days: int = 7) -> Dict:
        """
        タスク統計を取得

        Args:
            user_id: ユーザーID（指定しない場合は全体）
            days: 過去何日分の統計か

        Returns:
            統計情報
        """
        if self.mock_mode:
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'running': 0,
                'pending': 0
            }

        try:
            from datetime import timedelta
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            query = self.client.table('tasks').select('status').gte('created_at', start_date)

            if user_id:
                query = query.eq('user_id', user_id)

            response = query.execute()
            tasks = response.data

            stats = {
                'total': len(tasks),
                'success': sum(1 for t in tasks if t['status'] == 'success'),
                'failed': sum(1 for t in tasks if t['status'] == 'failed'),
                'running': sum(1 for t in tasks if t['status'] == 'running'),
                'pending': sum(1 for t in tasks if t['status'] == 'pending'),
                'cancelled': sum(1 for t in tasks if t['status'] == 'cancelled'),
            }

            return stats
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


# シングルトンインスタンス
supabase_client = SupabaseClient()
