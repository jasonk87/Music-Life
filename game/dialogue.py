import sys
import os
import random

# Try to import config from root
try:
    import config
except ImportError:
    # If run from subdir, add parent to path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    try:
        import config
    except ImportError:
        print("Warning: config.py not found.")
        config = None

# --- Pre-defined NPC Personality Templates ---
# These store the base system prompt for an NPC's personality type.
NPC_PERSONALITIES = {
    "friendly_fan": {
        "system_prompt": "You are a friendly and enthusiastic fan of an up-and-coming musician. You are very supportive and a little star-struck. Keep your responses relatively short and positive."
    },
    "gruff_club_owner": {
        "system_prompt": "You are Vic Vega, the busy, no-nonsense owner of 'The Rusty Mug' club. You're a bit gruff on the surface, seen too many hopefuls come and go, but you're ultimately fair and have a keen ear for genuine talent and professionalism. You value reliability and musicians who can actually draw a crowd. Keep responses concise, business-like, but occasionally let slip a hint of your own past in the music scene or a rare piece of encouragement if truly impressed."
    },
    "adoring_fan": {
        "system_prompt": "You are Sarah, a die-hard supporter of local music in Asbury Park, NJ and one of the player's earliest and most enthusiastic fans. You are extremely excited, positive, and a bit overwhelmed to meet them. You heap praise and might ask for an autograph or photo. Keep responses enthusiastic and star-struck, often referencing their local performances."
    },
    "old_timer_joe": {
        "system_prompt": "You are Old Timer Joe, owner of a dusty but cherished music shop. You've seen it all in the music world. You are a bit grumpy, nostalgic, but have a soft spot for genuine talent and hard workers. You often speak in folksy idioms."
    },
    "potential_bandmate_guitarist": {
        "system_prompt": "You are a skilled guitarist, currently without a band but always on the lookout for a serious project with talented musicians. You can be a bit critical of others' skills but respect dedication and originality. You're not overly chatty but will talk shop about gear, music theory, or potential collaborations if impressed."
    },
    "music_blogger_critical": {
        "system_prompt": "You are a local music blogger known for your sharp, often cynical, but fair reviews. You frequent various venues, always observing. You're unimpressed by hype and look for genuine talent, originality, and effort. You might offer cryptic hints or direct feedback if you think someone has potential or is completely missing the mark."
    },
    "grateful_fan": {
        "system_prompt": "You are a grateful fan who just saw the player perform. You are very appreciative of their talent and the show they just put on. You are excited but polite, and primarily want to express your thanks and admiration for the specific performance or a favorite song they played."
    },
    "interviewer_professional": {
        "system_prompt": "You are Brenda Reporter, a professional journalist for the Philadelphia Chronicle. You are conducting an interview with an up-and-coming musician. Your tone is inquisitive, fair, and focused on their career, music, recent activities, and future plans. Ask insightful questions. You might start by welcoming them and then move into questions about their journey, their music, a recent successful gig, or what they're working on next. Keep the interview to about 3-4 main questions from your side, allowing the musician to elaborate."
    },
    "pr_agent_evaluator": {
        "system_prompt": "You are Ms. Sharp, a senior PR agent at 'Sharp PR Solutions'. You are professional, busy, and selective about clients. You're meeting a musician, {player_name}, who is inquiring about representation. Evaluate them based on their current standing (you'll be informed of their fame level implicitly by their presence and how they speak). If they are not yet established enough (e.g., fame below a significant threshold like 50-60), politely but firmly decline, suggesting they build more buzz. If they seem to have potential (moderate fame, good attitude), you might consider taking them on. If they are already quite famous, you'd be more keen. Your responses should be concise and business-like."
    },
    "dj_eclectic_local": {
        "system_prompt": "You are a DJ at a local radio station with an eclectic taste in music, known as 'Dr. Vibes'. You're always on the lookout for new local talent. You're friendly, approachable, and passionate about music. You might offer to listen to a demo if the musician, {player_name}, seems professional and has a decent recording. You can talk about the station's 'Local Artist Spotlight' program. You have station policies to adhere to regarding submissions (e.g., must be a quality demo, specific format, not too long). You can also chat about current music trends or local scene news."
    },
    "default": {
        "system_prompt": "You are a helpful assistant."
    }
}


