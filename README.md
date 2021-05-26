# MAVLink ADS-B Emulator
Generate MAVLink [ADSB_VEHICLE](https://mavlink.io/en/messages/common.html#ADSB_VEHICLE) messages from PX4 telemetry.


## Installation
Clone this repository and install the python dependencies with `pip3 install -r requirements.txt`.


## Usage
This utility generates ADSB_VEHICLE messages from GLOBAL_POSITION_INT information.
Telemetry from the FMU is received on the input "device" and ADSB data is sent on a separate output mavlink connection.

The input and output connection strings are according to the PyMavlink library, e.g.:
- `udpin:$ip:$port`: Listening for UDP packets on the specified IP (normally 0.0.0.0) and port
- `udpout:$ip:$port`: Sending UDP packets to the specified IP and port, will start with a heartbeat to "activate" the connection when using mavlink-router
- `tcp:$ip:$port`: Connecting to the specified IP and port
- `/dev/ttyX`: UART connection. Optionally specify the baud rate with `-b $baudrate`.

So to connect to the FMU via UART and send ADS-B message out via UDP, execute:
```shell
python3 mavlink_adsb_emulator.py -i /dev/ttymxc2 -o udpout:$ip:$port
```

Notes:
- Domain names also work instead of the IP address
- If the FMU is only used as a GPS receiver, keep in mind, that all pre-flight checks need to pass (green light on the FMU/ GPS) before the GLOBAL_POSITION_INT is sent.
It might be necessary to set the following parameters:
  * CBRK_IO_SAFETY = 22027 (disable safety switch)
  * CBRK_SUPPLY_CHK = 894281 (also work on low battery)
