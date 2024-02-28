
import exceptions
import logging
import os
import requests
import sys
import time
from dotenv import load_dotenv
from http import HTTPStatus
from logging import StreamHandler
from telegram import Bot

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)
handler = StreamHandler(stream=sys.stdout)


def check_tokens():
    """
    Функция проверяет доступность переменных окружения.
    Если хоть одна отстутствует останавливает работу бота
    и выводит в лог какая конкретно отсутствует.
    """
    if not PRACTICUM_TOKEN:
        logging.critical(
            "Отсутствует обязательная переменная окружения:"
            " 'PRACTICUM_TOKEN'\n"
            'Программа принудительно остановлена'
        )
        sys.exit(-1)
    elif not TELEGRAM_TOKEN:
        logging.critical(
            "Отсутствует обязательная переменная окружения: 'TELEGRAM_TOKEN'\n"
            'Программа принудительно остановлена'
        )
        sys.exit(-1)
    elif not TELEGRAM_CHAT_ID:
        logging.critical(
            "Отсутствует обязательная переменная окружения:"
            " 'TELEGRAM_CHAT_ID'\n"
            'Программа принудительно остановлена'
        )
        sys.exit(-1)


def send_message(bot, message):
    """
    Функция отправления сообщения полученного в параметре.
    Отправляет в указанный в переменной окружения телеграм чат.
    """
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.debug(f'Бот отправил сообщение: {message}')


def get_api_answer(timestamp):
    """
    Функция делает запрос к эндпоинту API-сервиса.
    Возвращает ответ приведенный к типам данных Python.
    """
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            logging.error(f'Эднпоинт {ENDPOINT} недоступен.'
                          f'Код ответа API:{response.status_code}')
            raise exceptions.EndpointError(
                'Возникла ошибка при обращении к эндпоинту'
            )
        else:
            return response.json()
    except requests.RequestException as error:
        logging.error(f'Эднпоинт {ENDPOINT} недоступен: {error}')


def check_response(response):
    """
    Функция проверяет присутствуют ли данные по ключу в ответе от API.
    И проверяет соответствуют ли они необходимому формату.
    """
    if not isinstance(response, dict):
        raise TypeError('Ответ получен в некорректном формате')
    elif 'homeworks' not in response:
        raise Exception('Отсутствует ключ homeworks в ответе')
    elif not isinstance(response['homeworks'], list):
        raise TypeError('Ответ получен в некорректном формате')
    else:
        return response['homeworks']


def parse_status(homework):
    """Функция извлекает из информации о домашней работе статус этой работы."""
    if 'homework_name' not in homework:
        raise KeyError("Отсутствует ключ 'homework_name' в ответе")
    elif homework['status'] in HOMEWORK_VERDICTS:
        homework_name = homework['homework_name']
        verdict = homework['status']
        return (f'Изменился статус проверки работы "{homework_name}".'
                f'{HOMEWORK_VERDICTS[verdict]}')
    else:
        logging.error('Получен несуществующий статус домашней работы')
        raise exceptions.ParseError('Ошибка парсинга')


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = []

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if len(homework) == 0:
                pass
            else:
                message = parse_status(homework[0])
                if message != last_message:
                    try:
                        send_message(bot, message)
                        last_message = message
                    except Exception as error:
                        logging.error(
                            f'Ошибка отправки сообщения ботом: {error}'
                        )
                else:
                    pass
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
