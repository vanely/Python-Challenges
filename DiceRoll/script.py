import random

def dice_roll(number_of_dice):
  dice = []
  roll_sum = 0
  if type(number_of_dice) != int:
    return 'Invalid type, entry must be a number!'

  for i in range(1, (number_of_dice + 1)):
    dice.append(random.randint(1, 6))
    
  for j in range(len(dice)):
    roll_sum += dice[j]

  return "{0} \n{1}".format(dice, roll_sum)

rolls_and_sum = dice_roll(3)

print(rolls_and_sum)