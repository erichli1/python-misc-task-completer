import os
import streamlit as st
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()


def setup():
    if "token" in st.session_state:
        json_token = st.session_state["token"]
        json_token.update({"client_secret": os.getenv(
            "GOOGLE_CLIENT_SECRET"), "client_id": os.getenv("GOOGLE_CLIENT_ID")})

        creds = Credentials.from_authorized_user_info(
            st.session_state["token"])
        try:
            service = build("calendar", "v3", credentials=creds)

            return service

        except HttpError as error:
            print(f"An error occurred: {error}")

    return None


def add_to_calendar(service, input_event):
    event = service.events().insert(calendarId="primary", body=input_event).execute()
    return event


if __name__ == "__main__":
    setup()
