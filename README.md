# MAVLink ADS-B Emulator
Generate MAVLink [ADSB_VEHICLE](https://mavlink.io/en/messages/common.html#ADSB_VEHICLE) messages from MQTT messages with JSON position data.


## Installation
Clone this repository and install the python dependencies with `pip3 install -r requirements.txt`.


## Usage
This utility generates ADSB_VEHICLE messages from position information received from MQTT.

The input connection is defined using a MQTT URL.

The output connection strings are according to the PyMavlink library, e.g.:
- `udpin:$ip:$port`: Listening for UDP packets on the specified IP (normally 0.0.0.0) and port
- `udpout:$ip:$port`: Sending UDP packets to the specified IP and port, will start with a heartbeat to "activate" the connection when using mavlink-router
- `tcp:$ip:$port`: Connecting to the specified IP and port

To fetch data from a MQTT broker on localhost in topic "topicname" and send it to localhost:14550, run:
```shell
python3 mavlink_adsb_emulator.py -i tcp://localhost:1883/topicname -o udpout:localhost:14550
```

The MQTT input should contain these values:
```json
{
    "gnss": {
        "latitude": 52.142716,
        "longitude": 11.6573132,
        "altitude_m": 91.601,
        "speed_mps": 0.032,
        "heading_deg": 0,
    }
}
```
