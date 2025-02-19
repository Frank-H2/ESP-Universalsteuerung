import socket
import ujson
import gc
from hardware_control import *
from chain_management import *
import _thread

MAX_CONNECTIONS = 5  # Maximalzahl der gleichzeitigen Verbindungen
connection_count = 0

def serve_main_page():
    try:
        with open('index.html', 'r') as f:
            content = f.read()
            return content
    except OSError as e:
        print(f"Fehler beim Öffnen der Datei: {e}")
        return "<h1>Fehler: index.html konnte nicht geladen werden.</h1>"

def run_webserver(pins, inputs, servos, adcs):
    global connection_count
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print('Warte auf Verbindungen an:', addr)
    while True:
        cl, addr = s.accept()
        if connection_count < MAX_CONNECTIONS:
            connection_count += 1
            print('Client verbunden von', addr, 'Anzahl der aktuellen Verbindungen:', connection_count)
            _thread.start_new_thread(handle_client, (cl, pins, inputs, servos, adcs))
        else:
            print('Maximale Verbindungen erreicht, Verbindung abgelehnt von', addr)
            cl.close()

def handle_client(cl, pins, inputs, servos, adcs):
    global connection_count
    try:
        cl_file = cl.makefile('rwb', 0)
        request_line = cl_file.readline().decode('utf-8')
        if not request_line:
            raise Exception("Leere Anfrage")
        handle_request(cl, cl_file, request_line, pins, inputs, servos, adcs)
    finally:
        connection_count -= 1
        cl.close()
        gc.collect()  # Garbage Collection nach jeder abgeschlossenen Verbindung

def handle_request(cl, cl_file, request_line, pins, inputs, servos, adcs):
    request_parts = request_line.split()
    if len(request_parts) < 2:
        send_response(cl, "400 Bad Request", "Invalid request format")
        return

    path = request_parts[1]
    if path.startswith("/toggle?"):
        params = parse_query_params(path.split("?")[1])
        result = handle_toggle(params, pins)
    elif path == "/input_status":
        result = handle_input_status(inputs)
    elif path == "/analog_status":
        result = handle_analog_status(adcs)
    elif path.startswith("/servo?"):
        params = parse_query_params(path.split("?")[1])
        result = handle_servo(params, servos)
    elif path == "/chain_status":
        result = get_chain_status()
    elif path.startswith("/save_chain?"):
        params = parse_query_params(path.split("?")[1])
        result = handle_save_chain(params)
    elif path == "/load_chain":
        result = handle_load_chain()
    elif path == "/execute_chain":
        result = handle_execute_chain(pins, inputs, servos, adcs)
    elif path == "/abort_chain":
        result = handle_abort_chain()
    else:
        result = serve_main_page()
        send_response(cl, result, content_type="text/html")
        return

    send_response(cl, result, content_type="application/json" if result.startswith("{") else "text/plain")

def send_response(cl, content, content_type="text/html", status="200 OK"):
    response = f"HTTP/1.0 {status}\r\nContent-Type: {content_type}\r\n\r\n{content}"
    cl.send(response.encode("utf-8"))

def parse_query_params(query_string):
    params = {}
    if query_string:
        pairs = query_string.split('&')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key] = value
    return params

def handle_toggle(params, pins):
    switch = params.get('switch')
    state = params.get('state')
    if switch and state:
        pin = pins.get(switch)
        if pin:
            state_value = 1 if state == 'on' else 0
            pin.value(state_value)
            return ujson.dumps({"status": "success", "switch": switch, "state": state})
    return ujson.dumps({"status": "error", "message": "Invalid parameters"})

def handle_input_status(inputs):
    input_states = {key: inputs[key].value() for key in inputs}
    return ujson.dumps(input_states)

def handle_analog_status(adcs):
    analog_values = {"analog1": adcs["1"].read(), "analog2": adcs["2"].read()}
    return ujson.dumps(analog_values)

def handle_servo(params, servos):
    servo = params.get('servo')
    pos = params.get('pos')
    if servo and pos:
        try:
            pos_value = int(pos)
            if servo in servos and 0 <= pos_value <= 180:
                servos[servo].duty(angle_to_duty(pos_value))
                return ujson.dumps({"status": "success", "servo": servo, "position": pos_value})
        except ValueError:
            pass
    return ujson.dumps({"status": "error", "message": "Invalid parameters"})

def handle_save_chain(params):
    # Platzhalter für die Speicherung der Ablaufkette
    return ujson.dumps({"status": "success", "message": "Chain saved"})

def handle_load_chain():
    # Platzhalter für das Laden der Ablaufkette
    return ujson.dumps({"status": "success", "message": "Chain loaded"})

def handle_execute_chain(pins, inputs, servos, adcs):
    _thread.start_new_thread(run_chain, (pins, inputs, servos, adcs))
    return ujson.dumps({"status": "success", "message": "Chain execution started"})

def handle_abort_chain():
    return handle_abort_chain()  # Diese Funktion wird bereits importiert und sollte in chain_management.py definiert sein