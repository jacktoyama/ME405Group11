Hardware Diagram
================

Overview
--------

This diagram shows the overall hardware layout of the system, including
the microcontroller, motor drivers, encoders, and power supply.

.. image:: _static/_images/hardware405.png
   :width: 600px
   :align: center
   :alt: Hardware diagram of the system

Description
-----------

The STM32 microcontroller interfaces with the motor driver to control
two DC motors. Encoder feedback is used for closed-loop control.
Power is supplied through a regulated source connected to the driver
and control board.