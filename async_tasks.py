"""
Celery Async Tasks with Supabase Integration
非同期タスクの定義
"""
from celery import Task
from celery_app import get_celery_app
from supabase_client import supabase_client
from datetime import datetime
import logging
import os
import time

logger = logging.getLogger(__name__)
celery_app = get_celery_app()


class BaseVideoTask(Task):
    """ビデオ処理タスクの基底クラス（Supabase統合）"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """タスク失敗時の処理"""
        logger.error(f"Task {task_id} failed: {exc}", exc_info=True)

        # Supabaseを更新
        db_task_id = kwargs.get('db_task_id') or (args[0] if args else None)
        if db_task_id:
            try:
                supabase_client.update_task(db_task_id, {
                    'status': 'failed',
                    'error_message': str(exc),
                    'error_type': type(exc).__name__,
                    'completed_at': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Failed to update task status in Supabase: {e}")

    def on_success(self, retval, task_id, args, kwargs):
        """タスク成功時の処理"""
        logger.info(f"Task {task_id} succeeded")

        db_task_id = kwargs.get('db_task_id') or (args[0] if args else None)
        if db_task_id:
            try:
                supabase_client.update_task(db_task_id, {
                    'status': 'success',
                    'progress': 100,
                    'completed_at': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Failed to update task status in Supabase: {e}")

    def update_progress(self, db_task_id: str, progress: int, current_step: str = None):
        """
        進捗を更新

        Args:
            db_task_id: データベースタスクID
            progress: 進捗率（0-100）
            current_step: 現在のステップ説明
        """
        # Celeryの状態を更新
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': progress,
                'current_step': current_step,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

        # Supabaseを更新
        if db_task_id:
            try:
                update_data = {'progress': progress}
                if current_step:
                    update_data['current_step'] = current_step

                supabase_client.update_task(db_task_id, update_data)
            except Exception as e:
                logger.error(f"Failed to update progress in Supabase: {e}")


@celery_app.task(
    bind=True,
    base=BaseVideoTask,
    name='async_tasks.veo_generate_task',
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=900,
    time_limit=1200,
)
def veo_generate_task(self, db_task_id: str, image_path: str, prompt: str,
                       duration: int = 8, user_id: str = None):
    """
    Veo動画生成タスク（Supabase統合）

    Args:
        db_task_id: データベースタスクID
        image_path: 入力画像のパス
        prompt: 動画生成プロンプト
        duration: 動画の長さ（秒）
        user_id: ユーザーID
    """
    from veo_generator import VeoVideoGenerator

    logger.info(f"Starting Veo generation: {db_task_id}")

    # タスク開始
    supabase_client.update_task(db_task_id, {
        'status': 'running',
        'started_at': datetime.utcnow().isoformat()
    })

    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set")

        veo = VeoVideoGenerator(api_key)

        # 進捗更新
        self.update_progress(db_task_id, 10, "画像をアップロード中...")

        # 出力ディレクトリ
        output_dir = os.path.join('outputs', 'veo_videos', user_id or 'anonymous')
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(output_dir, f'veo_{timestamp}.mp4')

        # 進捗更新
        self.update_progress(db_task_id, 20, "動画生成中... (これには数分かかります)")

        # Veo動画生成（完全なワークフロー）
        video_path = veo.generate_from_image_file(
            image_path=image_path,
            prompt=prompt,
            output_path=output_path,
            duration=f"{duration}s"
        )

        # 結果を保存
        self.update_progress(db_task_id, 95, "結果を保存中...")

        file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0

        supabase_client.update_task(db_task_id, {
            'result_path': video_path,
            'result_url': f"/outputs/{os.path.relpath(video_path, 'outputs')}",
            'result_metadata': {
                'prompt': prompt,
                'duration': duration,
                'input_image': image_path,
                'file_size': file_size
            }
        })

        self.update_progress(db_task_id, 100, "完了")
        logger.info(f"Veo generation completed: {video_path}")

        return {'video_path': video_path}

    except Exception as exc:
        logger.error(f"Task failed: {exc}", exc_info=True)

        # リトライ判定
        if isinstance(exc, (ConnectionError, TimeoutError)) and self.request.retries < self.max_retries:
            supabase_client.update_task(db_task_id, {
                'status': 'retry',
                'retry_count': self.request.retries + 1,
                'error_message': f"Retrying... ({self.request.retries + 1}/{self.max_retries})"
            })
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

        raise


@celery_app.task(
    bind=True,
    base=BaseVideoTask,
    name='async_tasks.generate_video_from_image_task',
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=60,
    time_limit=120,
)
def generate_video_from_image_task(self, db_task_id: str, image_path: str,
                                     prompt: str, user_id: str = None):
    """
    画像から動画を生成（デモモード: 7秒待機）

    Args:
        db_task_id: データベースタスクID
        image_path: 入力画像のパス
        prompt: プロンプト
        user_id: ユーザーID
    """
    from frame_editor import AIFrameEditor

    logger.info(f"Starting video generation from image: {db_task_id}")

    # タスク開始
    supabase_client.update_task(db_task_id, {
        'status': 'running',
        'started_at': datetime.utcnow().isoformat()
    })

    try:
        api_key = os.getenv("GOOGLE_API_KEY", "demo-key")
        ai_editor = AIFrameEditor(api_key)

        # 進捗更新
        self.update_progress(db_task_id, 10, "動画生成準備中...")

        # デモモード: 7秒待機してプリセット動画を返す
        output_path = ""
        demo_video_path = ai_editor.generate_video_from_image(
            image_path=image_path,
            prompt=prompt,
            output_path=output_path,
            duration=8
        )

        self.update_progress(db_task_id, 90, "結果を保存中...")

        # 結果を保存
        supabase_client.update_task(db_task_id, {
            'result_path': demo_video_path,
            'result_url': f"/{demo_video_path}",
            'result_metadata': {
                'prompt': prompt,
                'input_image': image_path,
                'demo_mode': True
            }
        })

        self.update_progress(db_task_id, 100, "完了")
        logger.info(f"Video generation completed: {demo_video_path}")

        return {'video_path': demo_video_path}

    except Exception as exc:
        logger.error(f"Task failed: {exc}", exc_info=True)
        raise


@celery_app.task(
    bind=True,
    base=BaseVideoTask,
    name='async_tasks.extract_frames_task',
    max_retries=2,
    soft_time_limit=120,
    time_limit=180,
)
def extract_frames_task(self, db_task_id: str, video_path: str,
                         frame_count: int = 6, user_id: str = None):
    """
    動画からフレームを抽出

    Args:
        db_task_id: データベースタスクID
        video_path: 動画ファイルのパス
        frame_count: 抽出するフレーム数
        user_id: ユーザーID
    """
    from frame_editor import FrameEditor

    logger.info(f"Starting frame extraction: {db_task_id}")

    # タスク開始
    supabase_client.update_task(db_task_id, {
        'status': 'running',
        'started_at': datetime.utcnow().isoformat()
    })

    try:
        # 進捗更新
        self.update_progress(db_task_id, 10, "動画を解析中...")

        session_id = user_id or 'default'
        frames_dir = os.path.join('frames', session_id, 'editor')

        editor = FrameEditor(video_path, frames_dir)

        self.update_progress(db_task_id, 30, f"{frame_count}フレームを抽出中...")

        frames = editor.extract_frames(frame_count=frame_count)

        self.update_progress(db_task_id, 90, "結果を保存中...")

        # 結果を保存（base64データは除外）
        frames_info = [
            {
                "frame_id": frame['frame_id'],
                "path": frame['path'],
                "timestamp": frame['timestamp'],
                "seconds": frame['seconds']
            }
            for frame in frames
        ]

        supabase_client.update_task(db_task_id, {
            'result_metadata': {
                'frames_dir': frames_dir,
                'frame_count': len(frames),
                'frames': frames_info
            }
        })

        self.update_progress(db_task_id, 100, "完了")
        logger.info(f"Frame extraction completed: {len(frames)} frames")

        return {'frames': frames, 'frames_dir': frames_dir}

    except Exception as exc:
        logger.error(f"Task failed: {exc}", exc_info=True)
        raise
