# Sales AI Agent

Welcome to the Sales AI Agent CRM! This project is designed to streamline and enhance your sales process using AI-driven insights and automation. Below you'll find an overview of the features and functionalities provided by both the frontend CRM and the backend services.

## Features

### CRM Frontend

1. **Login Authentication**:
   - Secure login for authorized users.
   - Session management to maintain user authentication state.

2. **Sidebar Navigation**:
   - Easy navigation through different sections of the CRM.
   - Links to generate campaigns and check mail status.

3. **Mail Status Table**:
   - View the status of sent emails.
   - Detailed information about each email, including recipient, subject, body, and status.

4. **Potential Companies Form**:
   - Generate a list of potential companies based on product description and Ideal Client Profile (ICP).
   - Fetch decision makers for each company.
   - Draft and send personalized emails to decision makers.

5. **Header and Footer**:
   - Consistent header and footer across the application for a professional look.

### Backend Functionalities

1. **Email Tracking**:
   - Track the status of sent emails (Not Responded, Interested, Not Interested).
   - Generate unique tracking IDs for each email.
   - Update email status based on recipient actions.

2. **Potential Companies and Decision Makers**:
   - Use AI to identify potential companies based on product description and ICP.
   - Fetch decision makers from LinkedIn and other sources.
   - Validate email addresses of decision makers.

3. **Email Proposal Generation**:
   - Generate personalized email proposals using AI.
   - Tailor emails to the recipient's profile and company's context.

4. **Email Sending**:
   - Send emails with tracking pixels to monitor opens and clicks.
   - Handle email sending through SMTP.

5. **Reminder Emails**:
   - Generate follow-up reminder emails for non-responsive recipients.
   - Encourage recipients to take action with polite and concise reminders.

6. **API Endpoints**:
   - `/potential-companies`: Get potential companies based on product description and ICP.
   - `/potential-decision-makers`: Get decision makers for a given company.
   - `/email-proposal`: Generate email proposals.
   - `/send_email`: Send emails with tracking.
   - `/track/{tracking_id}`: Track email opens.
   - `/track-response/{tracking_id}/{response}`: Track recipient responses.
   - `/email-reminder`: Generate follow-up reminder emails.
   - `/status`: Fetch tracked emails.
   - `/fetch-mail-status`: Fetch mail status for the frontend.

## Getting Started

### Prerequisites

- Node.js
- Python
- PostgreSQL
- FastAPI
- React

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Dharani-Eswaramurthi/Sales-AI-Agent.git
   cd Sales-AI-Agent

2. Install frontend dependencies:
   ```bash
   cd crm
   npm install

3. Install backend dependencies:
   ```bash
   cd ../app
   pip install -r requirements.txt

4. Set up the PostgreSQL database and update the DATABASE_URL in app.py.

5. Start the backend server:
   ```bash
   uvicorn app:app --reload

6. Start the frontend server:
   ```bash
   cd ../crm
   npm start


### Usage
1. Open your browser and navigate to http://localhost:3000.
2. Log in with your credentials.
3. Use the sidebar to navigate through different sections.
4. Generate potential companies and decision makers.
5. Draft and send personalized emails.
6. Track the status of sent emails and follow up as needed.

### Contributing
We welcome contributions! Please fork the repository and submit pull requests.

### License
This project is licensed under the MIT License.

### Contact
For any questions or support, don't hesitate to get in touch with Dharani Eswaramurthi.

### Thank you for using Sales AI Agent CRM! We hope it enhances your sales process and drives success. 
