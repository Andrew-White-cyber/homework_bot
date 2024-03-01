import time
import logging
import sys
from logging import StreamHandler
import os

from telegram import Bot
import requests
from dotenv import load_dotenv

from exceptions import CustomException

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
    if all([TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN]):
        return False
    else:
        return True


def send_message(bot, message):
    """Отправляем сообщение о статусе ДЗ."""
    try:
        logger.debug(f'sending message "{message}"')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logger.error(error)
    logger.debug(f'Сообщение "{message}" отправленно успешно!')


def get_api_answer(timestamp):
    """Получаем ответ от сервиса яндекс-домашка."""
    url = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(url, headers=headers, params=payload)
    except requests.RequestException:
        raise CustomException(f'Эндпоинт {url} не доступен!')
    if homework_statuses.status_code != 200:
        raise CustomException(f'Эндпоинт {url} не доступен!')
    return homework_statuses.json()


def check_response(response):
    """Проверяем формат ответа."""
    if not isinstance(response, dict):
        raise TypeError(f'response is not dict, its {type(response)}')
    if response.get('homeworks') is None:
        raise TypeError('В API ответе отсутствует важный ключ!(homeworks)')
    if not isinstance(response.get('homeworks'), list):
        homeworks = response.get('homeworks')
        raise TypeError(
            f'Ключ homeworks возвращает не список, а {homeworks}'
        )
    if response.get('current_date') is None:
        raise TypeError('В API ответе отсутствует важный ключ!(current_date)')


def parse_status(homework):
    """Получаем статус домашней работы."""
    if not isinstance(homework, dict):
        raise CustomException(f'homeworks is not dict, its {type(homework)}')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    if (status is None
            or status not in HOMEWORK_VERDICTS.keys()):
        raise CustomException(f'status {status} is unknown!')
    if verdict not in HOMEWORK_VERDICTS.values():
        raise CustomException(f'verdict {verdict} is unknown!')
    if homework.get('homework_name') is None:
        raise CustomException('Отсутствует название ДЗ!')
    homework_name = homework.get('homework_name')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens():
        logger.critical('Отсутствуют токены!')
        raise CustomException('Отсутствуют токены!')
    else:
        logger.debug('tokens fine!')
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
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )

    handler = StreamHandler(sys.stdout)
    logger.addHandler(handler)
    handler.setFormatter(formatter)
    main()
