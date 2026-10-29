from launcher import bootstrap

bootstrap(__file__)

from ui import run  # noqa: E402  (after bootstrap: needs the installed libraries)

if __name__ == '__main__':
    run()
