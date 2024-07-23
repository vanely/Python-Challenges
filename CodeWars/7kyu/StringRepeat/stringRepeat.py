str1 = 'Word'
repitition = 6

def repeat_str(repeat, string):

    arr = []
    repeatTxt = ''

    for i in range(repeat):
        arr.append(string)

        repeatTxt = ''.join(arr)

    return repeatTxt

print(repeat_str(repitition, str1))
