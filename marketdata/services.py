"""CSV ingestion for the application's canonical format and MetaTrader exports.

Accepted layouts include:
- timestamp,open,high,low,close,tick_volume
- MT4: Date,Time,Open,High,Low,Close,Volume
- MT5: <DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<TICKVOL>,<VOL>,<SPREAD>

The parser detects common Windows encodings and CSV separators. Naive platform
clock values are interpreted in Django's configured current timezone; the parser
does not guess or silently shift a broker's server timezone.
"""

import csv
import io
import re
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Candle, CsvImportLog


MAX_ERROR_DETAILS = 8
CSV_DELIMITERS = (",", ";", "\t", "|")
HEADER_ALIASES = {
    "timestamp": {"timestamp", "datetime", "datetimestamp", "gmttime", "utctime"},
    "date": {"date", "tradedate"},
    "time": {"time", "tradetime"},
    "open": {"open", "o"},
    "high": {"high", "h"},
    "low": {"low", "l"},
    "close": {"close", "c"},
    "tick_volume": {"tickvolume", "tickvol", "volume", "realvolume", "realvol", "vol"},
}


def _normalise_header(value):
    value = str(value or "").replace("\ufeff", "").strip().strip("<>").strip()
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _header_spec(row):
    """Return a column-index map if row looks like a supported header."""
    found = {}
    for index, name in enumerate(row):
        normalised = _normalise_header(name)
        for canonical, aliases in HEADER_ALIASES.items():
            if normalised in aliases:
                # Prefer true tick volume over the generic/real volume columns.
                if canonical == "tick_volume":
                    priority = {"tickvolume": 0, "tickvol": 0, "volume": 1, "realvolume": 2, "realvol": 2, "vol": 1}
                    current = found.get(canonical)
                    if current is None or priority.get(normalised, 9) < current[0]:
                        found[canonical] = (priority.get(normalised, 9), index)
                else:
                    found[canonical] = index
                break
    if not all(name in found for name in ("open", "high", "low", "close", "tick_volume")):
        return None
    if not ("timestamp" in found or "time" in found or "date" in found):
        return None
    result = {key: value[1] if key == "tick_volume" else value for key, value in found.items()}
    return result


def _decode_csv(raw_bytes):
    """Decode MT4/MT5 CSV exports without requiring the user to resave as UTF-8."""
    if not raw_bytes:
        raise ValueError("فایل CSV خالی است.")

    if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw_bytes.decode("utf-16"), "UTF-16"
        except UnicodeDecodeError:
            pass
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        try:
            return raw_bytes.decode("utf-8-sig"), "UTF-8 BOM"
        except UnicodeDecodeError:
            pass

    # MetaTrader/Windows files are sometimes UTF-16 without a BOM.
    sample = raw_bytes[:4096]
    even_nuls = sum(sample[index] == 0 for index in range(0, len(sample), 2))
    odd_nuls = sum(sample[index] == 0 for index in range(1, len(sample), 2))
    if max(even_nuls, odd_nuls) > max(2, len(sample) // 20):
        encoding = "utf-16-be" if even_nuls > odd_nuls else "utf-16-le"
        try:
            return raw_bytes.decode(encoding), encoding.upper()
        except UnicodeDecodeError:
            pass

    for encoding in ("utf-8", "cp1252", "cp1251", "latin-1"):
        try:
            return raw_bytes.decode(encoding), encoding.upper()
        except UnicodeDecodeError:
            continue
    raise ValueError("کدگذاری فایل قابل تشخیص نیست. فایل CSV را از MetaTrader دوباره خروجی بگیر.")


def _is_blank_row(row):
    return not row or not any(str(cell).strip() for cell in row)


def _parse_decimal_text(value, decimal_comma=False):
    text = str(value or "").strip()
    text = text.replace("\u00a0", "").replace("\u202f", "").replace(" ", "")
    text = text.replace("'", "").replace("’", "").replace("−", "-")
    if not text:
        raise ValueError("مقدار عددی خالی است")

    if "," in text and "." in text:
        # The last punctuation mark is the decimal separator; the other is grouping.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        if decimal_comma:
            # European exports commonly use semicolon as the field separator
            # and comma as the decimal separator.
            text = text.replace(".", "").replace(",", ".")
        elif text.count(",") > 1:
            text = text.replace(",", "")
        else:
            left, right = text.split(",", 1)
            # A single comma followed by exactly three digits is commonly a
            # thousands group in comma-separated exports (e.g. "4,000").
            if len(right) == 3 and left.lstrip("+-").isdigit():
                text = left + right
            else:
                text = left + "." + right
    return text


def _decimal(value, field, decimal_comma=False):
    try:
        result = Decimal(_parse_decimal_text(value, decimal_comma=decimal_comma))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field} عدد معتبر نیست")
    if not result.is_finite():
        raise ValueError(f"{field} باید عدد محدود باشد")
    tuple_value = result.as_tuple()
    decimal_places = max(-tuple_value.exponent, 0)
    integer_digits = max(result.adjusted() + 1, 0) if result else 1
    if integer_digits > 16 or decimal_places > 8:
        raise ValueError(f"{field} بیش از دقت قابل ذخیره (۱۶ رقم صحیح و ۸ اعشار) است")
    return result


