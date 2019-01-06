#!/usr/bin/python
# -*- coding: utf-8 -*-

import Adafruit_DHT as dht

humidity, temperature = dht.read_retry(dht.DHT22, 4)

print '$say Il fait {0:0.1f}°C, humidité {1:0.1f}%'.format(temperature, humidity)
