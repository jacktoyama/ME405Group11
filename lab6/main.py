from motor_driver import motor_driver
from encoder      import encoder
from linesensor_driver import linesensor
from task_motor   import task_motor
from task_user    import task_user
from task_share   import Share, Queue, show_all
from cotask       import Task, task_list
from gc           import collect
from pyb import Pin, I2C
from imu_driver import IMU
from utime import sleep_ms
from task_estimator import task_observer

# Build all driver objects first
leftMotor    = motor_driver(3, 20000, 1, Pin.cpu.B4, Pin.cpu.B5, Pin.cpu.B3)
rightMotor   = motor_driver(4, 20000, 1, Pin.cpu.B6, Pin.cpu.A7, Pin.cpu.A6)
leftEncoder  = encoder(1, 0xFFFF, 0, Pin.cpu.A9, Pin.cpu.A8)
rightEncoder = encoder(2, 0xFFFF, 0, Pin.cpu.A1, Pin.cpu.A0)
myLineSensor = linesensor((Pin.cpu.C4, Pin.cpu.A4, Pin.cpu.B0, Pin.cpu.C1, Pin.cpu.C0, Pin.cpu.C2, Pin.cpu.C3), 8)

# Set up I2C for IMU
sleep_ms(5000)
i2c1 = I2C(1, I2C.CONTROLLER, baudrate=400000)
sleep_ms(5000)
print(i2c1.scan())
myIMU = IMU(i2c1, 0x28)                           # 0x28 is default BNO055 address

try:
    myIMU.load_cal_from_file()
    print("IMU calibration loaded from file.")
except:
    print("No calibration file found. Starting manual calibration...")
    print("Move Romi around until all calibration values reach 3.")
    
    # Stay in IMU mode so calibration can happen
    myIMU.change_mode("IMU")
    
    # Wait until fully calibrated (sys, gyro, accel all at 3)
    while True:
        sys, gyr, acc, mag = myIMU.get_cal_status()
        print(f"SYS:{sys} GYR:{gyr} ACC:{acc}")
        if sys and gyr and acc:
            print("Calibration complete! Saving to file...")
            break
        sleep_ms(500)
    
    myIMU.save_cal_to_file()
    print("Calibration saved to calibration.txt")

myIMU.change_mode("IMU")

# Build shares and queues
leftMotorGo   = Share("B",     name="Left Mot. Go Flag")
rightMotorGo  = Share("B",     name="Right Mot. Go Flag")
gainValue     = Share("f",     name="Gain Value")
setpointLeft  = Share("f",     name="Left Setpoint Value")
setpointRight = Share("f",     name="Right Setpoint Value")
stepResponse  = Share("B",     name="Step Response Flag")
dataValues_L  = Queue("f", 50, name="Data Collection Buffer Left")
dataValues_R  = Queue("f", 50, name="Data Collection Buffer Right")
timeValues_L  = Queue("f", 50, name="Time Buffer Left")
timeValues_R  = Queue("f", 50, name="Time Buffer Right")
# IMU and observier shares
uL             = Share("f", name="Left Motor Effort")
uR             = Share("f", name="Right Motor Effort")
sL             = Share("f", name="Left Wheel Arc Length")
sR             = Share("f", name="Right Wheel Arc Length")



# Build task class objects
leftMotorTask  = task_motor(leftMotor,  leftEncoder,
                            leftMotorGo, dataValues_L, timeValues_L,
                            gainValue, setpointLeft, stepResponse,
                            uL, sL)
rightMotorTask = task_motor(rightMotor, rightEncoder,
                            rightMotorGo, dataValues_R, timeValues_R,
                            gainValue, setpointRight, stepResponse,
                            uR, sR)
userTask = task_user(leftMotorGo, rightMotorGo,
                     dataValues_L, dataValues_R,
                     timeValues_L, timeValues_R,
                     gainValue, setpointLeft, setpointRight,
                     myLineSensor, stepResponse)
# psi and psi dot come from IMU, voltage and arc from motor task
observerTask = task_observer(uL, uR, sL, sR, myIMU)

# Add tasks to task list
task_list.append(Task(leftMotorTask.run, name="Left Mot. Task",
                      priority = 1, period = 20, profile=True))
task_list.append(Task(rightMotorTask.run, name="Right Mot. Task",
                      priority = 1, period = 20, profile=True))
task_list.append(Task(userTask.run, name="User Int. Task",
                      priority = 0, period = 0, profile=False))
task_list.append(Task(observerTask.run,   name="Observer Task",
                      priority=1, period=20, profile=True))



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