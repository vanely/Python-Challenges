# Count the number of occurrences of each character and return it as a list of tuples in order of appearance.

str1 = "abracadabra"; # [['a', 5], ['b', 2], ['r', 2], ['c', 1], ['d', 1]]]
str2 = "Code Wars"; # [['C', 1], ['o', 1], ['d', 1], ['e', 1], [' ', 1], ['W', 1], ['a', 1], ['r', 1], ['s', 1]]]
str3 = "212"; #  [['2', 2], ['1', 1 ]]]

def ordered_count(text):
  char_array = list(text)
  unique_chars = {}
  for c in range(len(char_array)):
    if char_array[c] in unique_chars:
      unique_chars[char_array[c]] += 1
    else:
      unique_chars[char_array[c]] = 1
  return unique_chars

# print(ordered_count(str1))
print(list(set(str1)))