#!/usr/bin/python

# Import smtplib for the actual sending function
import smtplib
import socket

# Import the email modules we'll need
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from optparse import OptionParser
import getopt
import sys 

usage = "usage: %prog [options]"
parser = OptionParser(usage=usage)
parser.add_option("-s", "--source", dest="source", help="define a source for the mail")
parser.add_option("-m", "--message", dest="message", help="define a specific message for the mail")
(options, args) = parser.parse_args()

src = '%s@oscaro.com' % socket.gethostname()
#src = 'florent.neyron@oscaro.com'
dst = 'florent.neyron@oscaro.com'
#dst = 'admin-infra@oscaro.com'

if options.message:
	msg = MIMEText('Server %s encounter an error on %s.\nLog extract below:\n%s\n' % (socket.gethostname(), options.source, options.message), 'plain')
else:
	msg = MIMEText('Server %s encounter an error on %s.\n' % options.source
% socket.gethostname(), 'plain')
msg['Subject'] = 'Problem on %s' % options.source
msg['From'] = src
msg['to'] = dst


s = smtplib.SMTP('localhost')
s.sendmail(src, dst, msg.as_string())
s.quit()




