import sys

from client.Client import Client


def main(argv):
    client = Client()
    client.send()
    client.close()

if __name__ == '__main__':
    main(sys.argv[1:])
