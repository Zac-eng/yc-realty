"""
Celery Application Configuration
"""
from celery import Celery
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def make_celery(app_name='video_tasks'):
    """
    Celeryアプリケーションを作成

    Args:
        app_name: アプリケーション名

    Returns:
        Celeryインスタンス
    """
    broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

    celery_app = Celery(
        app_name,
        broker=broker_url,
        backend=result_backend,
        include=['async_tasks']  # タスクモジュールをインポート
    )

    # Celery設定
    celery_app.conf.update(
        # タスク設定
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Tokyo',
        enable_utc=True,

        # タイムアウト設定
        task_soft_time_limit=1800,  # 30分
        task_time_limit=2400,       # 40分

        # リトライ設定
        task_acks_late=True,
        task_reject_on_worker_lost=True,

        # ワーカー設定
        worker_prefetch_multiplier=1,  # 一度に1つのタスクのみ取得
        worker_max_tasks_per_child=10,  # メモリリーク防止

        # 結果の有効期限
        result_expires=86400,  # 24時間

        # タスクルーティング（優先度別キュー）
        task_routes={
            'async_tasks.veo_generate_task': {'queue': 'veo_queue'},
            'async_tasks.generate_video_from_image_task': {'queue': 'video_queue'},
            'async_tasks.extract_frames_task': {'queue': 'default'},
        },

        # タスクの優先度設定
        task_queue_max_priority=10,
        task_default_priority=5,
    )

    logger.info(f"Celery app created: {app_name}")
    logger.info(f"Broker: {broker_url}")
    logger.info(f"Backend: {result_backend}")

    return celery_app


def get_celery_app():
    """
    Celeryアプリケーションのシングルトンインスタンスを取得

    Returns:
        Celeryインスタンス
    """
    return make_celery()


# グローバルインスタンス（Celery Workerが使用）
celery_app = get_celery_app()


if __name__ == '__main__':
    # Celery設定の確認
    print("Celery Configuration:")
    print(f"  Broker: {celery_app.conf.broker_url}")
    print(f"  Backend: {celery_app.conf.result_backend}")
    print(f"  Timezone: {celery_app.conf.timezone}")
    print(f"  Task routes: {celery_app.conf.task_routes}")
