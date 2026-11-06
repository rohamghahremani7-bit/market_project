from django.core.management.base import BaseCommand
from marketdata.models import Symbol

class Command(BaseCommand):
    help = 'نمادهای نمونه را ایجاد یا به‌روزرسانی می‌کند.'
    def handle(self, *args, **options):
        rows = [
            ('GOLD', 'طلای جهانی', 'Commodity', 'نمایش عمومی طلا'),
            ('XAUUSD', 'Gold / US Dollar', 'Commodity', 'نماد متداول طلای جهانی'),
            ('EURUSD', 'Euro / US Dollar', 'Forex', 'جفت‌ارز یورو و دلار'),
            ('BTCUSD', 'Bitcoin / US Dollar', 'Crypto', 'بیت‌کوین در برابر دلار'),
            ('NASDAQ', 'NASDAQ 100', 'Index', 'شاخص نزدک ۱۰۰'),
        ]
        for code, name, asset, desc in rows:
            Symbol.objects.update_or_create(code=code, defaults={'name': name, 'asset_class': asset, 'description': desc, 'is_active': True})
        self.stdout.write(self.style.SUCCESS(f'{len(rows)} نماد نمونه آماده شد.'))
