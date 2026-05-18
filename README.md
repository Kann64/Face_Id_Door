# Face ID Door

Simple smart door access system with:
- FastAPI backend (`main.py`)
- Guest face registration web page
- Android Java/XML app skeleton
- Supabase SQL schema

## 1) Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000/docs` for API docs.

## 2) Guest registration web

Use a generated one-time link from `POST /registration/generate-link`.
The registration page is available at `/register/{token}`.

## 3) Supabase schema

Run `/home/runner/work/Face_Id_Door/Face_Id_Door/db/schema.sql` in Supabase SQL editor.

## 4) Android app

Android source is in `/home/runner/work/Face_Id_Door/Face_Id_Door/android-app`.
Open that folder in Android Studio and set your backend base URL in `ApiClient.java`.

## Notes

- Door unlock duration is fixed to 5 seconds.
- Registration links are one-time and expire after 2 hours.
- Login uses JWT with 24h expiration.
- Admin persistence on Android is handled with SharedPreferences.
