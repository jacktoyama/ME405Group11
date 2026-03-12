''' UI task for ME 405 Romi Tuning Interface.
    Runs on a Nucleo STM32 microcontroller using MicroPython.
    Implemented as a cooperative multitasking generator.
'''
from pyb import USB_VCP
from task_share import Share, Queue, BaseShare
import micropython
from utime import ticks_ms, ticks_diff

# --- State constants ---
S0_INIT  = micropython.const(0)  # Print help menu
S1_CALW   = micropython.const(1)  # Wait for a command character
S2_CALB   = micropython.const(2)  # Wait for data collection to finish
S3_RUN   = micropython.const(3)  # Stream collected data out over serial
S4_SET   = micropython.const(4)  # Read a numeric value from the user
S5_RUN   = micropython.const(5)  # Run line following
S6_CALW  = micropython.const(6)  # Calibrate white
S7_CALB  = micropython.const(7)  # Calibrate black
'''
HELP_MENU = (
    "\r\n+------------------------------------------------------------------------------+\r\n"
    "| ME 405 Romi Tuning Interface Help Menu                                       |\r\n"
    "+---+--------------------------------------------------------------------------+\r\n"
    "| h | Print help menu                                                          |\r\n"
    "| k | Enter new gain values                                                    |\r\n"
    "| s | Choose a new setpoint                                                    |\r\n"
    "| g | Trigger step response and print results                                  |\r\n"
    "| c | Calibrate line sensor                                                    |\r\n"
    "| m | Start line following                                                     |\r\n"
    "| i | Run IMU check                                                            |\r\n"
    "+---+--------------------------------------------------------------------------+\r\n"
)

TERMINATORS = {"\r", "\n"}
DIGITS = set(map(str, range(10)))
'''

class task_user:
    '''
    UI task that reads single-character commands over USB serial and
    communicates with other tasks through shared variables and queues.
    '''

    def __init__(self, leftMotorGo, rightMotorGo,
                 dataValues_L, dataValues_R,
                 timeValues_L, timeValues_R,
                 gainValue, setpointLeft, setpointRight,
                 lineSensor, stepResponse, checkIMU,
                 crashDetect: Queue, buttonDetect: Queue):           # <-- new parameter
        self._state = S0_INIT

        self._leftMotorGo   = leftMotorGo
        self._rightMotorGo  = rightMotorGo
        self._dataValues_L  = dataValues_L
        self._dataValues_R  = dataValues_R
        self._timeValues_L  = timeValues_L
        self._timeValues_R  = timeValues_R
        self._gainValue     = gainValue
        self._set_internal  = 100
        self._setpointLeft  = setpointLeft
        self._setpointRight = setpointRight
        self._lineSensor    = lineSensor
        self._centroid      = 0
        self._stepResponse  = stepResponse
        self._checkIMU      = checkIMU
        self._crashDetect   = crashDetect      # <-- store the queue
        self._buttonDetect  = buttonDetect

        self._ser = USB_VCP()

        self._char_buf    = ""    # Accumulates typed characters in S4_SET
        self._setting_key = None  # Tracks which value we're editing: "gain" or "setpoint"

        self._gainValue.put(100 / 549)
        self._setpointLeft.put(self._set_internal)
        self._setpointRight.put(self._set_internal)

        self._ser.write("User Task object instantiated\r\n")

        self._startTime = 0

        self.runFlag = False

    def _println(self, text=""):
        self._ser.write(text + "\r\n")

    def _apply_setting(self, value):
        if self._setting_key == "gain":
            self._gainValue.put(value)
            self._println(f"Gain set to {value}")
        elif self._setting_key == "setpoint":
            self._set_internal = value
            self._setpointLeft.put(self._set_internal)
            self._setpointRight.put(self._set_internal)
            self._println(f"Setpoint set to {value} mm/s")
        self._setting_key = None

    def _stop_motors(self):
        '''Helper to stop both motors and clear the go flags.'''
        self._leftMotorGo.put(False)
        self._rightMotorGo.put(False)

    def run(self):

        while True:

            if self._state == S0_INIT:
                self._state = S1_CALW

            elif self._state == S1_CALW:
                if self._buttonDetect.any():
                    self._buttonDetect.get()
                    self._lineSensor.calwhite()
                    self._state = S2_CALB
                    self._ser.write("White calibrated\r\n")

            elif self._state == S2_CALB:
                if self._buttonDetect.any():
                    self._buttonDetect.get()
                    self._lineSensor.calblack()
                    self._state = S3_RUN
                    self._ser.write("Black calibrated\r\n")

            elif self._state == S3_RUN:
                self._lineSensor.printNormalized(500)
                # --- Check for a bump event first ---
                # crashDetect.any() returns True if at least one event is queued.
                # We check this BEFORE the serial check so a bump takes priority.
                if self._crashDetect.any():
                    self._crashDetect.get() 
                    self._stop_motors()
                    self._state = S0_INIT

                elif self._buttonDetect.any():
                    self._buttonDetect.get()
                    self.runFlag = not self.runFlag
                    self._leftMotorGo.put(self.runFlag)
                    self._rightMotorGo.put(self.runFlag)

                elif self.runFlag == True:
                    # Normal line following logic
                    self._centroid = self._lineSensor.findCentroid()
                    self._setpointLeft.put(self._set_internal + self._centroid * 3.5)
                    self._setpointRight.put(self._set_internal - self._centroid * 3.5)

            yield self._state