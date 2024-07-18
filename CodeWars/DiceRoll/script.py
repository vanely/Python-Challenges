import random

# @param = number of dice to roll
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

print(dice_roll(3))