'''
MAIN
1. Builds all driver objects: motors, encoders, linesensor
2. Creates I2C communication for IMU
3. Builds all shares and queues for tasks
4. Creates objects for left and right motors, user task
5. Initializes button and bump sensors
6. Runs tasks with appropriate priority and period
7. Start!
'''

from motor_driver import motor_driver
from encoder      import encoder
from linesensor_driver import linesensor
from task_motor   import task_motor
from task_user    import task_user
from task_crash   import task_crash
from task_button  import task_button
from task_share   import Share, Queue, show_all
from cotask       import Task, task_list
from gc           import collect
from pyb import Pin, I2C
from imu_driver import IMU
from utime import sleep_ms
from task_estimator import task_observer


def main():
    # Build all driver objects first
    leftMotor    = motor_driver(3, 20000, 1, Pin.cpu.B4, Pin.cpu.B5, Pin.cpu.B3)
    rightMotor   = motor_driver(4, 20000, 1, Pin.cpu.B6, Pin.cpu.A7, Pin.cpu.A6)
    leftEncoder  = encoder(1, 0xFFFF, 0, Pin.cpu.A9, Pin.cpu.A8)
    rightEncoder = encoder(2, 0xFFFF, 0, Pin.cpu.A1, Pin.cpu.A0)
    myLineSensor = linesensor((Pin.cpu.C4, Pin.cpu.A4, Pin.cpu.B0, Pin.cpu.C1, Pin.cpu.C0, Pin.cpu.C2, Pin.cpu.C3), 8)

    # Set up I2C for IMU
    sleep_ms(1000)
    i2c1 = I2C(1, I2C.CONTROLLER, baudrate=400000)
    sleep_ms(500)
    print(i2c1.scan())
    myIMU = IMU(i2c1, 0x28)                           # 0x28 is default BNO055 address

    # Build shares and queues
    leftMotorGo   = Share("B",     name="Left Mot. Go Flag")
    rightMotorGo  = Share("B",     name="Right Mot. Go Flag")
    Kp            = Share("f",     name="Proportional Gain")
    Ki            = Share("f",     name="Integral Gain")
    setpointLeft  = Share("f",     name="Left Setpoint Value")
    setpointRight = Share("f",     name="Right Setpoint Value")
    stepResponse  = Share("B",     name="Step Response Flag")
    dataValues_L  = Queue("f", 50, name="Data Collection Buffer Left")
    dataValues_R  = Queue("f", 50, name="Data Collection Buffer Right")
    timeValues_L  = Queue("f", 50, name="Time Buffer Left")
    timeValues_R  = Queue("f", 50, name="Time Buffer Right")
    checkIMU      = Share("B",     name="IMU Calibration Check Flag")

    # IMU and observer shares
    uL            = Share("f",     name="Left Motor Effort")
    uR            = Share("f",     name="Right Motor Effort")
    sL            = Share("f",     name="Left Wheel Arc Length")
    sR            = Share("f",     name="Right Wheel Arc Length")

    # Bump sensor queue: stores the pin number of whichever bumper was hit.
    # Size of 4 means up to 4 unread bump events can be buffered before overflow.
    crashDetect   = Queue("H", 4,  name="Crash Detect Queue")
    buttonDetect  = Queue("H", 4,  name="Button Detect Queue")

    # Build task class objects
    leftMotorTask  = task_motor(leftMotor,  leftEncoder,
                                leftMotorGo, dataValues_L, timeValues_L,
                                Kp, Ki, setpointLeft, stepResponse,
                                uL, sL)
    rightMotorTask = task_motor(rightMotor, rightEncoder,
                                rightMotorGo, dataValues_R, timeValues_R,
                                Kp, Ki, setpointRight, stepResponse,
                                uR, sR)
    userTask = task_user(leftMotorGo, rightMotorGo,
                         dataValues_L, dataValues_R,
                         timeValues_L, timeValues_R,
                         Kp, Ki, setpointLeft, setpointRight,
                         myLineSensor, stepResponse, checkIMU,
                         crashDetect, buttonDetect,
                         sL, sR, myIMU)

    # Bump sensor pins: PC10 and PC8.
    # Pin.PULL_UP is configured inside task_crash's ExtInt setup, but we define
    # the Pin objects here as plain inputs so they can be passed in.
    bump_pins = (Pin(Pin.cpu.C10, Pin.IN), Pin(Pin.cpu.C8, Pin.IN))
    crashTask = task_crash(crashDetect, bump_pins)

    buttonTask = task_button(
        buttonDetect,
        Pin(Pin.cpu.C13)
    )

    # psi and psi_dot come from IMU, voltage and arc from motor task
    observerTask = task_observer(uL, uR, sL, sR, myIMU, checkIMU)

    # Add tasks to task list
    task_list.append(Task(leftMotorTask.run,  name="Left Mot. Task",
                          priority=1, period=20,  profile=True))
    task_list.append(Task(rightMotorTask.run, name="Right Mot. Task",
                          priority=1, period=20,  profile=True))
    task_list.append(Task(userTask.run,       name="User Int. Task",
                          priority=0, period=0,   profile=False))
    task_list.append(Task(observerTask.run,   name="Observer Task",
                          priority=1, period=20,  profile=True))
    # Crash task runs at high priority with a short period so debounce is tight.
    # 10 ms period means each bump gets ~10 ms of debounce before re-arm.
    task_list.append(Task(crashTask.run,      name="Crash Task",
                          priority=2, period=10,  profile=True))
    task_list.append(Task(buttonTask.run,     name="Button Task",
                          priority=2, period=200, profile=True))

    # Run the garbage collector preemptively
    collect()

    # Run the scheduler until the user quits the program with Ctrl-C
    while True:
        try:
            task_list.pri_sched()

        except KeyboardInterrupt:
            print("Program Terminating")
            leftMotor.disable()
            rightMotor.disable()
            break

    print("\n")
    print(task_list)
    print(show_all())


if __name__ == "__main__":
    main()