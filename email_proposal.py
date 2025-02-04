import PyPDF2
import re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import json
from info_gather import chat_completion

class EmailProposalSystem:
    def __init__(self, pdf_paths):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.templates = self._load_all_templates(pdf_paths)
        self._create_faiss_index()

    def _load_all_templates(self, pdf_paths):
        """Load and structure templates from multiple PDFs"""
        templates = {}
        for category, path in pdf_paths.items():
            templates[category] = self._extract_templates_from_pdf(path)
        return templates

    def _extract_templates_from_pdf(self, pdf_path):
        """Extract numbered templates from a single PDF with error handling"""
        try:
            print(f"Processing PDF: {pdf_path}")  # Debug statement
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                full_text = '\n'.join([page.extract_text() for page in reader.pages])
                print(f"Extracted text from PDF:\n{full_text}")  # Debug statement

            # Preprocess the text: Replace multiple spaces and newlines with a single space
            full_text = re.sub(r'\s+', ' ', full_text).strip()

            # Improved regex pattern to match numbered templates
            # Matches patterns like "1. Template Title" or "1.  Template Title" or "2. “I Feel Like a Stalker”"
            pattern = r'(\b\d+\.\s+“?[A-Za-z].+?”?)(?=\b\d+\.\s+“?[A-Za-z]|\Z)'
            sections = re.split(pattern, full_text)

            templates = []
            current_title = None
            current_content = ""

            for i, section in enumerate(sections):
                if re.match(r'\b\d+\.\s+“?[A-Za-z].+?”?', section.strip()):
                    # Found new template title
                    if current_title:
                        # Add previous template if exists
                        templates.append({
                            'title': current_title.strip(),
                            'content': current_content.strip(),
                            'embedding': None
                        })
                    current_title = section.strip()
                    current_content = ""
                elif current_title:
                    # Accumulate content under current title
                    current_content += section.strip() + " "

            # Add the last template
            if current_title and current_content:
                templates.append({
                    'title': current_title.strip(),
                    'content': current_content.strip(),
                    'embedding': None
                })

            if not templates:
                print(f"No templates found in {pdf_path}")  # Debug statement

            print(f"Found {len(templates)} templates in {pdf_path}:")  # Debug statement
            for i, template in enumerate(templates, 1):
                print(f"Template {i}: {template['title']}")  # Debug statement

            return templates

        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
            return []

    def _create_faiss_index(self):
        """Create unified FAISS index for all templates"""
        all_embeddings = []
        self.template_list = []

        # Flatten templates and create embeddings
        for category in self.templates:
            for template in self.templates[category]:
                embedding = self.model.encode(template['title'] + " " + template['content'])
                template['embedding'] = embedding
                all_embeddings.append(embedding)
                self.template_list.append(template)

        # Create FAISS index if there are embeddings
        if all_embeddings:
            self.index = faiss.IndexFlatL2(len(all_embeddings[0]))
            self.index.add(np.array(all_embeddings))
        else:
            self.index = None
            print("No templates found to create FAISS index.")

    def retrieve_best_template(self, query):
        """Find most relevant template using semantic search"""
        if not self.index:
            raise ValueError("FAISS index has not been created. No templates available.")
        query_embed = self.model.encode(query)
        distances, indices = self.index.search(np.array([query_embed]), 1)
        return self.template_list[indices[0][0]]

    def generate_email(self, query, situation, **kwargs):
        """Generate personalized email using template and context"""
        # Check if FAISS index is available
        if not self.index:
            return {
                "subject": "No Templates Available",
                "body": "No templates are available to generate an email."
            }

        # Retrieve template
        template = self.retrieve_best_template(query)

        # Build context from kwargs
        req_info = json.loads(kwargs.get('req_info', '{}'))
        print("REQ INFO", req_info)
        company_analysis = req_info.get('company_analysis', {})
        decision_maker_profile = req_info.get('decision_maker_profile', {})
        synergy_points = req_info.get('synergy_points', {})

        company_context = f"""
        Recent News: {company_analysis.get('recent_news', '')}
        Financial Health: {company_analysis.get('financial_health', '')}
        Verified Challenges: {', '.join(company_analysis.get('verified_challenges', []))}
        Strategic Priorities: {', '.join(company_analysis.get('strategic_priorities', []))}
        """

        decision_maker_context = f"""
        Communication Style: {decision_maker_profile.get('communication_style', '')}
        Personality Indicators: {decision_maker_profile.get('personality_indicators', '')}
        Key Achievements: {decision_maker_profile.get('key_achievements', '')}
        Recent Activities: {decision_maker_profile.get('recent_activities', '')}
        """

        synergy_context = f"""
        Product Fit: {synergy_points.get('product_fit', '')}
        Persuasion Levers: {', '.join(synergy_points.get('persuasion_levers', []))}
        Urgency Factors: {', '.join(synergy_points.get('urgency_factors', []))}
        """

        # Construct AI prompt
        prompt = f"""
        Generate a highly personalized email using this template:
        --- TEMPLATE BEGIN ---
        {template['content']}
        --- TEMPLATE END ---

        Context:
        - Situation Type: {situation}
        - Product: {kwargs.get('product_description', '')}
        - Company Context: {company_context}
        - Decision Maker Profile: {decision_maker_context}
        - Synergy Points: {synergy_context}
        - Sender Name: {kwargs.get('sender_name', '')}
        - Sender Position: {kwargs.get('sender_position', '')}
        - Sender Company: {kwargs.get('sender_company', '')}

        Requirements:
        1. Maintain template structure exactly
        2. Personalize content using decision maker's profile
        3. Address company's specific pain points
        4. Use {decision_maker_profile.get('communication_style', 'professional')} tone
        5. You need to format the email correctly e.g,
        6. Do not assume any additional information not provided in the context. Include a dummy placeholder if needed.
        7. Include relevant HTML formatting
        8. Output JSON with 'subject' and 'body' keys. Use single line value for body instead of showing it multiline so that i can be converted to JSON format without errors.
        9. Generate a {decision_maker_profile.get('communication_style', '')} click bait subject line and as well as based on the template content.

        
        IMPORTANT NOTE: 
        - Keep in mind the max_tokens limit for the API call. So do not compromise on the quality of the email but avoid unnecessary spaces in the response.
        - STRICTLY, Do not add any other text, content or comments in the output except the JSON output
        """
        

        # Call your API here (implementation depends on your API client)
        return self._call_llm_api(prompt, decision_maker_profile.get('personality_type', ''))

    def _call_llm_api(self, prompt, decision_maker_context=None):
        """Mock API call implementation"""
        # Replace with actual API call
        # call the API with the prompt and get the response
        messages = [
            {"role": "system", "content": "You are a helpful assistant that generates emails based on given templates and context. The output should be in JSON format with 'subject' and 'body' keys."},
            {"role": "user", "content": prompt}
        ]

        response = chat_completion(messages, 900)
        # parse the response to extract the subject and body
        try:
            return response, decision_maker_context
        except json.JSONDecodeError:
            return {
                "subject": "Error Parsing Response",
                "body": "Failed to parse the response from the API."
            }
        

    
