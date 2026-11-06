from django.conf import settings
from django.db import models

class Symbol(models.Model):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    asset_class = models.CharField(max_length=40, blank=True, default='Other')
    description = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['code']
    def __str__(self):
        return f'{self.code} — {self.name}'

class Candle(models.Model):
    class Timeframe(models.TextChoices):
        M5 = '5m', '5 دقیقه'
        M15 = '15m', '15 دقیقه'
        M30 = '30m', '30 دقیقه'
        H1 = '1h', '1 ساعت'
        H4 = '4h', '4 ساعت'
        D1 = '1d', 'روزانه'
        W1 = '1w', 'هفتگی'
        MO1 = '1mo', 'ماهانه'
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name='candles')
    timeframe = models.CharField(max_length=4, choices=Timeframe.choices, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    open = models.DecimalField(max_digits=24, decimal_places=8)
    high = models.DecimalField(max_digits=24, decimal_places=8)
    low = models.DecimalField(max_digits=24, decimal_places=8)
    close = models.DecimalField(max_digits=24, decimal_places=8)
    tick_volume = models.BigIntegerField(default=0)
    imported_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['timestamp']
        constraints = [models.UniqueConstraint(fields=['symbol', 'timeframe', 'timestamp'], name='uniq_symbol_tf_timestamp')]
        indexes = [models.Index(fields=['symbol', 'timeframe', '-timestamp'], name='candle_chart_lookup')]
    def __str__(self):
        return f'{self.symbol.code} {self.timeframe} {self.timestamp:%Y-%m-%d %H:%M}'

class CsvImportLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'موفق'
        PARTIAL = 'PARTIAL', 'موفق با ردیف نامعتبر'
        FAILED = 'FAILED', 'ناموفق'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    symbol = models.ForeignKey(Symbol, on_delete=models.SET_NULL, null=True)
    timeframe = models.CharField(max_length=4, choices=Candle.Timeframe.choices)
    filename = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    inserted_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUCCESS)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f'{self.filename} ({self.status})'
