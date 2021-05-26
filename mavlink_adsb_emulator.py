#!/usr/bin/env python3
"""
D2X Demos - MAVLink ADSB_VEHILCE Emulator

Generate MAVLink ADSB_VEHICLE messages from PX4 telemetry.

Author:    Jannik Beyerstedt <beyerstedt@consider-it.de>
Copyright: (c) consider it GmbH, 2021
"""

import argparse
import logging
from math import sqrt
import sys
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
                        help="connection address to FMU, e.g. /dev/ttyx, tcp:$ip:$port, udpin:$ip:$port")
    parser.add_argument("-b", "--baud", type=int, default=115200,
                        help="baud rate (only for uart, default 115200)")
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
    # open connection to the FMU
    try:
        mav_in = mavutil.mavlink_connection(
            args.input, baud=args.baud, source_system=OWN_SYSID, source_component=OWN_COMPID)
    except OSError:
        logger.error("MAVLink connection failed, exiting")
        sys.exit(-1)

    # when udpout, start with sending a heartbeat
    if args.input.startswith('udpout:'):
        i = 0
        logger.info("UDP out: sending heartbeat to initilize a connection")
        while True:
            mav_in.mav.heartbeat_send(OWN_SYSID, OWN_COMPID, base_mode=0,
                                      custom_mode=0, system_status=0)
            i += 1

            msg = mav_in.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
            if msg is not None:
                break

            if i >= UDP_CONNECT_TIMEOUT:
                logger.error("UDP out: nothing received, terminating")
                sys.exit(-1)

            logger.debug("UDP out: retrying heartbeat")

    # open connection to the FMU
    try:
        # TODO: which sysID and compID should we use?
        mav_out = mavutil.mavlink_connection(
            args.output, source_system=OWN_SYSID, source_component=OWN_COMPID)
    except OSError:
        logger.error("MAVLink connection failed, exiting")
        sys.exit(-1)

    # RUN
    while True:
        msg = mav_in.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
        logger.debug("Message from %d/%d: %s", msg.get_srcSystem(), msg.get_srcComponent(), msg)

        # just evaluate messages from specific system, if requested
        if args.sysID is not None and msg.get_srcSystem() != args.sysID:
            logger.debug("Ignore message from system %d", msg.get_srcSystem())
            continue

        # fill ADSB_VEHICLE message and send
        hor_vel = int(sqrt(msg.vx ** 2 + msg.vy ** 2))
        adsb_callsign = bytes(ADSB_CALLSIGN, 'ascii')
        adbs_flags = mavlink.ADSB_FLAGS_VALID_COORDS + \
            mavlink.ADSB_FLAGS_VALID_ALTITUDE + \
            mavlink.ADSB_FLAGS_VALID_HEADING + \
            mavlink.ADSB_FLAGS_VALID_VELOCITY + \
            mavlink.ADSB_FLAGS_VALID_CALLSIGN + \
            mavlink.ADSB_FLAGS_VALID_SQUAWK + \
            mavlink.ADSB_FLAGS_VERTICAL_VELOCITY_VALID
        # TODO: What information is actually valid

        msg_out = mavlink.MAVLink_adsb_vehicle_message(ADSB_ICAO_ADDR,      # ICAO_address (uint32_t)
                                                       msg.lat, msg.lon,    # lan, lon (int32_t, degE7)
                                                       1,                   # altitude_type (uint8_t, 0=QNH, 1=GNSS)
                                                       msg.alt,             # altitude (uint32_t, mm)
                                                       msg.hdg,             # heading (uint16_t, cdeg)
                                                       hor_vel,             # hor_velocity (uint16_t, cm/s)
                                                       -msg.vz,             # ver_velocity (int16_t, cm/s, positive up)
                                                       adsb_callsign,       # callsign (char[9])
                                                       ADSB_EMITTER_TYPE,   # emitter_type (uint8_t)
                                                       0,  # TODO: time since last contact (uint8_t, s)
                                                       adbs_flags,          # flags (uint16_t)
                                                       ADSB_SQUAWK)         # squawk (uint16_t)
        mav_out.mav.send(msg_out)
        logger.debug("Message sent %d/%d: %s", msg.get_srcSystem(), msg.get_srcComponent(), msg_out)
