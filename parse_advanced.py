# parse_advanced.py (ULTRA FAST - UNLIMITED & EFFICIENT)
"""
LLM-driven parsing utilities - OPTIMIZED FOR SPEED
Processes all content in ONE API call instead of looping
"""

from typing import List, Optional
import google.generativeai as genai
import json
import os 

# ✅ Configure Gemini API: Key is loaded from the environment
api_key = os.getenv("GEMINI_API_KEY") 
genai.configure(api_key=api_key) 

# ✅ Default fastest model
MODEL_NAME_FLASH = "models/gemini-2.5-flash"


def parse_with_gemini(
    dom_chunks: List[str],
    parse_description: str,
    model_name: str
):
    """
    ULTRA FAST: Processes ALL content in ONE API call.
    """
    if not dom_chunks or not parse_description.strip():
        return "No content to analyze."

    # Explicit check for missing key
    if not api_key:
         return "❌ API Key Error: Please ensure your **valid** Gemini API key is set as the GEMINI_API_KEY environment variable."

    # ✅ SPEED OPTIMIZATION: Combine ALL chunks into ONE request
    combined = "\n\n---SECTION BREAK---\n\n".join(dom_chunks)
    
    # Truncate if too large 
    if len(combined) > 100000:
        combined = combined[:100000] + "\n\n[Content truncated for performance]"
    
    # Simple, effective prompt (UNLIMITED OUTPUT, STRUCTURE ADDED)
    prompt = (
        f"You are a helpful and expert analyst of website content.\n\n"
        f"User Question: {parse_description}\n\n"
        f"Website Content:\n{combined}\n\n"
        f"Instructions:\n"
        f"- Answer the question clearly and concisely.\n"
        f"- **CRITICAL: If the question asks for a list, product details, or structured data, provide the complete information in a clear, formatted Markdown table.**\n" # 🚀 New instruction for structure
        f"- Do not summarize data unless asked to.\n"
        f"- If information isn't in the content, state that concisely.\n"
        f"- Be specific and accurate.\n\n"
        f"Answer:"
    )
    
    try:
        model = genai.GenerativeModel(model_name)
        print(f"🚀 Processing {len(dom_chunks)} sections in ONE fast request using {model_name}...")
        
        response = model.generate_content(prompt)
        result = response.text.strip()
        
        print(f"✅ Analysis complete!")
        return result
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")
        
        if "API key" in error_msg or "authentication" in error_msg.lower():
            return "❌ API Key Error: The provided Gemini API key is invalid or missing. Ensure your valid key is set as GEMINI_API_KEY."
        elif "quota" in error_msg.lower():
            return "❌ Quota Exceeded: You've hit the API rate limit. Try again in a few minutes."
        elif "timed out" in error_msg.lower():
             return f"❌ Request Timed Out (504): The {model_name} model took too long. Try switching to the faster 'Flash' model or ask a more specific question." 
        else:
            return f"❌ Error processing content: {error_msg}"