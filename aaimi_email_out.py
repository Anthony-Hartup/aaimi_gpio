#!/bin/bash
# AAIMI EMAIL OUT

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Dedicated email account for AAIMI to send and receive email
system_email = ""
# Password for AAIMI's dedicated Gmail account
system_pass = ""
# User email address
user_email = ""


# Send reports, passkeys and alerts to users. Requires dedicated Gmail account for AAIMI           
def send_email_report(sub, arg1, arg2, arg3=""):
    global system_email, system_pass
    if system_pass != "":    
        # Create HTML head for email if it's intended for a human
        head = """
        <head>
          <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
          <title>Your Title</title>
          <style type="text/css" media="screen">
            h1{ color:white;
                font-size:2.5em;
                background-color:DarkGreen;
                text-align:center;
            }
            h2{
                color:gray;
                font-size:2em;
                text-align:center;
            }
            h3{
                color:purple;
                font-size:2em;
                text-align:center;
            }
            p{
                color:blue;
                font-size:1.5em;
                text-align:center;
            }
          </style>
        </head>
        <body>
        """

        # EMAIL OPTIONS
        # Include HTML header and body for emails to humans (pesky humans!)
        message_body = "<h1>" + sub + "</h1><p>" + arg1 + "</p><p>" + arg2 + "</p>"
        if arg3 != "":
            message_body += "<p>" + arg3 + "</p>"            
        message_body += "</body>"        
        content = head + message_body

        # Send email
        try:
            MESSAGE = MIMEMultipart('alternative')
            # Email details
            MESSAGE['subject'] = sub
            MESSAGE['To'] = user_email
            MESSAGE['From'] = system_email
            # Add body to email
            HTML_BODY = MIMEText(content, 'html')
            MESSAGE.attach(HTML_BODY)
            # Send
            mail = smtplib.SMTP("smtp.gmail.com",587)
            mail.ehlo()
            mail.starttls()
            mail.login(system_email, system_pass)
            mail.sendmail("AAIMI", user_email, MESSAGE.as_string())
            mail.close()
            print("Message sent")
        except:
            print("Email write failed")
