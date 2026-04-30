# =========================
# opto_tagging_protocol_extStim.py
# =========================

#old code
import time
import serial

# New Code
import sys  # New Code


# New Code
def confirm_shutter_ttl_mode():  # New Code
    """
    Blocking confirmation dialog with a single 'Yes' button.
    Falls back to a terminal prompt if GUI is unavailable (e.g., headless run).
    """  # New Code
    try:  # New Code
        import tkinter as tk  # New Code
        from tkinter import ttk  # New Code
    except Exception:  # New Code
        # Terminal fallback  # New Code
        resp = input("Have you switched the shutter to Opto-tagging TTL mode? Type 'yes' to continue: ").strip().lower()  # New Code
        if resp != "yes":  # New Code
            raise RuntimeError("User did not confirm shutter TTL mode.")  # New Code
        return  # New Code

    root = tk.Tk()  # New Code
    root.withdraw()  # New Code
    root.attributes("-topmost", True)  # New Code

    win = tk.Toplevel(root)  # New Code
    win.title("Confirmation")  # New Code
    win.attributes("-topmost", True)  # New Code
    win.resizable(False, False)  # New Code

    msg = "Have you switched the shutter to Opto-tagging TTL mode?"  # New Code
    lbl = ttk.Label(win, text=msg, padding=(20, 15))  # New Code
    lbl.grid(row=0, column=0, padx=10, pady=(10, 0))  # New Code

    def on_yes():  # New Code
        win.destroy()  # New Code

    btn = ttk.Button(win, text="Yes", command=on_yes)  # New Code
    btn.grid(row=1, column=0, pady=(10, 15))  # New Code

    win.protocol("WM_DELETE_WINDOW", lambda: None)  # New Code (force explicit Yes)
    win.grab_set()  # New Code
    win.update_idletasks()  # New Code
    # Center the window  # New Code
    w = win.winfo_reqwidth()  # New Code
    h = win.winfo_reqheight()  # New Code
    x = (win.winfo_screenwidth() // 2) - (w // 2)  # New Code
    y = (win.winfo_screenheight() // 2) - (h // 2)  # New Code
    win.geometry(f"+{x}+{y}")  # New Code

    root.wait_window(win)  # New Code
    root.destroy()  # New Code


def optotagging_protocol(port="COM8", interval=2, duration=120):
    # New Code (place as the FIRST line inside the function)
    confirm_shutter_ttl_mode()  # New Code

    try:
        ser = serial.Serial(port, write_timeout = 0.001)
        print("-------Stim Serial Connected--------")
    except Exception as e:
        print('No Stim serial')
        print(e)

    n_pulses = duration // interval
    print(f"Starting optotagging: {n_pulses} pulses, every {interval} sec")

    for i in range(n_pulses):
        try:
            msg = 'S'
            print(f"Pulse {i+1}/{n_pulses} sent")
            ser.write(msg.encode())

        except Exception as e:
            print(e)
        time.sleep(interval)
    ser.close()
    print("Optotagging complete.")


if __name__ == "__main__":
    confirm_shutter_ttl_mode()
    optotagging_protocol(port="COM8", interval=2, duration=120)