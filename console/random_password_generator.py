import string, os

class RandomPasswordGenerator:
    def __init__(self):
        pass

    def getRandomPassword(self):
        chars = string.ascii_letters + string.digits + '+/'
        assert 256 % len(chars) == 0  # non-biased later modulo
        pwd_len = 16
        return ''.join(chars[c % len(chars)] for c in os.urandom(pwd_len))