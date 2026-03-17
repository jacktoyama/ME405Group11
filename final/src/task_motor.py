''' Motor task with Proportional-Integral (PI) closed-loop control.

    Control law:
        effort = Kp * e + Ki * integral(e * dt)

    Anti-windup: the integral is frozen whenever effort is saturated.
'''
from motor_driver import motor_driver
from encoder      import encoder
from task_share   import Share, Queue
from utime        import ticks_us, ticks_diff
import micropython

S0_INIT = micropython.const(0)
S1_WAIT = micropython.const(1)
S2_RUN  = micropython.const(2)

EFFORT_MAX =  100.0
EFFORT_MIN = -100.0


class task_motor:

    def __init__(self,
                 mot: motor_driver, enc: encoder,
                 goFlag: Share, dataValues: Queue, timeValues: Queue,
                 Kp: Share, Ki: Share,
                 setpoint: Share, stepResponse: Share,
                 effort: Share, arcLength: Share):

        self._state         = S0_INIT
        self._mot           = mot
        self._enc           = enc
        self._goFlag        = goFlag
        self._dataValues    = dataValues
        self._timeValues    = timeValues
        self._startTime     = 0
        self._Kp            = Kp
        self._Ki            = Ki
        self._setpoint      = setpoint
        self._stepResponse  = stepResponse
        self._effortShare   = effort
        self._arcLengthShare = arcLength

        # PI internal state
        self._integral  = 0.0
        self._prev_time = 0

        print("Motor Task object instantiated")

    def _reset_pi(self):
        self._integral  = 0.0
        self._prev_time = ticks_us()

    def run(self):

        while True:

            if self._state == S0_INIT:
                self._enc.zero()
                self._mot.disable()
                self._mot.set_effort(0)
                self._state = S1_WAIT

            elif self._state == S1_WAIT:
                if self._goFlag.get():
                    self._startTime = ticks_us()
                    self._reset_pi()
                    self._state = S2_RUN

            elif self._state == S2_RUN:

                # 1. Read velocity from encoder
                self._enc.update()
                vel = self._enc.get_velocity()

                # 2. Error = desired - actual
                err = self._setpoint.get() - vel

                # 3. Time step in seconds
                now = ticks_us()
                dt  = ticks_diff(now, self._prev_time) / 1_000_000.0
                self._prev_time = now
                if dt > 0.1:        # clamp if scheduler was delayed
                    dt = 0.1

                # 4. Proportional term
                p_term = self._Kp.get() * err

                # 5. Anti-windup: check tentative effort before integrating
                tentative = p_term + self._Ki.get() * self._integral
                if EFFORT_MIN < tentative < EFFORT_MAX:
                    self._integral += err * dt  # only accumulate if not saturated

                # 6. Final PI effort, then clamp
                effort = p_term + self._Ki.get() * self._integral
                effort = max(EFFORT_MIN, min(EFFORT_MAX, effort))

                # 7. Drive motor
                self._mot.enable()
                self._mot.set_effort(effort)

                # 8. Publish to shares
                self._effortShare.put(abs(effort * 3.1 / 100.0))
                self._arcLengthShare.put(self._enc.get_position())

                # 9. Log data if step response active
                t = ticks_us()
                if self._stepResponse.get():
                    self._dataValues.put(vel)
                    self._timeValues.put(ticks_diff(t, self._startTime) / 1_000_000.0)
                    if self._dataValues.full():
                        self._state = S1_WAIT
                        self._goFlag.put(False)
                        self._mot.disable()

                # 10. Stop if go flag cleared externally
                if self._goFlag.get() == False:
                    self._state = S1_WAIT
                    self._mot.disable()
                    self._reset_pi()

            yield self._state