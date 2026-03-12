''' Bump sensor crash detection task for ME 405 Romi.
    Runs on a Nucleo STM32 microcontroller using MicroPython.
    Implemented as a cooperative multitasking generator.

    Monitors two bump sensor pins (PC10 and PC8) using external interrupts.
    When a bump is detected, the pin number is placed into the crash_detect
    queue so that task_user (or any other task) can respond.

    Debouncing is handled by disabling the interrupt channel for one scheduler
    period after it fires, then re-enabling it on the next run() pass.
'''

from pyb import ExtInt, Pin, enable_irq, disable_irq
from array import array
from task_share import Queue


class task_crash:

    def __init__(self, crash_detect: Queue, pins: tuple):
        '''
        Initialize the crash detection task.

        Args:
            crash_detect (Queue): A Queue where detected bump pin numbers
                                  are placed. task_user reads from this.
            pins (tuple):         A tuple of pyb.Pin objects for the bump
                                  sensors. Each pin must support ExtInt.
                                  Example: (Pin(Pin.cpu.C10), Pin(Pin.cpu.C8))
        '''

        # Store reference to the shared queue
        self._cd = crash_detect

        # Build a dictionary mapping pin NUMBER -> ExtInt object.
        # For each pin, we:
        #   - Configure it as an input with internal pull-up (Pin.PULL_UP)
        #     so it reads HIGH when nothing is pressed and LOW when pressed
        #   - Attach an interrupt that fires on a FALLING edge (HIGH -> LOW),
        #     which is the moment the bumper is pressed
        #   - Point all interrupts to the same self.callback method
        self._callbacks = {
            pin.pin(): ExtInt(
                pin,
                ExtInt.IRQ_FALLING,
                Pin.PULL_UP,
                self.callback
            )
            for pin in pins
        }

        # Two-element array of 16-bit unsigned integers used as bitmasks:
        #   _db_mask[0] = "current"  debounce state (set by ISR this pass)
        #   _db_mask[1] = "previous" debounce state (set last pass, ready to re-enable)
        # Each bit position corresponds to a pin/ISR line number.
        self._db_mask = array("H", [0x0000, 0x0000])

        print("Crash Task object instantiated")

    def callback(self, ISR_src):
        '''
        Interrupt Service Routine called when a bump sensor fires.
        Runs in interrupt context -- keep it SHORT, no memory allocation.

        Args:
            ISR_src (int): The ExtInt line number (== pin number) that fired.
        '''
        # Mark this pin as needing debounce by setting its bit in the mask
        self._db_mask[0] |= 1 << ISR_src

        # Disable this interrupt channel so mechanical bounce doesn't
        # trigger multiple callbacks before we re-enable it next pass
        self._callbacks[ISR_src].disable()

        # Notify task_user (or whoever reads crash_detect) which pin was hit.
        # in_ISR=True skips the thread-protection disable_irq call inside
        # Queue.put(), which is required because we're already in an ISR --
        # calling disable_irq again from inside an ISR is unsafe.
        self._cd.put(ISR_src, in_ISR=True)

    def run(self):
        '''
        Generator that runs one debounce pass each time it is scheduled.
        Re-enables any interrupt channels that completed their debounce delay.
        '''
        while True:

            # Re-enable any pins whose debounce period is over.
            # _db_mask[1] holds the state from the PREVIOUS scheduler pass.
            # If a bit is set there, that pin has waited one full period.
            for ISR_src in range(16):
                if self._db_mask[1] & (1 << ISR_src):
                    self._callbacks[ISR_src].enable()

            # --- Begin critical section ---
            # We need to atomically swap [0] into [1] and clear [0].
            # If an ISR fires between the read of [0] and the write to [1],
            # we would lose that event. Disabling interrupts prevents this.
            irq_state = disable_irq()

            # Move current state to previous, reset current to zero
            self._db_mask[1], self._db_mask[0] = self._db_mask[0], 0x0000

            enable_irq(irq_state)
            # --- End critical section ---

            yield  # Hand control back to the scheduler