''' Blue button state-change detection task for ME 405 Romi.
    Runs on a Nucleo STM32 microcontroller using MicroPython.
    Implemented as a cooperative multitasking generator.

    Monitors the Nucleo blue user button (PC13) using an external interrupt.
    When the button is pressed, a flag is placed into the button_queue
    so another task (ex: task_user) can detect the press and change states.

    Debouncing is handled by disabling the interrupt channel for one
    scheduler period after it fires, then re-enabling it on the next run().
'''

from pyb import ExtInt, Pin, enable_irq, disable_irq
from array import array
from task_share import Queue


class task_button:

    def __init__(self, button_queue: Queue, pin: Pin):
        '''
        Initialize the button task.

        Args:
            button_queue (Queue): Queue used to signal a button press
            pin (Pin):            The blue button pin (Pin.cpu.C13)
        '''

        self._bq = button_queue

        # Configure interrupt for the button
        self._callback = ExtInt(
            pin,
            ExtInt.IRQ_FALLING,     # button press causes falling edge
            Pin.PULL_UP,
            self.callback
        )

        # Two-element debounce mask (same method as crash task)
        self._db_mask = array("H", [0x0000, 0x0000])

        self._pin_num = pin.pin()

        print("Button Task object instantiated")

    def callback(self, ISR_src):
        '''
        Interrupt service routine for button press.
        Runs in interrupt context, so keep it short.
        '''

        # Mark interrupt for debounce
        self._db_mask[0] |= 1 << ISR_src

        # Disable interrupt temporarily
        self._callback.disable()

        # Send button press signal
        self._bq.put(1, in_ISR=True)

    def run(self):
        '''
        Generator that runs debounce handling each scheduler cycle.
        '''
        while True:

            # Re-enable interrupt if debounce period has passed
            if self._db_mask[1] & (1 << self._pin_num):
                self._callback.enable()

            # Critical section to swap debounce masks
            irq_state = disable_irq()
            self._db_mask[1], self._db_mask[0] = self._db_mask[0], 0x0000
            enable_irq(irq_state)

            yield