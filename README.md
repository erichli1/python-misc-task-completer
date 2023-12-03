# Misc task completer

This project enables me to use natural language text input to lower the friction of many of my current workflows. Specifically, I want to be able to quickly add Notion pages to my good moments journal and normal journal as well as events to my Google Calendar.

## Set up
Update `.env` file to include `OPENAI_APIKEY`, `NOTION_API_KEY`, `NOTION_GOOD_MOMENTS_DATABASE_ID`, and `NOTION_JOURNAL_DATABASE_ID`.

Create a `credentials.json` file by downloading your accounts' Google's OAuth 2.0 [credentials](https://developers.google.com/calendar/api/quickstart/python#authorize_credentials_for_a_desktop_application)

`streamlit run app.py`