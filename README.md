# Dziennik Elektroniczny Demo

Demo technologiczne dziennika szkolnego Flask + SQLite przygotowane do wdrożenia na Render.

## Render

Render oficjalnie wspiera Flask i dla aplikacji Python używa np. `pip install -r requirements.txt` jako Build Command oraz `gunicorn app:app` jako Start Command.

Możesz wdrożyć repo jako **Web Service** na planie Free.

### Ustawienia ręczne

- Runtime: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Plan: Free

W repo jest też `render.yaml`, więc konfiguracja może zostać odczytana automatycznie jako Blueprint.

## Konta demo

- Administrator: `admin` / `admin`
- Nauczyciel: `nauczyciel` / `demo123`
- Uczeń: `uczen` / `demo123`

## Ważne dla demo

SQLite jest tutaj użyte jako prosta baza demonstracyjna. Na darmowym Render bez trwałego dysku nie należy traktować lokalnego pliku SQLite jako trwałego magazynu produkcyjnego. Free Web Services mogą być usypiane po okresie bezczynności.

Dane testowe są tworzone przy pierwszym uruchomieniu, jeśli baza nie istnieje.
