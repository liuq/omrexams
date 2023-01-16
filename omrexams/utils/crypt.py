from itertools import cycle
from string import ascii_lowercase

def caesar_shift(text, places):
    def substitute(char):
        # the comma will be replaced by '_' which is coded to 95
        if char in ascii_lowercase or char in ",":
            if char == ",":
                char = "_"
            char_num = ord(char) - 95
            char = chr((char_num + places) % 28 + 95)
        return char
    text = text.lower().replace(" ", "")
    return "".join(substitute(char) for char in text)

def caesar_unshift(encrypted, places):
    def substitute(char):
        if char in ascii_lowercase or char in "_" or char in "`":            
            char_num = ord(char) - 95
            char = chr((char_num - places) % 28 + 95)
            if char == "_":
                char = ","
        return char
    encrypted = encrypted.lower().replace(' ', '')
    return "".join(substitute(char) for char in encrypted)

def vigenere_encrypt(text, key):
    if type(key) is not str:
        key = str(key)
    tmp = []
    for k in key:
        if k.isalpha():
            tmp.append(ord(k.lower()) - ord('a'))
        elif k.isdigit():
            tmp.append(int(k) + 1)        
    return "".join(caesar_shift(c, k) for c, k in zip(text, cycle(tmp)))

def vigenere_decrypt(text, key):
    if type(key) is not str:
        key = str(key)
    tmp = []
    for k in key:
        if k.isalpha():
            tmp.append(ord(k.lower()) - ord('a'))
        elif k.isdigit():
            tmp.append(int(k) + 1)
    return "".join(caesar_unshift(c, k) for c, k in zip(text, cycle(tmp)))

def binary_encrypt(solutions, key):
    assert type(solutions) is list, "Only lists can be binary encrypted"
    if type(key) is not str:
        key = str(key)
    # transform the key in sequence of bytes (taking only the least significant byte)
    mask = (1 << 8) - 1
    key_generator = cycle((map(lambda c: ord(c) & mask, key)))
    questions = 0b0    
    for i, text in enumerate(solutions):
        q = 0b0
        for c in text:
            b = ord(c.lower()) - ord('a')
            assert b < 8, f"Answer {c.lower()} out of range for question {i + 1} (limited to max 8, i.e., up to I)"
            q |= (1 << b)
        # xor encryption
        q = q ^ next(key_generator)
        questions = (questions << 8) | q
    return questions

def binary_decrypt(solutions, key):
    assert type(solutions) is int, "Only binary numbers can be decrypted"
    # 8 bit 11...1 mask
    mask = (1 << 8) - 1
    if type(key) is not str:
        key = str(key)
    # transform the key in sequence of bytes (taking only the least significant byte)
    key_generator = cycle((map(lambda c: ord(c) & mask, key)))
    # extract solutions, the order is reversed
    tmp_solutions = []
    while solutions: # NOTE: it is assumed at least one correct answer per question
        current = solutions & mask
        tmp_solutions.append(current)
        solutions = solutions >> 8
    # decrypt, in the reversed order
    for i in reversed(range(len(tmp_solutions))):
        tmp_solutions[i] ^= next(key_generator)    
    questions = []
    for current in reversed(tmp_solutions):
        q = ""
        extract, digit = 1, 0
        while digit < 8:
            if current & extract:
                q += chr(digit + ord('a'))
            extract = extract << 1
            digit = digit + 1
        questions.append(q)       
    return questions



