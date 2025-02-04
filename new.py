from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart 
import os
import smtplib

def register_user(email1):
    msg = MIMEMultipart()
    msg['From'] = os.getenv('EMAIL_USERNAME')
    msg['To'] = email1
    msg['Subject'] = "Your OTP Code"
    body = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <title>Email Notification</title>
</head>
<body style=\"background-color: rgb(89,227,167); font-family: 'Helvetica', 'Century Schoolbook', sans-serif; margin: 0; padding: 20px; text-align: center;\">

    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\">
        <tr>
            <td align="center">

                <!-- Logo -->
                <table role="presentation" width="600px" cellspacing="0" cellpadding="0" border="0">
                    <tr>
                        <td align="center" style="padding-bottom: 20px;">
                            <img src="https://twingenfuelfiles.blob.core.windows.net/lead-stream/heuro.png" alt="Heuro Logo" width="75">
                        </td>
                    </tr>
                </table>

                <!-- Email Content -->
                <table role="presentation" width="600px" cellspacing="0" cellpadding="0" border="0" 
                    style="background: #ffffff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); padding: 20px; text-align: left;">
                    
                    <tr>
                        <td style="font-size: 16px; color: #333; padding: 10px 20px; line-height: 1.6;">
                            <p>Hi sender_name,</p>
                            <p>Your email to <strong>recipient</strong> has been sent successfully.</p>
                            <p><strong>Subject:</strong> subject</p>
                            <p><strong>Body:</strong></p>
                            <p>body</p>
                            <p>Thank you for using Lead Stream!</p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>
</body>
</html>
"""
    
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(os.getenv('SMTP_SERVER'), os.getenv('SMTP_PORT')) as server:
            server.starttls()
            server.login(os.getenv('EMAIL_USERNAME'), os.getenv('EMAIL_PASSWORD'))
            server.sendmail(os.getenv('EMAIL_USERNAME'), email1, msg.as_string())
    except Exception as e:
        return {"message": f"Failed to send email: {str(e)}"}

    return {"message": "User registered successfully. Please verify your email with the OTP sent."}

email = 'dharani96556@gmail.com'
print(register_user(email))