import _thread
import ujson
from hardware_control import angle_to_duty

chain_running = False
current_chain_step = 0
active_action = {}
chain_lock = _thread.allocate_lock()

def run_chain(pins, inputs, servos, adcs):
    global chain_running, current_chain_step, active_action
    with chain_lock:
        chain_running = True
        current_chain_step = 0
        active_action = {}
    print("Starte Ablaufkette...")
    
    try:
        with open(CHAIN_FILE, "r") as f:
            chain_data = ujson.load(f)
    except Exception as e:
        print("Kein gültiges", CHAIN_FILE, "gefunden:", e)
        with chain_lock:
            chain_running = False
        return

    chain = sorted(chain_data.get("chain", []), key=lambda step: step.get("step_number", 0))
    step_index = 0
    jump_counters = {}
    
    while True:
        with chain_lock:
            if not chain_running:
                break
        if step_index >= len(chain):
            break
        step = chain[step_index]
        with chain_lock:
            current_chain_step = step.get("step_number", 0)
        print("Führe Schritt", current_chain_step, "aus")
        step_type = step.get("type")
        if step_type == "action":
            execute_action(step.get("action", {}), pins, servos)
        elif step_type == "condition":
            step_index = check_condition(step.get("condition", {}), inputs, adcs, step_index, chain, jump_counters)
        else:
            step_index += 1
        time.sleep(0.05)

    with chain_lock:
        chain_running = False
        current_chain_step = 0
    print("Ablaufkette abgeschlossen.")

def execute_action(action, pins, servos):
    with chain_lock:
        active_action = action
    if action.get("device") == "relay":
        pin = pins.get(str(action.get("number")))
        if pin:
            pin.value(1 if action.get("state") == "on" else 0)
            print("Relay", action.get("number"), "gesetzt auf", action.get("state"))
    elif action.get("device") == "servo":
        servo = servos.get(str(action.get("number")))
        if servo:
            angle = 90
            if "value" in action and action["value"] not in [None, ""]:
                try:
                    angle = float(action["value"])
                except:
                    pass
            servo.duty(angle_to_duty(angle))
            print("Servo", action.get("number"), "auf", angle, "Grad")
    time.sleep(0.5)
    with chain_lock:
        active_action = {}

def check_condition(condition, inputs, adcs, step_index, chain, jump_counters):
    executed = False
    if "digital" in condition:
        input_num = str(condition["digital"].get("input_number"))
        desired = str(condition["digital"].get("state", "")).lower()
        if input_num in inputs:
            current = "on" if inputs[input_num].value() == 1 else "off"
            if current == desired:
                executed = True
    elif "analog" in condition:
        analog = condition["analog"]
        input_num = str(analog.get("input_number"))
        comparator = analog.get("comparator")
        comp_value = analog.get("value")
        if comp_value not in [None, ""]:
            adc_val = adcs[input_num].read()
            if comparator == ">=" and adc_val >= float(comp_value):
                executed = True
            elif comparator == "<=" and adc_val <= float(comp_value):
                executed = True
    elif "wait" in condition:
        try:
            seconds = float(condition["wait"].get("seconds", 1))
        except:
            seconds = 1
        time.sleep(seconds)
        executed = True
    elif "jump" in condition:
        jump = condition["jump"]
        try:
            target = int(jump.get("target_step", 0))
            counter = int(jump.get("counter", 0))
        except:
            target = 0
            counter = 0
        key = str(target)
        if key not in jump_counters:
            jump_counters[key] = counter
        if jump_counters[key] > 0:
            jump_counters[key] -= 1
            for idx, st in enumerate(chain):
                if st.get("step_number") == target:
                    step_index = idx
                    print("Springe zu Schritt", target, "noch", jump_counters[key], "Mal")
                    break
            executed = True
        else:
            executed = True
            step_index += 1
    
    return step_index + 1 if executed and "jump" not in condition else step_index

def get_chain_status():
    global current_chain_step, active_action, chain_running, chain_lock
    with chain_lock:
        return ujson.dumps({
            "current_step": current_chain_step,
            "active_action": active_action,
            "running": chain_running
        })

def handle_abort_chain():
    global chain_running, current_chain_step, chain_lock
    with chain_lock:
        chain_running = False
        current_chain_step = 0
    print("Ablaufkette abgebrochen.")
    return "Ablaufkette abgebrochen"