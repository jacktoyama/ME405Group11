'''
imu_driver class: initializes I2C connection, calibration and reading functions
'''
from pyb import I2C
import struct
from utime import sleep_ms


class IMU:
    def __init__(self, I2C, addr):
        '''Initialize the IMU by taking in a CONTROLLER-configured I2C object.'''
        self.i2c        = I2C
        self.i2c_addr   = addr

    def change_mode(self, mode: str):
        '''Change the mode of the controller to one of several Fusion modes.\n
        Fusion modes:     OPR_MODE bytes:     Sensor signals:     Fusion data:\n
        IMU               xxxx1000b           accel, gyro         rel. orientation\n
        COMPASS           xxxx1001b           accel, mag          abs. orientation\n
        M4G               xxxx1010b           accel, mag          rel. orientation\n
        NDOF_FMC_OFF      xxxx1011b           accel, mag, gyro    abs. orientation\n
        NDOF              xxxx1100b           accel, mag, gyro    abs. orientation'''
        if mode == "IMU":
            self.i2c.mem_write(0b1000, self.i2c_addr, 0x3D)
            print("IMU mode active")
        elif mode == "COMPASS":
            self.i2c.mem_write(0b1001, self.i2c_addr, 0x3D)
        elif mode == "M4G":
            self.i2c.mem_write(0b1010, self.i2c_addr, 0x3D)
        elif mode == "NDOF_FMC_OFF":
            self.i2c.mem_write(0b1011, self.i2c_addr, 0x3D)
        elif mode == "NDOF":
            self.i2c.mem_write(0b1100, self.i2c_addr, 0x3D)
        sleep_ms(20)  # give the IMU time to switch modes

    
    def get_cal_status(self):
        '''Retrieve and parse the calibration byte of the IMU.\n
        Outputs booleans in order of SYS, GYR, ACC, and MAG.'''
        buf = bytearray((0 for _ in range(1)))
        self.i2c.mem_read(buf, self.i2c_addr, 0x35)
        print(buf)
        sys_cal = ((buf[0] & 0b11000000)==0b11000000)
        gyr_cal = ((buf[0] & 0b00110000)==0b00110000)
        acc_cal = ((buf[0] & 0b00001100)==0b00001100)
        mag_cal = ((buf[0] & 0b00000011)==0b00000011)
        return sys_cal, gyr_cal, acc_cal, mag_cal
        
    def get_cal_coeff(self):
        buf = bytearray((0 for _ in range(22)))
        self.i2c.mem_read(buf, self.i2c_addr, 0x55)
        (acc_off_x, acc_off_y, acc_off_z, mag_off_x, mag_off_y, 
         mag_off_z, gyr_off_x, gyr_off_y, gyr_off_z, acc_rad, mag_rad) = struct.unpack("<hhhhhhhhhhh", buf)
        return(acc_off_x, acc_off_y, acc_off_z, mag_off_x, mag_off_y, 
               mag_off_z, gyr_off_x, gyr_off_y, gyr_off_z, acc_rad, mag_rad)

    def set_cal_coeff(self, acc_off_x, acc_off_y, acc_off_z, mag_off_x, mag_off_y, 
                      mag_off_z, gyr_off_x, gyr_off_y, gyr_off_z, acc_rad, mag_rad):
        lastmode = bytearray((0 for _ in range(1)))
        self.i2c.mem_read(lastmode, self.i2c_addr, 0x3D)
        self.i2c.mem_write(0b0000, self.i2c_addr, 0x3D)
        sleep_ms(20)
        offsets = struct.pack("<hhhhhhhhhhh", acc_off_x, acc_off_y, acc_off_z, mag_off_x, mag_off_y, 
                              mag_off_z, gyr_off_x, gyr_off_y, gyr_off_z, acc_rad, mag_rad)
        self.i2c.mem_write(offsets, self.i2c_addr, 0x55)
        self.i2c.mem_write(lastmode, self.i2c_addr, 0x3D)
        sleep_ms(20)

    def get_euler_angles(self):
        buf = bytearray((0 for _ in range(6)))
        self.i2c.mem_read(buf, self.i2c_addr, 0x1A)
        (heading, roll, pitch) = struct.unpack("<hhh", buf)
        #print(heading/900, roll/900, pitch/900)
        return heading/900, roll/900, pitch/900

    def get_ang_velocity(self):
        buf = bytearray((0 for _ in range(6)))
        self.i2c.mem_read(buf, self.i2c_addr, 0x14)
        (gyr_x, gyr_y, gyr_z) = struct.unpack("<hhh", buf)
        return gyr_x/900, gyr_y/900, gyr_z/900
    
# testing purposes
    def save_cal_to_file(self, filename="calibration.txt"):
        '''Read calibration coefficients from the IMU and save them to a file.'''
        coeffs = self.get_cal_coeff()
        with open(filename, "w") as f:
            f.write(",".join(str(c) for c in coeffs))

    def load_cal_from_file(self, filename="calibration.txt"):
        '''Load calibration coefficients from a file and write them to the IMU.'''
        with open(filename, "r") as f:
            data = f.read().strip().split(",")
        coeffs = [int(x) for x in data]
        self.set_cal_coeff(*coeffs)