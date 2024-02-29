import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from telegram import Bot

import exceptions

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


def check_tokens():
    """
    Функция проверяет доступность переменных окружения.
    Если хоть одна отстутствует останавливает работу бота
    и выводит в лог какая конкретно отсутствует.
    """
    tokens = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    final_token_list = []
    for token in tokens:
        if not globals()[token]:
            final_token_list.append(token)
    if final_token_list:
        logging.critical(
            "Отсутствует обязательная переменная окружения:"
            f" {' '.join(final_token_list)}\n"
            'Программа принудительно остановлена'
        )
        sys.exit(-1)


def send_message(bot, message):
    """
    Функция отправления сообщения полученного в параметре.
    Отправляет в указанный в переменной окружения телеграм чат.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение: {message}')
    except telegram.TelegramError as error:
        logging.error(f'Ошибка отправки сообщения ботом: {error}')


def get_api_answer(timestamp):
    """
    Функция делает запрос к эндпоинту API-сервиса.
    Возвращает ответ приведенный к типам данных Python.
    """
    try:
        logging.debug(f'Совершается запрос на адрес {ENDPOINT} с параметрами:'
                      f'OAuth: PRACTICUM_TOKEN и временной меткой {timestamp}')
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException:
        raise ConnectionError
    if response.status_code != HTTPStatus.OK:
        raise exceptions.EndpointError(
            f'Возникла ошибка при обращении к эндпоинту : {ENDPOINT}.'
            'Запрос совершен с параметрами OAuth: PRACTICUM_TOKEN'
            f' и временной меткой {timestamp}'
            f'Ошибка - {response.reason}'
        )
    return response.json()


def check_response(response):
    """
    Функция проверяет присутствуют ли данные по ключу в ответе от API.
    И проверяет соответствуют ли они необходимому формату.
    """
    logging.debug('Начата проверка ответа сервера')
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ получен в некорректном формате {type(response)}'
        )
    elif 'homeworks' not in response:
        raise KeyError('Отсутствует ключ homeworks в ответе')
    elif 'current_date' not in response:
        raise KeyError("Отсутствует ключ 'current_date' в ответе")
    elif not isinstance(response['homeworks'], list):
        raise TypeError(
            f'Ответ получен в некорректном формате {type(response)}'
        )
    logging.debug('Успешно завершена проверка ответа сервера')
    return response['homeworks']


def parse_status(homework):
    """Функция извлекает из информации о домашней работе статус этой работы."""
    logging.debug('Начата проверка статуса домашней работы')
    if 'homework_name' not in homework:
        raise KeyError("Отсутствует ключ 'homework_name' в ответе")
    elif 'status' not in homework:
        raise KeyError("Отсутствует ключ 'status' в ответе")
    elif homework['status'] in HOMEWORK_VERDICTS:
        homework_name = homework['homework_name']
        verdict = homework['status']
        logging.debug('Успешно завершена проверка статуса домашней работы')
        return (f'Изменился статус проверки работы "{homework_name}".'
                f'{HOMEWORK_VERDICTS[verdict]}')
    else:
        raise exceptions.ParseError(
            'Ошибка парсинга. Получен неккоректный'
            f'статус домашней работы: {homework['status']}'
        )


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
            if not len(homework):
                logging.debug('Отсутствует новый статус домашней работы')
            else:
                message = parse_status(homework[0])
                send_message(bot, message)
                last_message = message
            timestamp = int(time.time())
        except Exception as error:
            logging.error(
                f'Во время выполнения программы получена ошибка: {error}',
                exc_info=True)
            message = f'Сбой в работе программы: {error}'
            if last_message != message:
                send_message(bot, message)
            else:
                pass
            last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=('%(asctime)s [%(levelname)s] %(message)s [%(lineno)s]'),
        stream=sys.stdout
    )
    main()
