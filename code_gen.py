import random

def get_random_code():
    code = ''
    for i in range(0,7):
        code += chr(random.randint(48,122))
    return code

