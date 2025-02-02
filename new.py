from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart 
import os
import smtplib

def register_user(email1):
    msg = MIMEMultipart()
    msg['From'] = os.getenv('EMAIL_USERNAME')
    msg['To'] = email1
    msg['Subject'] = "Your OTP Code"
    body = f"""<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <title>OTP Verification - Lead Stream</title>
                </head>
                <body style="background-color: rgb(89,227,167); margin: 0; padding: 20px; font-family: Arial, sans-serif; text-align: center;">

                    <!-- Wrapper Table to Center Everything -->
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                        <tr>
                            <td align="center">

                                <!-- Logo Row (Placed Above the Container) -->
                                <table role="presentation" width="360px" cellspacing="0" cellpadding="0" border="0">
                                    <tr>
                                        <td align="center" style="padding-bottom: 15px;">
                                            <img src="https://twingenfuelfiles.blob.core.windows.net/lead-stream/heuro.png" alt="Heuro Logo" width="80">
                                        </td>
                                    </tr>
                                </table>

                                <!-- Email Container -->
                                <table role="presentation" width="360px" cellspacing="0" cellpadding="0" border="0" style="background-color: #ffffff; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); padding: 20px; text-align: center;">
                                    
                                    <!-- Title -->
                                    <tr>
                                        <td style="font-size: 22px; font-weight: bold; color: #2c3e50; padding-bottom: 10px;">
                                            Lead Stream OTP Verification
                                        </td>
                                    </tr>

                                    <!-- Message -->
                                    <tr>
                                        <td style="font-size: 14px; color: #7f8c8d; padding-bottom: 20px;">
                                            Please use the following code to verify your account:
                                        </td>
                                    </tr>

                                    <!-- OTP Code -->
                                    <tr>
                                        <td style="font-size: 30px; font-weight: bold; color: #4ca1af; letter-spacing: 2px; padding: 10px; border: 2px solid #4ca1af; border-radius: 5px; display: inline-block;">
                                            123456
                                        </td>
                                    </tr>

                                    <!-- Expiry Notice -->
                                    <tr>
                                        <td style="font-size: 14px; color: #7f8c8d; padding-top: 20px;">
                                            This code will expire in 10 minutes.
                                        </td>
                                    </tr>

                                    <!-- Footer -->
                                    <tr>
                                        <td style="font-size: 12px; color: #95a5a6; padding-top: 20px;">
                                            Lead Stream is a product of <a href="https://heuro.in" target="_blank" style="color: #4ca1af; text-decoration: none;">heuro.in</a>
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
email1 = 'akshaybansal89@gmail.com'

print(register_user(email1))