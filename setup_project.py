"""راه‌اندازی اولیه ویندوز: ایجاد نقش/دیتابیس، ساخت env، migration و حساب مدیر."""
from __future__ import annotations
import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_NAME = 'marketanalysis_db'
APP_USER = 'marketanalysis_app'

def run(*args):
    print('\n>', ' '.join(str(x) for x in args))
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)

def main():
    if sys.version_info < (3, 12):
        raise SystemExit('Python 3.12 یا جدیدتر لازم است. این برنامه را با Python محیط .venv اجرا کنید.')
    if sys.prefix == sys.base_prefix:
        raise SystemExit('محیط مجازی فعال نیست. این فایل را با .venv\\Scripts\\python.exe اجرا کنید یا ابتدا .venv را فعال کنید.')
    if not (ROOT / '.venv').exists():
        print('هشدار: پوشه .venv در کنار setup_project.py پیدا نشد؛ مطمئن شوید ریشه پروژه را باز کرده‌اید.')
    env_path = ROOT / '.env'
    if env_path.exists():
        answer = input('فایل .env از قبل وجود دارد. آن را حفظ کنیم و فقط migration اجرا شود؟ [Y/N]: ').strip().lower()
        if answer not in {'y', 'yes'}:
            raise SystemExit('برای جلوگیری از بازنویسی تنظیمات محلی، عملیات متوقف شد.')
        run('manage.py', 'makemigrations', 'accounts', 'marketdata', 'publishing', 'analyses', 'auditlog_app')
        run('manage.py', 'migrate', '--noinput')
        run('manage.py', 'seed_symbols')
        run('manage.py', 'check')
        answer = input('آیا حساب مدیر جدید Django ساخته شود؟ [Y/N]: ').strip().lower()
        if answer in {'y', 'yes'}:
            run('manage.py', 'createsuperuser')
        print('تنظیمات و Migrationها بررسی شدند. برای اجرای سامانه، python manage.py runserver را اجرا کنید.')
        return

    print('این مرحله فقط یک نقش و دیتابیس مخصوص برنامه در PostgreSQL محلی ایجاد می‌کند.')
    print('رمز postgres فقط در همین پنجره دریافت می‌شود و در فایل یا گزارش ثبت نخواهد شد.')
    import getpass
    admin_password = getpass.getpass('رمز کاربر PostgreSQL با نام postgres: ')
    if not admin_password:
        raise SystemExit('رمز خالی پذیرفته نیست.')
    app_password = secrets.token_urlsafe(32)
    try:
        import psycopg
        from psycopg import sql
        conn = psycopg.connect(host='127.0.0.1', port=5432, dbname='postgres', user='postgres',
                               password=admin_password, connect_timeout=10, autocommit=True)
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (APP_USER,))
            if cur.fetchone():
                cur.execute(sql.SQL('ALTER ROLE {} WITH LOGIN PASSWORD {}').format(
                    sql.Identifier(APP_USER), sql.Literal(app_password)))
            else:
                cur.execute(sql.SQL('CREATE ROLE {} WITH LOGIN PASSWORD {}').format(
                    sql.Identifier(APP_USER), sql.Literal(app_password)))
            cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', (DB_NAME,))
            if not cur.fetchone():
                cur.execute(sql.SQL('CREATE DATABASE {} OWNER {} ENCODING {}').format(
                    sql.Identifier(DB_NAME), sql.Identifier(APP_USER), sql.Literal('UTF8')))
            else:
                cur.execute(sql.SQL('ALTER DATABASE {} OWNER TO {}').format(
                    sql.Identifier(DB_NAME), sql.Identifier(APP_USER)))
        conn.close()
    except Exception as exc:
        raise SystemExit(f'اتصال یا ساخت دیتابیس ناموفق بود: {exc}\nسرویس PostgreSQL و رمز postgres را بررسی کنید.')

    secret = secrets.token_urlsafe(48)
    env_text = f'''SECRET_KEY={secret}
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
TIME_ZONE=Europe/Berlin
DB_NAME={DB_NAME}
DB_USER={APP_USER}
DB_PASSWORD={app_password}
DB_HOST=127.0.0.1
DB_PORT=5432
AI_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
AI_MAX_CANDLES=35
AI_REQUIRE_ADMIN_APPROVAL=True
ARTICLE_REQUIRE_ADMIN_APPROVAL=False
MAX_CSV_SIZE_MB=20
MAX_CANDLES_PER_REQUEST=5000
'''
    env_path.write_text(env_text, encoding='utf-8')
    print('\nفایل .env ساخته شد. رمز نقش برنامه به‌صورت تصادفی تولید و فقط در همان فایل ذخیره شد.')
    print('اکنون Migrationها و جداول دیتابیس ساخته می‌شوند...')
    run('manage.py', 'makemigrations', 'accounts', 'marketdata', 'publishing', 'analyses', 'auditlog_app')
    run('manage.py', 'migrate', '--noinput')
    run('manage.py', 'seed_symbols')
    run('manage.py', 'check')
    print('\nحالا حساب مدیر Django را بسازید. نام کاربری و رمز را خودتان انتخاب کنید.')
    run('manage.py', 'createsuperuser')
    print('\nراه‌اندازی اولیه تمام شد. برای اجرای سامانه، runserver.bat را اجرا کنید یا دستور python manage.py runserver را بزنید.')

if __name__ == '__main__':
    main()
