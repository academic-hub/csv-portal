import streamlit as st
import SessionState
import json
import uuid
import requests
import urllib3
import time
from portal.csv_download import csv_download

urllib3.disable_warnings()

__version__ = "0.8.13"
auth_url = st.secrets["auth_url"]
auth0_roles_key = st.secrets["auth0_roles_key"]
secret_read = st.secrets["secret_read"]

hub_home = "https://academic.osisoft.com"
datasets_link = (
    f'<a href="{hub_home}/datasets" target="_blank">[dataset documentation]</a>'
)
registration_link = f'<a href="{hub_home}/register" target="_blank">[register here]</a>'
portal_link = f'<a href="{hub_home}" target="_blank">[back to hub portal]</a>'

session_state = SessionState.get(
    session_id=str(uuid.uuid4()), response=None, df=None
)  #
# st.write("[debug] session_id:", session_state.session_id)
st.image("https://academichub.blob.core.windows.net/images/aveva-banner.png", width=700)
st.markdown(
    f"<b>Hub Data Portal ({__version__})</b> {datasets_link} || {registration_link}  || {portal_link} ",
    unsafe_allow_html=True,
)


def rerun():
    raise st.script_runner.RerunException(st.script_request_queue.RerunData(None))


@st.cache(ttl=300, max_entries=4)
def get_token(previous_status):
    resp = requests.get(
        f"{auth_url}/token", headers={"hub-id": session_state.session_id}, verify=False
    )
    session_state.response = resp
    # print(resp.text)
    if resp.status_code == 200:
        js = json.loads(resp.text)
        roles = js[auth0_roles_key]
        session_state.client_key = secret_read
        session_state.roles = roles
    return resp


if session_state.response is None or session_state.response.status_code == 400:
    with st.form(key="login-form"):
        st.markdown("**Academic Hub Login Required**")
        step_info = "Step 1. Click here to initiate login sequence on new tab"
        st.markdown(
            f'<a href="{auth_url}?hub-id={session_state.session_id}" target="_blank">{step_info}</a>',
            unsafe_allow_html=True,
        )
        login_done = st.form_submit_button("Step2 . Click Login completed")

        if login_done:
            r = get_token(
                session_state.response.status_code if session_state.response else 400
            )
            if session_state.response.status_code != 200:
                st.markdown(
                    f"**Error ({session_state.response.status_code}): cannot login, make sure to use the correct "
                    f"academic hub account in Step 1.**"
                )
                time.sleep(5)
            rerun()

if session_state.response is not None:
    if session_state.response.status_code == 200:
        if session_state.client_key and "hub:read" in session_state.roles:
            csv_download(session_state)
        else:
            st.markdown(
                "**No application registered for user, please reload page to restart login process with another "
                "account**"
            )
    else:
        st.markdown("**Reload page to restart login process**")
