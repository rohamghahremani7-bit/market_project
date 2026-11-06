from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import Candle, Symbol
from .services import import_candles_csv

User = get_user_model()


class CsvImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="operator_test", password="Strong-Test-Password-2026"
        )
        self.symbol = Symbol.objects.create(code="TEST", name="Test Market")

    def upload(self, name, content):
        return SimpleUploadedFile(name, content, content_type="text/csv")

    def test_canonical_utf8_csv_imports_candles(self):
        content = (
            b"timestamp,open,high,low,close,tick_volume\n"
            b"2026-11-01T10:00:00+00:00,100,105,99,103,20\n"
            b"2026-11-01T10:05:00+00:00,103,108,102,106,25\n"
        )
        report = import_candles_csv(self.upload("candles.csv", content), self.symbol,
                                    Candle.Timeframe.M5, self.user)
        self.assertEqual(report.inserted_rows, 2)
        self.assertEqual(report.invalid_rows, 0)
        self.assertEqual(Candle.objects.filter(symbol=self.symbol).count(), 2)

    def test_mt5_utf16_comma_export_uses_tickvol(self):
        text = (
            "<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<TICKVOL>,<VOL>,<SPREAD>\r\n"
            "2026.11.06,10:00:00,3990.00,3995.00,3988.00,3993.00,120,0,18\r\n"
            "2026.11.06,10:05:00,3993.00,3998.00,3991.00,3996.00,145,0,18\r\n"
        )
        report = import_candles_csv(
            self.upload("mt5.csv", text.encode("utf-16")), self.symbol,
            Candle.Timeframe.M5, self.user
        )
        self.assertEqual(report.inserted_rows, 2)
        candles = list(Candle.objects.filter(symbol=self.symbol).order_by("timestamp"))
        self.assertEqual(candles[0].tick_volume, 120)
        self.assertEqual(str(candles[0].open), "3990.00000000")

    def test_mt4_semicolon_windows_encoding_and_decimal_comma(self):
        text = (
            "Date;Time;Open;High;Low;Close;Volume\r\n"
            "2026.11.06;10:00;3990,50;3995,75;3988,25;3993,50;120\r\n"
            "2026.11.06;10:05;3993,50;3998,25;3991,25;3996,00;145\r\n"
        )
        report = import_candles_csv(
            self.upload("mt4.csv", text.encode("cp1252")), self.symbol,
            Candle.Timeframe.M5, self.user
        )
        self.assertEqual(report.inserted_rows, 2)
        first = Candle.objects.filter(symbol=self.symbol).order_by("timestamp").first()
        self.assertEqual(str(first.open), "3990.50000000")
        self.assertEqual(first.tick_volume, 120)

    def test_mt5_tab_separated_utf16_without_bom_is_supported(self):
        text = (
            "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\r\n"
            "2026.11.06\t10:00:00\t3990\t3995\t3988\t3993\t120\t0\t18\r\n"
        )
        raw = text.encode("utf-16-le")  # deliberately no BOM
        report = import_candles_csv(
            self.upload("mt5-tab.csv", raw), self.symbol, Candle.Timeframe.M5, self.user
        )
        self.assertEqual(report.inserted_rows, 1)
        self.assertEqual(Candle.objects.get(symbol=self.symbol).tick_volume, 120)

    def test_windows_ansi_file_with_metadata_line_is_supported(self):
        text = (
            "# Exported from broker Café terminal\r\n"
            "Date;Time;Open;High;Low;Close;Volume\r\n"
            "2026.11.06;10:00;3990,50;3995,75;3988,25;3993,50;120\r\n"
        )
        report = import_candles_csv(
            self.upload("mt4-ansi.csv", text.encode("cp1252")),
            self.symbol, Candle.Timeframe.M5, self.user
        )
        self.assertEqual(report.inserted_rows, 1)

    def test_headerless_mt4_export_is_supported(self):
        text = (
            "2026.11.06,10:00,3990.00,3995.00,3988.00,3993.00,120\n"
            "2026.11.06,10:05,3993.00,3998.00,3991.00,3996.00,145\n"
        )
        report = import_candles_csv(
            self.upload("mt4-no-header.csv", text.encode("utf-8")), self.symbol,
            Candle.Timeframe.M5, self.user
        )
        self.assertEqual(report.inserted_rows, 2)

    def test_descending_rows_are_sorted_automatically(self):
        content = (
            b"Date,Time,Open,High,Low,Close,Volume\n"
            b"2026.11.06,10:05,103,108,102,106,25\n"
            b"2026.11.06,10:00,100,105,99,103,20\n"
        )
        report = import_candles_csv(self.upload("descending.csv", content), self.symbol,
                                    Candle.Timeframe.M5, self.user)
        self.assertEqual(report.inserted_rows, 2)
        candles = list(Candle.objects.filter(symbol=self.symbol).order_by("timestamp"))
        self.assertEqual(candles[0].timestamp < candles[1].timestamp, True)

    def test_duplicate_import_is_ignored(self):
        content = (
            b"timestamp,open,high,low,close,tick_volume\n"
            b"2026-11-01T10:00:00+00:00,100,105,99,103,20\n"
        )
        self.assertEqual(import_candles_csv(self.upload("candles.csv", content), self.symbol,
                                            Candle.Timeframe.M5, self.user).inserted_rows, 1)
        report = import_candles_csv(self.upload("candles.csv", content), self.symbol,
                                    Candle.Timeframe.M5, self.user)
        self.assertEqual(Candle.objects.filter(symbol=self.symbol).count(), 1)
        self.assertEqual(report.duplicate_rows, 1)

    def test_invalid_ohlc_is_reported(self):
        content = (
            b"timestamp,open,high,low,close,tick_volume\n"
            b"2026-11-01T10:00:00+00:00,100,98,99,103,20\n"
        )
        report = import_candles_csv(self.upload("bad.csv", content), self.symbol,
                                    Candle.Timeframe.M5, self.user)
        self.assertEqual(report.invalid_rows, 1)
        self.assertEqual(report.inserted_rows, 0)


