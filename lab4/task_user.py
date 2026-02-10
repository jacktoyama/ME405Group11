''' This file demonstrates an example UI task using a custom class with a
    run method implemented as a generator
'''
from pyb import USB_VCP
from task_share import Share, BaseShare
import micropython

S0_INIT = micropython.const(0) # State 0 - initialiation
S1_CMD  = micropython.const(1) # State 1 - wait for character input
S2_COL  = micropython.const(2) # State 2 - wait for data collection to end
S3_DIS  = micropython.const(3) # State 3 - display the collected data
S4_SET = micropython.const(4) # State 4 - set gain

UI_prompt = ">: "

class task_user:
    '''
    A class that represents a UI task. The task is responsible for reading user
    input over a serial port, parsing the input for single-character commands,
    and then manipulating shared variables to communicate with other tasks based
    on the user commands.
    '''

    def __init__(self, leftMotorGo, rightMotorGo, dataValues_L, dataValues_R, timeValues):
        '''
        Initializes a UI task object
        
        Args:
            leftMotorGo (Share):  A share object representing a boolean flag to
                                  start data collection on the left motor
            rightMotorGo (Share): A share object representing a boolean flag to
                                  start data collection on the right motor
            dataValues_L (Queue):   A queue object used to store collected encoder
                                  position values (LEFT)
            dataValues_R (Queue):   A queue object used to store collected encoder
                                  position values (RIGHT)
            timeValues (Queue):   A queue object used to store the time stamps
                                  associated with the collected encoder data
        '''
        
        self._state: int          = S0_INIT      # The present state
        
        self._leftMotorGo: Share  = leftMotorGo  # The "go" flag to start data
                                                 # collection from the left
                                                 # motor and encoder pair
        
        self._rightMotorGo: Share = rightMotorGo # The "go" flag to start data
                                                 # collection from the right
                                                 # motor and encoder pair
        
        self._ser: stream         = USB_VCP()    # A serial port object used to
                                                 # read character entry and to
                                                 # print output
        
        self._dataValues_L: Queue   = dataValues_L   # A reusable buffer for data
                                                 # collection
        
        self._dataValues_R: Queue   = dataValues_R   # A reusable buffer for data
                                                 # collection

        self._timeValues: Queue   = timeValues   # A reusable buffer for time
                                                 # stamping collected data
        
        
        # added variables for lab4
        # A share or queue object where the computed number is to be placed
        self.out_share: BaseShare = Share('f', name="A float share")

        # A character buffer used to store incoming characters as they're
        # received by the command processor
        self.char_buf: str      = ""

        # A set used to quickly check if a character entered by the user is
        # a numerical digit.
        self.digits:   set(str) = set(map(str,range(10)))

        # A set used to quickly check if a character entered by the user is
        # a terminator (a carriage return or newline)
        self.term:     set(str) = {"\r", "\n"}

        # A flag used to track whether or not the command processing is
        # still active.
        self.done = False

        self._propGainFlag: int = 0

        self._intGainFlag: int = 0

        self._ser.write("User Task object instantiated\r\n")

        
    def run(self):
        '''
        Runs one iteration of the task
        '''
        
        while True:
            
            if self._state == S0_INIT: # Init state (can be removed if unneeded)
                self._ser.write("""\r\n+------------------------------------------------------------------------------+\r
| ME 405 Romi Tuning Interface Help Menu                                       |\r
+---+--------------------------------------------------------------------------+\r
| h | Print help menu                                                          |\r
| k | Enter new gain values                                                    |\r
| s | Choose a new setpoint                                                    |\r
| g | Trigger step response and print results                                  |\r
+---+--------------------------------------------------------------------------+\r\n""")
                self._ser.write(UI_prompt)
                self._state = S1_CMD
                
            elif self._state == S1_CMD: # Wait for UI commands
                # Wait for at least one character in serial buffer
                if self._ser.any():
                    # Read the character and decode it into a string
                    inChar = self._ser.read(1).decode()
                    # If the character is an upper or lower case "l", start data
                    # collection on the left motor and if it is an "r", start
                    # data collection on the right motor
                    if inChar in {"g", "G"}:
                        self._ser.write(f"{inChar}\r\n")
                        self._leftMotorGo.put(True)
                        self._rightMotorGo.put(True)
                        self._ser.write("Step response triggered...\r\n")
                        self._ser.write("Data collecting... \r\n")
                        self._state = S2_COL
                    elif inChar in {"k", "K"}:
                        self._propGainFlag = 1
                        self._state = S4_SET
                    elif inChar in {"s", "S"}:
                        self._intGainFlag = 1
                        self._state = S4_SET
                    elif inChar in {"h", "H"}:
                        self._state = S0_INIT
                    else: 
                        self._ser.write("Invalid command\r\n")
                        self._state = S0_INIT
                
            elif self._state == S2_COL:
                # While the data is collecting (in the motor task) block out the
                # UI and discard any character entry so that commands don't
                # queue up in the serial buffer
                if self._ser.any(): self._ser.read(1)
                
                # When both go flags are clear, the data collection must have
                # ended and it is time to print the collected data.
                if not self._leftMotorGo.get() and not self._rightMotorGo.get():
                    self._ser.write("Data collection complete...\r\n")
                    self._ser.write("Printing data...\r\n")
                    self._ser.write("--------------------\r\n")
                    self._ser.write("Time (s), Velocity_L (mm/s), Velocity_R (mm/s)\r\n")
                    self._state = S3_DIS
            
            elif self._state == S3_DIS:
                # While data remains in the buffer, print that data in a command
                # separated format. Otherwise, the data collection is finished.
                if self._dataValues_R.any() or self._dataValues_L.any():
                    self._ser.write(f"{self._timeValues.get()},{self._dataValues_L.get()},\r\n,{self._dataValues_R.get()},\r\n")
                else:
                    self._ser.write("--------------------\r\n")
                    self._state = S0_INIT

            elif self._state == S4_SET:
                while not self.done:

                    if self._ser.any():

                        char_in = self._ser.read(1).decode()

                        if char_in in self.digits:
                            self._ser.write(char_in)
                            self.char_buf += char_in

                        elif char_in == "." and "." not in self.char_buf:
                            self._ser.write(char_in)
                            self.char_buf += char_in
                        
                        elif char_in == "-" and len(self.char_buf) == 0:
                            self._ser.write(char_in)
                            self.char_buf += char_in
                        
                        elif char_in == "\x7f" and len(self.char_buf) > 0:
                            self._ser.write(char_in)
                            self.char_buf = self.char_buf[:-1]
                        
                        elif char_in in self.term:
                            
                            if len(self.char_buf) == 0:
                                self._ser.write("\r\n")
                                self._ser.write("Value not changed\r\n")
                                self.char_buf = ""
                                self.done = True
                                
                            elif self.char_buf not in {"-", "."}:
                                self._ser.write("\r\n")
                                value = float(self.char_buf)
                                self.out_share.put(value)
                                self._ser.write(f"Value set to {value}\r\n")
                                self.char_buf = ""
                                self.one = True
                
                if self._intGainFlag == 1:
                    #code to update integral Gain
                    self._intGainFlag = 0
                    self._state = S0_INIT
                    self.done = False
                if self._propGainFlag == 1:
                    #code to update proportional Gain
                    self._propGainFlag = 0
                    self._state = S0_INIT
                    self.done = False
            
            yield self._state