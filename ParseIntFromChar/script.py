import re

age1 = "4 years old"
age2 = "5 years old"
age3 = "9 years old"
age4 = "1 years old"


#method 1
def get_age(age):
    return int(re.sub(r'\D+', '', age))

#method 2
def get_age2(age):
    for i in age:
        if i.isdigit():
            return int(i)

print(get_age(age4))
print(get_age2(age3))