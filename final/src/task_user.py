''' UI task for ME 405 Romi Tuning Interface.
    Runs on a Nucleo STM32 microcontroller using MicroPython.
    Implemented as a cooperative multitasking generator.
'''
from pyb import USB_VCP
from task_share import Share, Queue, BaseShare
import micropython
from utime import ticks_ms, ticks_diff
import math
from time import sleep

# --- State constants ---
S0_INIT  = micropython.const(0)  # Print help menu
S1_CALW  = micropython.const(1)  # Wait for a command character
S2_CALB  = micropython.const(2)  # Wait for data collection to finish
S3_RUN   = micropython.const(3)  # Stream collected data out over serial
S4_SET   = micropython.const(4)  # Read a numeric value from the user
S5_RUN   = micropython.const(5)  # Run line following
S6_CALW  = micropython.const(6)  # Calibrate white
S7_CALB  = micropython.const(7)  # Calibrate black


class task_user:
    '''
    UI task that reads single-character commands over USB serial and
    communicates with other tasks through shared variables and queues.
    '''

    def __init__(self, leftMotorGo, rightMotorGo,
                 dataValues_L, dataValues_R,
                 timeValues_L, timeValues_R,
                 Ki, Kp, setpointLeft, setpointRight,
                 lineSensor, stepResponse, checkIMU,
                 crashDetect: Queue, buttonDetect: Queue,
                 sL: Share, sR: Share, myIMU):       # <-- added sL, sR, myIMU
        self._state = 0

        self._leftMotorGo   = leftMotorGo
        self._rightMotorGo  = rightMotorGo
        self._dataValues_L  = dataValues_L
        self._dataValues_R  = dataValues_R
        self._timeValues_L  = timeValues_L
        self._timeValues_R  = timeValues_R
        self._Kp = Kp
        self._Ki = Ki
        self._set_internal  = 100
        self._setpointLeft  = setpointLeft
        self._setpointRight = setpointRight
        self._lineSensor    = lineSensor
        self._centroid      = 0
        self._stepResponse  = stepResponse
        self._checkIMU      = checkIMU
        self._crashDetect   = crashDetect
        self._buttonDetect  = buttonDetect
        self._sL            = sL       # left wheel arc length share [mm]
        self._sR            = sR       # right wheel arc length share [mm]
        self._imu           = myIMU    # IMU object for heading reads

        self._ser = USB_VCP()

        self._char_buf    = ""
        self._setting_key = None

        self._Kp.put(100 / 549)
        self._Ki.put(0.0)

        self._setpointLeft.put(self._set_internal)
        self._setpointRight.put(self._set_internal)

        self._ser.write("User Task object instantiated\r\n")

        self._startTime = 0
        self.runFlag = False
        self._printed = False

        self._headingRef = 0

        self._calFlag = False

    def _println(self, text=""):
        self._ser.write(text + "\r\n")

    def _apply_setting(self, value):
        if self._setting_key == "gain":
            self._Kp.put(value)
            self._println(f"Kp set to {value}")
        elif self._setting_key == "ki":
            self._Ki.put(value)
            self._println(f"Ki set to {value}")
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

    def pause(self):
        sleep(1)
        yield

    # -------------------------------------------------------------------------
    # drive_distance: move both wheels forward (or backward) a given distance.
    #
    # How it works:
    #   - Records the starting arc length of each wheel from the sL/sR shares.
    #   - Sets both motor setpoints to +speed (or -speed for negative distance).
    #   - Every time the scheduler calls run(), this generator yields so the
    #     motor task can actually run and turn the wheels.
    #   - Each yield it checks how far the wheels have traveled. When the
    #     average of both wheels reaches the target, it stops.
    #
    # Why average both wheels? If one wheel slips slightly they won't travel
    # exactly the same distance. Averaging avoids stopping too early or late
    # on either side.
    #
    # Args:
    #   distance_mm : how far to drive in mm. Positive = forward.
    #   speed_mm_s  : wheel speed in mm/s (always positive; sign of distance
    #                 controls direction).
    # -------------------------------------------------------------------------
    def drive_distance(self, distance_mm, speed_mm_s=80):
        '''
        Generator sub-routine: drives straight for distance_mm millimeters.
        Call with "yield from self.drive_distance(300)" inside run().
        '''
        # Record where each wheel starts so we measure relative travel
        start_L = self._sL.get()
        start_R = self._sR.get()

        # Decide direction: if distance is negative we want to go backward
        direction = 1 if distance_mm >= 0 else -1
        target    = abs(distance_mm)
        spd       = abs(speed_mm_s) * direction

        # Enable motors and set constant forward (or backward) speed
        self._leftMotorGo.put(True)
        self._rightMotorGo.put(True)
        self._setpointLeft.put(spd)
        self._setpointRight.put(spd)

        # Keep looping (and yielding) until both wheels have covered the distance
        while True:
            # How far has each wheel traveled since we started?
            traveled_L = abs(self._sL.get() - start_L)
            traveled_R = abs(self._sR.get() - start_R)

            # Use the average so a slight mismatch doesn't stop us too soon
            avg_traveled = (traveled_L + traveled_R) / 2.0

            if avg_traveled >= target:
                break   # Target reached — exit the loop

            yield   # Hand control back to the scheduler so motors keep running

        # Stop both motors cleanly
        self._stop_motors()
        self._setpointLeft.put(0.0)
        self._setpointRight.put(0.0)
        yield   # One final yield so the motor task sees the stop command

    # -------------------------------------------------------------------------
    # turn_angle: rotate in place by a given angle using the IMU heading.
    #
    # How it works:
    #   - Reads the current IMU heading as the starting reference.
    #   - Spins the left wheel backward and the right wheel forward (for a
    #     positive/counterclockwise turn) or vice versa.
    #   - Every yield it reads the new IMU heading and computes how many
    #     degrees we've turned so far using _heading_diff().
    #   - Stops when the accumulated rotation matches the target angle.
    #
    # Why use the IMU instead of encoders for turning?
    #   Encoders measure wheel arc length. To convert that to a heading change
    #   you need the exact track width, which is hard to measure precisely and
    #   changes with surface friction. The IMU directly measures rotation, so
    #   it's more accurate for turns.
    #
    # Heading wrap-around problem:
    #   IMU heading goes 0 → 2π then wraps back to 0. If you start at 5.9 rad
    #   and turn 0.5 rad, the new heading is 0.1 rad, not 6.4 rad. The helper
    #   _heading_diff() handles this so we always get the correct signed
    #   angular change regardless of wrap.
    #
    # Args:
    #   angle_deg   : how many degrees to turn. Positive = CCW (left turn),
    #                 negative = CW (right turn). Change the sign convention
    #                 below if your Romi turns the opposite direction.
    #   speed_mm_s  : speed of each wheel during the turn in mm/s.
    # -------------------------------------------------------------------------
    '''
    def turn_angle(self, angle_deg):
        
        Generator sub-routine: rotates Romi by angle_deg degrees using IMU.
        Call with "yield from self.turn_angle(90)" inside run().
        Positive angle = CCW (left turn), negative = CW (right turn).
        
        # Convert target to radians to match the IMU's output units
        target_rad = math.radians(abs(angle_deg))

        # Record heading at the start of the turn
        heading_start, _, _ = self._imu.get_euler_angles()  # returns radians

        # Decide spin direction.
        # CCW (positive angle): left wheel backward, right wheel forward.
        # CW  (negative angle): left wheel forward, right wheel backward.
        if angle_deg >= 0:
            left_spd  = -abs(40)   # left wheel goes backward
            right_spd =  abs(40)   # right wheel goes forward
        else:
            left_spd  =  abs(40)
            right_spd = -abs(40)

        # Enable motors and set spin speeds
        self._leftMotorGo.put(True)
        self._rightMotorGo.put(True)
        self._setpointLeft.put(left_spd)
        self._setpointRight.put(right_spd)

        # Keep looping until we've rotated far enough
        while True:
            heading_now, _, _ = self._imu.get_euler_angles()

            # _heading_diff gives signed change from start to now (radians)
            delta = self._heading_diff(heading_start, heading_now)

            # We care about total rotation magnitude matching our target
            if abs(delta) >= target_rad:
                break

            yield   # Let the motor task and other tasks run

        # Stop motors
        self._stop_motors()
        self._setpointLeft.put(self._set_internal)
        self._setpointRight.put(self._set_internal)
        yield   # One final yield so the motor task sees the stop command
'''
    def turn_angle(self, angle_deg):
        '''
        Generator sub-routine: rotates Romi by angle_deg degrees using encoders.
        Call with "yield from self.turn_angle(90)" inside run().
        Positive angle = CCW (left turn), negative = CW (right turn).

        Math: each wheel must travel arc = (track_width/2) * angle_rad
        track_width = 149 mm, so arc = 74.5 * angle_rad
        '''
        TRACK_WIDTH_MM = 149.0

        angle_rad  = math.radians(abs(angle_deg))
        target_arc = (TRACK_WIDTH_MM / 2.0) * angle_rad   # mm each wheel must travel

        # Snapshot starting positions from the shares
        start_L = self._sL.get()
        start_R = self._sR.get()

        # CCW (positive): left goes backward, right goes forward
        # CW  (negative): left goes forward, right goes backward
        if angle_deg >= 0:
            left_spd  = -40.0
            right_spd =  40.0
        else:
            left_spd  =  40.0
            right_spd = -40.0

        self._leftMotorGo.put(True)
        self._rightMotorGo.put(True)
        self._setpointLeft.put(left_spd)
        self._setpointRight.put(right_spd)

        while True:
            # How far has each wheel actually traveled since the turn started?
            traveled_L = abs(self._sL.get() - start_L)
            traveled_R = abs(self._sR.get() - start_R)
            print(traveled_L)

            # Average both wheels in case of slight slip
            avg_traveled = (traveled_L + traveled_R) / 2.0

            if avg_traveled >= target_arc:
                print(f"total traveled: {avg_traveled}")
                break
                

            yield   # Let motor task run

        self._stop_motors()
        self._setpointLeft.put(self._set_internal)
        self._setpointRight.put(self._set_internal)
        yield   # Let motor task see the stop
    # -------------------------------------------------------------------------
    # _heading_diff: computes the signed angular change between two headings,
    #               correctly handling the 0/2π wrap-around.
    #
    # Example without wrap handling:
    #   start=5.9 rad, now=0.1 rad → naive diff = 0.1-5.9 = -5.8 rad (WRONG)
    #   correct answer = +0.48 rad (small CCW rotation crossing zero)
    #
    # The fix: after subtracting, force the result into the range (-π, +π]
    # by adding or subtracting 2π. This always gives the shortest-path angle.
    # -------------------------------------------------------------------------
    @staticmethod
    def _heading_diff(start_rad, now_rad):
        '''Returns signed angular change from start to now, in radians.
           Result is in (-π, π] so wrap-around is handled correctly.'''
        diff = now_rad - start_rad
        # Wrap into (-π, π]
        while diff >  math.pi:
            diff -= 2 * math.pi
        while diff <= -math.pi:
            diff += 2 * math.pi
        return diff

    def run(self):

        while True:

            # Change state on press of a button
            if self._buttonDetect.any():
                self._buttonDetect.get()
                if self._state == 0 and self._calFlag:
                    self._state = 5
                elif self._state >= 5:
                    self._state = 0
                else:
                    self._state += 1
                self._headingRef, _, _ = self._imu.get_euler_angles()

            if self._state == 0:
                self._stop_motors()
                if self._printed == False:
                    self._ser.write("Place on white, then press button to calibrate\r\n")
                    self._printed = True

            elif self._state == 1:
                self._lineSensor.calwhite()
                self._ser.write("White calibrated\r\n")
                self._state += 1
                self._printed = False

            elif self._state == 2:
                if self._printed == False:
                    self._ser.write("Place on black, then press button to calibrate\r\n")
                    self._printed = True

            elif self._state == 3:
                self._lineSensor.calblack()
                self._ser.write("Black calibrated\r\n")
                self._state += 1
                self._printed = False
                self._calFlag = True

            elif self._state == 4:
                if self._printed == False:
                    self._ser.write("Place on starting position and hit button to run\r\n")
                    self._printed = True

            elif self._state == 5:
                if self._crashDetect.any():
                    self._crashDetect.get()
                    self._stop_motors()
                    self._state = 0

                self._leftMotorGo.put(True)
                self._rightMotorGo.put(True)

                checkHeading, _, _ = self._imu.get_euler_angles()
                checkdiff = checkHeading - self._headingRef
                # Wrap into (-π, π]
                while checkdiff >  math.pi:
                    checkdiff -= 2 * math.pi
                while checkdiff <= -math.pi:
                    checkdiff += 2 * math.pi
                if checkdiff >= math.radians(90):
                    self._state = 6
                    self._stop_motors()
                self._centroid, _ = self._lineSensor.findCentroid()
                self._setpointLeft.put(self._set_internal + min(self._centroid * 6,0))
                self._setpointRight.put(self._set_internal - max(self._centroid * 6,0))
                self._printed = False

            # ---------------------------------------------------------------
            # Example hardcoded sequence using drive_distance and turn_angle.
            # "yield from" means: run that generator completely before moving
            # on, but keep yielding to the scheduler the whole time so the
            # motor task keeps running in the background.
            # ---------------------------------------------------------------
            elif self._state == 6:
                yield from self.pause()
                self._state = 7
            elif self._state == 7:
                '''
                if not hasattr(self, '_state6_ref'):
                    self._state6_ref = None
                if self._state6_ref is None:
                    self._state6_ref, _, _ = self._imu.get_euler_angles()
                    # Set setpoints BEFORE enabling motors
                    self._setpointLeft.put(60)
                    self._setpointRight.put(-60)
                    self._leftMotorGo.put(True)
                    self._rightMotorGo.put(True)

                checkHeading, _, _ = self._imu.get_euler_angles()
                checkdiff = checkHeading - self._state6_ref
                while checkdiff > math.pi:
                    checkdiff -= 2 * math.pi
                while checkdiff <= -math.pi:
                    checkdiff += 2 * math.pi
                if checkdiff <= -math.radians(85):
                    self._stop_motors()
                    self._state6_ref = None
                    self._state = 7
                '''
                
                yield from self.turn_angle(-90)
                self._state = 8
                self._leftMotorGo.put(False)
                self._rightMotorGo.put(False)
                self._setpointLeft.put(100)
                self._setpointRight.put(100)
            
            elif self._state == 8:
                yield from self.pause()
                self._state = 9

            elif self._state == 9:
                yield from self.pause()
                if self._crashDetect.any():
                    self._crashDetect.get()
                    self._stop_motors()
                    self._state = 0
                self._leftMotorGo.put(True)
                self._rightMotorGo.put(True)

            yield self._state