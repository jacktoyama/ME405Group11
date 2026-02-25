from motor_driver import motor_driver
from encoder      import encoder
from linesensor_driver import linesensor
from task_motor   import task_motor
from task_user    import task_user
from task_share   import Share, Queue, show_all
from cotask       import Task, task_list
from gc           import collect
from pyb import Pin

# Build all driver objects first
leftMotor    = motor_driver(3, 20000, 1, Pin.cpu.B4, Pin.cpu.B5, Pin.cpu.B3)
rightMotor   = motor_driver(4, 20000, 1, Pin.cpu.B6, Pin.cpu.A7, Pin.cpu.A6)
leftEncoder  = encoder(1, 0xFFFF, 0, Pin.cpu.A9, Pin.cpu.A8)
rightEncoder = encoder(2, 0xFFFF, 0, Pin.cpu.A1, Pin.cpu.A0)
myLineSensor = linesensor((Pin.cpu.C4, Pin.cpu.A4, Pin.cpu.B0, Pin.cpu.C1, Pin.cpu.C0, Pin.cpu.C2, Pin.cpu.C3), 8)

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


# Build task class objects
leftMotorTask  = task_motor(leftMotor,  leftEncoder,
                            leftMotorGo, dataValues_L, timeValues_L, gainValue,
                            setpointLeft, stepResponse)
rightMotorTask = task_motor(rightMotor, rightEncoder,
                            rightMotorGo, dataValues_R, timeValues_R, gainValue,
                            setpointRight, stepResponse)
userTask = task_user(leftMotorGo, rightMotorGo, dataValues_L, dataValues_R,
                     timeValues_L, timeValues_R, gainValue, setpointLeft, setpointRight, myLineSensor, stepResponse)

# Add tasks to task list
task_list.append(Task(leftMotorTask.run, name="Left Mot. Task",
                      priority = 1, period = 20, profile=True))
task_list.append(Task(rightMotorTask.run, name="Right Mot. Task",
                      priority = 1, period = 20, profile=True))
task_list.append(Task(userTask.run, name="User Int. Task",
                      priority = 0, period = 0, profile=False))

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