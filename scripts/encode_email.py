import base64, sys
from_addr, to_addr, subject, body_file = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
body = open(body_file).read()
msg = f"From: {from_addr}\nTo: {to_addr}\nSubject: {subject}\nMIME-Version: 1.0\nContent-Type: text/plain; charset=utf-8\n\n{body}"
print(base64.urlsafe_b64encode(msg.encode("utf-8")).decode("utf-8"))
