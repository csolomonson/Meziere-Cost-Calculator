import getpass

from authentication import password_hash


if __name__ == "__main__":
    print(password_hash(getpass.getpass("Password: ")))
