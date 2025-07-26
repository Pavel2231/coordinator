import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Настройки Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Настройки серверов с множественными ботами
    SERVERS = {
        'server1': {
            'id': 1,
            'name': 'Сервер 1',
            'url': os.getenv('SERVER1_URL', 'http://server1:5001'),
            'agent_url': os.getenv('SERVER1_AGENT_URL', 'http://server1:5001'),
            'is_primary': True,
            'bots': {
                'bot1': {
                    'name': 'Бот 1',
                    'start_command': os.getenv('SERVER1_BOT1_COMMAND', 'cd /path/to/bot1 && python bot1.py'),
                    'stop_command': os.getenv('SERVER1_BOT1_STOP', 'pkill -f bot1.py'),
                    'process_name': os.getenv('SERVER1_BOT1_PROCESS', 'bot1.py')
                },
                'bot2': {
                    'name': 'Бот 2',
                    'start_command': os.getenv('SERVER1_BOT2_COMMAND', 'cd /path/to/bot2 && python bot2.py'),
                    'stop_command': os.getenv('SERVER1_BOT2_STOP', 'pkill -f bot2.py'),
                    'process_name': os.getenv('SERVER1_BOT2_PROCESS', 'bot2.py')
                },
                'bot3': {
                    'name': 'Бот 3',
                    'start_command': os.getenv('SERVER1_BOT3_COMMAND', 'cd /path/to/bot3 && python bot3.py'),
                    'stop_command': os.getenv('SERVER1_BOT3_STOP', 'pkill -f bot3.py'),
                    'process_name': os.getenv('SERVER1_BOT3_PROCESS', 'bot3.py')
                },
                'bot4': {
                    'name': 'Бот 4',
                    'start_command': os.getenv('SERVER1_BOT4_COMMAND', 'cd /path/to/bot4 && python bot4.py'),
                    'stop_command': os.getenv('SERVER1_BOT4_STOP', 'pkill -f bot4.py'),
                    'process_name': os.getenv('SERVER1_BOT4_PROCESS', 'bot4.py')
                }
            }
        },
        'server2': {
            'id': 2,
            'name': 'Сервер 2',
            'url': os.getenv('SERVER2_URL', 'http://server2:5002'),
            'agent_url': os.getenv('SERVER2_AGENT_URL', 'http://server2:5002'),
            'is_primary': False,
            'bots': {
                'bot1': {
                    'name': 'Бот 1',
                    'start_command': os.getenv('SERVER2_BOT1_COMMAND', 'cd /path/to/bot1 && python bot1.py'),
                    'stop_command': os.getenv('SERVER2_BOT1_STOP', 'pkill -f bot1.py'),
                    'process_name': os.getenv('SERVER2_BOT1_PROCESS', 'bot1.py')
                },
                'bot2': {
                    'name': 'Бот 2',
                    'start_command': os.getenv('SERVER2_BOT2_COMMAND', 'cd /path/to/bot2 && python bot2.py'),
                    'stop_command': os.getenv('SERVER2_BOT2_STOP', 'pkill -f bot2.py'),
                    'process_name': os.getenv('SERVER2_BOT2_PROCESS', 'bot2.py')
                },
                'bot3': {
                    'name': 'Бот 3',
                    'start_command': os.getenv('SERVER2_BOT3_COMMAND', 'cd /path/to/bot3 && python bot3.py'),
                    'stop_command': os.getenv('SERVER2_BOT3_STOP', 'pkill -f bot3.py'),
                    'process_name': os.getenv('SERVER2_BOT3_PROCESS', 'bot3.py')
                },
                'bot4': {
                    'name': 'Бот 4',
                    'start_command': os.getenv('SERVER2_BOT4_COMMAND', 'cd /path/to/bot4 && python bot4.py'),
                    'stop_command': os.getenv('SERVER2_BOT4_STOP', 'pkill -f bot4.py'),
                    'process_name': os.getenv('SERVER2_BOT4_PROCESS', 'bot4.py')
                }
            }
        }
    }
    
    # Настройки мониторинга
    MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', 30))  # секунды
    HEALTH_CHECK_TIMEOUT = int(os.getenv('HEALTH_CHECK_TIMEOUT', 10))  # секунды
    
    # Настройки веб-интерфейса
    WEB_PORT = int(os.getenv('WEB_PORT', 5000))
    WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
    
    # Настройки для хостинга
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',') 