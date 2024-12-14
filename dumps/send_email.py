import requests

def send_mailgun_email(sender_email, recipient_email, subject, content):
    try:
        # Set the API details
        api_url = "https://api.mailgun.net/v3/sandboxe2e101f96ef74e9d9e650189cfac22ab.mailgun.org/messages"
        api_key = "640411ef7a0159f1a6f92a039e707b97-f55d7446-00a7d323"  # Replace with your Mailgun API key
        sender_domain = "sandboxe2e101f96ef74e9d9e650189cfac22ab.mailgun.org"

        # Prepare email data
        data = {
            "from": f"Excited User <mailgun@{sender_domain}>",
            "to": recipient_email,
            "subject": subject,
            "text": content
        }

        # Make the POST request to Mailgun API
        response = requests.post(
            api_url,
            auth=("api", api_key),
            data=data
        )

        if response.status_code == 200:
            print("Email sent successfully!")
        else:
            print(f"Failed to send email. Status code: {response.status_code}, Message: {response.text}")
    
    except Exception as e:
        print(f"Error while sending email: {e}")


# Replace with your details
sender_email = "dharani96556@gmail.com"  # This won't be used directly, as Mailgun uses the sender's domain email.
recipient_email = "20i114@kce.ac.in"
subject = "Hello from Mailgun API!"
content = "This is a test email sent using Mailgun's API."

# Call the function to send the email
send_mailgun_email(sender_email, recipient_email, subject, content)
