#! /usr/bin/python3

"""
[Unit]
Description=CO2 Data Collector
After=multi-user.target

[Service]
Type=simple
ExecStart=/home/pi/co2reading/app.py
Restart=always
PIDFile=/run/my.pid

[Install]
WantedBy=multi-user.target
"""

print("Importing")

import requests
import sys
from CO2Meter import *
from time import time, sleep
from sched import scheduler
import requests
import sys
import Adafruit_DHT
import Adafruit_BMP.BMP085 as BMP085


print("Starting collector...")

s = scheduler(time, sleep)

t = list()
h = list()
co2 = list()
p = list()

l_t = None
l_co2 = None
l_h = None
l_p = None


updated = False

meter = CO2Meter("/dev/hidraw0")
dht_sensor = Adafruit_DHT.DHT11
dht_pin = 4
bmp_sensor = BMP085.BMP085()

def periodic(interval, action, actionargs=()):
    global s
    s.enter(interval, 1, periodic, (interval, action, actionargs))
    try:
        action(*actionargs)
    except KeyboardInterrupt:
        raise
    except Exception as e:
       print('Failed to call action', action)
       print(e)

def update():
    global t, co2, l_t, l_co2, updated, l_h, h, p, l_p
    if len(t) == 0 or len(co2) == 0 or len(t) == 0 or len(p) == 0:
        return
    l_t = sum(t)/len(t)
    t = list()
    l_co2 = sum(co2)/len(co2)
    co2 = list()
    l_h = sum(h)/len(h)
    h = list()
    l_p = (sum(p) / len(p)) / 133.322368
    p = list()
    updated = True

def measure():
    global t, co2, h, p
    m = meter.get_data()
    if 'co2' in m:
        co2.append(float(m['co2']))
    if 'temperature' in m:
        t.append(float(m['temperature']))
    _h, _t = Adafruit_DHT.read_retry(dht_sensor, dht_pin)
    if _h:
        h.append(float(_h))
    _p = bmp_sensor.read_pressure()
    print(m, _h, _t, _p)
    p.append(float(_p))

def upload_eiva(tag, val):
    r = requests.get('http://eivanote.cloudapp.net:8080/measure/eiva/home/{}/{}'.format(tag, val))
    print('Posting {}: {} code {}'.format(tag, val, r.status_code))

def post_private():
    global l_t, l_co2, updated
    update()
    if not updated:
        return
    # upload_eiva('co2', l_co2)
    # upload_eiva('temp', l_t)

def post_public():
    global l_t, l_co2, updated, l_h, l_p
    update()
    if not updated:
        return
    payload={'private_key': 'b5Evxnx74kHPjKgJkG7x', 't': l_t, 'co2': l_co2, 'p': l_p, 'h': l_h}
    print(payload)
    r = requests.get('http://data.sparkfun.com/input/4JRdjajKqECl97DNJrga/', params=payload)
    print('Publishing:', r.status_code)

#periodic(30, post_private)
periodic(20*60, post_public)

while True:
    measure()
    s.run(False)
    sys.stdout.flush()
    sleep(1)
