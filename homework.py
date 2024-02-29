import time
import logging
import sys
from logging import StreamHandler
import os

from telegram import Bot
import requests


from dotenv import load_dotenv

from exceptions import MyException

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
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

handler = StreamHandler(sys.stdout)
logger.addHandler(handler)
handler.setFormatter(formatter)


def check_tokens():
    """Проверяем доступность токенов."""
    if ((PRACTICUM_TOKEN is None)
        or (TELEGRAM_TOKEN is None)
            or (TELEGRAM_CHAT_ID is None)):
        logger.critical('tokens.')
        raise MyException('Missing tokens.')
    else:
        logger.debug('tokens fine.')
        pass


def send_message(bot, message):
    """Отправляем сообщение о статусе ДЗ."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logger.error(error)
    logger.debug('message success')


def get_api_answer(timestamp):
    """Получаем ответ от сервиса яндекс-домашка."""
    url = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(url, headers=headers, params=payload)
    except requests.RequestException:
        logger.error('Эндпоинт не доступен!')
    if homework_statuses.status_code != 200:
        logger.error('Эндпоинт не доступен!')
        raise MyException
    return homework_statuses.json()


def check_response(response):
    """Проверяем формат ответа."""
    if not isinstance(response, dict):
        raise TypeError('not dict')
    if response.get('homeworks') is None:
        logger.error('missing key!')
        raise TypeError('empty')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Not list')
    if response.get('current_date') is None:
        logger.error('missing key!')
        raise TypeError
    if len(response.get('homeworks')) == 0:
        response.get('homeworks').append({
            "id": 124,
            "status": "rejected",
            "homework_name": "username__hw_python_oop.zip",
            "reviewer_comment": "Код не по PEP8, нужно исправить",
            "date_updated": "2020-02-13T16:42:47Z",
            "lesson_name": "Итоговый проект"
        },)


def parse_status(homework):
    """Получаем статус домашней работы."""
    if type(homework) is not dict:
        raise MyException('not dict')
    if (homework.get('status') is None
            or homework.get('status') not in HOMEWORK_VERDICTS.keys()):
        logger.error('unknown status!')
        raise MyException('meh')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict not in HOMEWORK_VERDICTS.values():
        logger.error('verdict error!')
        raise MyException('oi')
    if homework.get('homework_name') is None:
        raise MyException('meh')
    homework_name = homework.get('homework_name')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            answer = get_api_answer(timestamp)
            check_response(answer)
            message = parse_status(answer.get('homeworks')[0])
            send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
