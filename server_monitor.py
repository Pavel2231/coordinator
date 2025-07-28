import requests
import time
import threading
import logging
from datetime import datetime
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServerMonitor:
    def __init__(self):
        self.servers_status = {}
        self.active_server = None
        self.monitoring_thread = None
        self.is_monitoring = False
        self.auto_restart_enabled = True
        self.failover_lock = threading.Lock()
        self.last_switch_time = None
        self.failover_in_progress = False
        
    def start_monitoring(self):
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        logger.info("Мониторинг серверов запущен")
        
    def stop_monitoring(self):
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        logger.info("Мониторинг серверов остановлен")
        
    def set_auto_restart(self, enabled):
        self.auto_restart_enabled = enabled
        logger.info(f"Автоперезапуск ботов: {'включен' if enabled else 'выключен'}")
        
    def _monitoring_loop(self):
        while self.is_monitoring:
            try:
                self._check_all_servers()
                self._handle_failover_with_delay_and_telegram()
                if self.auto_restart_enabled:
                    self._handle_auto_restart()
                time.sleep(Config.MONITORING_INTERVAL)
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                time.sleep(Config.MONITORING_INTERVAL)

    def _check_all_servers(self):
        for server_key, server_config in Config.SERVERS.items():
            status = self._check_server_health(server_config)
            self.servers_status[server_key] = status
            logger.info(f"Сервер {server_config['name']}: {status['status']}")

    def _check_server_health(self, server_config):
        try:
            response = requests.get(
                f"{server_config['agent_url']}/health",
                timeout=Config.HEALTH_CHECK_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'online',
                    'bots_status': data.get('bots_status', {}),
                    'all_bots_running': data.get('all_bots_running', False),
                    'last_check': datetime.now().isoformat(),
                    'response_time': response.elapsed.total_seconds(),
                    'details': data
                }
            else:
                return {
                    'status': 'error',
                    'bots_status': {},
                    'all_bots_running': False,
                    'last_check': datetime.now().isoformat(),
                    'error': f"HTTP {response.status_code}"
                }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'offline',
                'bots_status': {},
                'all_bots_running': False,
                'last_check': datetime.now().isoformat(),
                'error': str(e)
            }

    def _handle_auto_restart(self):
        for server_key, server_config in Config.SERVERS.items():
            server_status = self.servers_status.get(server_key, {})
            if server_key != self.active_server:
                continue
            if server_status.get('status') != 'online':
                continue
            bots_status = server_status.get('bots_status', {})
            for bot_id, bot_status in bots_status.items():
                if not bot_status.get('running', False):
                    logger.info(f"Автоперезапуск бота {bot_id} на сервере {server_config['name']}")
                    self.start_specific_bot(server_key, bot_id)

    def _handle_failover_with_delay_and_telegram(self):
        with self.failover_lock:
            if self.failover_in_progress:
                return
            self.failover_in_progress = True
        try:
            # Получаем список серверов по приоритету
            servers_priority = sorted(Config.SERVERS.items(), key=lambda x: x[1]['id'])
            primary_key = None
            backup_key = None
            third_key = None
            for key, cfg in servers_priority:
                if cfg['is_primary']:
                    primary_key = key
                elif backup_key is None:
                    backup_key = key
                else:
                    third_key = key
            # Получаем статусы
            primary_status = self.servers_status.get(primary_key, {})
            backup_status = self.servers_status.get(backup_key, {})
            third_status = self.servers_status.get(third_key, {})
            now = time.time()
            # Если primary работает и все боты запущены
            if (primary_status.get('status') == 'online' and primary_status.get('all_bots_running', False)):
                if self.active_server != primary_key:
                    self._notify_telegram(f"Переключение обратно на основной сервер: {Config.SERVERS[primary_key]['name']} через 1 минуту...")
                    time.sleep(60)
                    self._switch_to_server(primary_key, Config.SERVERS[primary_key])
            # Если primary не работает, но backup работает
            elif (primary_status.get('status') != 'online' or not primary_status.get('all_bots_running', False)) and (backup_status.get('status') == 'online' and backup_status.get('all_bots_running', False)):
                if self.active_server != backup_key:
                    self._notify_telegram(f"Основной сервер недоступен. Переключение на резервный сервер 2: {Config.SERVERS[backup_key]['name']} через 1 минуту...")
                    time.sleep(60)
                    self._switch_to_server(backup_key, Config.SERVERS[backup_key])
            # Если ни primary, ни backup не работают, но работает третий
            elif (primary_status.get('status') != 'online' or not primary_status.get('all_bots_running', False)) and (backup_status.get('status') != 'online' or not backup_status.get('all_bots_running', False)) and (third_status.get('status') == 'online' and third_status.get('all_bots_running', False)):
                if self.active_server != third_key:
                    self._notify_telegram(f"Основной и резервный 2 серверы недоступны. Переключение на резервный сервер 3: {Config.SERVERS[third_key]['name']} через 1 минуту...")
                    time.sleep(60)
                    self._switch_to_server(third_key, Config.SERVERS[third_key])
        finally:
            self.failover_in_progress = False

    def _notify_telegram(self, message):
        token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_CHAT_ID
        if not token or not chat_id:
            logger.warning("TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы!")
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": message})
            logger.info(f"Отправлено уведомление в Telegram: {message}")
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram: {e}")

    def _switch_to_server(self, server_key, server_config):
        try:
            for other_key, other_config in Config.SERVERS.items():
                if other_key != server_key:
                    self._stop_all_bots_on_server(other_config)
            self._start_all_bots_on_server(server_config)
            self.active_server = server_key
            logger.info(f"Успешно переключились на сервер: {server_config['name']}")
        except Exception as e:
            logger.error(f"Ошибка при переключении на сервер {server_config['name']}: {e}")

    def _start_all_bots_on_server(self, server_config):
        for bot_key, bot_config in server_config['bots'].items():
            try:
                response = requests.post(
                    f"{server_config['agent_url']}/start_bot",
                    json={
                        'bot_id': bot_key,
                        'command': bot_config['start_command']
                    },
                    timeout=Config.HEALTH_CHECK_TIMEOUT
                )
                if response.status_code == 200:
                    logger.info(f"Бот {bot_config['name']} запущен на сервере: {server_config['name']}")
                else:
                    logger.error(f"Ошибка запуска бота {bot_config['name']} на сервере {server_config['name']}: {response.status_code}")
            except Exception as e:
                logger.error(f"Ошибка запуска бота {bot_config['name']} на сервере {server_config['name']}: {e}")

    def _stop_all_bots_on_server(self, server_config):
        for bot_key, bot_config in server_config['bots'].items():
            try:
                response = requests.post(
                    f"{server_config['agent_url']}/stop_bot",
                    json={
                        'bot_id': bot_key,
                        'command': bot_config['stop_command']
                    },
                    timeout=Config.HEALTH_CHECK_TIMEOUT
                )
                if response.status_code == 200:
                    logger.info(f"Бот {bot_config['name']} остановлен на сервере: {server_config['name']}")
                else:
                    logger.error(f"Ошибка остановки бота {bot_config['name']} на сервере {server_config['name']}: {response.status_code}")
            except Exception as e:
                logger.error(f"Ошибка остановки бота {bot_config['name']} на сервере {server_config['name']}: {e}")

    def start_specific_bot(self, server_key, bot_id):
        if server_key not in Config.SERVERS:
            raise ValueError(f"Неизвестный сервер: {server_key}")
        server_config = Config.SERVERS[server_key]
        if bot_id not in server_config['bots']:
            raise ValueError(f"Неизвестный бот: {bot_id}")
        bot_config = server_config['bots'][bot_id]
        try:
            response = requests.post(
                f"{server_config['agent_url']}/start_bot",
                json={
                    'bot_id': bot_id,
                    'command': bot_config['start_command']
                },
                timeout=Config.HEALTH_CHECK_TIMEOUT
            )
            if response.status_code == 200:
                logger.info(f"Бот {bot_config['name']} запущен на сервере: {server_config['name']}")
                return True
            else:
                logger.error(f"Ошибка запуска бота {bot_config['name']}: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Ошибка запуска бота {bot_config['name']}: {e}")
            return False

    def stop_specific_bot(self, server_key, bot_id):
        if server_key not in Config.SERVERS:
            raise ValueError(f"Неизвестный сервер: {server_key}")
        server_config = Config.SERVERS[server_key]
        if bot_id not in server_config['bots']:
            raise ValueError(f"Неизвестный бот: {bot_id}")
        bot_config = server_config['bots'][bot_id]
        try:
            response = requests.post(
                f"{server_config['agent_url']}/stop_bot",
                json={
                    'bot_id': bot_id,
                    'command': bot_config['stop_command']
                },
                timeout=Config.HEALTH_CHECK_TIMEOUT
            )
            if response.status_code == 200:
                logger.info(f"Бот {bot_config['name']} остановлен на сервере: {server_config['name']}")
                return True
            else:
                logger.error(f"Ошибка остановки бота {bot_config['name']}: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Ошибка остановки бота {bot_config['name']}: {e}")
            return False

    def restart_specific_bot(self, server_key, bot_id):
        logger.info(f"Перезапуск бота {bot_id} на сервере {server_key}")
        stop_success = self.stop_specific_bot(server_key, bot_id)
        if stop_success:
            time.sleep(2)
            return self.start_specific_bot(server_key, bot_id)
        return False

    def get_status(self):
        return {
            'servers': self.servers_status,
            'active_server': self.active_server,
            'is_monitoring': self.is_monitoring,
            'auto_restart_enabled': self.auto_restart_enabled
        }
    
    def manual_switch(self, server_key):
        if server_key not in Config.SERVERS:
            raise ValueError(f"Неизвестный сервер: {server_key}")
        server_config = Config.SERVERS[server_key]
        self._switch_to_server(server_key, server_config)
        return True 