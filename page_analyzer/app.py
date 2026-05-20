from datetime import datetime
import os

import validators
import requests
from flask import Flask, render_template,request, redirect, url_for, flash
import psycopg2
from bs4 import BeautifulSoup

from .db import get_db_connection
from .utils import normalize_url


app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '09ca872aa6a312027870de98ba97c813')

@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        url_input = request.form.get('url')
        normalized = normalize_url(url_input)
        if not validators.url(normalized) or len(normalized) > 255:
            flash('Incorrect URL', 'danger')
            return render_template('index.html'), 422
        conn = get_db_connection()
        try:
            with conn.cursor() as curs:
                # Проверка на существование
                curs.execute("SELECT id, name FROM urls WHERE name = %s", (normalized,))
                existing_url = curs.fetchone()
                conn.commit()
                if existing_url:
                    url_id = existing_url['id']
                    flash('Страница уже существует', 'info')
                else:
                    created_at = datetime.now()
                    curs.execute(
                        "INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id",
                        (normalized, created_at)
                    )
                    url_id = curs.fetchone()['id']
                    conn.commit()
                    flash('Страница успешно добавлена', 'success')
        finally:
            conn.close()
        return redirect(url_for('url_show', url_id=url_id))
    return render_template('index.html')

@app.route('/urls')
def urls_list():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Вывод всех URL, новые первые
            cur.execute("""
                        SELECT
                            urls.id,
                            urls.name,
                            last_check.created_at AS last_check_date,
                            last_check.status_code AS last_status_code
                        FROM urls
                        LEFT JOIN (
                            SELECT DISTINCT ON (url_id)
                                url_id, created_at, status_code
                            FROM url_checks
                        ORDER BY url_id, created_at DESC
                        ) AS last_check ON urls.id = last_check.url_id
                        ORDER BY urls.id DESC
                        """)
            urls = cur.fetchall()
    finally:
        conn.close()
    return render_template('urls.html', urls=urls)

@app.route('/urls/<int:url_id>')
def url_show(url_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as curs:
            curs.execute("SELECT * FROM urls WHERE id = %s", (url_id,))
            url = curs.fetchone()
            if url is None:
                flash('Страница не найдена', 'danger')
                return redirect(url_for('urls_list'))
            curs.execute(
                "SELECT * FROM url_checks WHERE url_id = %s ORDER BY id DESC",
                (url_id,)
            )
            checks = curs.fetchall()
    finally:
        conn.close()
    return render_template('url.html', url=url, checks=checks)


@app.route('/urls/<int:url_id>/checks',methods=['POST'])
def url_check(url_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as curs:
            # 1. достать имя сайта
            curs.execute("SELECT name FROM urls WHERE id = %s", (url_id,))
            row = curs.fetchone()
            if row is None:
                flash("Страница не найдена", 'danger')
                return redirect(url_for('urls_list'))
            site_url = row['name']

        try:
            response = requests.get(site_url, timeout=7)
            response.raise_for_status()
        except requests.RequestException:
            flash('Произошла ошибка при проверке', 'danger')
            return redirect(url_for('url_show', url_id=url_id))

        status_code = response.status_code

        soup = BeautifulSoup(response.text, 'html.parser')
        h1_tag = soup.find('h1')
        title_tag = soup.find('title')
        desc_tag = soup.find('meta', attrs={'name': 'description'})

        h1 = h1_tag.get_text(strip=True) if h1_tag else ''
        title = title_tag.get_text(strip=True) if title_tag else ''
        description = desc_tag.get('content', '') if desc_tag else ''

        with conn.cursor() as curs:
            created_at = datetime.now()
            curs.execute("INSERT INTO url_checks "
                         "(url_id, status_code, h1, title, description, created_at) "
                         "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                         (url_id, status_code, h1, title, description, created_at))
            conn.commit()
        flash('Страница успешно проверена', 'success')
    except psycopg2.Error:
        conn.rollback()
        flash('Произошла ошибка при проверке', 'danger')
    finally:
        conn.close()
    return redirect(url_for('url_show', url_id=url_id))




if __name__ == '__main__':
    app.run(debug=True)