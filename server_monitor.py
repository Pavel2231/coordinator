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
        self.auto_restart_enabled = True  # Включение автоперезапуска
        
    def start_monitoring(self):
        """Запуск мониторинга серверов"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
            
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        logger.info("Мониторинг серверов запущен")
        
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        logger.info("Мониторинг серверов остановлен")
        
    def set_auto_restart(self, enabled):
        """Включение/выключение автоперезапуска"""
        self.auto_restart_enabled = enabled
        logger.info(f"Автоперезапуск ботов: {'включен' if enabled else 'выключен'}")
        
    def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while self.is_monitoring:
            try:
                self._check_all_servers()
                self._handle_failover()
                if self.auto_restart_enabled:
                    self._handle_auto_restart()
                time.sleep(Config.MONITORING_INTERVAL)
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                time.sleep(Config.MONITORING_INTERVAL)
                
    def _check_all_servers(self):
        """Проверка всех серверов"""
        for server_key, server_config in Config.SERVERS.items():
            status = self._check_server_health(server_config)
            self.servers_status[server_key] = status
            logger.info(f"Сервер {server_config['name']}: {status['status']}")
            
    def _check_server_health(self, server_config):
        """Проверка здоровья сервера"""
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
        """Обработка автоперезапуска остановленных ботов"""
        for server_key, server_config in Config.SERVERS.items():
            server_status = self.servers_status.get(server_key, {})
            
            # Проверяем только активный сервер
            if server_key != self.active_server:
                continue
                
            if server_status.get('status') != 'online':
                continue
                
            bots_status = server_status.get('bots_status', {})
            
            for bot_id, bot_status in bots_status.items():
                if not bot_status.get('running', False):
                    logger.info(f"Автоперезапуск бота {bot_id} на сервере {server_config['name']}")
                    self.start_specific_bot(server_key, bot_id)
                    
    def _handle_failover(self):
        """Обработка автоматического переключения"""
        primary_server = None
        backup_server = None
        
        # Определяем primary и backup серверы
        for server_key, server_config in Config.SERVERS.items():
            if server_config['is_primary']:
                primary_server = (server_key, server_config)
            else:
                backup_server = (server_key, server_config)
                
        if not primary_server or not backup_server:
            logger.error("Не настроены primary и backup серверы")
            return
            
        primary_key, primary_config = primary_server
        backup_key, backup_config = backup_server
        
        primary_status = self.servers_status.get(primary_key, {})
        backup_status = self.servers_status.get(backup_key, {})
        
        # Если primary сервер работает и все боты запущены
        if (primary_status.get('status') == 'online' and 
            primary_status.get('all_bots_running', False)):
            
            if self.active_server != primary_key:
                logger.info(f"Переключение на primary сервер: {primary_config['name']}")
                self._switch_to_server(primary_key, primary_config)
                
        # Если primary сервер не работает, но backup работает
        elif (primary_status.get('status') != 'online' and 
              backup_status.get('status') == 'online'):
            
            if self.active_server != backup_key:
                logger.info(f"Переключение на backup сервер: {backup_config['name']}")
                self._switch_to_server(backup_key, backup_config)
                
        # Если primary сервер восстановился
        elif (primary_status.get('status') == 'online' and 
              self.active_server == backup_key):
            
            logger.info(f"Primary сервер восстановлен, переключение обратно: {primary_config['name']}")
            self._switch_to_server(primary_key, primary_config)
            
    def _switch_to_server(self, server_key, server_config):
        """Переключение на указанный сервер"""
        try:
            # Останавливаем все боты на всех серверах
            for other_key, other_config in Config.SERVERS.items():
                if other_key != server_key:
                    self._stop_all_bots_on_server(other_config)
                    
            # Запускаем все боты на выбранном сервере
            self._start_all_bots_on_server(server_config)
            self.active_server = server_key
            
            logger.info(f"Успешно переключились на сервер: {server_config['name']}")
            
        except Exception as e:
            logger.error(f"Ошибка при переключении на сервер {server_config['name']}: {e}")
            
    def _start_all_bots_on_server(self, server_config):
        """Запуск всех ботов на сервере"""
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
        """Остановка всех ботов на сервере"""
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
        """Запуск конкретного бота"""
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
        """Остановка конкретного бота"""
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
        """Перезапуск конкретного бота"""
        logger.info(f"Перезапуск бота {bot_id} на сервере {server_key}")
        
        # Сначала останавливаем
        stop_success = self.stop_specific_bot(server_key, bot_id)
        if stop_success:
            # Ждем немного
            time.sleep(2)
            # Затем запускаем
            return self.start_specific_bot(server_key, bot_id)
        return False
            
    def get_status(self):
        """Получение текущего статуса всех серверов"""
        return {
            'servers': self.servers_status,
            'active_server': self.active_server,
            'is_monitoring': self.is_monitoring,
            'auto_restart_enabled': self.auto_restart_enabled
        }
        
    def manual_switch(self, server_key):
        """Ручное переключение на сервер"""
        if server_key not in Config.SERVERS:
            raise ValueError(f"Неизвестный сервер: {server_key}")
            
        server_config = Config.SERVERS[server_key]
        self._switch_to_server(server_key, server_config)
        return True 