import network
import time
from config import *
from hardware_control import setup_hardware
from web_server import run_webserver

def setup_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Verbinde mit Netzwerk...')
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.1)
    print('Netzwerk-Konfiguration:', wlan.ifconfig())
    return wlan

def main():
    setup_wifi()
    pins, inputs, servos, adcs = setup_hardware()
    run_webserver(pins, inputs, servos, adcs)

if __name__ == "__main__":
    main()