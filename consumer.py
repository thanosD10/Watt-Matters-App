"""
MQTT Subscriber - Listens to topic "electricity" and sends data to InfluxDB
"""

import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
import paho.mqtt.client as mqtt
from datetime import date

load_dotenv()  # take environment variables from .env.

# InfluxDB config
BUCKET = os.getenv('INFLUXDB_BUCKET')
client = InfluxDBClient(url=os.getenv('INFLUXDB_URL'),
                token=os.getenv('INFLUXDB_TOKEN'), org=os.getenv('INFLUXDB_ORG'))
write_api = client.write_api()

# MQTT broker config
MQTT_BROKER_URL    = "mqtt.eclipseprojects.io"
MQTT_PUBLISH_TOPIC = "electricity"

mqttc = mqtt.Client()
mqttc.connect(MQTT_BROKER_URL)

# The callback for when the client connects to the broker.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribe tο a topic
    client.subscribe(MQTT_PUBLISH_TOPIC)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

    # We received bytes we need to converts into something usable
    measurement = int(msg.payload)

    # Write in InfluxDB
    point = Point(MQTT_PUBLISH_TOPIC).field("electricity", measurement )
    write_api.write(bucket=BUCKET, record=point)

    # Keep track of measurements per sec even when app frontend is not running
    with open("total-watt.csv", "r") as file:
        last_line = file.readlines()[-1]
        current_line = last_line.split(",")
        watt_old_date = current_line[0]
        watt_old_measurement = current_line[1]
        running_hours = current_line[2]

    # Check if it's new day
    today = date.today().strftime("%Y-%m-%d")
    if(watt_old_date != today):
        f = open("total-watt.csv", "a")
        f.write("\n" + str(today) + ",0,0")
        f.close()
    else:
        lines = open("total-watt.csv", "r").readlines()
        lines[-1] = today + "," + str(int(watt_old_measurement) + measurement) + "," + str(float(running_hours) + 0.000278)
        f = open("total-watt.csv", "w")
        f.writelines(lines)
        f.close()



# Register callbacks and start MQTT client
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.loop_forever()
