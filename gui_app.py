import requests
import streamlit as st


st.set_page_config(layout="wide")
st.title("Panel sterowania ContRIS")


DEFAULT_PORT = 8000


def api_url(ip: str, port: int, endpoint: str) -> str:
    ip = ip.strip()
    return f"http://{ip}:{port}{endpoint}"


def call_api(ip: str, endpoint: str, port: int = DEFAULT_PORT):
    url = api_url(ip, port, endpoint)

    try:
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
    url = api_url(ip, port, endpoint)

    try:
        response = requests.get(url, timeout=5)
        return response.json()

    except requests.exceptions.RequestException as error:
        return {
            "ok": False,
            "message": "Nie udało się pobrać logów",
            "error": str(error),
            "logs": [],
        }


def show_result(result):
    if result.get("ok"):
        message = result.get("data", {}).get("message", "OK")
        st.success(message)
    else:
        st.error("Błąd komunikacji z FastAPI")
        st.code(result)


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


top_cols = st.columns([1, 1, 1, 1])

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

        results.append(call_api(st.session_state["ip_system"], "/start/system"))
        results.append(call_api(st.session_state["ip_generator"], "/start/generator"))

        for i in range(int(ris_count)):
            ip = st.session_state.get(f"ip_ris_{i}", st.session_state.get("ip_ris_0", ""))
            results.append(call_api(ip, f"/start/ris/{i}"))

        for i in range(int(rx_count)):
            ip = st.session_state.get(f"ip_rx_{i}", st.session_state.get("ip_rx_0", ""))
            results.append(call_api(ip, f"/start/rx/{i}"))

        st.write("Wynik Start all:")
        st.json(results)

with top_cols[3]:
    if st.button("Stop all", use_container_width=True):
        results = []

        for i in range(int(rx_count)):
            ip = st.session_state.get(f"ip_rx_{i}", st.session_state.get("ip_rx_0", ""))
            results.append(call_api(ip, f"/stop/rx/{i}"))

        for i in range(int(ris_count)):
            ip = st.session_state.get(f"ip_ris_{i}", st.session_state.get("ip_ris_0", ""))
            results.append(call_api(ip, f"/stop/ris/{i}"))

        results.append(call_api(st.session_state["ip_generator"], "/stop/generator"))
        results.append(call_api(st.session_state["ip_system"], "/stop/system"))

        st.write("Wynik Stop all:")
        st.json(results)


st.divider()


main_cols = st.columns(3)

with main_cols[0]:
    st.markdown("## Główny kontroler")
    make_device_control("System Controller", "system", "ip_system")

    st.markdown("## Generator")
    make_device_control("Generator Controller", "generator", "ip_generator")

with main_cols[1]:
    st.markdown("## RIS")

    for i in range(int(ris_count)):
        key = f"ip_ris_{i}"

        if key not in st.session_state:
            st.session_state[key] = st.session_state.get("ip_ris_0", "localhost")

        make_device_control(f"RIS {i}", "ris", key, i)

with main_cols[2]:
    st.markdown("## RX")

    for i in range(int(rx_count)):
        key = f"ip_rx_{i}"

        if key not in st.session_state:
            st.session_state[key] = st.session_state.get("ip_rx_0", "localhost")

        make_device_control(f"RX {i}", "rx", key, i)

#Logi

st.divider()
st.markdown("## Logi")

log_sources = {
    "System Controller": {
        "ip_key": "ip_system",
        "controller": "system",
    },
    "Generator Controller": {
        "ip_key": "ip_generator",
        "controller": "generator",
    },
}

for i in range(int(ris_count)):
    log_sources[f"RIS {i}"] = {
        "ip_key": f"ip_ris_{i}",
        "controller": f"ris_{i}",
    }

for i in range(int(rx_count)):
    log_sources[f"RX {i}"] = {
        "ip_key": f"ip_rx_{i}",
        "controller": f"rx_{i}",
    }


log_cols = st.columns([1, 1, 1])

with log_cols[0]:
    selected_log_label = st.selectbox(
        "Kontroler",
        options=list(log_sources.keys()),
    )

with log_cols[1]:
    log_lines = st.number_input(
        "Liczba linii",
        min_value=10,
        max_value=1000,
        value=100,
        step=10,
    )

with log_cols[2]:
    refresh_logs = st.button("Odśwież logi", use_container_width=True)


selected_log = log_sources[selected_log_label]
selected_ip = st.session_state.get(selected_log["ip_key"], "")
selected_controller = selected_log["controller"]

st.caption(
    f"Endpoint logów: "
    f"{api_url(selected_ip, DEFAULT_PORT, f'/logs?controller={selected_controller}&lines={int(log_lines)}')}"
    if selected_ip else
    "Endpoint logów: uzupełnij IP"
)

if refresh_logs:
    st.session_state["last_logs"] = call_logs(
        ip=selected_ip,
        controller_name=selected_controller,
        port=DEFAULT_PORT,
        lines=int(log_lines),
    )

logs_result = st.session_state.get("last_logs")

if logs_result is not None:
    if not logs_result.get("ok", False):
        st.error(logs_result.get("message", "Nie udało się pobrać logów"))
        if "error" in logs_result:
            st.code(logs_result["error"], language="text")
    else:
        logs = logs_result.get("logs", [])
        if logs:
            st.code("\n".join(logs), language="text")
        else:
            st.info("Brak logów dla wybranego kontrolera.")
else:
    st.info("Kliknij `Odśwież logi`, żeby pobrać ostatnie linie z terminala kontrolera.")
