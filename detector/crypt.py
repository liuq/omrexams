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
        if char in ascii_lowercase or char in "_":            
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
            tmp.append(ord(k.lower()) - 96)
        elif k.isdigit():
            tmp.append(int(k) + 1)        
    return "".join(caesar_shift(c, k) for c, k in zip(text, cycle(tmp)))

def vigenere_decrypt(text, key):
    if type(key) is not str:
        key = str(key)
    tmp = []
    for k in key:
        if k.isalpha():
            tmp.append(ord(k.lower()) - 96)
        elif k.isdigit():
            tmp.append(int(k) + 1)
    return "".join(caesar_unshift(c, k) for c, k in zip(text, cycle(tmp)))