from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
from server_monitor import ServerMonitor
from config import Config
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Настройка CORS для хостинга
CORS(app, origins=Config.CORS_ORIGINS)

# Инициализация монитора серверов
monitor = ServerMonitor()

@app.route('/')
def index():
    """Главная страница веб-панели"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """API для получения статуса серверов"""
    return jsonify(monitor.get_status())

@app.route('/api/start_monitoring', methods=['POST'])
def start_monitoring():
    """API для запуска мониторинга"""
    try:
        monitor.start_monitoring()
        return jsonify({'success': True, 'message': 'Мониторинг запущен'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stop_monitoring', methods=['POST'])
def stop_monitoring():
    """API для остановки мониторинга"""
    try:
        monitor.stop_monitoring()
        return jsonify({'success': True, 'message': 'Мониторинг остановлен'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/switch_server', methods=['POST'])
def switch_server():
    """API для ручного переключения сервера"""
    try:
        data = request.get_json()
        server_key = data.get('server')
        
        if not server_key:
            return jsonify({'success': False, 'error': 'Не указан сервер'}), 400
            
        monitor.manual_switch(server_key)
        return jsonify({'success': True, 'message': f'Переключение на сервер {server_key}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/start_bot', methods=['POST'])
def start_bot():
    """API для запуска конкретного бота"""
    try:
        data = request.get_json()
        server_key = data.get('server')
        bot_id = data.get('bot_id')
        
        if not server_key or not bot_id:
            return jsonify({'success': False, 'error': 'Не указан сервер или бот'}), 400
            
        success = monitor.start_specific_bot(server_key, bot_id)
        if success:
            return jsonify({'success': True, 'message': f'Бот {bot_id} запущен на сервере {server_key}'})
        else:
            return jsonify({'success': False, 'error': f'Ошибка запуска бота {bot_id}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stop_bot', methods=['POST'])
def stop_bot():
    """API для остановки конкретного бота"""
    try:
        data = request.get_json()
        server_key = data.get('server')
        bot_id = data.get('bot_id')
        
        if not server_key or not bot_id:
            return jsonify({'success': False, 'error': 'Не указан сервер или бот'}), 400
            
        success = monitor.stop_specific_bot(server_key, bot_id)
        if success:
            return jsonify({'success': True, 'message': f'Бот {bot_id} остановлен на сервере {server_key}'})
        else:
            return jsonify({'success': False, 'error': f'Ошибка остановки бота {bot_id}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/restart_bot', methods=['POST'])
def restart_bot():
    """API для перезапуска конкретного бота"""
    try:
        data = request.get_json()
        server_key = data.get('server')
        bot_id = data.get('bot_id')
        
        if not server_key or not bot_id:
            return jsonify({'success': False, 'error': 'Не указан сервер или бот'}), 400
            
        success = monitor.restart_specific_bot(server_key, bot_id)
        if success:
            return jsonify({'success': True, 'message': f'Бот {bot_id} перезапущен на сервере {server_key}'})
        else:
            return jsonify({'success': False, 'error': f'Ошибка перезапуска бота {bot_id}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auto_restart', methods=['POST'])
def set_auto_restart():
    """API для включения/выключения автоперезапуска"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        monitor.set_auto_restart(enabled)
        status = 'включен' if enabled else 'выключен'
        return jsonify({'success': True, 'message': f'Автоперезапуск {status}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers')
def get_servers():
    """API для получения списка серверов"""
    return jsonify(Config.SERVERS)

@app.route('/api/bots')
def get_bots():
    """API для получения списка ботов"""
    bots_info = {}
    for server_key, server_config in Config.SERVERS.items():
        bots_info[server_key] = {
            'name': server_config['name'],
            'bots': server_config['bots']
        }
    return jsonify(bots_info)

@app.route('/health')
def health_check():
    """Проверка здоровья координатора"""
    return jsonify({
        'status': 'healthy',
        'service': 'coordinator',
        'timestamp': datetime.now().isoformat(),
        'monitoring_active': monitor.is_monitoring,
        'auto_restart_enabled': monitor.auto_restart_enabled
    })

if __name__ == '__main__':
    logger.info("Запуск центрального сервера мониторинга")
    logger.info(f"Веб-панель доступна по адресу: http://{Config.WEB_HOST}:{Config.WEB_PORT}")
    
    # Автоматический запуск мониторинга при старте
    monitor.start_monitoring()
    
    app.run(
        host=Config.WEB_HOST,
        port=Config.WEB_PORT,
        debug=Config.DEBUG
    ) 