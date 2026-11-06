# Architecture Notes

## Application boundaries
- `accounts`: custom user identity and server-side role checks.
- `marketdata`: symbol registry, normalized OHLCV candles, CSV ingestion, chart API.
- `publishing`: operator-written market notes and user bookmarks.
- `analyses`: provider abstraction, bounded market-context construction, structured analysis persistence, review/version history and evaluation.
- `auditlog_app`: write-action audit events without storing submitted form bodies.

## Data integrity
`Candle` has a database-level unique constraint over `(symbol, timeframe, timestamp)`. CSV ingestion validates timestamps, ascending order, finite decimals, OHLC coherence and non-negative integer tick volume. Duplicate imports are reported and ignored.

## AI boundary
The application compacts market data before an external model request. It does not submit unlimited candle history. The provider is isolated behind `BaseAIProvider`. Model output is stored as JSON, versioned, and requires review by default. Scenario language is conditional; no order execution code exists.

## Deployment boundary
The included `runserver` script is for local development only. A production deployment requires HTTPS, a production WSGI/ASGI server, secure secret management, backups, host validation and operational monitoring.
