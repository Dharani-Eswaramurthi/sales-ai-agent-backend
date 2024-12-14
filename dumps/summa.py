import json
import re
import ast

text = "{\n\"subject\": \"Revolutionizing Fitbit's Health Tracking with Our Advanced VR Wearable Device\",\n\n\"body\": \'\'\'\nDear Mr. James Park,\n\nI hope this email finds you well.\n\nAs someone who has been instrumental in making wearable fitness technology accessible to the masses, I thought it would be apt to bring our latest product, VR, to your attention. Given your personal fitness journey and fascination with technology, I believe you will find this product intriguing.\n\nOur new VR device is a compact wearable that monitors health metrics like heart rate, sleep quality, and activity levels. It's designed to sync seamlessly with mobile apps to provide actionable health insights, enabling users to take control of their wellness journey.\n\nI understand that Fitbit is going through a transitionary phase under Google, with challenges such as integration issues, service outages, and the sunset of community features. Moreover, the reliance on subscriptions and high pricing for new devices present further obstacles. \n\nHere's where our VR device could be of great value to Fitbit. Our device is not only priced competitively, but its innovative technology could also enhance the user experience by providing accurate health insights without the need for a subscription. \n\nWe believe our VR device could complement the existing Fitbit product line, providing a fresh perspective on wearable technology and possibly sparking innovation in Fitbit-branded products. I would love the opportunity to further discuss how our product can help Fitbit rise above these challenges and continue to be a leader in the wearable technology industry.\n\nPlease let me know a convenient time for a call or meeting where we can discuss this in detail. I look forward to the possibility of working with Fitbit and contributing to a healthier, more connected world.\n\nKind regards,\n\n[Your Name]\n[Your Position]\n[Your Contact Information]\n\'\'\'\n}"

# Replace invalid control characters with escaped versions
escaped_text = re.sub(r'(?<!\\)\n', '\\n', text)

print(escaped_text)


# Parse the JSON string
try:
    
    print(ast.literal_eval(escaped_text)['body'])
except json.JSONDecodeError as e:
    print(f"JSONDecodeError: {e}")
