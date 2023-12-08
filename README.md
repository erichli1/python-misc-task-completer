# Misc task completer

This project enables me to use natural language text input to lower the friction of many of my current workflows. Specifically, I want to be able to quickly add Notion pages to my good moments journal and normal journal as well as events to my Google Calendar.

## Set up
Update `.env` file to include the following:
- `OPENAI_APIKEY`
- `NOTION_API_KEY`
- `NOTION_GOOD_MOMENTS_DATABASE_ID`
- `NOTION_JOURNAL_DATABASE_ID`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

Run using
`streamlit run app.py`