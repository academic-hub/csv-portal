#
import streamlit as st
import datetime
import pytimeparse
from dateutil.parser import parse
from ocs_academic_hub.datahub import hub_connect
import pandas as pd
import json

dataset_time_range = dict(
    Classroom_Data="Feb 2018 - Dec 2019",
    Brewery="Jan 2017 - May 2020",
    MIT="July 2021 - now",
    Pilot_Plant="Oct 2020 - now",
    USC_Well_Data="July 2011 - Jan 2020 (one event per month)",
    Wind_Farms="Jan 2018 - Dec 2019",
)
MAX_STORED_ROWS = 500 * 1000


@st.cache
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode("utf-8")


def csv_download(session_state):
    @st.cache(allow_output_mutation=True, ttl=3600.0)
    def hub_client(session_st):
        # st.write(f"jwt= {session_st.jwt}")
        new_hub = hub_connect(eval(session_st.jwt))
        return new_hub

    @st.cache(show_spinner=False)
    def get_interpolated_data_view(
        hub, dataset, asset, start_time, end_time, interpolation
    ):
        return hub.dataview_interpolated_pd(
            hub.namespace_of(dataset),
            hub.asset_dataviews(filter="", asset=asset)[0],
            start_time.isoformat(),
            end_time.isoformat(),
            interpolation,
        )

    @st.cache(show_spinner=False)
    def get_stored_data_view(hub, dataset, asset, start_time, end_time, resume=0):
        return hub.dataview_stored_pd(
            hub.namespace_of(dataset),
            hub.asset_dataviews(filter="", asset=asset)[0],
            start_time.isoformat(),
            end_time.isoformat(),
            resume=True if resume else False,
            max_rows=MAX_STORED_ROWS,
        )

    def download_csv(hub):

        with st.form(key="dataset"):

            dataset = st.selectbox(
                "Step 1: Select dataset",
                hub.datasets(first="Classroom_Data"),
                help="Check datasets info at https://academic.osisoft.com/datasets",
            )
            st.form_submit_button(label="Submit")

        with st.form(key="asset-dv"):
            hub.set_dataset(dataset)
            st.markdown(f"**Dataset time range: {dataset_time_range[dataset]}**")
            asset = st.selectbox(
                "Step 2: Select asset",
                hub.assets()["Asset_Id"],
                help="For asset info check URL",
            )
            start = st.text_input(
                "Step 3: Start time",
                "2021-05-07T20:03:35",
                None,
                "start-time",
                "default",
                "Start time for CSV result using ISO 8601 time format "
                "https://en.wikipedia.org/wiki/ISO_8601",
            )
            window = st.text_input(
                "Step 4: Time window",
                "240 mins",
                None,
                "window-time",
                "default",
                "CSV results will end at start time + this time window, supported format "
                + "https://github.com/wroberts/pytimeparse#pytimeparse-time-expression-parser \n"
                + f"**WARNING:** stored data view maximum of rows is {MAX_STORED_ROWS}",
            )
            dataview_kind = st.radio(
                "Step 5: Select data view kind", ("Interpolated", "Stored")
            )
            interpolation = st.text_input(
                "Step 6 for interpolation period (format is HH:MM:SS)",
                "00:05:00",
                None,
                "interpolation",
                "default",
                "Interpolation interval with format HH:MM:SS",
            )
            csv_button = st.form_submit_button(
                label="Final step: Click to generate CSV file"
            )

        start_time = end_time = None
        try:
            start_time = parse(start)
        except ValueError:
            st.warning(
                "#### Invalid start time, "
                "please consult https://en.wikipedia.org/wiki/ISO_8601"
            )
        try:
            delta = datetime.timedelta(seconds=pytimeparse.parse(window))
            end_time = start_time + delta
        except TypeError:
            st.warning(
                "#### Invalid time window, "
                "please consult https://github.com/wroberts/pytimeparse#pytimeparse-time-expression-parser"
            )

        if start_time and end_time:
            interpolation_info = (
                f"<br>Interpolation interval (HH:MM:SS): {interpolation}"
                if dataview_kind == "Interpolated"
                else ""
            )
            dataview_info = f"""
Current dataset: {dataset} || Selected asset: {asset}<br>
Namespace: {hub.namespace_of(dataset)} || Data view ID: {hub.asset_dataviews(filter="", asset=asset)[0]} ({dataview_kind.lower()})<br> 
Start time: {start_time.isoformat()} || End time: {end_time.isoformat()}{interpolation_info}
"""
            st.markdown(dataview_info, unsafe_allow_html=True)

        if csv_button and start_time and end_time:
            with st.spinner(
                text=f"Getting {dataview_kind.lower()} CSV from Data View... (can take some time)"
            ):
                if dataview_kind == "Interpolated":
                    df = get_interpolated_data_view(
                        hub, dataset, asset, start_time, end_time, interpolation
                    )
                else:  # "Stored"
                    df = get_stored_data_view(
                        hub, dataset, asset, start_time, end_time, resume=0
                    )
                if len(df) > 0:
                    session_state.df = df.set_index("Timestamp")
                    st.success(
                        f"Data View Request Complete!! (number of rows: {len(df)})"
                    )
                else:
                    st.warning(
                        f"Data View is empty - please try with another time range"
                    )
            with st.spinner(text="Preparing for download..."):
                if len(df) > 0:
                    suffix = f"{'-stored' if dataview_kind == 'Stored' else ''}.csv"
                    data_file = (
                        asset
                        + "-"
                        + start_time.isoformat().replace(":", "_")
                        + "-"
                        + end_time.isoformat().replace(":", "_")
                        + suffix
                    )
                    session_state.data_file = data_file
                else:
                    st.markdown(f"** No data to download (try another time range)**")

        st.markdown("**Data frame preview:**")
        pivot = False
        asset_meta = False
        df = None
        if dataview_kind != "Interpolated":
            pivot = st.checkbox(
                "Pivot table",
                help="Switch from narrow CSV to wide format (Field values become columns)",
            )
            asset_meta = st.checkbox(
                "Add asset metadata", help="Add asset metadata to CSV - REQUIRES PIVOT"
            )
        with st.spinner(text=f"Preparing preview..."):
            if pivot:
                session_state.df_pivot = session_state.df.pivot_table(
                    values="Value", index="Timestamp", columns="Field"
                )
                if asset_meta:
                    session_state.df_meta = pd.DataFrame(
                        hub.asset_metadata(asset=asset),
                        index=session_state.df_pivot.index,
                    )
                    session_state.df_pivot_meta = session_state.df_pivot.merge(
                        session_state.df_meta, on="Timestamp"
                    )
                    df = session_state.df_pivot_meta
                else:
                    df = session_state.df_pivot
            else:
                df = session_state.df
            try:
                if df is not None:
                    st.markdown(
                        f"number of (columns, rows) = ({len(df.columns) + 1}, {len(df)})"
                    )
                    st.write(df)
            except:
                st.warning(
                    "**Unable to generate preview (download link is still valid)**"
                )

            if session_state.df is not None and len(session_state.df) > 0:
                if hub.remaining_data():
                    st.markdown(
                        '<p style="color:red;font-size:32px"><strong>Download link below is missing data: try a '
                        "smaller time range</strong></p>",
                        unsafe_allow_html=True,
                    )
                csv = convert_df(df)
                st.download_button(
                    label="**Download data as CSV**",
                    data=csv,
                    file_name=f"{session_state.data_file}",
                    mime="text/csv",
                    help="Click this link to get a copy of the data frame as a CSV file",
                )

    hub = hub_client(session_state)
    download_csv(hub)
