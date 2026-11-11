from datetime import datetime, timezone


def as_utc(dt: datetime | None) -> datetime | None:
    """Приводит datetime к timezone-aware UTC.

    MongoDB (PyMongo) хранит даты как naive UTC, поэтому при чтении
    документов добавляем tzinfo, чтобы API отдавало однозначное время.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
