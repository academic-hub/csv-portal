import streamlit as st
import SessionState
import uuid
import time
import requests
import urllib3
from portal.csv_download import csv_download


urllib3.disable_warnings()

base_url = "https://data.academic.osisoft.com/auth"

session_state = SessionState.get(session_id=str(uuid.uuid4()), response=None)  #
st.write("[debug] session_id:", session_state.session_id)

def rerun():
    raise st.script_runner.RerunException(st.script_request_queue.RerunData(None))

@st.cache(ttl=300, max_entries=4)
def get_token(previous_status):
    resp = requests.get(f"{base_url}/token", headers={"hub-id": session_state.session_id}, verify=False)
    # st.write(f"[{resp.status_code}]", resp.text)
    session_state.response = resp
    return resp


if session_state.response is None or \
        session_state.response.status_code == 400:
    with st.form(key='login-form'):
        st.markdown("**Academic Hub Login Required**")
        step_info = "Step 1. Click here to initiate login sequence on new tab"
        st.markdown(
            f'<a href="{base_url}?hub-id={session_state.session_id}" target="_blank">{step_info}</a>',
            unsafe_allow_html=True)
        login_done = st.form_submit_button('Step2 . Click Login completed')

        if login_done:
            r = get_token(session_state.response.status_code if session_state.response else 400)
            # session_state.response = r
            st.write(f"[[{session_state.response.status_code}]]")
            rerun()

if session_state.response is not None:
    if session_state.response.status_code == 200:
        # x = st.slider('Pick a number')
        # st.write('You picked:', x)
        csv_download()
    else:
        st.markdown("**Reload page to restart login process**")

