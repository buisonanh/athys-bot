import discord
import asyncio
from google import genai
from google.genai import types
import config
import prompt as prompt_config

# Global variable to store message history (channel_id: [messages])
message_history = {}
MAX_HISTORY_LENGTH = 4  # Store last N items (user messages and bot responses)


def generate(current_user_message_content, previous_history_list, sender_name, sender_mention):
    client = genai.Client(
        api_key=config.GEMINI_API_KEY,
    )

    model_name_from_user = "gemini-2.0-flash" # As per user's existing code

    # Format the history part for the prompt template
    history_str = "\n".join(previous_history_list)

    # Format the user-specific part of the prompt using USER_PROMPT template
    formatted_user_centric_prompt = prompt_config.USER_PROMPT.format(
        sender_name=sender_name,
        sender_mention=sender_mention,
        user_prompt=current_user_message_content,
        history=history_str
    )

    # Prepend the SYSTEM_PROMPT to the formatted_user_centric_prompt
    final_prompt_for_model = f"{prompt_config.SYSTEM_PROMPT}\n\n{formatted_user_centric_prompt}"

    print(final_prompt_for_model)
    contents = [
        types.Content(
            role="user", # System prompt is embedded within the user role text
            parts=[
                types.Part.from_text(text=final_prompt_for_model),
            ],
        ),
    ]
    generation_config_obj = types.GenerateContentConfig(
        response_mime_type="text/plain",
    )

    response = client.models.generate_content(
        model=model_name_from_user,
        contents=contents,
        config=generation_config_obj,
    )
    return response.text




intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    print(f"--- on_message triggered by: {message.author.name} in channel {message.channel.name} ({message.channel.id}) ---")
    if message.author == client.user:
        return

    channel_id = message.channel.id
    if channel_id not in message_history:
        message_history[channel_id] = []

    # Add user's message to history, prefixed
    message_history[channel_id].append(f"User: {message.content}")

    # Trim history if it's too long
    if len(message_history[channel_id]) > MAX_HISTORY_LENGTH:
        message_history[channel_id] = message_history[channel_id][-MAX_HISTORY_LENGTH:]

    if client.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        # User's direct message to the bot (after removing mention)
        # Use client.user.mention for robust removal of bot's own mention
        user_direct_prompt_content = message.content.replace(client.user.mention, '').strip()
        
        if not user_direct_prompt_content:
            # If only a mention with no extra text, or empty message after stripping mention
            current_user_actual_content = "Hello!" 
        else:
            current_user_actual_content = user_direct_prompt_content

        # message_history[channel_id] includes the current user's message as the last item.
        # For the {history} template variable, we need messages *before* the current one.
        previous_history_for_template = message_history[channel_id][:-1]

        print(f"Received mention/DM in channel {channel_id}. User's actual content after stripping mention: '{current_user_actual_content}'")
        # print(f"History for prompt: {previous_history_for_template}") # Potentially long

        try:
            async with message.channel.typing():
                # Run the blocking generate function in a separate thread
                bot_response_text = await asyncio.to_thread(
                    generate,
                    current_user_actual_content,
                    previous_history_for_template,
                    message.author.name,
                    message.author.mention
                )
                await message.reply(bot_response_text)

                # Add bot's response to history, prefixed
                message_history[channel_id].append(f"Bot: {bot_response_text}")
                # Trim history again after adding bot's response
                if len(message_history[channel_id]) > MAX_HISTORY_LENGTH:
                    message_history[channel_id] = message_history[channel_id][-MAX_HISTORY_LENGTH:]

        except Exception as e:
            print(f"Error calling Gemini API or processing response: {e}")
            await message.reply(f"Sorry, I encountered an error while trying to respond. Please try again later.")
    # else:
        # If not mentioned and not a DM, the message was already added to history for context.
        # No direct response is generated in this case.
        pass

if __name__ == "__main__":
    if config.DISCORD_BOT_TOKEN:
        client.run(config.DISCORD_BOT_TOKEN)
    else:
        print("Discord bot token not found. Please set DISCORD_BOT_TOKEN in your .env file.")
