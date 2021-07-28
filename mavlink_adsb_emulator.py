#!/usr/bin/env python3
"""
D2X Demos - MAVLink ADSB_VEHILCE Emulator

Generate MAVLink ADSB_VEHICLE messages from PX4 telemetry.

Author:    Jannik Beyerstedt <beyerstedt@consider-it.de>
Copyright: (c) consider it GmbH, 2021
"""

import argparse
import logging
import sys
import json
import time
from urllib.parse import urlparse
import paho.mqtt.client as paho
import pymavlink.mavlink as mavlink
import pymavlink.mavutil as mavutil

OWN_SYSID = 255
OWN_COMPID = 0
UDP_CONNECT_TIMEOUT = 10

# TODO: fill this information or un-set the flags (down below)
ADSB_ICAO_ADDR = 1234  # uint32_t
ADSB_SQUAWK = 1234  # uint16_t
ADSB_CALLSIGN = "aaaaaaaa"  # char[9] (8 characters + NULL)
ADSB_EMITTER_TYPE = mavlink.ADSB_EMITTER_TYPE_ROTOCRAFT


if __name__ == "__main__":
    log_format = '%(asctime)s %(levelname)s:%(name)s: %(message)s'
    log_datefmt = '%Y-%m-%dT%H:%M:%S%z'
    logging.basicConfig(format=log_format, datefmt=log_datefmt, level=logging.INFO)
    logger = logging.getLogger()

    parser = argparse.ArgumentParser(description='MAVLink GNSS Status Display')
    parser.add_argument("-i", "--input", required=True,
                        help="MQTT URL, e.g. tcp://localhos:1883/topicname")
    parser.add_argument("-o", "--output", required=True,
                        help="connection address for ADS-B data, e.g. tcp:$ip:$port, udpout:$ip:$port")
    parser.add_argument("-s", "--sysID", type=int,
                        help="just use data from the specified system ID")
    parser.add_argument("-v", "--verbosity", action="count",
                        help="increase output and logging verbosity")
    args = parser.parse_args()

    if args.verbosity == 2:
        logger.setLevel(logging.DEBUG)
    elif args.verbosity == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    # SETUP
    # open MQTT connection
    mqtt_url = urlparse(args.input)
    if len(mqtt_url.path) <= 1:  # just a '/' is not enough
        logger.error("MQTT URL must contain a topic as URL path")
        sys.exit()
    mqtt_host = mqtt_url.netloc[0:mqtt_url.netloc.find(":")]
    mqtt_port = int(mqtt_url.netloc[mqtt_url.netloc.find(":")+1:])
    mqtt_topic = mqtt_url.path[1:]

    # logger.info("Starting MQTT connection to %s:%i, topic '%s'", mqtt_host, mqtt_port, mqtt_topic)
    # mqtt_client = paho.Client()
    # mqtt_client.connect(mqtt_host, port=mqtt_port)

    # open MAVLink output
    logger.info("Starting MAVLink connection to %s", args.output)
    try:
        mav_out = mavutil.mavlink_connection(
            args.output, source_system=OWN_SYSID, source_component=OWN_COMPID)
    except OSError:
        logger.error("MAVLink connection failed, exiting")
        sys.exit(-1)

    # RUN
    def on_message(client, userdata, msg):
        logger.debug("IN: %s", msg.payload.decode())

        data = json.loads(msg.payload)

        # fill ADSB_VEHICLE message and send
        adsb_callsign = bytes(ADSB_CALLSIGN, 'ascii')
        adbs_flags = mavlink.ADSB_FLAGS_VALID_COORDS + \
            mavlink.ADSB_FLAGS_VALID_ALTITUDE + \
            mavlink.ADSB_FLAGS_VALID_HEADING + \
            mavlink.ADSB_FLAGS_VALID_VELOCITY + \
            mavlink.ADSB_FLAGS_VALID_CALLSIGN + \
            mavlink.ADSB_FLAGS_VALID_SQUAWK

        adsb = mavlink.MAVLink_adsb_vehicle_message(
            ADSB_ICAO_ADDR,                             # ICAO_address (uint32_t)
            int(data["gnss"]["latitude"]*10000000),     # lat (int32_t, degE7)
            int(data["gnss"]["longitude"]*10000000),    # lon (int32_t, degE7)
            1,                                          # altitude type (0=QNH, 1=GNSS)
            int(data["gnss"]["altitude_m"]*1000),       # altitude (uint32_t, mm)
            int(data["gnss"]["heading_deg"]*100),       # heading (uint16_t, cdeg)
            int(data["gnss"]["speed_mps"]*100),         # hor_vel (uint16_t, cm/s)
            0,                                          # ver_vel (int16_t, cm/s, positive up)
            adsb_callsign,                              # callsign (char[9])
            ADSB_EMITTER_TYPE,                          # emitter_type (uint8_t)
            0,                                          # TODO: time since last contact (uint8_t, s)
            adbs_flags,                                 # flags (uint16_t)
            ADSB_SQUAWK)                                # squawk (uint16_t)
        mav_out.mav.send(adsb)
        logger.info("OUT: %s", adsb)

    # mqtt_client.subscribe(mqtt_topic)

    heading = 0
    while True:
        heading = heading + 0.1
        if heading >= 360:
            heading = 0

        json_msg = {'gnss': {'latitude': 53.542566399999998,
                             "longitude": 9.9850910000000006,
                             "altitude_m": 497.0,
                             "speed_mps": 0,
                             "heading_deg": heading}}

        msg = paho.MQTTMessage()
        msg.payload = str.encode(json.dumps(json_msg))
        msg.topic = str.encode(mqtt_topic)
        on_message(None, None, msg)

        time.sleep(0.1)
