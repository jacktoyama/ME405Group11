from motor_driver import motor_driver
from encoder      import encoder
from task_motor   import task_motor
from task_user    import task_user
from task_share   import Share, Queue, show_all
from cotask       import Task, task_list
from gc           import collect
from pyb import Pin

# Build all driver objects first
"""leftMotor    = motor_driver()
rightMotor   = motor_driver()
leftEncoder  = encoder()
rightEncoder = encoder()"""

# test implementation (Jack)
leftMotor    = motor_driver(3, 20000, 1, Pin.cpu.B4, Pin.cpu.B5, Pin.cpu.B3)
rightMotor   = motor_driver(4, 20000, 1, Pin.cpu.B6, Pin.cpu.A7, Pin.cpu.A6)
leftEncoder  = encoder(1, 0xFFFF, 0, Pin.cpu.A9, Pin.cpu.A8)
rightEncoder = encoder(2, 0xFFFF, 0, Pin.cpu.A1, Pin.cpu.A0)

# Build shares and queues
leftMotorGo   = Share("B",     name="Left Mot. Go Flag")
rightMotorGo  = Share("B",     name="Right Mot. Go Flag")
gainValue     = Share("f",     name="Gain Value")
setpointValue = Share("f",     name="Setpoint Value")
dataValues_L  = Queue("f", 50, name="Data Collection Buffer Left")
dataValues_R  = Queue("f", 50, name="Data Collection Buffer Right")
timeValues_L  = Queue("f", 50, name="Time Buffer Left")
timeValues_R  = Queue("f", 50, name="Time Buffer Right")

# Build task class objects
leftMotorTask  = task_motor(leftMotor,  leftEncoder,
                            leftMotorGo, dataValues_L, timeValues_L, gainValue,
                            setpointValue)
rightMotorTask = task_motor(rightMotor, rightEncoder,
                            rightMotorGo, dataValues_R, timeValues_R, gainValue,
                            setpointValue)
userTask = task_user(leftMotorGo, rightMotorGo, dataValues_L, dataValues_R,
                     timeValues_L, timeValues_R, gainValue, setpointValue)

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