import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from telegram.ext import CommandHandler, Updater

import exceptions

load_dotenv()
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(os.sys.stdout)]
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'reviewing': 'Работа взята в ревью,',
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Sending message to the chat."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Message sent')
    except exceptions.SendMessageFailure:
        logger.error('Error while sending the message to chat')


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
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except exceptions.APIResponseStatusCodeException:
        logger.error('Error by requesting the endpoint')
    if response.status_code != HTTPStatus.OK:
        msg = 'Error by requesting the endpoint'
        logger.error(msg)
        raise exceptions.APIResponseStatusCodeException(msg)
    return response.json()


def check_response(response):
    """Check on correctness of API response."""
    try:
        homeworks_list = response['homeworks']
    except KeyError as e:
        msg = f'Key access error by homeworks: {e}'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if homeworks_list is None:
        msg = 'In the API response there is no dict with homeworks'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if len(homeworks_list) == 0:
        msg = 'There are no homeworks'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if not isinstance(homeworks_list, list):
        msg = 'In the API response homeworks are not listed'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    return homeworks_list


def parse_status(homework):
    """Getting the information and status of homework."""
    try:
        homework_name = homework.get('homework_name')
    except KeyError as e:
        msg = f'Key access error by homework_name: {e}'
        logger.error(msg)
    try:
        homework_status = homework.get('status')
    except KeyError as e:
        msg = f'Key access error by status: {e}'
        logger.error(msg)

    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        msg = 'Unknown status of homework'
        logger.error(msg)
        raise exceptions.UnknownHWStatusException(msg)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Check availibility of tokens."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if token is None:
            logging.critical('Not found environmental token')
            return False
    logging.info('Successfuly found all tokens')
    return True


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
    previous_status = None
    previous_error = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
        except exceptions.IncorrectAPIResponseException as e:
            if str(e) != previous_error:
                previous_error = str(e)
                send_message(bot, e)
            logger.error(e)
            time.sleep(RETRY_TIME)
            continue
        try:
            homeworks = check_response(response)
            hw_status = homeworks[0].get('status')
            if hw_status != previous_status:
                previous_status = hw_status
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('There is no change in status')

            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Error in programm: {error}'
            if previous_error != str(error):
                previous_error = str(error)
                send_message(bot, message)
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