def _parse_datetime_text(value):
    text = str(value or "").strip().replace("\ufeff", "")
    if not text:
        raise ValueError("تاریخ/زمان خالی است")

    # Unix timestamps occasionally appear in vendor-generated CSV files.
    if re.fullmatch(r"\d{10}(?:\.\d+)?", text):
        return datetime.fromtimestamp(float(text), tz=datetime_timezone.utc)
    if re.fullmatch(r"\d{13}", text):
        return datetime.fromtimestamp(int(text) / 1000, tz=datetime_timezone.utc)

    iso_text = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        return datetime.fromisoformat(iso_text)
    except ValueError:
        pass

    formats = (
        "%Y.%m.%d %H:%M:%S.%f", "%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y.%m.%d",
        "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S.%f", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y",
    )
    for date_format in formats:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue
    raise ValueError(f"قالب تاریخ/زمان شناخته نشد: {text[:40]}")


def _parse_timestamp(row, columns):
    timestamp_index = columns.get("timestamp")
    date_index = columns.get("date")
    time_index = columns.get("time")

    if timestamp_index is not None:
        value = _cell(row, timestamp_index)
    elif date_index is not None and time_index is not None:
        date_value = _cell(row, date_index)
        time_value = _cell(row, time_index)
        value = f"{date_value} {time_value}".strip()
    elif time_index is not None:
        # Some exports call a complete date-time column simply "Time".
        value = _cell(row, time_index)
    elif date_index is not None:
        value = _cell(row, date_index)
    else:
        raise ValueError("ستون تاریخ/زمان پیدا نشد")

    parsed = _parse_datetime_text(value)
    if timezone.is_naive(parsed):
        # Naive MT4/MT5 timestamps are broker/server time. Keep the wall-clock
        # value and interpret it in the app timezone rather than guessing a shift.
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _cell(row, index):
    if index is None or index >= len(row):
        return ""
    return str(row[index] or "").strip().replace("\ufeff", "")


def _looks_like_clock_time(value):
    value = str(value or "").strip()
    for fmt in ("%H:%M:%S.%f", "%H:%M:%S", "%H:%M"):
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def _positional_columns(row):
    """Map common headerless MT4/MT5 layouts without misreading generic CSV."""
    if len(row) >= 7:
        # MT4/MT5 bars: Date,Time,Open,High,Low,Close,TickVolume/Volume,...
        try:
            _parse_datetime_text(_cell(row, 0))
            date_is_date_only = not any(mark in _cell(row, 0) for mark in ("T", ":"))
        except ValueError:
            date_is_date_only = False
        if date_is_date_only and _looks_like_clock_time(_cell(row, 1)):
            return {"date": 0, "time": 1, "open": 2, "high": 3, "low": 4,
                    "close": 5, "tick_volume": 6}
    if len(row) >= 6:
        # Canonical/headerless vendor layout: Timestamp,Open,High,Low,Close,Volume
        return {"timestamp": 0, "open": 1, "high": 2, "low": 3, "close": 4,
                "tick_volume": 5}
    return None


