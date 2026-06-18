import requests
import streamlit as st


st.set_page_config(layout="wide")
st.title("Panel sterowania ContRIS")


DEFAULT_PORT = 8000


def session_port(ip_key: str) -> int:
    return int(st.session_state.get(f"port_{ip_key}", DEFAULT_PORT))


def api_url(ip: str, port: int, endpoint: str) -> str:
    ip = ip.strip()
    return f"http://{ip}:{port}{endpoint}"


def call_api(ip: str, endpoint: str, port: int = DEFAULT_PORT, method: str = "GET"):
    url = api_url(ip, port, endpoint)

    try:
        if method == "POST":
            response = requests.post(url, timeout=60)
        else:
            response = requests.get(url, timeout=5)

        try:
            data = response.json()
        except Exception:
            data = {"raw_response": response.text}

        return {
            "ok": response.ok,
            "url": url,
            "status_code": response.status_code,
            "data": data,
        }

    except requests.exceptions.RequestException as error:
        return {
            "ok": False,
            "url": url,
            "error": str(error),
            "data": {
                "message": "Nie udało się połączyć z FastAPI"
            },
        }


def call_logs(ip: str, controller_name: str, port: int = DEFAULT_PORT, lines: int = 100):
    endpoint = f"/logs?controller={controller_name}&lines={lines}"
    return call_api(ip, endpoint, port)


def show_result(result: dict):
    data = result.get("data", {})
    message = data.get("message", "")
    succeeded = result.get("ok") and data.get("success", True)

    if succeeded:
        st.success(message or "OK")
    else:
        st.error(message or data.get("stderr") or result.get("error") or "Błąd")

    st.json(result)


def show_status():
    with st.expander("Status głównego API"):
        ip = st.session_state.get("ip_system", "localhost")
        port = session_port("ip_system")

        if st.button("Odśwież status", use_container_width=True):
            show_result(call_api(ip, "/status", port))


def make_device_control(label: str, controller_type: str, ip_key: str, controller_id=None):
    with st.container(border=True):
        st.markdown(f"### {label}")

        ip = st.text_input(
            "IP komputera-kontrolera",
            key=ip_key,
        )

        port = st.number_input(
            "Port FastAPI",
            min_value=1,
            max_value=65535,
            value=DEFAULT_PORT,
            step=1,
            key=f"port_{ip_key}",
        )

        if controller_id is None:
            start_endpoint = f"/start/{controller_type}"
            stop_endpoint = f"/stop/{controller_type}"
        else:
            start_endpoint = f"/start/{controller_type}/{controller_id}"
            stop_endpoint = f"/stop/{controller_type}/{controller_id}"

        status_endpoint = "/status"

        b1, b2, b3 = st.columns(3)

        if b1.button("Start", key=f"start_{controller_type}_{controller_id}", use_container_width=True):
            result = call_api(ip, start_endpoint, port)
            show_result(result)

        if b2.button("Stop", key=f"stop_{controller_type}_{controller_id}", use_container_width=True):
            result = call_api(ip, stop_endpoint, port)
            show_result(result)

        if b3.button("Status", key=f"status_{controller_type}_{controller_id}", use_container_width=True):
            result = call_api(ip, status_endpoint, port)
            show_result(result)

        st.caption(f"Start: {api_url(ip, port, start_endpoint) if ip else 'uzupełnij IP'}")
        st.caption(f"Stop: {api_url(ip, port, stop_endpoint) if ip else 'uzupełnij IP'}")


if "ip_system" not in st.session_state:
    st.session_state["ip_system"] = "localhost"

if "ip_generator" not in st.session_state:
    st.session_state["ip_generator"] = "localhost"

if "ip_ris_0" not in st.session_state:
    st.session_state["ip_ris_0"] = "localhost"

if "ip_rx_0" not in st.session_state:
    st.session_state["ip_rx_0"] = "localhost"


top_cols = st.columns([1, 1, 1, 1, 1])

with top_cols[0]:
    ris_count = st.number_input(
        "Liczba RIS",
        min_value=1,
        max_value=8,
        value=1,
        step=1,
    )

with top_cols[1]:
    rx_count = st.number_input(
        "Liczba RX",
        min_value=1,
        max_value=8,
        value=1,
        step=1,
    )

with top_cols[2]:
    if st.button("Start all", use_container_width=True):
        results = []

        results.append(call_api(st.session_state["ip_system"], "/start/system", session_port("ip_system")))
        results.append(call_api(st.session_state["ip_generator"], "/start/generator", session_port("ip_generator")))

        for i in range(int(ris_count)):
            ip = st.session_state.get(f"ip_ris_{i}", st.session_state.get("ip_ris_0", ""))
            results.append(call_api(ip, f"/start/ris/{i}", session_port(f"ip_ris_{i}")))

        for i in range(int(rx_count)):
            ip = st.session_state.get(f"ip_rx_{i}", st.session_state.get("ip_rx_0", ""))
            results.append(call_api(ip, f"/start/rx/{i}", session_port(f"ip_rx_{i}")))

        st.write("Wynik Start all:")
        st.json(results)

with top_cols[3]:
    if st.button("Stop all", use_container_width=True):
        results = []

        results.append(call_api(st.session_state["ip_generator"], "/stop/generator", session_port("ip_generator")))

        for i in range(int(ris_count)):
            ip = st.session_state.get(f"ip_ris_{i}", st.session_state.get("ip_ris_0", ""))
            results.append(call_api(ip, f"/stop/ris/{i}", session_port(f"ip_ris_{i}")))

        for i in range(int(rx_count)):
            ip = st.session_state.get(f"ip_rx_{i}", st.session_state.get("ip_rx_0", ""))
            results.append(call_api(ip, f"/stop/rx/{i}", session_port(f"ip_rx_{i}")))

        results.append(call_api(st.session_state["ip_system"], "/stop/system", session_port("ip_system")))
        st.toast("Wysłano komendy Stop all")
        st.json(results)

with top_cols[3]:
    st.markdown(f"API system: `{api_url(st.session_state['ip_system'], session_port('ip_system'), '')}`")

with top_cols[4]:
    if st.button("Git pull", use_container_width=True):
        result = call_api(
            st.session_state["ip_system"],
            "/git/pull",
            session_port("ip_system"),
            method="GET",
        )
        show_result(result)


main_cols = st.columns(3)

with main_cols[0]:
    st.markdown("## Główny kontroler")
    make_device_control("System Controller", "system", "ip_system")

    st.markdown("## Generator")
    make_device_control("Generator Controller", "generator", "ip_generator")

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
        make_device_control(f"RIS {i}", "ris", f"ip_ris_{i}", i)


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
        make_device_control(f"RX {i}", "rx", f"ip_rx_{i}", i)


show_status()
