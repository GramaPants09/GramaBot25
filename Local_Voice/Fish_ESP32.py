# fish_movement_test.py

import asyncio
import websockets
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

ESP32_IP = "192.168.0.53"
ESP32_PORT = 81
# ESP32_IP = os.getenv("ESP32_IP", "192.168.0.53")
# ESP32_PORT = int(os.getenv("ESP32_PORT", "81"))
URL = f"ws://{ESP32_IP}:{ESP32_PORT}"


def print_connection_help(err: Exception):
    print(f"Could not connect to ESP32 at {URL}")
    print(f"Error: {err}")
    print("Check that:")
    print("  1) ESP32 is powered on and running websocket server")
    print("  2) IP/port are correct")
    print("  3) Raspberry Pi and ESP32 are on the same network")
    print("  4) .env has ESP32_IP and optional ESP32_PORT")

async def send_test_action(part, state, duration=2000):
    action = {
        "mode": "speaking",
        "sequence": [
            { "part": part, "state": state, "duration": duration }
        ]
    }

    try:
        async with websockets.connect(URL, open_timeout=3) as ws:
            await ws.send(json.dumps(action))
            print(f"Sent: {action}")

            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2)
                    print("Received:", msg)
            except asyncio.TimeoutError:
                print("No response, assuming movement done.")
    except (OSError, asyncio.TimeoutError, websockets.WebSocketException) as err:
        print_connection_help(err)

async def fish_performance_test(sequence = [
        {"part": "head", "state": "turn", "duration": 1000, "delay": 0},
        {"part": "mouth", "state": "open", "duration": 100, "delay": 100},
        {"part": "mouth", "state": "close", "duration": 100, "delay": 300},
        {"part": "mouth", "state": "open", "duration": 150, "delay": 500},
        {"part": "mouth", "state": "close", "duration": 100, "delay": 700},
        {"part": "mouth", "state": "open", "duration": 200, "delay": 900},
        {"part": "mouth", "state": "close", "duration": 100, "delay": 1150},
        {"part": "tail", "state": "wag", "duration": 300, "delay": 1300}
    ]):

    message = {
        "mode": "speaking",
        "sequence": sequence
    }

    try:
        async with websockets.connect(URL, open_timeout=3) as ws:
            await ws.send(json.dumps(message))
            print("?? Sent performance test to fish")

            try:
                while True:
                    reply = await asyncio.wait_for(ws.recv(), timeout=5)
                    print("?? ESP32 says:", reply)
                    if '"sequence_complete"' in reply:
                        print("? Sequence complete. The fish has spoken.")
                        break
            except asyncio.TimeoutError:
                print("??? Timeout. Fish may be sulking.")
    except (OSError, asyncio.TimeoutError, websockets.WebSocketException) as err:
        print_connection_help(err)


def print_menu():
    print("\n--- Billy Bass Movement Tester ---")
    print("Available commands:")
    print("  mouth open")
    print("  mouth close")
    print("  tail")
    print("  head")
    print("  perform")
    print("  quit\n")


def run_command(cmd: str) -> bool:
    if cmd == "mouth open":
        asyncio.run(send_test_action("mouth", "open"))
    elif cmd == "mouth close":
        asyncio.run(send_test_action("mouth", "close"))
    elif cmd == "tail":
        asyncio.run(send_test_action("tail", "wag"))
    elif cmd == "head":
        asyncio.run(send_test_action("head", "turn"))
    elif cmd == "perform":
        asyncio.run(fish_performance_test())
    elif cmd == "quit":
        return False
    else:
        print("Invalid command.")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg_cmd = " ".join(sys.argv[1:]).strip().lower()
        if arg_cmd and arg_cmd != "quit":
            run_command(arg_cmd)
        sys.exit(0)

    print_menu()
    while True:
        try:
            cmd = input("Enter command: ").strip().lower()
        except EOFError:
            print("No interactive stdin detected. Run with an argument, e.g.:")
            print("python Local_Voice/Fish_ESP32.py \"mouth open\"")
            break

        if not run_command(cmd):
            break