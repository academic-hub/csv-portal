#
import streamlit as st
import datetime
import pytimeparse
from dateutil.parser import parse
from ocs_academic_hub import HubClient
import pathlib

STREAMLIT_STATIC_PATH = pathlib.Path(st.__path__[0]) / "static"
DOWNLOADS_PATH = STREAMLIT_STATIC_PATH / "downloads"
if not DOWNLOADS_PATH.is_dir():
    DOWNLOADS_PATH.mkdir()


def csv_download(session_state):
    @st.cache(allow_output_mutation=True, ttl=3600.0)
    def hub_client(client_key):
        hub_ocs = HubClient(client_key=client_key)
        hub_ocs.refresh_datasets(
            experimental=True,
            # additional_status="eds_onboarding",
        )
        return hub_ocs

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
                + "https://github.com/wroberts/pytimeparse#pytimeparse-time-expression-parser",
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
            csv_button = st.form_submit_button(label="Final step: Click for CSV")

        start_time = parse(start)
        delta = datetime.timedelta(seconds=pytimeparse.parse(window))
        end_time = start_time + delta

        st.write("Current dataset: ", dataset, " || Selected asset:", asset)
        st.write(
            "Start time:",
            start_time.isoformat(),
            "||",
            "End time :",
            end_time.isoformat(),
        )
        if dataview_kind == "Interpolated":
            st.write("Interpolation interval (HH:MM:SS):", interpolation)
        st.write(
            "OCS namespace:",
            hub.namespace_of(dataset),
            "||",
            "Default data view ID:",
            hub.asset_dataviews(filter="", asset=asset)[0],
        )

        if csv_button:
            with st.spinner(
                text=f"Getting {dataview_kind.lower()} CSV from OCS Data View... (can take some time)"
            ):
                if dataview_kind == "Interpolated":
                    df = get_interpolated_data_view(
                        hub, dataset, asset, start_time, end_time, interpolation
                    )
                else:  # "Stored"
                    df = get_stored_data_view(
                        hub, dataset, asset, start_time, end_time, resume=0
                    )
                session_state.df = df

            st.success(f"Data View Request Complete!! (number of rows: {len(df)})")
            if hub.remaining_data():
                st.warning("**WARNING: download link is missing data: try a small time range**")
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
                    df.to_csv(str(DOWNLOADS_PATH / f"{data_file}"), index=False)
                    link = f"Download from [this link](downloads/{data_file})"
                    st.markdown(link, unsafe_allow_html=True)
                else:
                    st.markdown(f"** No data to download (try another time range)**")

        st.markdown("**Data frame preview:**")
        with st.spinner(text=f"Preparing preview..."):
            try:
                st.write(session_state.df)
            except:
                st.warning("**Unable to generate preview (download link is valid)**")

#        with st.form(key="plot"):
#            plot_button = st.form_submit_button(
#                label="(Optional step) Click here for plot"
#            )
#            if plot_button:
#                st.write("Data line plot:")
#                with st.spinner(
#                    text="Plotting data... (can take some time with big data frame)"
#                ):
#                    df = session_state.df
#                    columns = list(df.select_dtypes(include="number").columns)
#                    if dataview_kind == "Interpolated":
#                        st.write(px.line(df, x="Timestamp", y=columns))
#                    else:
#                        title = f"Time-series scatter+line plot for asset {asset} of dataset {dataset} on Academic Hub"
#                        st.write(
#                            px.scatter(
#                                df,
#                                x=df["Timestamp"],
#                                y=df["Value"],
#                                color=df["Field"],
#                                title=title,
#                            ).update_traces(mode="lines+markers")
#                        )
            st.success("Done!")

    hub = hub_client(session_state.client_key)
    download_csv(hub)