# Usage Example
# if __name__ == "__main__":
#     # Initialize with your PDF paths
#     pdf_paths = {
#         "email": "email-template.pdf",
#         "followup": "followup-template.pdf",
#         "breakup": "breakup-template.pdf"
#     }
    
#     proposal_system = EmailProposalSystem(pdf_paths)
    
#     # Mock request data
#     mock_request = {
#         "product_description": "AI-powered supply chain optimization",
#         "sender_name": "John Doe",
#         "sender_position": "Sales Director",
#         "sender_company": "Tech Solutions Inc"
#     }
    
#     # Generate req_info (from your separate function)
#     req_info = {
#         "company_analysis": {
#             "recent_news": "Khozema Shipchandler was appointed as the Chief Executive Officer of Twilio in January 2024, marking a significant leadership transition. He has been instrumental in various roles at Twilio, including Chief Financial Officer, Chief Operating Officer, and President of Twilio Communications.",
#             "financial_health": "Twilio's financial health has been robust, with the company continuing to grow in the customer engagement platform market. However, specific earnings reports from the last 6 months are not detailed in the provided sources. Twilio has seen significant investment and growth under Shipchandler's leadership.",
#             "verified_challenges": [
#                 "Operational efficiency: Ensuring streamlined experiences for hundreds of thousands of businesses across the globe.",
#                 "Market competition: Maintaining a competitive edge in the highly competitive tech industry.",
#                 "Technological adoption: Continuously innovating and adopting new technologies to drive real-time, personalized customer experiences."
#             ],
#             "strategic_priorities": [
#                 "Driving efficiency and innovation across Twilio's communications business.",
#                 "Ensuring the security and trustworthiness of the company's operations.",
#                 "Expanding and enhancing the company's customer engagement platform capabilities."
#             ]
#         },
#         "decision_maker_profile": {
#             "communication_style": "Data-driven and pragmatic, given his extensive background in finance and operational roles at GE and Twilio.",
#             "personality_indicators": "While specific Myers-Briggs type is not inferable, his career suggests a detail-oriented and strategic thinker with strong leadership skills.",
#             "key_achievements": "Over 25 years of experience growing businesses and driving financial performance, significant roles at GE including Chief Commercial Officer at GE Digital, and various executive positions at Twilio.",
#             "recent_activities": "Appointment as CEO of Twilio, serving on the boards of Smartsheet and Ethos, and previous roles such as President of Twilio Communications and Chief Operating Officer."
#         },
#         "synergy_points": {
#             "product_fit": "Providing top 3% remote Indian IT talent can help Twilio address operational efficiency and technological adoption challenges by ensuring access to skilled and specialized workforce, thereby enhancing their customer engagement platform capabilities.",
#             "persuasion_levers": [
#                 "Highlighting the cost-effectiveness and quality of remote IT talent, which aligns with Shipchandler's data-driven and pragmatic approach.",
#                 "Emphasizing the potential for increased operational efficiency through the integration of skilled remote workers.",
#                 "Showcasing case studies or success stories of other companies that have benefited from similar staffing services, appealing to his strategic and detail-oriented leadership style."
#             ],
#             "urgency_factors": [
#                 "The need for continuous innovation and technological adoption to stay competitive in the market.",
#                 "The immediate requirement for skilled IT talent to support the growth and expansion of Twilio's customer engagement platform.",
#                 "The potential for improved operational efficiency and reduced costs through the use of high-quality remote IT talent."
#             ]
#         }
#     }
    
#     # Generate email
#     response = proposal_system.generate_email(
#         query="Need to contact decision maker about supply chain improvements",
#         situation="Finding a Decision Maker Introduction",
#         company_name="Global Manufacturing Corp",
#         decision_maker="Sarah Johnson",
#         decision_maker_position="Chief Operations Officer",
#         req_info=json.dumps(req_info),
#         **mock_request
#     )
    
#     # print the generated email
#     print(response)