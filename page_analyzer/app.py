from datetime import datetime
import os

import validators
from flask import Flask, render_template,request, redirect, url_for, flash

from .db import get_db_connection
from .utils import normalize_url

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '09ca872aa6a312027870de98ba97c813')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url_input = request.form.get('url')
        normalized = normalize_url(url_input)
        if not validators.url(normalized) or len(normalized) > 255:
            flash('Incorrect URL', 'A danger situation')
            return render_template('index.html'), 422
        conn = get_db_connection()
        try:
            with conn.cursor() as curs:
                # Проверка на существование
                curs.execute("SELECT id, name FROM urls WHERE name = %s", (normalized,))
                existing_url = curs.fetchone()
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
        return redirect(url_for('url_show', id=url_id))
    return render_template('index.html')

@app.route('/urls')
def urls_list():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Вывод всех URL, новые первые
            cur.execute("SELECT * FROM urls ORDER BY id DESC")
            urls = cur.fetchall()
    finally:
        conn.close()
    return render_template('urls.html', urls=urls)

@app.route('/urls/<int:url_id>')
def url_show(url_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM urls WHERE id = %s", (url_id,))
            url = cur.fetchone()
            if url is None:
                flash('Страница не найдена', 'danger')
                return redirect(url_for('urls_list'))
    finally:
        conn.close()
    return render_template('url.html', url=url)

if __name__ == '__main__':
    app.run(debug=True)