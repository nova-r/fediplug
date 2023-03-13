"""Buttplug controller"""

import asyncio
import logging
import sys

from buttplug import Client, WebsocketConnector, ProtocolSpec

from fediplug.cli import options

from typing import Tuple


async def connect_plug_client(websocket_url: str = "127.0.0.1:12345") -> Client:
    """create Client object and connect plug client to Intiface Central or similar"""
    plug_client = Client("fediplug", ProtocolSpec.v3)
    connector = WebsocketConnector(f"ws://{websocket_url}", logger=plug_client.logger)

    try:
        await plug_client.connect(connector)
    except Exception as e:
        logging.error(f"Could not connect to server, exiting: {e}")
        return
    print("plug client connected")
    return plug_client


async def scan_devices(plug_client: Client) -> Client:
    # scan for devices for 5 seconds
    await plug_client.start_scanning()
    await asyncio.sleep(5)
    await plug_client.stop_scanning()
    plug_client.logger.info(f"Devices: {plug_client.devices}")

    # If we have any device we can print the list of devices
    # and access it by its ID: ( this step is done is trigger_actuators() )
    if len(plug_client.devices) != 0:
        print(plug_client.devices)
        print(len(plug_client.devices), "devices found")
    return plug_client


async def trigger_actuators(
    plug_client: Client, actuator_command: Tuple[float, float]
) -> None:
    MAX_DURATION = 60  # maximum duration in seconds
    MAX_POWER = 1  # has to be 0 <= n <= 1 or it will not work
    duration = clamp(actuator_command[0], 0, MAX_DURATION)
    power = clamp(actuator_command[1], 0, MAX_POWER)
    # If we have any device we can access it by its ID:
    device = plug_client.devices[0]
    if len(device.actuators) != 0:
        print(len(device.actuators), "actuators found")
        # cycle through all actuators in device
        print(device.actuators)
        print(f"{duration=} {power=}")
        for actuator in device.actuators:
            await actuator.command(power)
            print("generic actuator")
        await asyncio.sleep(duration)
        # stops all actuators
        for actuator in device.actuators:
            await actuator.command(0)


"""
    # Some devices may have linear actuators which need a different command.
    # The first parameter is the time duration in ms and the second the
    # position for the linear axis (0.0-1.0).
    if len(device.linear_actuators) != 0:
        await device.linear_actuators[0].command(1000, 0.5)
        print("linear actuator")

    # Other devices may have rotatory actuators which another command.
    # The first parameter is the speed (0.0-1.0) and the second parameter
    # is a boolean, true for clockwise, false for anticlockwise.
    if len(device.rotatory_actuators) != 0:
        await device.rotatory_actuators[0].command(0.5, True)
        print("rotary actuator") 
"""


async def disconnect_plug_client(plug_client: Client) -> None:
    # Disconnect the plug_client.
    await plug_client.disconnect()


def clamp(n: float, smallest: float, largest: float) -> float:
    """returns the closest value to n still in range (clamp)"""
    return max(smallest, min(n, largest))


# First things first. We set logging to the console and at INFO level.
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
