import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

email_sender = "warning.airguard@gmail.com"
email_password = os.environ.get("EMAIL_PASSWORD")


def attach_file_to_email(email_message, filename, extra_headers=None):
    # Open the attachment file for reading in binary mode, and make it a MIMEApplication class
    with open(filename, "rb") as f:
        file_attachment = MIMEApplication(f.read())
    # Add header/name to the attachments
    file_attachment.add_header(
        "Content-Disposition",
        f"attachment; filename= {filename}",
    )
    """  
     Set up the input extra_headers for img
       Default is None: since for regular file attachments, it's not needed
       When given a value: the following code will run
          Used to set the cid for image
    """
    if extra_headers is not None:
        for name, value in extra_headers.items():
            file_attachment.add_header(name, value)
    # Attach the file to the message
    email_message.attach(file_attachment)


def send_email(email_receiver, subject, paragraph):
    color = 31923  # Example variable with the price
    photo_path = "/Users/mariatsiompra/Documents/master/diplwmatiki/pollutionLogo.png"

    body = '''
    <html>
    <head>
        <title>Header Example</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
            }}
            .header {{
                background-color: #{};
                text-align: center;
                padding: 20px;
            }}
            .header img {{
                max-width: auto;
                height: 30%;
                display: block;
                margin: 0 auto;
            }}
            .main-body {{
                background-color: #E5FFCA;
                padding: 20px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <img src="cid:header_photo" alt="Header Photo">
        </div>
        <div class="main-body">
            <h1>Air Guard Information</h1>
            <p>{}</p>
        </div>
    </body>
    </html>
    '''.format(color, paragraph)

    # em = EmailMessage()
    em = MIMEMultipart()
    em['From'] = email_sender
    em['To'] = email_receiver
    em['Subject'] = subject
    # em.set_content(body)
    em.attach(MIMEText(body, "html"))
    attach_file_to_email(em, photo_path, {"Content-ID": "<header_photo>"})
    # context = ssl.create_default_context()

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_sender, email_password)
        # smtp.sendmail(email_sender, email_receiver, em.as_string())
        try:
            smtp.sendmail(email_sender, email_receiver, em.as_string())
            print("Email sent successfully.")
        except Exception as e:
            print("Failed to send email:", str(e))
