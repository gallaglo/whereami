import logging
import os
import json
import markdown
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_google_vertexai import ChatVertexAI
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from pydantic import BaseModel, Field
from typing import Optional, List
from gcp_tools import get_gcp_region_info, list_gcp_regions, get_gcp_services_in_region

class ChatResponse(BaseModel):
    """Structured response model for chat responses"""
    content: str = Field(description="The main response content")
    sections: Optional[List[str]] = Field(default=None, description="List of content sections if applicable")
    is_technical: bool = Field(default=False, description="Whether this is a technical/GCP-focused response")
    location_mentioned: Optional[str] = Field(default=None, description="City/location mentioned in the query")

class ChatService:
    def __init__(self):
        # Initialize Wikipedia tool
        wikipedia = WikipediaQueryRun(
            api_wrapper=WikipediaAPIWrapper(
                top_k_results=2,
                doc_content_chars_max=4000
            )
        )

        # Define available function tools
        self.function_tools = [
            wikipedia,
            get_gcp_region_info,
            list_gcp_regions,
            get_gcp_services_in_region
        ]

        # Configure thinking budget for complex reasoning
        # Set to 0 for simple queries (low latency), or higher for complex reasoning
        self.default_thinking_budget = 1024

        # Initialize LangChain ChatVertexAI model with function tools
        # Note: Google Search is configured separately to avoid tool_type conflict
        # Gemini 3 Flash preview requires location="global"
        base_model = ChatVertexAI(
            model="gemini-3-flash-preview",
            project=os.environ["PROJECT_ID"],
            location="global",
            temperature=0.3,
            top_p=0.6,
            max_output_tokens=8192
        )

        # Bind tools separately - first Google Search, then function tools
        self.langchain_llm = base_model.bind(tools=[{"google_search": {}}]).bind_tools(self.function_tools)

        # Create structured output version for consistent formatting
        self.structured_llm = self.langchain_llm.with_structured_output(ChatResponse)
        
        # Define system message template for GCP/cloud regions focus
        system_template = """You are a helpful AI assistant powered by Gemini 3 Flash, specialized in Google Cloud Platform (GCP) and cloud computing topics, with a particular focus on cloud regions, zones, and geographic distribution of cloud services.

Your role is to provide accurate, helpful information about:
- GCP regions, zones, and availability zones
- Cloud infrastructure and geographic distribution
- Regional deployment strategies and best practices
- Cloud networking and latency considerations
- Multi-region and global cloud architectures
- GCP services availability across different regions
- Data residency and compliance considerations
- Geographic locations, their history, culture, and current conditions (weather, events, etc.)

AVAILABLE TOOLS:
You have access to the following specialized tools that you should use when appropriate:
- google_search: For general web searches, current information, real-time data (weather, events, news), and factual verification
- wikipedia: For detailed encyclopedic information about locations, history, geography, and general knowledge
- get_gcp_region_info: Get detailed information about a specific GCP region including zones and quotas
- list_gcp_regions: List all available GCP regions with basic information
- get_gcp_services_in_region: Get information about GCP services available in a specific region

USE THESE TOOLS ACTIVELY: When users ask about GCP regions, cloud services, locations, weather, or current events, use the appropriate tools to get accurate, real-time information rather than relying only on your training data. For weather information, use Google Search. For historical or encyclopedic information about places, use Wikipedia.

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
12. For current/real-time information (weather, temperature, current events), ALWAYS use Google Search
13. For historical, encyclopedic, or general knowledge about locations, use Wikipedia
14. When users ask about specific cities different from the deployment location, focus on THOSE cities, not the deployment location

Response approach:
- For questions specifically about cities, locations, places, or geographical areas as places to visit or learn about (like "What is an interesting fact about [city]?"): 
  1. First share fascinating local facts about culture, history, geography, or notable features
  2. Include the current temperature and weather conditions for that city (always search for this)
  3. Then gently connect to cloud infrastructure by mentioning how the region benefits cloud deployments
- For technical questions about GCP regions (like "Tell me more about us-west1"): Focus on technical details, availability, services, and cloud infrastructure without including weather information
- For topics completely unrelated to geography or technology: Politely redirect with: "That's an interesting question! While I'm specialized in GCP and cloud infrastructure, I'd love to help you explore cloud regions, GCP services, or deployment strategies instead."

IMPORTANT: Only include weather information when users are asking about cities/locations from a geographical or cultural perspective, not when asking technical questions about GCP regions.

RESPONSE FORMAT: You must respond with structured content that includes:
- content: The main response text with proper markdown formatting
- sections: List any major sections if your response has multiple parts
- is_technical: Set to true for GCP/cloud technical questions, false for geographical/cultural questions
- location_mentioned: The city/location name if the user is asking about a specific place
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
            
            # Use structured LangChain output for consistent formatting
            try:
                structured_response = self.structured_llm.invoke(formatted_prompt)
                # Extract just the content field from the structured response
                if hasattr(structured_response, 'content') and structured_response.content:
                    full_response = structured_response.content
                    logging.info(f"Structured response - Technical: {structured_response.is_technical}, Location: {structured_response.location_mentioned}")
                else:
                    # Handle case where structured response doesn't have expected content
                    full_response = str(structured_response)
                    logging.warning(f"Structured response missing content field: {structured_response}")
            except Exception as struct_error:
                logging.warning(f"Structured output failed, falling back to regular response: {struct_error}")
                # Fallback to regular response
                response = self.langchain_llm.invoke(formatted_prompt)
                if hasattr(response, 'content'):
                    full_response = response.content
                else:
                    full_response = str(response)
            
            # Ensure full_response is a string (handle case where it might be a list)
            if isinstance(full_response, list):
                full_response = ' '.join(str(item) for item in full_response)
            elif not isinstance(full_response, str):
                full_response = str(full_response)
            
            # Clean up citations and improve formatting
            full_response = full_response.replace("[my knowledge]", "")

            # Improve list formatting - ensure proper spacing for markdown lists
            lines = full_response.split('\n')
            formatted_lines = []
            in_list = False

            for i, line in enumerate(lines):
                stripped = line.strip()

                # Check if this line is a bullet point
                is_bullet = stripped.startswith('* ') or stripped.startswith('- ') or stripped.startswith('•')

                # If starting a new list, add blank line before it (unless it's the first line)
                if is_bullet and not in_list and formatted_lines and formatted_lines[-1].strip():
                    formatted_lines.append('')
                    in_list = True
                elif not is_bullet and in_list and stripped:
                    # Ending a list
                    in_list = False
                    if formatted_lines and formatted_lines[-1].strip():
                        formatted_lines.append('')

                # Normalize bullet points to use "* "
                if stripped.startswith('•'):
                    formatted_lines.append(stripped.replace('•', '*', 1))
                elif is_bullet:
                    formatted_lines.append(stripped)
                else:
                    formatted_lines.append(line)

            full_response = '\n'.join(formatted_lines)

            # Format the response with markdown, using extensions for better list handling
            formatted_text = markdown.markdown(
                full_response,
                extensions=['nl2br', 'sane_lists']
            )

            # Add CSS styling for proper list indentation
            styled_text = f'<div style="margin-left: 0;">{formatted_text}</div>'
            # Ensure lists have proper indentation
            styled_text = styled_text.replace('<ul>', '<ul style="margin-left: 20px; padding-left: 20px;">')
            styled_text = styled_text.replace('<ol>', '<ol style="margin-left: 20px; padding-left: 20px;">')

            return styled_text
            
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