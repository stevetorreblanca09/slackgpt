import os
import openai
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

SLACK_BOT_TOKEN = "xoxb-5252412705844-5248182524389-aCutGhlfDrKadLl9mGHMudOJ"
SLACK_APP_TOKEN = "xapp-1-A057CTMTT7V-5253573451860-d234d9176a898b09cf269e44aaad7c5715d75293214289fcc63aa47e6f657c91"
OPENAI_API_KEY  = "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"

# Initialize the Slack API client and OpenAI API client
slack_client = WebClient(token=SLACK_BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

# Initialize the conversation dictionary to keep track of context for each user
conversation_dict = {}

# Define your bot's persona
bot_persona = {
    "name": "Ada",
    "backstory": "Ada was created by Steven Torres. Her mission is to assist users with a wide range of tasks, from answering questions to providing personalized recommendations.",
    "responses": {
        "greeting": ["Hi there!", "Hello!", "Hey, how can I help you today?"],
        "thanks": ["You're welcome!", "No problem!", "Happy to help!"],
        "farewell": ["Goodbye!", "Bye!", "See you later!"],
        "default": ["I'm sorry, I don't know how to respond to that.", "I'm not sure what you mean.", "Could you please rephrase that?"],
    }
}

# Define a function to generate a persona response
def generate_persona_response(prompt):
    # Get a response from OpenAI based on the user's prompt
    openai_response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5
    )
    # Parse the response from the OpenAI API
    output_text = openai_response.choices[0].text.strip()
    # Choose a pre-defined response based on the bot's persona
    if "hello" in prompt.lower() or "hi" in prompt.lower():
        output_text = bot_persona["responses"]["greeting"][0]
    elif "thank" in prompt.lower() or "appreciate" in prompt.lower():
        output_text = bot_persona["responses"]["thanks"][0]
    elif "goodbye" in prompt.lower() or "bye" in prompt.lower():
        output_text = bot_persona["responses"]["farewell"][0]
    else:
        if not output_text:
            output_text = bot_persona["responses"]["default"][0] # default response if no response is generated
    return output_text

# Initialize the Slack Bolt app
app = App(token=SLACK_BOT_TOKEN)

# Handle app mentions
@app.event("app_mention")
def handle_app_mention(event, say):
    # Get the user ID, channel ID, and message text
    user_id = event["user"]
    channel_id = event["channel"]
    message_text = event["text"].replace("<@U01U23F1LTL>", "").strip()

    # If the user has an existing conversation context, append the message to it
    if user_id in conversation_dict:
        conversation_dict[user_id].append(message_text)
        prompt = "\n".join(conversation_dict[user_id])
    else:
        # Otherwise, start a new conversation
        prompt = message_text
        conversation_dict[user_id] = []

    # Send a message to the user to let them know we're processing their request
    try:
        response = slack_client.conversations_open(users=user_id)
        channel = response["channel"]["id"]
        slack_client.chat_postMessage(channel=channel, text="One moment please, processing your request...")
    except SlackApiError as e:
        print("Error opening conversation: {}".format(e))

    # Call the OpenAI API to get a response to the user's message
    openai_response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5
    )

    # Parse the response from the OpenAI API and send it to the user
    output_text = openai_response.choices[0].text.strip()

    # If the output is empty, send a default response
    if not output_text:
        output_text = "I'm sorry, I don't know how to respond to that."

    # Personalize the conversation by using the user's name or username
    if "name" in conversation_dict[user_id]:
        output_text = output_text.replace("name", conversation_dict[user_id]["name"])
    elif "username" in conversation_dict[user_id]:
        output_text = output_text.replace("username", conversation_dict[user_id]["username"])

    # Use natural langu age that is more conversational and less formal
    output_text = output_text.replace("I think", "Maybe")
    output_text = output_text.replace("you should", "maybe try")
    output_text = output_text.replace("you seem", "It seems like")

    # Send the response back to the user
    say(output_text)

    # Update the conversation dictionary with the latest message
    if user_id in conversation_dict:
            if conversation_dict[user_id]:
                conversation_dict[user_id][-1] = output_text
            else:
                conversation_dict[user_id].append(output_text)
    else:
            conversation_dict[user_id] = [message_text, output_text]

# Start the Socket Mode handler
if __name__ == "__main__":
    handler = SocketModeHandler(app_token=SLACK_APP_TOKEN, app=app)
    handler.start()