class CsvChartLinkMetadataTests(TestCase):
    """The successful import result carries a non-persistent chart time range."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="chart_meta_test", password="Strong-Test-Password-2026"
        )
        self.symbol = Symbol.objects.create(code="CHARTMETA", name="Chart Meta Test")

    def upload(self, name, content):
        return SimpleUploadedFile(name, content, content_type="text/csv")

    def test_import_result_contains_exact_chart_range(self):
        content = (
            b"timestamp,open,high,low,close,tick_volume\n"
            b"2026-11-06T10:00:00+00:00,100,105,99,103,20\n"
            b"2026-11-06T10:05:00+00:00,103,108,102,106,25\n"
        )
        report = import_candles_csv(
            self.upload("range.csv", content), self.symbol, Candle.Timeframe.M5, self.user
        )
        self.assertIsNotNone(report.chart_from_ts)
        self.assertIsNotNone(report.chart_to_ts)
        self.assertLess(report.chart_from_ts, report.chart_to_ts)
        self.assertEqual(report.chart_candle_count, 2)


class CandleChartRangeApiTests(TestCase):
    def setUp(self):
        from datetime import datetime, timezone as dt_timezone
        self.symbol = Symbol.objects.create(code="RANGE", name="Range Test")
        self.user = User.objects.create_user(
            username="chart_api_test", password="Strong-Test-Password-2026"
        )
        self.client.force_login(self.user)
        Candle.objects.create(
            symbol=self.symbol, timeframe=Candle.Timeframe.M5,
            timestamp=datetime(2026, 11, 6, 10, 0, tzinfo=dt_timezone.utc),
            open=100, high=105, low=99, close=103, tick_volume=20,
        )
        Candle.objects.create(
            symbol=self.symbol, timeframe=Candle.Timeframe.M5,
            timestamp=datetime(2026, 11, 6, 10, 5, tzinfo=dt_timezone.utc),
            open=103, high=108, low=102, close=106, tick_volume=25,
        )
        Candle.objects.create(
            symbol=self.symbol, timeframe=Candle.Timeframe.M5,
            timestamp=datetime(2026, 11, 6, 10, 10, tzinfo=dt_timezone.utc),
            open=106, high=109, low=104, close=108, tick_volume=30,
        )

    def test_candles_api_respects_unix_time_range(self):
        from datetime import datetime, timezone as dt_timezone
        start = int(datetime(2026, 11, 6, 10, 5, tzinfo=dt_timezone.utc).timestamp())
        end = int(datetime(2026, 11, 6, 10, 10, tzinfo=dt_timezone.utc).timestamp())
        response = self.client.get("/api/candles/", {
            "symbol": "RANGE", "timeframe": "5m", "from": start, "to": end,
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["candles"][0]["open"], 103.0)
        self.assertEqual(payload["candles"][-1]["close"], 108.0)

    def test_candles_api_rejects_invalid_time_range(self):
        response = self.client.get("/api/candles/", {
            "symbol": "RANGE", "timeframe": "5m", "from": "not-a-timestamp",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("from", response.json()["error"])

    def test_chart_page_preserves_csv_range_and_selected_timeframe(self):
        from datetime import datetime, timezone as dt_timezone
        start = int(datetime(2026, 11, 6, 10, 0, tzinfo=dt_timezone.utc).timestamp())
        end = int(datetime(2026, 11, 6, 10, 10, tzinfo=dt_timezone.utc).timestamp())
        response = self.client.get(
            "/market/charts/RANGE/",
            {"timeframe": "5m", "from": start, "to": end, "source": "csv", "filename": "gold.csv"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "gold.csv")
        self.assertContains(response, 'id="price-field"')
        self.assertContains(response, 'id="candle-search"')


class CsvImportChartActionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="operator_chart_test", password="Strong-Test-Password-2026",
            role=User.Role.OPERATOR,
        )
        self.symbol = Symbol.objects.create(code="GOLDTEST", name="Gold Test")
        self.client.force_login(self.user)

    def test_successful_csv_import_renders_direct_chart_button(self):
        content = (
            b"timestamp,open,high,low,close,tick_volume\n"
            b"2026-11-06T10:00:00+00:00,100,105,99,103,20\n"
            b"2026-11-06T10:05:00+00:00,103,108,102,106,25\n"
        )
        response = self.client.post("/operator/import-csv/", {
            "symbol": str(self.symbol.pk),
            "timeframe": "5m",
            "file": SimpleUploadedFile("gold.csv", content, content_type="text/csv"),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "دریافت نمودار بر اساس فایل CSV واردشده")
        self.assertContains(response, "source=csv")
        self.assertContains(response, "timeframe=5m")
