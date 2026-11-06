from django.contrib import admin
from .models import Symbol, Candle, CsvImportLog

@admin.register(Symbol)
class SymbolAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'asset_class', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('asset_class', 'is_active')

@admin.register(Candle)
class CandleAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'tick_volume')
    list_filter = ('timeframe', 'symbol')
    search_fields = ('symbol__code',)
    date_hierarchy = 'timestamp'

@admin.register(CsvImportLog)
class CsvImportLogAdmin(admin.ModelAdmin):
    list_display = ('filename', 'symbol', 'timeframe', 'inserted_rows', 'duplicate_rows', 'invalid_rows', 'status', 'created_at')
    readonly_fields = [f.name for f in CsvImportLog._meta.fields]