def _row_is_numeric_ohlc(row, columns, delimiter):
    try:
        for name in ("open", "high", "low", "close", "tick_volume"):
            _decimal(_cell(row, columns[name]), name, decimal_comma=delimiter in (";", "\t", "|"))
        _parse_timestamp(row, columns)
        return True
    except (ValueError, KeyError, IndexError):
        return False


def _parse_rows(text):
    """Choose a separator by recognizing headers or valid MT-style data rows."""
    useful_lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not useful_lines:
        raise ValueError("فایل CSV خالی است یا ردیف قابل خواندن ندارد.")
    candidates = []
    for delimiter in CSV_DELIMITERS:
        try:
            rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
        except csv.Error:
            continue
        header = None
        header_line = None
        for index, row in enumerate(rows[:30]):
            spec = _header_spec(row)
            if spec:
                header, header_line = spec, index
                break
        data_rows = [(index + 1, row) for index, row in enumerate(rows)
                     if index > (header_line if header_line is not None else -1) and not _is_blank_row(row)]
        if header is not None:
            # A recognized field header is decisive; prefer the first such candidate.
            return rows, header, header_line, delimiter
        score = 0
        inspected = 0
        for _line, row in data_rows[:20]:
            if _is_blank_row(row):
                continue
            inspected += 1
            positional = _positional_columns(row)
            if positional and _row_is_numeric_ohlc(row, positional, delimiter):
                score += 1
        candidates.append((score, inspected, delimiter, rows))

    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1], item[2] == ","), reverse=True)
        score, _inspected, delimiter, rows = candidates[0]
        if score:
            return rows, None, None, delimiter

    # Some MT text exports use spaces instead of a conventional CSV delimiter.
    # Split on one or more spaces/tabs; this handles the date and time as two fields.
    whitespace_rows = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        whitespace_rows.append(re.split(r"\s+", line.strip()))
    for index, row in enumerate(whitespace_rows[:30]):
        spec = _header_spec(row)
        if spec:
            return whitespace_rows, spec, index, " "
    if whitespace_rows:
        positional = _positional_columns(whitespace_rows[0])
        if positional and _row_is_numeric_ohlc(whitespace_rows[0], positional, " "):
            return whitespace_rows, None, None, " "

    raise ValueError(
        "ساختار CSV شناسایی نشد. فایل باید شامل Date/Time یا Timestamp، "
        "چهار ستون Open/High/Low/Close و یکی از Tick Volume/Volume باشد. "
        "خروجی Bars را از MT4/MT5 انتخاب کن، نه خروجی Ticks."
    )


def _insert_batch(symbol, timeframe, batch):
    timestamps = [item.timestamp for item in batch]
    with transaction.atomic():
        existing = set(Candle.objects.filter(
            symbol=symbol, timeframe=timeframe, timestamp__in=timestamps
        ).values_list("timestamp", flat=True))
        fresh = [item for item in batch if item.timestamp not in existing]
        if fresh:
            Candle.objects.bulk_create(fresh, batch_size=500, ignore_conflicts=True)
            persisted = Candle.objects.filter(
                symbol=symbol, timeframe=timeframe,
                timestamp__in=[item.timestamp for item in fresh]
            ).count()
        else:
            persisted = 0
    inserted = min(persisted, len(fresh))
    return inserted, len(batch) - inserted


