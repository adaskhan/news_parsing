import datetime

import requests
import psycopg2
from bs4 import BeautifulSoup
from translate import Translator

translator = Translator(from_lang="ru", to_lang="en")

# Подключение к базе данных PostgreSQL
host = 'localhost'
user = 'user_name'
password = 'password'
db_name = 'database_name'

conn = psycopg2.connect(
    host=host,
    database=db_name,
    user=user,
    password=password
)

# Определите схему таблицы ресурсов
resource_table = """CREATE TABLE IF NOT EXISTS resources (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255),
                        url VARCHAR(255),
                        top_tag VARCHAR(255),
                        bottom_tag VARCHAR(255),
                        title_cut VARCHAR(255),
                        date_cut VARCHAR(255)
                    );"""

items_table = """CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    res_id INTEGER REFERENCES resources(id),
                    link VARCHAR(255),
                    title VARCHAR(255),
                    content TEXT,
                    nd_date INTEGER,
                    s_date INTEGER,
                    not_date DATE
                );"""

# Создайте таблицы ресурсов и элементов, если они еще не существуют
cur = conn.cursor()
cur.execute(resource_table)
cur.execute(items_table)
conn.commit()

# Извлеките ресурсы из базы данных
cur.execute("SELECT id, url, top_tag, bottom_tag, title_cut, date_cut FROM resources;")
resources = cur.fetchall()

for resource in resources:
    response = requests.get(resource[1])
    soup = BeautifulSoup(response.text, 'html.parser')

    links = soup.find_all(resource[2], class_='article-preview-mixed article-preview-mixed--secondary article-preview-mixed--with-absolute-secondary-item js-article-link')

    for link in links:
        article_url = link.get('href')

        article_response = requests.get(article_url)
        article_soup = BeautifulSoup(article_response.text, 'html.parser')

        title = article_soup.find(resource[4], class_='main-headline js-main-headline').text.strip()
        print(title)
        content = article_soup.find(resource[3], class_='formatted-body io-article-body').text.strip()
        nd_date_str = article_soup.find(resource[5], class_='datetime datetime--publication').text.strip()
        nd_date_str_en = translator.translate(nd_date_str)
        if 'Today' in nd_date_str_en or 'Yesterday' in nd_date_str_en:
            nd_date = int(datetime.datetime.strptime(nd_date_str_en[nd_date_str_en.find(',')+2:], '%d %B %Y, %H:%M').timestamp())
        else:
            nd_date = int(datetime.datetime.strptime(nd_date_str_en, '%d %B %Y, %H:%M').timestamp())
        s_date = int(datetime.datetime.now().timestamp())
        if 'Today' in nd_date_str_en or 'Yesterday' in nd_date_str_en:
            not_date = datetime.datetime.strptime(nd_date_str_en[nd_date_str_en.find(',')+2:], '%d %B %Y, %H:%M')
        else:
            not_date = datetime.datetime.strptime(nd_date_str_en, '%d %B %Y, %H:%M')

        # Вставьте данные статьи в базу данных
        cur.execute(
            "INSERT INTO items (res_id, link, title, content, nd_date, s_date, not_date) VALUES (%s, %s, %s, %s, %s, %s, %s);",
            (resources.index(resource)+1, article_url, title, content, nd_date, s_date, not_date))
        conn.commit()

# Закройте подключение к базе данных
cur.close()
conn.close()

print("All news have been parsed successfully")
