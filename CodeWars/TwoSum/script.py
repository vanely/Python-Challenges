# Write a function that takes an array of numbers (integers for the tests) and a target number. 
# It should find two different items in the array that, when added together, give the target value. 
# The indices of these items should then be returned in a tuple / list (depending on your language) like so: (index1, index2).
# For the purposes of this kata, some tests may have multiple answers; any valid solutions will be accepted.
# The input will always be valid (numbers will be an array of length 2 or greater, and all of the items will be numbers; target will always be the sum of two different items from that array).
# Based on: https://leetcode.com/problems/two-sum/

#                             numbers               target   valid results
example_one, target_one =     [1 ,2, 3],            4        # ((0,2), (2,0))
example_two, target_two =     [1234, 5678, 9012],   14690    # ((1,2), (2,1))
example_three, target_three = [2, 2, 3],            4        # ((0,1), (1,0))
example_four, target_four =   [3, 2, 4],            6        # ((1,2), (2,1))

def subtract_vals(num1, num2):
  if num1 > num2:
    return num1 - num2
  else:
    return num2 - num1

def two_sum(numbers, target):
  print('\n')
  results = []
  for num in numbers:
    if len(results) == 2:
      break
    possible_target = subtract_vals(target, num)
    if possible_target in numbers:
      if numbers.index(possible_target) != numbers.index(num):
        results.extend((numbers.index(num), numbers.index(possible_target)))
      else:
        indices = [i for i, x in enumerate(numbers) if x == num]
        if len(indices) > 1:
          results.extend((indices[0], indices[1]))
  return tuple(results)

print(f'results for example 1: ${two_sum(example_one, target_one)}')
print(f'results for example 2: ${two_sum(example_two, target_two)}')
print(f'results for example 3: ${two_sum(example_three, target_three)}')
print(f'results for example 4: ${two_sum(example_four, target_four)}')        

