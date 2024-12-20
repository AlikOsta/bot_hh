import requests
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from bs4 import BeautifulSoup
import re
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bot.log'
)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')

bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def send_vacancy_to_telegram(vacancy):
    """
    Формирует и отправляет сообщение о вакансии в Telegram группу.
    """
    title = vacancy['name']
    description = vacancy['description'] or "Описание отсутствует"
    

    if description != "Описание отсутствует":
        soup = BeautifulSoup(description, 'html.parser')
        description = soup.get_text()

        description = re.sub(r'\s+', ' ', description).strip()

        description = description[:400].rsplit(' ', 1)[0] + '...'

    experience = vacancy.get('experience', {}).get('name', "Не указано")
    salary = vacancy.get('salary', "Не указана")
    # company = vacancy['employer']['name']
    url = vacancy['alternate_url']

    if salary and isinstance(salary, dict):
        salary_from = salary.get('from')
        salary_to = salary.get('to')
        currency = salary.get('currency', '')
        salary = f"{salary_from or ''} - {salary_to or ''} {currency}".strip(" - ")
    if salary == None:
        salary = "Не указана"

    work_format = "Удаленная работа"
    
    message = (
        f"📌 *{title}*\n"
        f"*Оплата:* {salary}\n"
        f"*Опыт:* {experience}\n\n"
        f"*Описание:* {description}\n"
        f"*Формат работы:* {work_format}\n\n"
        # f"*Компания:* {company}"
    )

    keyboard = [[InlineKeyboardButton("Посмотреть вакансию", url=url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(
        chat_id=TELEGRAM_GROUP_ID,
        text=message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


def get_vacancy_details(vacancy_id):
    url = f'https://api.hh.ru/vacancies/{vacancy_id}'
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка при получении детальной информации о вакансии {vacancy_id}: {response.status_code}")
        return None


async def get_vacancies(keyword, seen_vacancies):
    url = 'https://api.hh.ru/vacancies'
    new_vacancies_found = False

    params = {
        'text': keyword,
        'per_page': 5,
        'page': 0,
        'schedule': 'remote',
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        vacancies = response.json()
        for item in vacancies['items']:
            vacancy_id = item['id']
            if vacancy_id not in seen_vacancies:
                seen_vacancies.add(vacancy_id)
                new_vacancies_found = True

                details = get_vacancy_details(vacancy_id)
                if details:
                    await send_vacancy_to_telegram(details)
    else:
        print(f"Ошибка при выполнении запроса: {response.status_code}")

    if not new_vacancies_found:
        print("Новых вакансий не найдено.")


async def main():
    keyword = ""  
    seen_vacancies = set()  

    while True:
        await get_vacancies(keyword, seen_vacancies)
        await asyncio.sleep(60 * 60 * 1) 


if __name__ == "__main__":
    asyncio.run(main())