def import_candles_csv(uploaded_file, symbol, timeframe, user):
    max_bytes = settings.MAX_CSV_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ValueError(f"حجم فایل نباید بیشتر از {settings.MAX_CSV_SIZE_MB} مگابایت باشد.")
    if not uploaded_file.name.lower().endswith(".csv"):
        raise ValueError("فقط فایل با پسوند CSV پذیرفته می‌شود.")

    try:
        raw_bytes = uploaded_file.read()
        text, encoding_name = _decode_csv(raw_bytes)
        rows, header_columns, header_line, delimiter = _parse_rows(text)
    except UnicodeDecodeError:
        raise ValueError("کدگذاری فایل CSV قابل تشخیص نیست.")

    if header_columns is None:
        first_data_index = next((index for index, row in enumerate(rows) if not _is_blank_row(row)), None)
        if first_data_index is None:
            raise ValueError("فایل CSV ردیف داده ندارد.")
        header_columns = _positional_columns(rows[first_data_index])
        if not header_columns:
            raise ValueError("تعداد ستون‌های فایل برای قالب شناخته‌شده MT4/MT5 کافی نیست.")
        data_start = first_data_index
    else:
        data_start = header_line + 1

    required = ("open", "high", "low", "close", "tick_volume")
    if not all(key in header_columns for key in required):
        raise ValueError("ستون‌های OHLC و حجم در فایل پیدا نشدند.")

    total = inserted = duplicates = invalid = 0
    parsed_candles = []
    errors = []
    decimal_comma = delimiter in (";", "\t", "|")

    for line_number, row in enumerate(rows[data_start:], start=data_start + 1):
        if _is_blank_row(row):
            continue
        # Ignore repeated header rows sometimes emitted when files are concatenated.
        if _header_spec(row):
            continue
        total += 1
        try:
            candle_time = _parse_timestamp(row, header_columns)
            o = _decimal(_cell(row, header_columns["open"]), "open", decimal_comma)
            h = _decimal(_cell(row, header_columns["high"]), "high", decimal_comma)
            l = _decimal(_cell(row, header_columns["low"]), "low", decimal_comma)
            c = _decimal(_cell(row, header_columns["close"]), "close", decimal_comma)
            volume_decimal = _decimal(_cell(row, header_columns["tick_volume"]), "volume", decimal_comma)
            if (volume_decimal < 0 or volume_decimal != volume_decimal.to_integral_value()
                    or volume_decimal > 9223372036854775807):
                raise ValueError("حجم باید عدد صحیح، نامنفی و در محدوده قابل ذخیره باشد")
            if h < max(o, c, l) or l > min(o, c, h) or h < l:
                raise ValueError("ترتیب مقادیر OHLC نامعتبر است")
            parsed_candles.append(Candle(
                symbol=symbol, timeframe=timeframe, timestamp=candle_time,
                open=o, high=h, low=l, close=c, tick_volume=int(volume_decimal),
            ))
        except (ValueError, InvalidOperation, TypeError, IndexError, KeyError) as exc:
            invalid += 1
            if len(errors) < MAX_ERROR_DETAILS:
                errors.append(f"ردیف {line_number}: {exc}")

    # MT4/MT5 files may be exported newest-first. Sort automatically rather than
    # rejecting the whole file because of row order.
    parsed_candles.sort(key=lambda candle: candle.timestamp)
    buffer = []
    seen_in_file = set()
    for candle in parsed_candles:
        if candle.timestamp in seen_in_file:
            duplicates += 1
            continue
        seen_in_file.add(candle.timestamp)
        buffer.append(candle)
        if len(buffer) >= 1000:
            inserted_now, duplicates_now = _insert_batch(symbol, timeframe, buffer)
            inserted += inserted_now
            duplicates += duplicates_now
            buffer = []
    if buffer:
        inserted_now, duplicates_now = _insert_batch(symbol, timeframe, buffer)
        inserted += inserted_now
        duplicates += duplicates_now

    if total == 0:
        raise ValueError("در فایل هیچ ردیف کندل قابل پردازشی پیدا نشد.")

    status = CsvImportLog.Status.SUCCESS if invalid == 0 else CsvImportLog.Status.PARTIAL
    notes = [f"کدگذاری تشخیص‌داده‌شده: {encoding_name}", f"جداکننده تشخیص‌داده‌شده: {repr(delimiter)}"]
    if errors:
        notes.extend(errors)
    log = CsvImportLog.objects.create(
        user=user, symbol=symbol, timeframe=timeframe,
        filename=uploaded_file.name[:255], total_rows=total,
        inserted_rows=inserted, duplicate_rows=duplicates,
        invalid_rows=invalid, status=status, message="\n".join(notes),
    )
    # These transient attributes let the upload page link directly to the exact
    # time span represented by this CSV without requiring a database migration.
    valid_times = [candle.timestamp for candle in parsed_candles]
    if valid_times:
        first_timestamp = min(valid_times)
        last_timestamp = max(valid_times)
        log.chart_from_ts = int(first_timestamp.timestamp())
        log.chart_to_ts = int(last_timestamp.timestamp())
        log.chart_candle_count = len(valid_times)
    else:
        log.chart_from_ts = None
        log.chart_to_ts = None
        log.chart_candle_count = 0
    return log
