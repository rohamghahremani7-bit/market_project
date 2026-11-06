from rest_framework import serializers
from .models import Symbol, Candle

class SymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symbol
        fields = ('id', 'code', 'name', 'asset_class')

class CandleSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()
    class Meta:
        model = Candle
        fields = ('time', 'open', 'high', 'low', 'close', 'tick_volume')
    def get_time(self, obj):
        return int(obj.timestamp.timestamp())
