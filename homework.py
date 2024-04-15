import time
import logging
import sys
from logging import StreamHandler
import os

from telegram import Bot
import requests
from dotenv import load_dotenv

from exceptions import EndPointException

load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN_PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)


def check_tokens():
    """Проверяем доступность токенов."""
    return not all([TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN])


def send_message(bot, message):
    """Отправляем сообщение о статусе ДЗ."""
    try:
        logger.debug(f'Отправка сообщения: "{message}"')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logger.error(error)
    logger.debug(f'Сообщение "{message}" отправленно успешно!')


def get_api_answer(timestamp):
    """Получаем ответ от сервиса Яндекс-Домашка."""
    url = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(url, headers=headers, params=payload)
    except requests.RequestException:
        raise EndPointException(f'Эндпоинт {url} не доступен!')
    if homework_statuses.status_code != 200:
        raise EndPointException(
            f'Код ответа не 200, а {homework_statuses.status_code},'
            f'причина: {homework_statuses.reason}'
        )
    return homework_statuses.json()


def check_response(response):
    """Проверяем формат ответа."""
    if not isinstance(response, dict):
        raise TypeError(f'response не является словарём: {type(response)}')
    if 'homeworks' not in response:
        raise TypeError('В API ответе отсутствует важный ключ!(homeworks)')
    else:
        homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(
            f'Ключ homeworks возвращает не список, а {type(homeworks)}'
        )
    if response.get('current_date') is None:
        raise TypeError('В API ответе отсутствует важный ключ!(current_date)')
    return response.get('homeworks')[0]


def parse_status(homework):
    """Получаем статус домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError(
            f'homeworks не является словарём: {type(homework)}'
        )
    if 'status' not in homework:
        raise KeyError('Ключ status отсутствует!')
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Неизвестное заключение о ДЗ!')
    verdict = HOMEWORK_VERDICTS[status]
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует название ДЗ!')
    homework_name = homework['homework_name']

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens():
        logger.critical('Отсутствуют токены!')
        sys.exit('Отсутствуют токены!')
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            answer = get_api_answer(timestamp)
            message = parse_status(check_response(answer))
            send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )

    handler = StreamHandler(sys.stdout)
    logger.addHandler(handler)
    handler.setFormatter(formatter)
    main()
