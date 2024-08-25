import socket
import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
from pytz import timezone
from ttkthemes import ThemedStyle
from pytz import all_timezones

Ball_Start_XPosition = 50
Ball_Start_YPosition = 50
Ball_Radius = 30
Ball_min_movement = 5
Refresh_Sec = 0.01
Window_Width = 800
Window_Height = 600


class ClientHandler(threading.Thread):
    def __init__(self, client_socket, server):
        super().__init__()
        self.client_socket = client_socket
        self.server = server

    def run(self):
        self.server.handle_client(self.client_socket)


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}
        self.running = True

    def start_server(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen()
            print(f"Server listening on {self.host}:{self.port}")

            while self.running:
                client_socket, client_addr = self.server_socket.accept()
                client_handler = ClientHandler(client_socket, self)
                client_handler.start()
                self.clients[client_socket] = timezone('UTC')

        except OSError as e:
            print(f"Error binding to address {self.host}:{self.port}: {e}")

    def handle_client(self, client_socket):
        print(f"Accepted connection from {client_socket.getpeername()}")

        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break

                if data == 'GET_TIME':
                    current_time = self.get_current_time(client_socket)
                    client_socket.send(current_time.encode('utf-8'))

                elif data.startswith('SET_TIMEZONE'):
                    _, timezone_str = data.split(' ')
                    self.set_client_timezone(client_socket, timezone_str)

        except ConnectionResetError:
            pass  # Handle the exception gracefully

        print(f"Connection from {client_socket.getpeername()} closed")
        client_socket.close()
        del self.clients[client_socket]

    def get_current_time(self, client_socket):
        current_time = datetime.now(timezone('UTC')).astimezone(self.clients[client_socket])
        return current_time.strftime('%Y-%m-%d %H:%M:%S %Z')

    def set_client_timezone(self, client_socket, timezone_str):
        try:
            client_timezone = timezone(timezone_str)
            client_socket.send(f"Timezone set to {timezone_str}".encode('utf-8'))
            self.clients[client_socket] = client_timezone
        except Exception as e:
            client_socket.send(f"Error setting timezone: {str(e)}".encode('utf-8'))

    def stop_server(self):
        self.running = False
        self.server_socket.close()


class TimeClientGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Time Client")

        style = ThemedStyle(master)
        style.set_theme("arc")

        style.configure("TLabel", font=("Candara", 12))
        style.configure("TButton", font=("Candara", 12))
        style.configure("TEntry", font=("Candara", 12))

        self.label_timezone = ttk.Label(master, text="Selected Timezone:", font=("Candara", 12))
        self.label_timezone.pack(pady=10)

        self.label_current_time = ttk.Label(master, text="", font=("Candara", 18, "bold", "italic"))
        self.label_current_time.pack(pady=20)

        self.timezone_listbox = tk.Listbox(master, selectmode=tk.SINGLE, font=("Arial", 12))
        for timezone_name in all_timezones:
            self.timezone_listbox.insert(tk.END, timezone_name)
        self.timezone_listbox.pack(pady=5)

        self.get_time_button = ttk.Button(master, text="Get Time", command=self.get_time)
        self.get_time_button.pack(pady=5)

        self.set_timezone_button = ttk.Button(master, text="Set Timezone", command=self.set_timezone)
        self.set_timezone_button.pack(pady=5)

        # Create a canvas for ball animation
        self.canvas = tk.Canvas(master, width=Window_Width, height=Window_Height, bg="white")
        self.canvas.pack()

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('127.0.0.1', 12345))

    def get_time(self):
        try:
            self.client_socket.send('GET_TIME'.encode('utf-8'))
            data = self.client_socket.recv(1024).decode('utf-8')
            self.label_current_time.config(text=f"{data}")
        except Exception as e:
            self.label_current_time.config(text=f"Error getting time: {str(e)}")

    def set_timezone(self):
        try:
            selected_index = self.timezone_listbox.curselection()
            if selected_index:
                timezone_str = self.timezone_listbox.get(selected_index)
                self.client_socket.send(f'SET_TIMEZONE {timezone_str}'.encode('utf-8'))
                response = self.client_socket.recv(1024).decode('utf-8')
                self.label_timezone.config(text=f"Selected Timezone: {timezone_str}")
            else:
                self.label_timezone.config(text="Please select a timezone from the list.")
        except Exception as e:
            self.label_timezone.config(text=f"Error setting timezone: {str(e)}")


def animate_ball(canvas, xinc, yinc):
    ball = canvas.create_oval(Ball_Start_XPosition - Ball_Radius,
                              Ball_Start_YPosition - Ball_Radius,
                              Ball_Start_XPosition + Ball_Radius,
                              Ball_Start_YPosition + Ball_Radius,
                              fill="alice blue", outline="Black", width=2)
    while True:
        canvas.move(ball, xinc, yinc)
        canvas.update()
        time.sleep(Refresh_Sec)
        ball_pos = canvas.coords(ball)
        al, bl, ar, br = ball_pos
        if al < abs(xinc) or ar > Window_Width - abs(xinc):
            xinc = -xinc
        if bl < abs(yinc) or br > Window_Height - abs(yinc):
            yinc = -yinc


def main():
    server = Server('127.0.0.1', 12345)
    server_thread = threading.Thread(target=server.start_server)
    server_thread.start()

    root = tk.Tk()
    client_gui = TimeClientGUI(root)

    # Start animating the ball
    animation_thread = threading.Thread(target=animate_ball,
                                        args=(client_gui.canvas, Ball_min_movement, Ball_min_movement))
    animation_thread.start()

    root.mainloop()

    # Graceful termination
    server.stop_server()


if __name__ == "__main__":
    main()