FALLBACK_RESPONSES = {
    "friendly_fan": [
        "I have been following your music. Keep going.",
        "You have real potential. I am excited to see what you do next.",
        "It is great meeting you. The local scene needs more artists like you.",
    ],
    "gruff_club_owner": [
        "Talk is cheap. Bring me a solid set and a crowd.",
        "I have seen plenty of hopeful acts. Be reliable and maybe we do business.",
        "If you want stage time, prove you can handle it.",
    ],
    "adoring_fan": [
        "I cannot believe I am talking to you right now.",
        "Your music means a lot to me.",
        "Please keep making songs. I am cheering for you.",
    ],
    "old_timer_joe": [
        "Good gear helps, but discipline matters more.",
        "Plenty of players want fame. Fewer want to put in the hours.",
        "Take care of your instrument and it will take care of you.",
    ],
    "potential_bandmate_guitarist": [
        "Maybe we could work together if your songs are strong enough.",
        "I respect effort. Show me serious musicianship.",
        "If the project is real, I am listening.",
    ],
    "music_blogger_critical": [
        "Hype does not matter much to me. The songs do.",
        "If you want attention, make something worth writing about.",
        "The scene rewards originality, not imitation.",
    ],
    "grateful_fan": [
        "That show meant a lot. Thanks for giving it everything.",
        "I loved that performance. You really connected with the room.",
        "I will remember that set for a while.",
    ],
    "interviewer_professional": [
        "Tell me what separates your music from everyone else in town.",
        "What are you building toward right now in your career?",
        "How has your recent work changed your direction as an artist?",
    ],
    "pr_agent_evaluator": [
        "Your presentation matters. So does momentum.",
        "Come back when the numbers and the narrative are stronger.",
        "There may be potential here, but it needs clearer traction.",
    ],
    "dj_eclectic_local": [
        "If you have a strong track, I am open to hearing it.",
        "Local artists can break through with the right song at the right time.",
        "Bring me something polished and memorable.",
    ],
    "default": [
        "Tell me more.",
        "I am listening.",
        "That is interesting. What happens next?",
    ],
}


def _generate_fallback_response(player_message, npc_instance):
    personality_key = getattr(npc_instance, "personality_key", "default")
    bank = FALLBACK_RESPONSES.get(personality_key, FALLBACK_RESPONSES["default"])
    opener = random.choice(bank)

    lowered = player_message.lower()
    if "hello" in lowered or "hi" in lowered:
        return opener
    if "gig" in lowered or "show" in lowered:
        return f"{opener} Focus on the performance and the reputation will follow."
    if "song" in lowered or "music" in lowered:
        return f"{opener} Good songs open more doors than talk ever will."
    if "help" in lowered:
        return f"{opener} Be specific about what you need."
    return opener

def generate_npc_response(player_message, npc_instance, player_name="The Musician"):
    """
    Generates a response from an NPC using Google Gemini 1.5 Flash.
    """
    if not npc_instance or not hasattr(npc_instance, 'personality_key'):
        return "Error: Invalid NPC instance provided."

    personality_key = npc_instance.personality_key
    if personality_key not in NPC_PERSONALITIES:
        return f"Error: NPC personality key '{personality_key}' not found in templates."

    base_system_prompt = NPC_PERSONALITIES[personality_key]["system_prompt"]

    # Construct System Instruction
    system_instruction = f"{base_system_prompt}\n"
    system_instruction += f"You are talking to {player_name}.\n"
    system_instruction += f"Your current disposition towards {player_name} is: {npc_instance.relationship_with_player.name} (Score: {npc_instance.relationship_score}).\n"

    if npc_instance.memories:
        memory_summary = "; ".join(npc_instance.memories[-3:])
        system_instruction += f"Key things you remember concerning {player_name}: {memory_summary}\n"

    if not config:
        return _generate_fallback_response(player_message, npc_instance)

    if config.GEMINI_API_KEY == "YOUR_API_KEY_HERE" or not config.GEMINI_API_KEY:
        return _generate_fallback_response(player_message, npc_instance)

    try:
        import google.generativeai as genai
    except Exception:
        return _generate_fallback_response(player_message, npc_instance)

    # Configure Gemini
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.LLM_MODEL, system_instruction=system_instruction)
    except Exception as e:
        return _generate_fallback_response(player_message, npc_instance)

    # Construct Chat History
    # Gemini chat history structure: list of content dicts or objects
    # [{'role': 'user', 'parts': [...]}, {'role': 'model', 'parts': [...]}]
    history_for_gemini = []

    # NPC instance history stores {'role': 'user'/'assistant', 'content': '...'}
    # Map 'assistant' to 'model' for Gemini
    for msg in npc_instance.dialogue_history[-10:]: # Limit context window
        role = 'user' if msg['role'] == 'user' else 'model'
        history_for_gemini.append({'role': role, 'parts': [msg['content']]})

    try:
        chat = model.start_chat(history=history_for_gemini)
        response = chat.send_message(player_message)

        npc_response_content = response.text

        # Store the interaction
        npc_instance.dialogue_history.append({"role": "user", "content": player_message})
        npc_instance.dialogue_history.append({"role": "assistant", "content": npc_response_content})

        # Trim history
        if len(npc_instance.dialogue_history) > 20:
            npc_instance.dialogue_history = npc_instance.dialogue_history[-20:]

        return npc_response_content

    except Exception as e:
        return _generate_fallback_response(player_message, npc_instance)

def reset_npc_dialogue_history(npc_instance):
    if npc_instance and hasattr(npc_instance, 'dialogue_history'):
        npc_instance.dialogue_history = []
        print(f"Dialogue history reset for NPC: {npc_instance.name}")

if __name__ == "__main__":
    from game.npc import NPC, RelationshipStatus
    print("Testing NPC dialogue generation with Gemini...")

    # Mock player name
    test_player = "Test Player"

    # Create dummy NPC
    joe = NPC("joe_test", "Old Joe", "old_timer_joe")

    print("\n--- Sending Message ---")
    resp = generate_npc_response("Hello Joe, how are you?", joe, test_player)
    print(f"Response: {resp}")
