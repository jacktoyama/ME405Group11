''' State estimator (Luenberger observer) task for ME 405 Romi.
    Runs on a Nucleo STM32 microcontroller using MicroPython.
    Implemented as a cooperative multitasking generator.

    The observer update equation (discretized) is:
        x_hat[k+1] = Ad * x_hat[k] + Bd_tilde * u_tilde[k]

    where:
        x_hat    = [S, psi, omegaL, omegaR]  (estimated state, 4x1)
        u_tilde  = [uL, uR, sL, sR, psi, psi_dot]  (inputs + measurements, 6x1)
        Ad       = discretized observer A matrix (4x4)  -- precomputed in MATLAB
        Bd_tilde = discretized observer B matrix (4x6)  -- precomputed in MATLAB

    The estimated output is:
        y_hat = C * x_hat  (4x1)
        y_hat = [sL_hat, sR_hat, psi_hat, psi_dot_hat]
'''

from ulab import numpy as np
from task_share import Share
from pyb import USB_VCP
from utime import ticks_ms, ticks_diff
import micropython

# --- State constants ---
S0_INIT = micropython.const(0)  # Initialize state vector and matrices
S1_RUN  = micropython.const(1)  # Run observer update every task period

# -------------------------------------------------------------------------
# Paste the matrices output by your MATLAB script here.
# These are PLACEHOLDERS — replace with your computed values.
# -------------------------------------------------------------------------

Ad = np.array([
    [0.4789257245, 0.0000000000, 0.2136304120, 0.2328848496],
    [-0.0000000000, 0.5827482524, -0.0000000000, -0.0000000000],
    [-0.0547845229, 0.0000000000, 0.7173387147, 0.0805170340],
    [-0.0545961810, 0.0000000000, 0.0733082364, 0.7246226877],
])

Bd_tilde = np.array([
    [0.1452242790, 0.1582588349, 0.2605371378, 0.2605371378, 0.0000000000, -0.0432968956],
    [-0.0000000000, -0.0000000000, -0.0029589346, 0.0029589346, 0.0000419707, 0.0154537684],
    [0.9910695320, 0.0546225919, 0.0273922615, 0.0273922615, 0.0000000000, -0.4073186792],
    [0.0497411433, 0.9959837044, 0.0272980905, 0.0272980905, 0.0000000000, 0.3747345585],
])

# C matrix from your system model (used to compute estimated output y_hat)
# y_hat = C * x_hat
# Columns map to [S, psi, omegaL, omegaR]
# Rows map to    [sL, sR, psi, psi_dot]
r = 35.0   # wheel radius [mm]   -- update to match your model
w = 149.0  # track width  [mm]   -- update to match your model

C = np.array([
    [1.0, -w/2,  0.0,  0.0 ],
    [1.0,  w/2,  0.0,  0.0 ],
    [0.0,  1.0,  0.0,  0.0 ],
    [0.0,  0.0, -r/w,  r/w ],
])

# Print interval in milliseconds
PRINT_INTERVAL_MS = 500


class task_observer:
    '''
    A cooperative multitasking task that runs a discretized Luenberger
    observer to estimate the state of Romi using encoder and IMU measurements.

    Shares read (inputs u and measurements y):
        uL_share      -- left motor effort  (float, 0-3.1V)
        uR_share      -- right motor effort (float, 0-3.1V)
        sL_share      -- left wheel arc length from encoder [mm]
        sR_share      -- right wheel arc length from encoder [mm]
        psi_share     -- heading/yaw angle from IMU [rad]
        psi_dot_share -- yaw rate from IMU [rad/s]
    '''

    def __init__(self,
                 uL_share:       Share,
                 uR_share:       Share,
                 sL_share:       Share,
                 sR_share:       Share,
                 psi_share:      Share,
                 psi_dot_share:  Share,):
        '''
        Args:
            uL_share        -- Share holding current left motor effort [V]
            uR_share        -- Share holding current right motor effort [V]
            sL_share        -- Share holding left encoder arc length [mm]
            sR_share        -- Share holding right encoder arc length [mm]
            psi_share       -- Share holding IMU heading/yaw angle [rad]
            psi_dot_share   -- Share holding IMU yaw rate [rad/s]

        '''
        self._state = S0_INIT

        # --- Input shares (read by this task) ---
        self._uL       = uL_share
        self._uR       = uR_share
        self._sL       = sL_share
        self._sR       = sR_share
        self._psi      = psi_share
        self._psi_dot  = psi_dot_share


        # State estimate vector x_hat = [S, psi, omegaL, omegaR]^T (4x1)
        self._x_hat = np.array([[0.0], [0.0], [0.0], [0.0]])

        # Serial port for printing
        self._ser = USB_VCP()

        # Timer for half-second print interval
        self._last_print_ms = 0

        print("Observer Task object instantiated")

    def _println(self, text=""):
        self._ser.write(text + "\r\n")

    def run(self):
        '''
        Generator that runs one observer update step each time it is scheduled.
        '''

        while True:

            if self._state == S0_INIT:
                # Reset state estimate to zero on startup
                self._x_hat = np.array([[0.0], [0.0], [0.0], [0.0]])
                self._last_print_ms = ticks_ms()
                self._state = S1_RUN

            elif self._state == S1_RUN:

                # --- 1. Read inputs u = [uL, uR] from shares ---
                uL = self._uL.get()
                uR = self._uR.get()

                # --- 2. Read measurements y = [sL, sR, psi, psi_dot] from shares ---
                sL      = self._sL.get()
                sR      = self._sR.get()
                psi     = self._psi.get()
                psi_dot = self._psi_dot.get()

                # --- 3. Build augmented input vector u_tilde (6x1) ---
                # u_tilde = [uL, uR, sL, sR, psi, psi_dot]^T
                u_tilde = np.array([[uL],
                                    [uR],
                                    [sL],
                                    [sR],
                                    [psi],
                                    [psi_dot]])

                # --- 4. Observer update: x_hat[k+1] = Ad*x_hat[k] + Bd_tilde*u_tilde ---
                self._x_hat = (np.dot(Ad, self._x_hat) +
                               np.dot(Bd_tilde, u_tilde))

                # --- 5. Write estimated states to output shares ---
                self._S_hat.put(self._x_hat[0][0])
                self._psi_hat.put(self._x_hat[1][0])
                self._omegaL_hat.put(self._x_hat[2][0])
                self._omegaR_hat.put(self._x_hat[3][0])

                # --- 6. Print estimated output y_hat every 500 ms ---
                now = ticks_ms()
                if ticks_diff(now, self._last_print_ms) >= PRINT_INTERVAL_MS:
                    self._last_print_ms = now

                    # y_hat = C * x_hat  (4x1)
                    y_hat = np.dot(C, self._x_hat)

                    sL_hat      = y_hat[0][0]
                    sR_hat      = y_hat[1][0]
                    psi_hat     = y_hat[2][0]
                    psi_dot_hat = y_hat[3][0]

                    self._println("--- Observer Estimated Outputs ---")
                    self._println(f"  sL_hat     : {sL_hat:.4f} mm")
                    self._println(f"  sR_hat     : {sR_hat:.4f} mm")
                    self._println(f"  psi_hat    : {psi_hat:.4f} rad")
                    self._println(f"  psi_dot_hat: {psi_dot_hat:.4f} rad/s")
                    self._println()

            yield self._state



