def operation(a, operand, b):
    if operand == '*':
        return a * b
    elif operand == '/':
        return a // b
    elif operand == '+':
        return a + b
    elif operand == '-':
        return a - b

def zero(op=None):  # your code here
    if op != None:
        return operation(0, op[0], op[1])
    else:
        return 0


def one(op=None):  # your code here
    if op != None:
        return operation(1, op[0], op[1])
    else:
        return 1


def two(op=None):  # your code here
    if op != None:
        return operation(2, op[0], op[1])
    else:
        return 2


def three(op=None):  # your code here
    if op != None:
        return operation(3, op[0], op[1])
    else:
        return 3


def four(op=None):  # your code here
    if op != None:
        return operation(4, op[0], op[1])
    else:
        return 4


def five(op=None):  # your code here
    if op != None:
        return operation(5, op[0], op[1])
    else:
        return 5


def six(op=None):  # your code here
    if op != None:
        return operation(6, op[0], op[1])
    else:
        return 6


def seven(op=None):  # your code here
    if op != None:
        return operation(7, op[0], op[1])
    else:
        return 7


def eight(op=None):  # your code here
    if op != None:
        return operation(8, op[0], op[1])
    else:
        return 8


def nine(op=None):  # your code here
    if op != None:
        return operation(9, op[0], op[1])
    else:
        return 9


def plus(num):  # your code here
    return ['+', num]


def minus(num):  # your code here
    return ['-', num]


def times(num):  # your code here
    return ['*', num]


def divided_by(num):  # your code here
    return ['/', num]

print(five(times(eight())))