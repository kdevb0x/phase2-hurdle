from datetime import datetime, timedelta

SECS_PER_DAY = 86400
MIDNIGHT_WRAP_THRESHOLD_SECS = -600

import logging
logger = logging.getLogger(__name__)


# Parse the mgen file found at filename
def mgen_parser(filename):

    mgenfile = []

    # Open the MGEN File and read and parse each line
    with open(filename, "r") as f:

        logger.debug("parsing mgen file: %s", filename)
        for (linecount,line) in enumerate(f):
            try:
                # first two lines are a header
                if(linecount < 2): continue

                # If this line isn't a "RECV" line don't bother processing
                if(line.find("RECV") == -1): continue

                # Split the line into "words" separated by space
                words = line.split()
                for (i,word) in enumerate(words):

                    # 0: Receive Time
                    if(i == 0):
                        time_recv = datetime.strptime(word, "%H:%M:%S.%f")

                    # 3: Flow ID
                    elif (i==3):
                        flow_id = int(word.split(">")[1])

                    # 4: Packet Seq Num
                    elif (i==4):
                        seq_num = int(word.split(">")[1])

#                    # 5: Fragment Number
#                    elif (i==5):
#                        frag_num = int(word.split(">")[1])

                    # 5: Source IP
                    elif (i==5):
                        ip_src = word.split(">")[1]

                    # 6: Destination IP
                    elif (i==6):
                        ip_dst = word.split(">")[1]

                    # 7: Time the packet was sent
                    elif (i==7):
                        time_sent = datetime.strptime(word.split(">")[1], "%H:%M:%S.%f")

                    # 8: Size of the packet
                    elif (i==8):
                        size =  word.split(">")[1]

                # Correct for time wrapping around midnight
                if 't0' not in locals(): t0 = time_sent
                if (time_recv-t0).total_seconds() < MIDNIGHT_WRAP_THRESHOLD_SECS:
                    time_recv += timedelta(0,SECS_PER_DAY)
                if (time_sent-t0).total_seconds() < MIDNIGHT_WRAP_THRESHOLD_SECS:
                    time_sent += timedelta(0,SECS_PER_DAY)

                # Add this entry to the file
                #  the time_sent check is basically a check for an empty file, then this variable won't exist
                if "time_sent" in locals() or "time_sent" in globals():
                    mgen_entry = {"time_recv":time_recv,
                                  "time_sent":time_sent,
                                  "flowid":flow_id,
                                  "seq_num":seq_num,
                                  "ip_src":ip_src,
                                  "ip_dst":ip_dst,
                                  "size":size}

                    mgenfile.append(mgen_entry)

            except ValueError as err:
                logger.error("Error parsing line number %i: %s", linecount, line)
                raise err


    return mgenfile
