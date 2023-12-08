import json
import base64
import os

import streamlit as st
from streamlit_oauth import OAuth2Component
from dotenv import load_dotenv

load_dotenv()

google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"


def block_on_oauth() -> bool:
    # from https://github.com/dnplus/streamlit-oauth/blob/main/examples/google.py
    if "auth" not in st.session_state:
        # create a button to start the OAuth2 flow
        oauth2 = OAuth2Component(google_client_id, google_client_secret,
                                 AUTHORIZE_ENDPOINT, TOKEN_ENDPOINT, TOKEN_ENDPOINT, REVOKE_ENDPOINT)
        result = oauth2.authorize_button(
            name="Continue with Google",
            icon="https://www.google.com.tw/favicon.ico",
            redirect_uri=google_redirect_uri,
            scope="openid email https://www.googleapis.com/auth/calendar",
            key="google",
            extras_params={"prompt": "consent", "access_type": "offline"},
        )

        if result:
            st.write(result)
            id_token = result["token"]["id_token"]
            payload = id_token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            payload = json.loads(base64.b64decode(payload))
            email = payload["email"]
            st.session_state["auth"] = email
            st.session_state["token"] = result["token"]
            st.rerun()

        return True

    if st.button(f"Logout from {st.session_state['auth']}"):
        del st.session_state["auth"]
        del st.session_state["token"]
        st.rerun()

    return False
