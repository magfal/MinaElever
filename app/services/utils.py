from datetime import datetime, timezone, timedelta

# -------------------------------------------------
# HJÄLPFUNKTIONER
# -------------------------------------------------
def utc_now():
    return datetime.now(timezone.utc)

# Säkerställer att datetime är timezone-aware (UTC)
def utcify(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt