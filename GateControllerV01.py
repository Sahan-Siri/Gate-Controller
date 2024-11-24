import pyfirmata
import time
import tkinter as tk
from tkinter import ttk
from threading import Thread
import webbrowser  # Import for opening the link in a browser

# Function to create a pyfirmata board instance and start an iterator
def setup_board(port):
    try:
        board = pyfirmata.Arduino(port)
        it = pyfirmata.util.Iterator(board)
        it.start()
        # Define analog pins for voltage reading
        board.analog[0].enable_reporting()
        board.analog[1].enable_reporting()
        board.analog[2].enable_reporting()
        return board
    except Exception as e:
        return None

# Define the digital pins to control
pins = {}
board = None

# Set up the GUI
root = tk.Tk()
root.title("Arduino Gate Controller")

# Set a fixed window size
window_width = 600
window_height = 600
root.geometry(f"{window_width}x{window_height}")
root.resizable(False, False)  # Disable window resizing

# Selected COM port
selected_port = tk.StringVar()

# Label to show connection status
status_label = tk.Label(root, text="Enter a port and click Initialize")
status_label.pack(anchor=tk.W)

# Function to initialize the board and set up pins
def initialize():
    global pins, board
    port = 'COM'+selected_port.get()
    board = setup_board(port)
    if board is not None:
        status_label.config(text=f"Connected to {port}")
        pins = {
            1: board.get_pin('d:3:o'),   # Connect checkbox 1 to pin 3
            2: board.get_pin('d:5:o'),   # Connect checkbox 2 to pin 5
            3: board.get_pin('d:6:o'),   # Connect checkbox 3 to pin 6
            4: board.get_pin('d:9:o'),   # Connect checkbox 4 to pin 9
            5: board.get_pin('d:10:o')   # Connect checkbox 5 to pin 10
        }
        submit_button.config(state=tk.NORMAL)
        reset_button.config(state=tk.NORMAL)
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.NORMAL)
        update_voltages()  # Start updating voltage readings
    else:
        status_label.config(text=f"Failed to connect to {port}")

# Dictionary to hold the state of each checkbox
pin_states = {pin_number: tk.IntVar() for pin_number in range(1, 6)}

# Function to set the selected pins high and others low
def submit():
    for pin_number, pin in pins.items():
        if pin_states[pin_number].get() == 1:
            pin.write(1)  # Set the pin high
        else:
            pin.write(0)  # Set the pin low

# Function to set all pins low
def reset():
    for pin_number, pin in pins.items():
        pin.write(0)
        pin_states[pin_number].set(0)

# Function to start switching
def start_switching():
    try:
        frequency = float(frequency_entry.get())
        dead_band = float(dead_band_entry.get()) / 1_000_000  # Convert us to seconds
        charging_duty_cycle = float(charging_duty_cycle_entry.get()) / 100
        discharging_duty_cycle = float(discharging_duty_cycle_entry.get()) / 100
        period = 1.0 / frequency
        charging_time = period * charging_duty_cycle
        discharging_time = period * discharging_duty_cycle

        if dead_band >= period:
            status_label.config(text="Error: Dead band must be less than period")
            return

        selected_charging_pins = [pin_num for pin_num, var in pwm_charging_checkboxes.items() if var.get()]
        selected_discharging_pins = [pin_num for pin_num, var in pwm_discharging_checkboxes.items() if var.get()]


        def switch():
            while switching:
                # Charging cycle
                for pin_num in selected_charging_pins:
                    pins[pin_num].write(1)
                time.sleep(charging_time)
                for pin_num in selected_charging_pins:
                    pins[pin_num].write(0)
                time.sleep(dead_band)
                # Discharging cycle
                for pin_num in selected_discharging_pins:
                    pins[pin_num].write(1)
                time.sleep(discharging_time)
                for pin_num in selected_discharging_pins:
                    pins[pin_num].write(0)
                time.sleep(dead_band)

        global switching_thread
        global switching
        switching = True
        switching_thread = Thread(target=switch)
        switching_thread.start()

    except ValueError:
        status_label.config(text="Error: Invalid frequency, dead band, or duty cycle value")

# Function to stop switching
def stop_switching():
    global switching
    switching = False
    reset()

# Function to update voltage readings
def update_voltages():
    if board:
        voltage_a0 = board.analog[0].read()
        voltage_a1 = board.analog[1].read()
        voltage_a2 = board.analog[2].read()

        # Scale readings from 0-1 to 0-5V
        if voltage_a0 is not None:
            voltage_a0_label.config(text=f"9V Super Capacitor: {voltage_a0*25:.2f} V")
        if voltage_a1 is not None:
            voltage_a1_label.config(text=f"3V Super Capacitor: {(2.5897*(voltage_a1)**3)-(4.8153*(voltage_a1)**2)+5.6571*(voltage_a1):.2f} V")
        if voltage_a2 is not None:
            voltage_a2_label.config(text=f"Battery: {voltage_a2*25:.2f} V")
        
    root.after(500, update_voltages)

# Create COM port entry field
tk.Label(root, text="Enter COM Port:").pack(anchor=tk.W)
com_port_entry = tk.Entry(root, textvariable=selected_port)
com_port_entry.pack(anchor=tk.W)

# Create initialize button
tk.Button(root, text="Initialize", command=initialize).pack()

# Create checkboxes for pin selection
for pin_number in range(1, 6):
    tk.Checkbutton(root, text=f"Gate {pin_number}", variable=pin_states[pin_number]).pack(anchor=tk.W)

# Create submit button
submit_button = tk.Button(root, text="Submit", command=submit, state=tk.DISABLED)
submit_button.pack()

# Create reset button
reset_button = tk.Button(root, text="Reset", command=reset, state=tk.DISABLED)
reset_button.pack()

# Create frequency and dead band entry fields with parallel checkboxes
control_frame = tk.Frame(root)
control_frame.pack(anchor=tk.W, pady=10)

tk.Label(control_frame, text="Frequency (Hz):").grid(row=0, column=0, sticky=tk.W)
frequency_entry = tk.Entry(control_frame)
frequency_entry.grid(row=0, column=1, sticky=tk.W)

tk.Label(control_frame, text="Dead Band (us):").grid(row=1, column=0, sticky=tk.W)
dead_band_entry = tk.Entry(control_frame)
dead_band_entry.grid(row=1, column=1, sticky=tk.W)

# Duty cycle and parallel checkboxes for charging and discharging
tk.Label(control_frame, text="PWM 1 Duty Cycle (%):").grid(row=2, column=0, sticky=tk.W)
charging_duty_cycle_entry = tk.Entry(control_frame)
charging_duty_cycle_entry.grid(row=2, column=1, sticky=tk.W)

tk.Label(control_frame, text="PWM 2 Duty Cycle (%):").grid(row=3, column=0, sticky=tk.W)
discharging_duty_cycle_entry = tk.Entry(control_frame)
discharging_duty_cycle_entry.grid(row=3, column=1, sticky=tk.W)

# PWM pin selection checkboxes for charging
tk.Label(control_frame, text="Select PWM 1 Pins:").grid(row=4, column=0, sticky=tk.W)
pwm_charging_checkboxes = {pin_number: tk.IntVar() for pin_number in range(1, 6)}
for idx, (pin_number, var) in enumerate(pwm_charging_checkboxes.items()):
    tk.Checkbutton(control_frame, text=f"Gate {pin_number}", variable=var).grid(row=4, column=idx+1)

# PWM pin selection checkboxes for discharging
tk.Label(control_frame, text="Select PWM 2 Pins:").grid(row=5, column=0, sticky=tk.W)
pwm_discharging_checkboxes = {pin_number: tk.IntVar() for pin_number in range(1, 6)}
for idx, (pin_number, var) in enumerate(pwm_discharging_checkboxes.items()):
    tk.Checkbutton(control_frame, text=f"Gate {pin_number}", variable=var).grid(row=5, column=idx+1)

# Create start switching button
start_button = tk.Button(root, text="Start Switching", command=start_switching, state=tk.DISABLED)
start_button.pack()

# Create stop switching button
stop_button = tk.Button(root, text="Stop Switching", command=stop_switching, state=tk.DISABLED)
stop_button.pack()

# Create labels for voltage readings
# Create labels for voltage readings
voltage_a0_label = tk.Label(root, text="9V Super Capacitor: -- V")
voltage_a0_label.pack(anchor=tk.W)

voltage_a1_label = tk.Label(root, text="3V Super Capacitor: -- V")
voltage_a1_label.pack(anchor=tk.W)

voltage_a2_label = tk.Label(root, text="Battery: -- V")
voltage_a2_label.pack(anchor=tk.W)

# Function to open the link in a web browser
def open_about_link(event):
    webbrowser.open("https://github.com/Sahan-Siri/Gate-Controller")

# Create "About" hyperlink
about_label = tk.Label(root, text="About", fg="blue", cursor="hand2")
# Place the "About" hyperlink at the bottom-right
about_label.pack(side=tk.RIGHT, anchor=tk.S, padx=10, pady=10)

about_label.bind("<Button-1>", open_about_link)  # Bind left-click event to open the link


# Start the GUI loop
root.mainloop()

