"""
Chat NLP module for MSU Enrollment Advisor Bot.
Handles context detection, language processing, and intent recognition.
"""
import re
from flask import current_app


def detect_language(text):
    """
    Detect the language of the input text.
    Enhanced implementation with more comprehensive language patterns.
    
    Args:
        text (str): Input text
        
    Returns:
        str: Language code ('en', 'ms', 'zh', 'es')
    """
    # Define language detection patterns (enhanced)
    language_patterns = {
        "ms": [
            "apa", "boleh", "saya", "bagaimana", "siapa", "bila", "kenapa", "berapa", "mana", "tolong", 
            "terima kasih", "selamat", "maklumat", "pendaftaran", "universiti", "kursus", "program",
            "yuran", "biasiswa", "tarikh", "pelajar", "antarabangsa", "tempatan", "fakulti"
        ],
        "es": [
            "como", "puedo", "donde", "cuando", "quien", "que", "por favor", "gracias", "hola",
            "universidad", "programa", "curso", "estudiar", "matrícula", "inscripción", "requisitos",
            "beca", "información", "fecha", "límite", "internacional", "estudiante", "facultad",
            "título", "grado", "maestría", "doctorado", "pregunta", "respuesta", "ayuda", "costo"
        ],
        "zh": [
            "我", "你", "他", "她", "们", "请", "谢谢", "怎么", "什么", "为什么", "大学", "课程", 
            "专业", "学费", "奖学金", "申请", "入学", "要求", "截止日期", "国际", "学生", "学院",
            "学士", "硕士", "博士", "问题", "回答", "帮助", "费用", "信息", "招生", "如何"
        ]
    }
    
    # Default to English
    detected_language = "en"
    
    if text:
        query_lower = text.lower()
        
        # Check for Chinese characters first (higher priority)
        if any(char in text for char in "我你他她们请谢谢怎么什么为什么"):
            detected_language = "zh"
            current_app.logger.info(f"Detected language: {detected_language} (character-based detection)")
            return detected_language
        
        # Check for other languages based on word patterns
        for lang, patterns in language_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                detected_language = lang
                current_app.logger.info(f"Detected language: {detected_language} (pattern-based detection)")
                break
                
    return detected_language


def detect_intent(text):
    """
    Detect the intent of the user message.
    
    Args:
        text (str): User message
        
    Returns:
        str: Intent category
    """
    text = text.lower()
    
    # Define intent patterns
    intent_patterns = {
        "program_inquiry": [
            r"program", r"course", r"degree", r"major", r"study", 
            r"bachelor", r"master", r"phd", r"diploma", r"certificate"
        ],
        "admission_inquiry": [
            r"admission", r"apply", r"application", r"enroll", r"register", 
            r"requirements", r"qualify", r"eligible", r"criteria"
        ],
        "fee_inquiry": [
            r"fee", r"tuition", r"cost", r"price", r"scholarship", 
            r"financial aid", r"funding", r"discount", r"payment"
        ],
        "deadline_inquiry": [
            r"deadline", r"due date", r"when.*apply", r"last date", 
            r"closing date", r"submission", r"timeline"
        ],
        "contact_inquiry": [
            r"contact", r"email", r"phone", r"address", r"location", 
            r"campus", r"visit", r"tour", r"meet", r"advisor"
        ],
        "greeting": [
            r"^hi\b", r"^hello\b", r"^hey\b", r"greetings", r"^good morning", 
            r"^good afternoon", r"^good evening", r"^howdy\b"
        ]
    }
    
    # Check for matches in each intent category
    for intent, patterns in intent_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return intent
    
    # Default intent if no patterns matched
    return "general_inquiry"


def detect_education_level(text):
    """
    Detect the education level mentioned in the text.
    
    Args:
        text (str): User message
        
    Returns:
        str or None: Detected education level or None if not found
    """
    text = text.lower()
    
    # Define education level patterns
    edu_patterns = {
        "high_school": [r"high school", r"secondary", r"spm", r"stpm", r"o level", r"a level"],
        "diploma": [r"diploma", r"advanced diploma", r"foundation"],
        "bachelor": [r"bachelor", r"undergraduate", r"degree", r"b\."],
        "master": [r"master", r"postgraduate", r"graduate", r"m\."],
        "phd": [r"phd", r"doctorate", r"doctoral", r"research degree", r"dr\."]
    }
    
    # Check for matches in each education level
    for level, patterns in edu_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return level
    
    return None


def detect_context(user_input):
    """
    Detect the overall context of the user message with strict language enforcement.
    Combines language, intent, and education level detection.
    
    Args:
        user_input (str): User message
        
    Returns:
        dict: Context information including language, intent, and education level
    """
    from flask import session, current_app
    
    # Check if we have a strict language setting in the session
    strict_language = None
    if hasattr(current_app, 'strict_language_settings') and current_app.strict_language_settings.get('current_language'):
        strict_language = current_app.strict_language_settings.get('current_language')
        current_app.logger.info(f"STRICT ENFORCEMENT: Using strict language from app context: {strict_language}")
    elif session and 'strict_language' in session:
        strict_language = session.get('strict_language')
        current_app.logger.info(f"STRICT ENFORCEMENT: Using strict language from session: {strict_language}")
    
    # If strict language is set, use it instead of detecting language
    if strict_language:
        language = strict_language
    else:
        language = detect_language(user_input)
        current_app.logger.info(f"No strict language set, detected language: {language}")
    
    context = {
        "language": language,
        "intent": detect_intent(user_input),
        "education_level": detect_education_level(user_input)
    }
    
    return context
