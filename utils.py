from fuzzywuzzy import fuzz, process
import random

def fuzzy_search(query, choices, limit=5, threshold=60):
    """
    Perform fuzzy search on a list of choices
    """
    results = process.extract(query, choices, limit=limit, scorer=fuzz.partial_ratio)
    return [result for result in results if result[1] >= threshold]

def format_results(results, private_mode=False, private_link=""):
    """
    Format search results for display
    """
    if not results:
        return None
    
    formatted = "Powered By @ChannelName\nHere are the results 👇\n\n"
    
    for result in results:
        post_title = result.get('caption', 'No Title')[:50] + "..." if len(result.get('caption', '')) > 50 else result.get('caption', 'No Title')
        message_id = result.get('message_id', '')
        
        if private_mode and private_link:
            post_link = f"{private_link}/{message_id}"
        else:
            post_link = f"https://t.me/c/{str(result.get('channel_id', ''))[4:]}/{message_id}"
        
        formatted += f"♻️ **{post_title}**\n🔗 [Post Link]({post_link})\n\n---\n\n"
    
    return formatted

def get_random_emoji():
    """
    Return a random emoji for reactions
    """
    emojis = ["👍", "❤️", "🔥", "🎯", "⭐", "👏", "🙌", "💯"]
    return random.choice(emojis)
