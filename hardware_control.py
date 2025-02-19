import machine
import ujson
from config import RELAY_PINS, INPUT_PINS, SERVO_PINS, ANALOG_PINS

def setup_hardware():
    pins = {str(k): machine.Pin(v, machine.Pin.OUT, value=0) for k, v in RELAY_PINS.items()}
    inputs = {str(k): machine.Pin(v, machine.Pin.IN, machine.Pin.PULL_DOWN) for k, v in INPUT_PINS.items()}
    servos = {
        "1": machine.PWM(machine.Pin(SERVO_PINS["1"]), freq=50),
        "2": machine.PWM(machine.Pin(SERVO_PINS["2"]), freq=50)
    }
    for servo in servos.values():
        servo.duty(angle_to_duty(90))

    adcs = {
        "1": machine.ADC(machine.Pin(ANALOG_PINS["1"])),
        "2": machine.ADC(machine.Pin(ANALOG_PINS["2"]))
    }
    for adc in adcs.values():
        adc.atten(machine.ADC.ATTN_11DB)

    return pins, inputs, servos, adcs

def angle_to_duty(angle):
    try:
        a = float(angle)
    except:
        a = 90
    return int(round((1 + (a / 180)) / 20 * 1023))