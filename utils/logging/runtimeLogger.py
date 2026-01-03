import gzip
import logging
import os
import shutil
from logging.handlers import TimedRotatingFileHandler

#  We Will First Create The file If Not Then We Will Create But If Already Exist then it is okay
os.makedirs("./logs/runtime", exist_ok=True)


# Then We Will Use the TimedRotatingFileHandler this is an in build function from the logging and this allow us to rotate our file here at every midnight the file that are older then the seven days will rotate

handler = TimedRotatingFileHandler(
    "./logs/runtime/runtime.log", when="midnight", interval=1, backupCount=7, encoding="utf-8"
)


# The rotating Function is the function that will convert the log file into the .gz file such that we will save some space on the vps server


def rotator(source, dest):

    with open(source, "rb") as main_file:

        with gzip.open(dest, "wb") as copy_file:

            shutil.copyfileobj(main_file, copy_file)

    os.remove(source)


handler.rotator = rotator
handler.namer = lambda name: name + ".gz"


formate = logging.Formatter(fmt="%(asctime)s | %(levelname)s | %(message)s |(%(module)s)")


handler.setFormatter(formate)

runtimeLogger = logging.getLogger("app")
runtimeLogger.setLevel(logging.INFO)
runtimeLogger.addHandler(handler)
runtimeLogger.propagate = False

# This is The logger Will log Every thins form a incoming message to the message
