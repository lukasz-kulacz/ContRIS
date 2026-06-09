import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"

st.set_page_config(layout="wide")
st.title("Panel sterowania ContRIS")


def call_api(endpoint: str):
    """
    Wysyła żądanie GET do FastAPI.
    """
    url = f"{API_BASE_URL}{endpoint}"

    try:
        response = requests.get(url, timeout=5)
        return response.json()
    except requests.exceptions.RequestException as error:
        return {
            "error": str(error),
            "message": "Nie udało się połączyć z FastAPI"
        }


def make_device_control(label: str, controller_type: str, controller_id=None):
    """
    Tworzy prosty panel Start/Stop dla jednego kontrolera.
    """

    with st.container(border=True):
        st.markdown(f"### {label}")

        if controller_id is None:
            start_endpoint = f"/start/{controller_type}"
            stop_endpoint = f"/stop/{controller_type}"
        else:
            start_endpoint = f"/start/{controller_type}/{controller_id}"
            stop_endpoint = f"/stop/{controller_type}/{controller_id}"

        b1, b2 = st.columns(2)

        if b1.button("Start", key=f"start_{controller_type}_{controller_id}", use_container_width=True):
            result = call_api(start_endpoint)
            st.toast(result.get("message", str(result)))

        if b2.button("Stop", key=f"stop_{controller_type}_{controller_id}", use_container_width=True):
            result = call_api(stop_endpoint)
            st.toast(result.get("message", str(result)))


def show_status():
    """
    Pobiera status z FastAPI i pokazuje go w GUI.
    """

    result = call_api("/status")

    st.markdown("## Status")

    if "error" in result:
        st.error(result["message"])
        st.code(result["error"])
    else:
        st.json(result)


top_cols = st.columns([1, 1, 1, 1])

with top_cols[0]:
    if st.button("Odśwież status", use_container_width=True):
        st.session_state["show_status"] = True

with top_cols[1]:
    if st.button("Start all", use_container_width=True):
        call_api("/start/system")
        call_api("/start/rx/0")
        call_api("/start/ris/0")
        call_api("/start/generator")
        st.toast("Wysłano komendy Start all")

with top_cols[2]:
    if st.button("Stop all", use_container_width=True):
        call_api("/stop/generator")
        call_api("/stop/ris/0")
        call_api("/stop/rx/0")
        call_api("/stop/system")
        st.toast("Wysłano komendy Stop all")

with top_cols[3]:
    st.markdown(f"API: `{API_BASE_URL}`")


main_cols = st.columns(3)

with main_cols[0]:
    st.markdown("## Główny kontroler")
    make_device_control("System Controller", "system")

    st.markdown("## Generator")
    make_device_control("Generator", "generator")


with main_cols[1]:
    st.markdown("## RIS")

    ris_count = st.slider(
        "Liczba RIS",
        min_value=1,
        max_value=4,
        value=1,
        key="ris_count"
    )

    for i in range(ris_count):
        make_device_control(f"RIS {i}", "ris", i)


with main_cols[2]:
    st.markdown("## RX")

    rx_count = st.slider(
        "Liczba RX",
        min_value=1,
        max_value=4,
        value=1,
        key="rx_count"
    )

    for i in range(rx_count):
        make_device_control(f"RX {i}", "rx", i)


show_status()