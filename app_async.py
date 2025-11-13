"""
Flask Application with Celery + Supabase Integration
非同期処理対応のFlaskアプリケーション
"""
from flask import Flask, request, jsonify, session, send_from_directory, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from supabase_client import supabase_client
from celery_app import get_celery_app
import async_tasks
import os
import uuid
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key'),
    MAX_CONTENT_LENGTH=int(os.getenv('MAX_UPLOAD_SIZE', 524288000)),  # 500MB
    UPLOAD_FOLDER=os.getenv('UPLOAD_FOLDER', 'uploads'),
    OUTPUT_FOLDER=os.getenv('OUTPUT_FOLDER', 'outputs'),
)

CORS(app)

# Celery
celery = get_celery_app()

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs('frames', exist_ok=True)


def get_or_create_session_id():
    """セッションIDを取得または生成"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']


# ============================================================================
# タスク管理API
# ============================================================================

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """
    新しいタスクを作成して非同期実行
    """
    try:
        data = request.json
        task_type = data.get('task_type')
        params = data.get('params', {})
        user_id = get_or_create_session_id()

        # Supabaseにタスクを作成
        task = supabase_client.create_task({
            'user_id': user_id,
            'task_type': task_type,
            'status': 'pending',
            'params': params
        })

        db_task_id = task['id']

        # タスクタイプに応じてCeleryタスクを起動
        if task_type == 'veo_generate':
            # Veo動画生成
            image_path = params.get('image_path')
            prompt = params.get('prompt')
            duration = params.get('duration', 8)

            if not image_path or not prompt:
                return jsonify({'error': 'image_path and prompt are required'}), 400

            celery_task = async_tasks.veo_generate_task.apply_async(
                kwargs={
                    'db_task_id': db_task_id,
                    'image_path': image_path,
                    'prompt': prompt,
                    'duration': duration,
                    'user_id': user_id
                }
            )

        elif task_type == 'generate_video_from_image':
            # 画像から動画生成（デモモード）
            image_path = params.get('image_path')
            prompt = params.get('prompt')

            if not image_path or not prompt:
                return jsonify({'error': 'image_path and prompt are required'}), 400

            celery_task = async_tasks.generate_video_from_image_task.apply_async(
                kwargs={
                    'db_task_id': db_task_id,
                    'image_path': image_path,
                    'prompt': prompt,
                    'user_id': user_id
                }
            )

        elif task_type == 'frame_extract':
            # フレーム抽出
            video_path = params.get('video_path')
            frame_count = params.get('frame_count', 6)

            if not video_path:
                return jsonify({'error': 'video_path is required'}), 400

            celery_task = async_tasks.extract_frames_task.apply_async(
                kwargs={
                    'db_task_id': db_task_id,
                    'video_path': video_path,
                    'frame_count': frame_count,
                    'user_id': user_id
                }
            )

        else:
            return jsonify({'error': f'Unknown task type: {task_type}'}), 400

        # CeleryタスクIDを保存
        supabase_client.update_task(db_task_id, {
            'celery_task_id': celery_task.id
        })

        logger.info(f"Task created: {db_task_id} (Celery: {celery_task.id})")

        return jsonify({
            'task_id': db_task_id,
            'celery_task_id': celery_task.id,
            'status': 'Task submitted successfully',
            'message': 'タスクを開始しました'
        }), 202

    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """タスク状態を取得"""
    try:
        task = supabase_client.get_task(task_id)

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        return jsonify(task)

    except Exception as e:
        logger.error(f"Error getting task status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """タスク一覧を取得"""
    try:
        user_id = get_or_create_session_id()
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 50))

        tasks = supabase_client.get_user_tasks(user_id, limit, status_filter)

        return jsonify({
            'tasks': tasks,
            'count': len(tasks)
        })

    except Exception as e:
        logger.error(f"Error getting tasks: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """タスクをキャンセル"""
    try:
        task = supabase_client.get_task(task_id)

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if task['status'] in ['success', 'failed', 'cancelled']:
            return jsonify({'error': 'Task already finished'}), 400

        # Celeryタスクを終了
        if task.get('celery_task_id'):
            celery.control.revoke(task['celery_task_id'], terminate=True)

        # Supabaseを更新
        updated_task = supabase_client.update_task(task_id, {
            'status': 'cancelled',
            'completed_at': datetime.utcnow().isoformat()
        })

        return jsonify(updated_task)

    except Exception as e:
        logger.error(f"Error cancelling task: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ファイルアップロード
# ============================================================================

@app.route('/api/upload/image', methods=['POST'])
def upload_image():
    """画像をアップロード"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']

        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400

        user_id = get_or_create_session_id()
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_id, 'images')
        os.makedirs(upload_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(upload_dir, filename)

        file.save(file_path)

        logger.info(f"Image uploaded: {file_path}")

        return jsonify({
            'status': 'success',
            'file_path': file_path,
            'filename': filename
        })

    except Exception as e:
        logger.error(f"Error uploading image: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload/video', methods=['POST'])
def upload_video():
    """動画をアップロード"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        file = request.files['video']

        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400

        user_id = get_or_create_session_id()
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_id, 'videos')
        os.makedirs(upload_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(upload_dir, filename)

        file.save(file_path)

        logger.info(f"Video uploaded: {file_path}")

        return jsonify({
            'status': 'success',
            'file_path': file_path,
            'filename': filename
        })

    except Exception as e:
        logger.error(f"Error uploading video: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ファイル提供
# ============================================================================

@app.route('/outputs/<path:filename>')
def serve_output_file(filename):
    """出力ファイルを提供"""
    try:
        output_dir = os.path.abspath(app.config['OUTPUT_FOLDER'])
        return send_from_directory(output_dir, filename)
    except Exception as e:
        logger.error(f"Error serving file: {e}", exc_info=True)
        return jsonify({'error': 'File not found'}), 404


@app.route('/uploads/<path:filename>')
def serve_upload_file(filename):
    """アップロードファイルを提供"""
    try:
        upload_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
        return send_from_directory(upload_dir, filename)
    except Exception as e:
        logger.error(f"Error serving file: {e}", exc_info=True)
        return jsonify({'error': 'File not found'}), 404


# ============================================================================
# UIエンドポイント
# ============================================================================

@app.route('/')
def index():
    """メインページ"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    return render_template('async_video_ui.html')


@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'celery_connected': True,
        'supabase_connected': not supabase_client.mock_mode
    })


if __name__ == '__main__':
    logger.info("Starting Flask application with async support...")
    logger.info(f"Uploads: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"Outputs: {app.config['OUTPUT_FOLDER']}")

    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=(os.getenv('FLASK_ENV') == 'development')
    )
