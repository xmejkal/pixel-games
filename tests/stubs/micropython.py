"""MicroPython's micropython module on the Mac: its code emitters and const are plain Python here."""


def viper(function):
    return function


native = viper


def const(value):
    return value
