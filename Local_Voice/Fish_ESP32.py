# fish_movement_test.py

import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

# ESP32_IP = os.getenv("ESP32_IP")
ESP32_IP="192.168.0.53"
URL = f"ws://{ESP32_IP}:81"

async def send_test_action(part, state, duration=2000):
    action = {
        "mode": "speaking",
        "sequence": [
            { "part": part, "state": state, "duration": duration }
        ]
    }

    async with websockets.connect(URL) as ws:
        await ws.send(json.dumps(action))
        print(f"Sent: {action}")

        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=2)
                print("Received:", msg)
        except asyncio.TimeoutError:
            print("No response, assuming movement done.")

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

    async with websockets.connect(URL) as ws:
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


def print_menu():
    print("\n--- Billy Bass Movement Tester ---")
    print("Available commands:")
    print("  mouth open")
    print("  mouth close")
    print("  tail")
    print("  head")
    print("  perform")
    print("  quit\n")

if __name__ == "__main__":
    print_menu()
    while True:
        cmd = input("Enter command: ").strip().lower()
        if cmd == "quit":
            break
        elif cmd == "mouth open":
            asyncio.run(send_test_action("mouth", "open"))
        elif cmd == "mouth close":
            asyncio.run(send_test_action("mouth", "close"))
        elif cmd == "tail":
            asyncio.run(send_test_action("tail", "wag"))
        elif cmd == "head":
            asyncio.run(send_test_action("head", "turn",))
        elif cmd == "perform":
            asyncio.run(fish_performance_test())
        else:
            print("Invalid command.")