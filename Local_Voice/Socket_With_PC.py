import socket
import json

# ==== CONFIG ====
PC_IP = "192.168.0.134"  # ? Replace with your actual PC IP
PC_PORT = 5050           # Port where PC is listening for responses
PI_LISTEN_PORT = 5051    # Port where Pi listens for transcript from PC

# ==== Response Generator ====
def generate_response(user_text):
    print(f"??? User said: {user_text}")
    # Simple rule-based logic (you can replace this with AI later)
    if "joke" in user_text.lower():
        return "Why don't fish do well in school? Because they're always swimming below sea level."
    elif "hi" in user_text.lower():
        return "Hello from the Raspberry Pi!"
    return "I heard you, let me think about that."

# ==== Main Socket Loop ====
def start_pi_socket():
    print(f"?? Waiting for PC speech input on port {PI_LISTEN_PORT}...")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(('', PI_LISTEN_PORT))
        server.listen(1)

        while True:
            conn, addr = server.accept()
            with conn:
                print(f"?? Connected from PC: {addr}")
                user_text = conn.recv(4096).decode().strip()

                if not user_text:
                    print("?? Received empty transcript")
                    continue

                print(f"?? Received from PC: {user_text}")

                # Generate response to send back to PC
                response = generate_response(user_text)

                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as pc_socket:
                        print(f"?? Connecting to PC at {PC_IP}:{PC_PORT}...")
                        pc_socket.connect((PC_IP, PC_PORT))
                        print(f"?? Sending response: {response}")
                        pc_socket.sendall(response.encode())

                        print("? Waiting for phoneme JSON...")
                        data = pc_socket.recv(8192)

                        try:
                            phoneme_data = json.loads(data.decode())
                            print("? Received phoneme timing data:")
                            for p in phoneme_data:
                                print(f"{p['phoneme']:>3} : {p['start']:.2f}�{p['end']:.2f}")

                            # ?? TODO: Animate Billy Bass using `phoneme_data` here

                        except json.JSONDecodeError as e:
                            print(f"? Failed to decode phoneme JSON: {e}")

                except ConnectionRefusedError:
                    print(f"? Could not connect to PC at {PC_IP}:{PC_PORT}. Is the server running?")

if __name__ == "__main__":
    start_pi_socket()
