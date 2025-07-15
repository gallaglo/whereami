import logging
import os
import json
import markdown
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_google_vertexai import ChatVertexAI

class ChatService:
    def __init__(self):
        # Initialize LangChain ChatVertexAI model with built-in Google Search
        self.langchain_llm = ChatVertexAI(
            model="gemini-2.0-flash-001",
            project=os.environ["PROJECT_ID"],
            location="us-central1",
            temperature=0.3,
            top_p=0.6,
            max_output_tokens=8192
        ).bind_tools([{"google_search": {}}])
        
        # Define system message template for GCP/cloud regions focus
        system_template = """You are a helpful AI assistant specialized in Google Cloud Platform (GCP) and cloud computing topics, with a particular focus on cloud regions, zones, and geographic distribution of cloud services.

Your role is to provide accurate, helpful information about:
- GCP regions, zones, and availability zones
- Cloud infrastructure and geographic distribution
- Regional deployment strategies and best practices
- Cloud networking and latency considerations
- Multi-region and global cloud architectures
- GCP services availability across different regions
- Data residency and compliance considerations

IMPORTANT DISTINCTION:
- Google DATA CENTERS: Physical facilities where Google operates servers (like The Dalles, Council Bluffs)
- GCP REGIONS: Logical groupings of zones that provide GCP services to customers (like us-west1, us-central1)
- A data center location may not always correspond to a customer-facing GCP region
- Always clarify whether you're discussing data centers or GCP regions when answering questions

Current deployment context:
- This application is running in GCP region: {region}
- Application deployment location: {location}
- Application context: whereami demo application

IMPORTANT: The above context is about WHERE THIS APPLICATION IS DEPLOYED, not necessarily about where the user is asking questions. When users ask about other cities or locations, answer about THOSE locations, not the deployment location.

Guidelines:
1. When users ask about cities or locations where cloud regions are located, provide interesting non-cloud facts but gently steer toward cloud topics
2. For questions about the local area/city, share fascinating cultural, historical, or geographical facts, then connect to cloud infrastructure
3. Always relate responses back to GCP and cloud infrastructure when appropriate
4. Provide specific, actionable information about cloud regions and deployment
5. Include relevant best practices for cloud architecture
6. Use your knowledge of the current deployment region/location to provide contextual responses
7. IMPORTANT: Use Google Search to verify factual claims about Google's infrastructure, data centers, and GCP regions
8. When asked specifically about GCP regions or data centers in specific locations, always search for current information
9. For questions like "Is there a GCP region in [location]?" or "Are there data centers in [location]?", search before answering
10. Be precise: distinguish between Google data centers (physical facilities) and GCP regions (customer service areas)
11. When discussing Google facilities, clarify: "Google operates a data center in [location], but this is not the same as a GCP region available to customers"
12. For current/real-time information (weather, temperature, current events), always use Google Search
13. When users ask about specific cities different from the deployment location, focus on THOSE cities, not the deployment location

Response approach:
- For questions about cities, locations, places, or geographical areas (like "What is an interesting fact about [city]?"): 
  1. First share fascinating local facts about culture, history, geography, or notable features
  2. Include the current temperature and weather conditions for that city (always search for this)
  3. Then gently connect to cloud infrastructure by mentioning how the region benefits cloud deployments
- For topics completely unrelated to geography or technology: Politely redirect with: "That's an interesting question! While I'm specialized in GCP and cloud infrastructure, I'd love to help you explore cloud regions, GCP services, or deployment strategies instead."

IMPORTANT: Whenever a user asks about ANY city or location, always include the current temperature and weather conditions as part of your response.

IMPORTANT: Questions about cities, places, or locations should ALWAYS be answered with interesting local facts first, then connected to cloud topics.
"""

        # Create the prompt template
        self.chat_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template("{user_message}")
        ])

    def generate_response(self, prompt, region=None, location=None):
        """
        Generate a response using LangChain with Google Search grounding.
        
        Args:
            prompt (str): User's input message
            region (str): GCP region where app is deployed
            location (str): Geographic location of deployment
            
        Returns:
            str: Formatted HTML response
        """
        logging.info(f"ChatService generating response for prompt: {prompt}")
        
        try:
            # Format the prompt using LangChain template
            formatted_prompt = self.chat_prompt.format_messages(
                region=region or "unknown",
                location=location or "unknown location",
                user_message=prompt
            )
            
            # Use LangChain with tool calling for grounding
            response = self.langchain_llm.invoke(formatted_prompt)
            
            # Extract the final response content
            if hasattr(response, 'content'):
                full_response = response.content
            else:
                full_response = str(response)
            
            # Ensure full_response is a string (handle case where it might be a list)
            if isinstance(full_response, list):
                full_response = ' '.join(str(item) for item in full_response)
            elif not isinstance(full_response, str):
                full_response = str(full_response)
            
            # Format the response with markdown
            formatted_text = markdown.markdown(full_response.replace("•", "*"))
            return formatted_text
            
        except Exception as e:
            logging.error(f"Error in ChatService.generate_response: {str(e)}", exc_info=True)
            error_response = f'Error: {str(e)}'
            return markdown.markdown(error_response)

    def stream_response(self, prompt, region=None, location=None):
        """
        Generate a streaming response for the chat interface.
        
        Args:
            prompt (str): User's input message
            region (str): GCP region where app is deployed
            location (str): Geographic location of deployment
            
        Yields:
            str: Server-sent event formatted response chunks
        """
        try:
            formatted_text = self.generate_response(prompt, region, location)
            yield f"data: {json.dumps({'chunk': formatted_text})}\n\n"
        except Exception as e:
            logging.error(f"Error in ChatService.stream_response: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'chunk': f'Error: {str(e)}'})}\n\n"