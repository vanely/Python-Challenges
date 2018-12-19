def rental_car_cost(d):
    total = 0
    rCost = 40

    if d >= 7:
        total = rCost * d - 50
    elif d >= 3:
        total = rCost * d - 20
    else:
        total = rCost * d
    return total

def letterGrade(score):
    if score >= 90:
        letter = 'A'
    elif score >= 80:
        letter = 'B'
    elif score >= 70:
        letter = 'C'
    elif score >= 60:
        letter = 'D'
    else:
        letter = 'F'
    return letter

print(rental_car_cost(3))
print(letterGrade(70))