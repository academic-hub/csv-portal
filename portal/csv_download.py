#
import streamlit as st
import pandas as pd
import datetime
import pytimeparse
from dateutil.parser import parse
from ocs_academic_hub import HubClient
import plotly.express as px
import base64


def csv_download(client_key):
    @st.cache(allow_output_mutation=True, ttl=3600.0)
    def hub_client(hub_key=client_key):
        hub_ocs = HubClient(client_key=hub_key)
        hub_ocs.refresh_datasets(
            experimental=True,
            # additional_status="eds_onboarding",
        )
        hub_ocs.set_dataset("Classroom_Data")
        return hub_ocs

    @st.cache(show_spinner=False)
    def get_interpolated_data_view(dataset, asset, start_time, end_time, interpolation):
        return hub.dataview_interpolated_pd(hub.namespace_of(dataset),
                                            hub.asset_dataviews(filter='', asset=asset)[0],
                                            start_time.isoformat(), end_time.isoformat(), interpolation)

    @st.cache(show_spinner=False)
    def get_stored_data_view(dataset, asset, start_time, end_time):
        return hub.dataview_stored_pd(hub.namespace_of(dataset),
                                      hub.asset_dataviews(filter='', asset=asset)[0],
                                      start_time.isoformat(), end_time.isoformat())

    def get_table_download_link_csv(df):
        csv = df.to_csv(index=False).encode()
        b64 = base64.b64encode(csv).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="dataview.csv" target="_blank">Download CSV file</a>'
        return href

    def download_csv(hub):
        with st.form(key='dataset'):

            dataset = st.selectbox("Step 1: Select dataset", hub.datasets(),
                                   help="Check datasets info at https://academic.osisoft.com/datasets")
            st.form_submit_button(label='Submit')

        with st.form(key='asset-dv'):
            hub.set_dataset(dataset)
            asset = st.selectbox('Step 2: Select asset', hub.assets()["Asset_Id"],
                                 help="For asset info check URL")
            start = st.text_input("Step 3: Start time", "2021-05-07T20:03:35", None, "start-time",
                                  "default",
                                  "Start time for CSV result using ISO 8601 time format "
                                  "https://en.wikipedia.org/wiki/ISO_8601")
            window = st.text_input("Step 4: Time window", "240 mins", None, "window-time", "default",
                                   "CSV results will end at start time + this time window, supported format " +
                                   "https://github.com/wroberts/pytimeparse#pytimeparse-time-expression-parser")
            dataview_kind = st.radio("Step 5: Select data view kind", ("Interpolated", "Stored"))
            interpolation = st.text_input("Step 6 for interpolation period (format is HH:MM:SS)", "00:05:00", None,
                                          "interpolation", "default", "Interpolation interval with format HH:MM:SS")
            csv_button = st.form_submit_button(label='Final step: Click for CSV')

        start_time = parse(start)
        delta = datetime.timedelta(seconds=pytimeparse.parse(window))
        end_time = start_time + delta

        st.write("Current dataset: ", dataset, " || Selected asset:", asset)
        st.write("Start time:", start_time.isoformat(), "||", "End time :", end_time.isoformat())
        if dataview_kind == "Interpolated":
            st.write("Interpolation interval (HH:MM:SS):", interpolation)
        st.write("OCS namespace:", hub.namespace_of(dataset), "||", "Default data view ID:",
                 hub.asset_dataviews(filter="", asset=asset)[0])

        if 'df' not in globals():
            df = pd.DataFrame()

        if csv_button:
            with st.spinner(text=f'Getting {dataview_kind.lower()} CSV from OCS Data View...'):
                if dataview_kind == "Interpolated":
                    df = get_interpolated_data_view(dataset, asset, start_time, end_time, interpolation)
                else:  # "Stored"
                    df = get_stored_data_view(dataset, asset, start_time, end_time)
            st.success('Data View Request Complete!!')
            st.markdown(get_table_download_link_csv(df), unsafe_allow_html=True)

        st.write(df)

        with st.form(key="plot"):
            plot_button = st.form_submit_button(label="(Optional step) Click here for line plot (interpolated only)")
            if plot_button and dataview_kind == "Interpolated":
                df = get_interpolated_data_view(dataset, asset, start_time, end_time, interpolation)
                st.write("Data line plot")
                with st.spinner(text='Plotting data...'):
                    columns = list(df.select_dtypes(include='number').columns)
                    st.write(px.line(df, x="Timestamp", y=columns))
                st.success("Done!")

    hub = hub_client()
    download_csv(hub)
