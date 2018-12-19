# A digital root is the recursive sum of all the digits in a 
# number. Given n, take the sum of the digits of n. If that 
# value has two digits, continue reducing in this way until a 
# single-digit number is produced. This is only applicable to 
# the natural numbers.

num1 = 16
# digital_root(16)
# = > 1 + 6
# = > 7

num2 = 942
# digital_root(942)
# = > 9 + 4 + 2
# = > 15 ...
# = > 1 + 5
# = > 6

num3 = 132189
# digital_root(132189)
# = > 1 + 3 + 2 + 1 + 8 + 9
# = > 24 ...
# = > 2 + 4
# = > 6

num4 = 493193
# digital_root(493193)
# = > 4 + 9 + 3 + 1 + 9 + 3
# = > 29 ...
# = > 2 + 9
# = > 11 ...
# = > 1 + 1
# = > 2

def digital_root(n):

    root = 0
    for i in list(str(n)):
        root += int(i)

    return root if root < 10 else digital_root(root)
         


print(digital_root(num3))
print(num3 // 10)