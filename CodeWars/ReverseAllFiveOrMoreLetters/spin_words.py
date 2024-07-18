import re

phrase1 = "Hey fellow warriors"
phrase2 = "This is a test"
phrase3 = "This is another test"

#method 1
def spin_words(sentence):

    words = list(sentence.split(' '))

    for word in words:
        if len(word) >= 5:
            words[words.index(word)] = word[::-1]

    return ' '.join(words) 


#method 2
def spin_words2(sentence):
    return " ".join([x[::-1] if len(x) >= 5 else x for x in sentence.split(" ")])


#method 3
def spin_words3(sentence):
    words = [word for word in sentence.split(" ")]
    words = [word if len(word) < 5 else word[::-1] for word in words]
    return " ".join(words)


#method 4
def spin_words4(sentence):
    return re.sub(r"\w{5,}", lambda w: w.group(0)[::-1], sentence)

print(spin_words(phrase1))
