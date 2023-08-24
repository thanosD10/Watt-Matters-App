"""
MQTT Publisker - Works as Smart Sensor
"""

from csv import reader
import time
import pandas as pd
import os

import paho.mqtt.client as mqtt

# Connect to the MQTT broker
MQTT_BROKER_URL    = "mqtt.eclipseprojects.io"
MQTT_PUBLISH_TOPIC = "electricity"

mqttc = mqtt.Client()
mqttc.connect(MQTT_BROKER_URL)

# Change directory where data are stored locally
data_directory = os.path.abspath("watt_data")
os.chdir(data_directory)

# Specific dates to open data files in order
datelist = pd.date_range("2012-06-01", "2013-01-13").strftime('%Y-%m-%d').to_list()

# Loop through data sent to the Broker
for date in datelist:
    print("--------------------------------------------------------------")
    print(f"------------------------- {date} -------------------------")
    print("--------------------------------------------------------------")

    # Iterate over each line as an ordered dictionary and publish only column that contains electricity consumption value
    with open('{}.csv'.format(date), 'r') as read_obj:
        csv_reader = reader(read_obj)
        for row in csv_reader:
            mqttc.publish(MQTT_PUBLISH_TOPIC, row[0])
            print(f"Published new electricity measurement: {row[0]}")
            time.sleep(1)