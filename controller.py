import os
from pathlib import Path

from inbox import ReadEmailInbox
from AgentOne.AgentOne import process_email

def main() :
    ReadEmailInbox()

    entries = os.listdir("./IncomingEmails")
    for entry in entries : 
        script_dir = str(Path(__file__).parent)
        entry = script_dir + "/IncomingEmails/" + entry
        prompt, response = process_email(entry)


if __name__ == "__main__" :
    main()