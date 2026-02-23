''' UI task for ME 405 Romi Tuning Interface.
    Runs on a Nucleo STM32 microcontroller using MicroPython.
    Implemented as a cooperative multitasking generator.
'''
from pyb import USB_VCP
from task_share import Share, BaseShare
import micropython

# --- State constants ---
S0_INIT = micropython.const(0)  # Print help menu
S1_CMD  = micropython.const(1)  # Wait for a command character
S2_COL  = micropython.const(2)  # Wait for data collection to finish
S3_DIS  = micropython.const(3)  # Stream collected data out over serial
S4_SET  = micropython.const(4)  # Read a numeric value from the user
S5_RUN  = micropython.const(5)  # Run line following

HELP_MENU = (
    "\r\n+------------------------------------------------------------------------------+\r\n"
    "| ME 405 Romi Tuning Interface Help Menu                                       |\r\n"
    "+---+--------------------------------------------------------------------------+\r\n"
    "| h | Print help menu                                                          |\r\n"
    "| k | Enter new gain values                                                    |\r\n"
    "| s | Choose a new setpoint                                                    |\r\n"
    "| g | Trigger step response and print results                                  |\r\n"
    "| m | Start line following                                                     |\r\n"
    "+---+--------------------------------------------------------------------------+\r\n"
)

TERMINATORS = {"\r", "\n"}
DIGITS = set(map(str, range(10)))


class task_user:
    '''
    UI task that reads single-character commands over USB serial and
    communicates with other tasks through shared variables and queues.
    '''

    def __init__(self, leftMotorGo, rightMotorGo,
                 dataValues_L, dataValues_R,
                 timeValues_L, timeValues_R,
                 gainValue, setpointValue):
        self._state = S0_INIT

        self._leftMotorGo   = leftMotorGo
        self._rightMotorGo  = rightMotorGo
        self._dataValues_L  = dataValues_L
        self._dataValues_R  = dataValues_R
        self._timeValues_L  = timeValues_L
        self._timeValues_R  = timeValues_R
        self._gainValue     = gainValue
        self._setpointValue = setpointValue

        self._ser = USB_VCP()

        self._char_buf    = ""    # Accumulates typed characters in S4_SET
        self._setting_key = None  # Tracks which value we're editing: "gain" or "setpoint"

        self._gainValue.put(100 / 549)
        self._setpointValue.put(250)

        self._ser.write("User Task object instantiated\r\n")

    def _println(self, text=""):
        self._ser.write(text + "\r\n")

    def _apply_setting(self, value):
        if self._setting_key == "gain":
            self._gainValue.put(value)
            self._println(f"Gain set to {value}")
        elif self._setting_key == "setpoint":
            self._setpointValue.put(value)
            self._println(f"Setpoint set to {value} mm/s")
        self._setting_key = None

    def run(self):

        while True:

            if self._state == S0_INIT:
                self._ser.write(HELP_MENU)
                self._state = S1_CMD

            elif self._state == S1_CMD:
                if self._ser.any():
                    in_char = self._ser.read(2).decode()

                    if in_char in {"g\n", "G\n"}:
                        self._leftMotorGo.put(True)
                        self._rightMotorGo.put(True)
                        self._println("Step response triggered...")
                        self._println("Data collecting...")
                        self._state = S2_COL

                    elif in_char in {"k\n", "K\n"}:
                        self._println("Input desired PROPORTIONAL gain:")
                        self._setting_key = "gain"
                        self._char_buf = ""
                        self._state = S4_SET

                    elif in_char in {"s\n", "S\n"}:
                        self._println("Input desired velocity setpoint (mm/s):")
                        self._setting_key = "setpoint"
                        self._char_buf = ""
                        self._state = S4_SET

                    elif in_char in {"h\n", "H\n"}:
                        self._state = S0_INIT

                    elif in_char in {"m\n", "M\n"}:
                        self._state = S5_RUN

                    else:
                        self._println("Invalid command")
                        self._state = S0_INIT

            elif self._state == S2_COL:
                if self._ser.any():
                    self._ser.read(1)  # Discard input while collecting

                if not self._leftMotorGo.get() and not self._rightMotorGo.get():
                    self._println("Data collection complete...")
                    self._println("Printing data...")
                    self._println("--------------------")
                    self._println("Time_L (s), Velocity_L (mm/s), Time_R (s), Velocity_R (mm/s)")
                    self._state = S3_DIS

            elif self._state == S3_DIS:
                if self._dataValues_L.any() or self._dataValues_R.any():
                    t_l = self._timeValues_L.get()
                    v_l = self._dataValues_L.get()
                    t_r = self._timeValues_R.get()
                    v_r = self._dataValues_R.get()
                    self._ser.write(f"{t_l},{v_l},{t_r},{v_r},\r\n")
                else:
                    self._println("--------------------")
                    self._state = S0_INIT

            elif self._state == S4_SET:
                if self._ser.any():
                    char_in = self._ser.read(1).decode()

                    if char_in in DIGITS:
                        self._ser.write(char_in)
                        self._char_buf += char_in

                    elif char_in == "." and "." not in self._char_buf:
                        self._ser.write(char_in)
                        self._char_buf += char_in

                    elif char_in == "-" and len(self._char_buf) == 0:
                        self._ser.write(char_in)
                        self._char_buf += char_in

                    elif char_in == "\x7f" and len(self._char_buf) > 0:
                        self._ser.write(char_in)
                        self._char_buf = self._char_buf[:-1]

                    elif char_in in TERMINATORS:
                        buf = self._char_buf
                        self._char_buf = ""  # Always reset, regardless of outcome

                        if len(buf) == 0 or buf in {"-", "."}:
                            self._println("\r\nValue not changed")
                        else:
                            self._apply_setting(float(buf))

                        self._state = S0_INIT  # Return to help menu after either outcome

            elif self._state == S5_RUN:

                # Read line position from sensor
                # if centroid < 0
                    # increase left motor setpoint
                    # #decrease right motor setpoint
                # if centroid > 0
                    # decrease left motor setpoint
                    # increase right motor setpoint

                # if any characters are written to the buffer, stop line following
                if self._ser.any():
                    self._ser.read(2)  # consume the character
                    self._println("Line following stopped.")
                    self._state = S0_INIT
                

            yield self._state