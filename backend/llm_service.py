import logging
import os

logger = logging.getLogger(__name__)

# Lazy-initialized so the server can start without API keys configured
_client = None

# Conversation history per call, keyed by call id (bounded to last 20 turns)
CONVERSATIONS = {}

SYSTEM_PROMPTS = {
    "hi": """आप एक व्यावसायिक ग्राहक सहायक हैं।

निर्देश:
1. हमेशा हिंदी में जवाब दें
2. दिए गए ज्ञान आधार से जानकारी प्रदान करें
3. यदि आप कुछ नहीं जानते तो कहें "मुझे नहीं पता"
4. मित्रवत और पेशेवर रहें
5. संक्षिप्त और स्पष्ट उत्तर दें - यह फोन कॉल है

ज्ञान आधार:
{knowledge_base}""",
    "gu": """તમે એક વ્યાવસાયિક ગ્રાહક સહાયક છો.

સૂચનાઓ:
1. હમેશા ગુજરાતીમાં જવાબ આપો
2. આપેલ જ્ઞાન આધાર પરથી માહિતી આપો
3. જો તમે કંઈક જાણતા નથી તો કહો "મને ખબર નથી"
4. મૈત્રીપૂર્ણ અને વ્યાવસાયિક રહો
5. સંક્ષિપ્ત અને સ્પષ્ટ જવાબ આપો - આ ફોન કૉલ છે

જ્ઞાન આધાર:
{knowledge_base}""",
    "en": """You are a professional business customer support agent.

Instructions:
1. Always respond in English
2. Provide information from the knowledge base provided
3. If you don't know something, say "I don't know"
4. Be friendly and professional
5. Keep responses brief and clear - this is a phone call

Knowledge Base:
{knowledge_base}""",
}

FALLBACK_RESPONSES = {
    "hi": "मुझे खेद है, मुझे आपका सवाल समझने में समस्या हुई। कृपया दोबारा कोशिश करें।",
    "gu": "મને આપનો પ્રશ્ન સમજવામાં સમસ્યા હતી. કૃપા કરીને ફરીથી પ્રયાસ કરો.",
    "en": "I'm sorry, I had trouble understanding your question. Please try again.",
}

MODEL = "claude-sonnet-4-5"


def _get_client():
    """Create the Anthropic client on first use, not at import time."""
    global _client
    if _client is None:
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured in .env")
        _client = Anthropic(api_key=api_key)
    return _client


def get_agent_response(
    business_name: str,
    knowledge_base: str,
    language_code: str,
    customer_query: str,
    conversation_history: list = None,
) -> str:
    """Get a response from Claude based on the customer query."""
    logger.info(f"Getting response: {customer_query[:50]}... (lang: {language_code})")

    if conversation_history is None:
        conversation_history = []

    try:
        system_prompt = SYSTEM_PROMPTS.get(language_code, SYSTEM_PROMPTS["en"])
        system_prompt = system_prompt.format(knowledge_base=knowledge_base)

        messages = []
        for turn in conversation_history:
            messages.append({
                "role": turn.get("role"),
                "content": turn.get("content"),
            })
        messages.append({"role": "user", "content": customer_query})

        logger.info(f"Calling Claude API with {len(messages)} message(s)")

        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=messages,
        )

        response_text = response.content[0].text
        logger.info(f"Response: {response_text[:100]}...")

        conversation_history.append({"role": "user", "content": customer_query})
        conversation_history.append({"role": "assistant", "content": response_text})

        if len(conversation_history) > 20:
            del conversation_history[:-20]

        return response_text

    except Exception as e:
        logger.error(f"Error getting response: {str(e)}")
        return FALLBACK_RESPONSES.get(language_code, FALLBACK_RESPONSES["en"])
