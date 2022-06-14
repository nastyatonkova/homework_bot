import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv
from telegram.ext import CommandHandler, Updater

import exceptions

load_dotenv()
logger = logging.getLogger(__name__)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'reviewing': 'Работа взята в ревью,',
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Sending message to the chat."""
    try:
        result = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Message sent successfully')
    except telegram.error.TelegramError as telegram_error:
        raise telegram.error.TelegramError(
            f'Error while sending the message to chat: {telegram_error}'
        ) from telegram_error
    return result


def wake_up(update, context):
    """Hello to user."""
    chat = update.effective_chat
    name = update.message.chat.first_name
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Hello, {}. I can help you to know '
            'the status of your homework').format(name),
    )


def get_api_answer(current_timestamp):
    """Making request to the endpoint of API-service."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logger.info('Trying to connect to endpoint')
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            msg = ('Error by requesting the endpoint')
            raise exceptions.APIResponseStatusCodeException(msg)
    except Exception as error:
        raise Exception(f'Error by requesting the endpoint: {error}')
    else:
        return response.json()


def check_response(response):
    """Check on correctness of API response."""
    if response is None:
        msg = (f'In the API response there is no dict '
               f'with homeworks: {type(response)}')
        raise exceptions.CheckResponseException(msg)
    if not isinstance(response, dict):
        msg = ('Incorrect values in the response')
        raise TypeError(msg)
    if 'homeworks' not in response:
        msg = ('Key access error by homeworks')
        raise KeyError(msg)
    if not response['homeworks']:
        return {}
    homeworks_list = response.get('homeworks')
    if not isinstance(homeworks_list, list):
        msg = ('With the key "homework" cannot find any list')
        raise TypeError(msg)
    return homeworks_list


def parse_status(homework):
    """Getting the information and status of homework."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        msg = ('Access error by homework_name')
        raise KeyError(msg)
    status = homework.get('status')
    if status is None:
        raise KeyError(f'Key error in {status}')
    hw_verdict = HOMEWORK_VERDICTS[status]
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Unknown status of '
                         f'homework {status}')
    return (f'Изменился статус проверки '
            f'работы "{homework_name}". {hw_verdict}')


def check_tokens():
    """Check availibility of tokens."""
    logger.info('Start checking the availability of environmental tokens')
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """How the bot is functioning."""
    if not check_tokens():
        msg = 'Missing environmental tokens'
        logger.critical(msg)
        raise exceptions.MissingRequiredTokenException(msg)

    updater = Updater(TELEGRAM_TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', wake_up))
    updater.start_polling()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status_old = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            status = parse_status(homework[0])
            if status_old != status:
                send_message(bot, status)
                status_old = status
            current_timestamp = response.get('current_date')
        except exceptions.APIResponseStatusCodeException as error:
            error_message = f'Error in programm: {error}'
            status_old = error_message
            logging.exception(error_message)
            send_message(bot, error_message)
        except telegram.error.TelegramError as telegram_error:
            error_message = f'Error in programm: {telegram_error}'
            logging.exception(error_message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    )
    handler = StreamHandler(sys.stdout)
    logger.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    main()
