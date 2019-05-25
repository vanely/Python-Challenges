# player lvl range 1 - 170
# from lvl 1 to lvl 2 a player needs 314XP
# every other lvl up past the first requires that we add the previous XP + 25% of the previous XP

# EX:
#   XP from lvl1 to lvl2 = 314
#   XP from lvl2 to lvl3 = 314 + (314*0.25) = 392
#   XP from lvl3 to lvl4 = 392 + (392*0.25) = 490
#   XP from lvl4 to lvl5 = 490 + (490*0.25) = 612
#   XP from lvl1 to target_lvl = 314 + 392 + 490 + 612 = 1808
#   XP from current_xp to target_lvl = 1808 - 0 = 1808

# after every 10 levels the percentage decreases by 1%
# when a player reaches lvl 170 they stop leveling but they can still accumulate more Xp
# If one or both of the arguments are invalid(not given, not in correct format, not in range...etc) return "Input is invalid.".
# If the player has already reached the target_lvl return "You have already reached level target_lvl.".
def xp_to_target_lvl(current_xp, target_lvl):
  not_given = current_xp == None or target_lvl == None
  incorrect_format = type(current_xp) != int or type(target_lvl) != int
  not_in_range = current_xp < 0 or target_lvl > 170

  if not_given or incorrect_format or not_in_range:
    return "Input is invalid."
  elif current_xp >= target_lvl:
    return "You have already reached level target_lvl."