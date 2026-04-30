# =========================
# opto_tagging_protocol_v2.py
# =========================

#old code
import time  #old code
import serial  #old code

# New Code
import threading  # New Code
import tkinter as tk  # New Code
from tkinter import ttk  # New Code


# New Code
class OptoTaggingGUI:  # New Code
    def __init__(self, root: tk.Tk):  # New Code
        self.root = root  # New Code
        self.root.title("Opto-tagging Control")  # New Code
        self.root.resizable(False, False)  # New Code

        # State  # New Code
        self.confirmed_shutter = False  # New Code
        self.is_running = False  # New Code
        self.abort_flag = False  # New Code

        # Defaults (match your prior defaults)  # New Code
        self.port_var = tk.StringVar(value="COM8")  # New Code
        self.ttl_char_var = tk.StringVar(value="S")  # New Code
        self.interval_var = tk.DoubleVar(value=2.0)  # New Code
        self.duration_var = tk.IntVar(value=120)  # New Code

        # Serial handle  # New Code
        self.ser = None  # New Code
                # New Code: define green Run button style
        self.style = ttk.Style()  # New Code
        self.style.configure("Green.TButton", foreground="black")  # New Code
        self.style.map(
            "Green.TButton",
            background=[("active", "green"), ("!disabled", "green")]
        )  # New Code

        self._build_ui()  # New Code
        self._update_buttons()  # New Code

    # New Code
    def _build_ui(self):  # New Code
        pad = {"padx": 10, "pady": 6}  # New Code

        frm = ttk.Frame(self.root)  # New Code
        frm.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)  # New Code

                # New Code: green button style
        style = ttk.Style()  # New Code
        style.configure("Green.TButton", background="green")  # New Code


        # Connection / params  # New Code
        ttk.Label(frm, text="Serial Port (COM):").grid(row=0, column=0, sticky="w", **pad)  # New Code
        ttk.Entry(frm, textvariable=self.port_var, width=14).grid(row=0, column=1, sticky="w", **pad)  # New Code

        ttk.Label(frm, text="TTL Letter:").grid(row=0, column=2, sticky="w", **pad)  # New Code
        ttk.Entry(frm, textvariable=self.ttl_char_var, width=6).grid(row=0, column=3, sticky="w", **pad)  # New Code

        ttk.Label(frm, text="Inter-TTL Interval (s):").grid(row=1, column=0, sticky="w", **pad)  # New Code
        ttk.Entry(frm, textvariable=self.interval_var, width=14).grid(row=1, column=1, sticky="w", **pad)  # New Code

        ttk.Label(frm, text="Duration (s):").grid(row=1, column=2, sticky="w", **pad)  # New Code
        ttk.Entry(frm, textvariable=self.duration_var, width=14).grid(row=1, column=3, sticky="w", **pad)  # New Code

        # Buttons row  # New Code
        self.test_btn = ttk.Button(frm, text="Test Stimulation (1 TTL)", command=self.on_test)  # New Code
        self.test_btn.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 6))  # New Code

        self.run_btn = ttk.Button(frm, text="Run Opto-tagging Protocol", command=self.on_run)  # New Code
        self.run_btn.grid(row=2, column=2, columnspan=2, sticky="ew", padx=10, pady=(10, 6))  # New Code

        self.abort_btn = ttk.Button(frm, text="Abort", command=self.on_abort)  # New Code
        self.abort_btn.grid(row=3, column=2, columnspan=2, sticky="ew", padx=10, pady=(0, 6))  # New Code

        # Big red confirmation area (hidden until needed)  # New Code
        self.confirm_frame = tk.Frame(frm, bd=2, relief="ridge")  # New Code
        self.confirm_frame.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=(8, 0))  # New Code
        self.confirm_frame.grid_remove()  # New Code

        self.confirm_label = tk.Label(  # New Code
            self.confirm_frame,  # New Code
            text="DID YOU FLIP SHUTTER TO OPTO-TAGGING?",  # New Code
            fg="red",  # New Code
            font=("TkDefaultFont", 16, "bold"),  # New Code
            padx=12, pady=10  # New Code
        )  # New Code
        self.confirm_label.grid(row=0, column=0, columnspan=2, sticky="ew")  # New Code

        self.confirm_yes_btn = ttk.Button(self.confirm_frame, text="Yes", command=self.on_confirm_yes)  # New Code
        self.confirm_yes_btn.grid(row=1, column=0, sticky="ew", padx=10, pady=10)  # New Code

        self.confirm_cancel_btn = ttk.Button(self.confirm_frame, text="Cancel", command=self.on_confirm_cancel)  # New Code
        self.confirm_cancel_btn.grid(row=1, column=1, sticky="ew", padx=10, pady=10)  # New Code

        # Status  # New Code
        self.status_var = tk.StringVar(value="Idle.")  # New Code
        self.status_lbl = ttk.Label(frm, textvariable=self.status_var)  # New Code
        self.status_lbl.grid(row=5, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 0))  # New Code

    # New Code
    def _update_buttons(self):  # New Code
        if self.is_running:  # New Code
            self.test_btn.state(["disabled"])  # New Code
            self.run_btn.state(["disabled"])  # New Code
            self.abort_btn.state(["!disabled"])  # New Code
        else:  # New Code
            self.test_btn.state(["!disabled"])  # New Code
            self.run_btn.state(["!disabled"])  # New Code
            self.abort_btn.state(["disabled"])  # New Code

    # New Code
    def _open_serial(self):  # New Code
        port = self.port_var.get().strip()  # New Code
        if not port:  # New Code
            raise ValueError("Port is empty.")  # New Code
        # Keep your write_timeout behavior  # New Code
        self.ser = serial.Serial(port, write_timeout=0.001)  # New Code

    # New Code
    def _close_serial(self):  # New Code
        try:  # New Code
            if self.ser is not None and self.ser.is_open:  # New Code
                self.ser.close()  # New Code
        finally:  # New Code
            self.ser = None  # New Code

    # New Code
    def _get_params(self):  # New Code
        ttl_char = self.ttl_char_var.get().strip()  # New Code
        if len(ttl_char) != 1:  # New Code
            raise ValueError("TTL Letter must be exactly 1 character (e.g., 'S').")  # New Code

        interval = float(self.interval_var.get())  # New Code
        duration = int(self.duration_var.get())  # New Code

        if interval <= 0:  # New Code
            raise ValueError("Inter-TTL Interval must be > 0.")  # New Code
        if duration <= 0:  # New Code
            raise ValueError("Duration must be > 0.")  # New Code

        return ttl_char, interval, duration  # New Code

    # New Code
    def _set_status(self, msg: str):  # New Code
        self.status_var.set(msg)  # New Code
        self.root.update_idletasks()  # New Code

    # New Code
    def on_test(self):  # New Code
        try:  # New Code
            ttl_char, _, _ = self._get_params()  # New Code
            self._open_serial()  # New Code
            self.ser.write(ttl_char.encode())  # New Code
            self._set_status(f"Test TTL sent: '{ttl_char}'")  # New Code
        except Exception as e:  # New Code
            self._set_status(f"Test failed: {e}")  # New Code
        finally:  # New Code
            self._close_serial()  # New Code

    # New Code
    def on_run(self):  # New Code
        # First click should prompt for shutter confirmation  # New Code
        if not self.confirmed_shutter:  # New Code
            self.confirm_frame.grid()  # New Code
            self._set_status("Waiting for shutter confirmation...")  # New Code
            return  # New Code

        # Second click actually starts the protocol  # New Code
        if self.is_running:  # New Code
            return  # New Code

        try:  # New Code
            ttl_char, interval, duration = self._get_params()  # New Code
        except Exception as e:  # New Code
            self._set_status(f"Invalid parameters: {e}")  # New Code
            return  # New Code

        self.abort_flag = False  # New Code
        self.is_running = True  # New Code
        self._update_buttons()  # New Code
        self._set_status("Starting opto-tagging...")  # New Code

        t = threading.Thread(  # New Code
            target=self._run_protocol_thread,  # New Code
            args=(ttl_char, interval, duration),  # New Code
            daemon=True  # New Code
        )  # New Code
        t.start()  # New Code

    # New Code
    def on_abort(self):  # New Code
        if self.is_running:  # New Code
            self.abort_flag = True  # New Code
            self._set_status("Abort requested...")  # New Code

    # New Code
    def on_confirm_yes(self):  # New Code
        self.confirmed_shutter = True  # New Code
        self.confirm_frame.grid_remove()  # New Code

        # New Code: Run button turns green immediately
        self.run_btn.configure(style="Green.TButton")  # New Code

        self._set_status(
            "Shutter confirmed. Click Run again to start protocol."
        )  # New Code

    # New Code
    def on_confirm_cancel(self):  # New Code
        self.confirmed_shutter = False  # New Code
        self.confirm_frame.grid_remove()  # New Code
        self._set_status("Confirmation cancelled.")  # New Code

    # New Code
    def _run_protocol_thread(self, ttl_char: str, interval: float, duration: int):  # New Code
        try:  # New Code
            self._open_serial()  # New Code
            n_pulses = int(duration // interval)  # New Code
            if n_pulses <= 0:  # New Code
                raise ValueError("Duration is shorter than one interval; no pulses would be sent.")  # New Code

            self.root.after(0, lambda: self._set_status(  # New Code
                f"Running: {n_pulses} pulses, every {interval:g}s (TTL='{ttl_char}')."  # New Code
            ))  # New Code

            for i in range(n_pulses):  # New Code
                if self.abort_flag:  # New Code
                    break  # New Code
                try:  # New Code
                    self.ser.write(ttl_char.encode())  # New Code
                except Exception as e:  # New Code
                    raise RuntimeError(f"Serial write failed on pulse {i+1}: {e}")  # New Code

                self.root.after(0, lambda i=i, n=n_pulses: self._set_status(  # New Code
                    f"Pulse {i+1}/{n} sent."  # New Code
                ))  # New Code

                time.sleep(interval)  # New Code

            if self.abort_flag:  # New Code
                self.root.after(0, lambda: self._set_status("Protocol aborted."))  # New Code
            else:  # New Code
                self.root.after(0, lambda: self._set_status("Opto-tagging complete."))  # New Code

        except Exception as e:  # New Code
            self.root.after(0, lambda: self._set_status(f"Run failed: {e}"))  # New Code
        finally:  # New Code
            self._close_serial()  # New Code
            self.run_btn.configure(style="TButton")  # New Code


            #old code
            self.is_running = False  #old code
            self.root.after(0, self._update_buttons)  #old code

            # New Code
            self.confirmed_shutter = False  # New Code
            self.root.after(0, lambda: self._set_status(
                "Run finished. Shutter confirmation will be required again."
            ))  # New Code


            # New Code
            self.is_running = False  # New Code
            self.root.after(0, self._update_buttons)  # New Code



# New Code
def main():  # New Code
    root = tk.Tk()  # New Code
    app = OptoTaggingGUI(root)  # New Code
    root.mainloop()  # New Code


# New Code
if __name__ == "__main__":  # New Code
    main()  # New Code
