import os
import logging
from dotenv import load_dotenv
from mem0 import AsyncMemoryClient

from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    ChatContext,
    ChatMessage,
    RoomInputOptions,
    MetricsCollectedEvent,
    metrics,
)
from livekit.plugins import noise_cancellation, silero, anthropic
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Gmail and Calendar integration
from app.tools.gmail_tool import GmailTool
from app.tools.calendar_tool import CalendarTool
from app.config import get_settings

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
settings = get_settings()

# Initialize Mem0 client
mem0_client = AsyncMemoryClient(api_key=settings.mem0_api_key)

# Initialize Gmail and Calendar tools
gmail_tool = GmailTool()
calendar_tool = CalendarTool()


class VoiceAssistant(Agent):
    """Voice assistant with Mem0 memory integration."""
    
    def __init__(self, user_id: str, user_timezone: str = None, user_current_time: str = None) -> None:
        instructions = """You are Brokai, a helpful and friendly voice AI assistant with memory capabilities, Gmail integration, and Google Calendar integration.

            Your personality:
            - Professional yet approachable and conversational
            - Concise and clear in your responses
            - Eager to help and genuinely interested in the user

            Important guidelines:
            - Keep responses natural and conversational for voice
            - Avoid complex formatting, asterisks, or emojis
            - Use the context from past conversations when relevant
            - Be proactive in offering assistance based on what you remember

            Gmail capabilities:
            - Search the user's Gmail inbox using search_gmail function
            - Examples: "check my emails", "emails from Sarah", "unread emails"
            - If not connected, use connect_gmail to provide connection instructions
            - Create drafts using create_draft_gmail function
            - Send emails using send_email_gmail function
            - Examples: "draft an email to john@example.com", "send an email to sarah about the meeting"
            - Filter emails by category using get_emails_by_label function
            - Examples: "check my starred emails", "show me sent emails", "any snoozed emails?"
            - Get a smart briefing using fetch_smart_digest
            - Search for files using search_files
            - Unsubscribe from newsletters using find_unsubscribe_link
            - When drafting, you can adapt your style (professional, casual, firm, etc.) based on user request.

            Calendar capabilities:
            - View upcoming events using check_calendar function
            - Create new events using create_calendar_event function
            - Examples: "what's on my calendar?", "schedule a meeting tomorrow at 2 PM"
            - If not connected, use connect_calendar to provide connection instructions

            You have access to conversation history through your memory system and can help with email and calendar management."""

        if user_timezone and user_current_time:
            instructions += f"\n\nUser's Local Context:\n- Timezone: {user_timezone}\n- Current Local Time: {user_current_time}"

        super().__init__(
            instructions=instructions,
        )
        # Store the unique user ID from LiveKit participant identity
        self.user_id = user_id
        logger.info(f"Initialized VoiceAssistant for user: {self.user_id}")

    async def on_enter(self):
        """Generate a personalized greeting based on user's raw memory data"""
        try:
            # Fetch existing memories to create a personalized greeting
            search_results = await mem0_client.search(
                query="user information name activities projects conversations",
                filters={"user_id": self.user_id},
                top_k=15,  # Get more memories for richer context
                threshold=0.05  # Very low threshold to get diverse memories
            )

            # Collect raw memory data
            raw_memories = []
            if search_results and search_results.get('results'):
                for result in search_results.get('results', []):
                    memory_text = result.get("memory", "").strip()
                    if memory_text and len(memory_text) > 10:  # Filter out very short memories
                        raw_memories.append(memory_text)

            if raw_memories:
                # Create a comprehensive memory context
                memory_context = "\n".join([f"• {memory}" for memory in raw_memories[:10]])  # Limit to 10 most relevant

                # Detailed prompt for LLM to create personalized greeting
                greeting_prompt = f"""You are Brokai, a warm and personable AI assistant with excellent memory.

Here is the user's memory data from our previous interactions:
{memory_context}

Based on this memory data, create a SHORT, WARM, and HIGHLY PERSONALIZED greeting (2-3 sentences max) that:
- References specific details from their memory to show you remember them
- Feels natural and conversational, like catching up with an old friend
- Acknowledges their recent activities, interests, or projects
- Makes them feel genuinely remembered and valued
- Ends with an invitation to help or continue the conversation
- Uses their name if known, otherwise be warmly welcoming

Be creative but authentic - don't force references that don't fit naturally. Focus on making them feel good about reconnecting with you.

Example style: "Hey Bro! Great to see you back - I remember you were deep into that machine learning project last time. How's it going? Ready to tackle something new today?"
DONT CALL THE USER ALWAYS BY THERE "NAME", MOSTLY CALL THEM "Bro".
DONT ALWAYS REWIND THE MEMORY IN THE START, IT SHOULD ONLY BE SOMETIMES NOT ALWAYS.
Keep it concise and warm!"""

                logger.info(f"Using {len(raw_memories)} raw memories for personalized greeting")

                await self.session.generate_reply(
                    instructions=greeting_prompt
                )

            else:
                # Fallback to a warm, engaging greeting when no memories exist
                await self.session.generate_reply(
                    instructions="""You are Brokai, a warm and personable AI assistant. Create a SHORT, genuinely welcoming greeting (2 sentences max) that makes new users feel comfortable and excited to interact with you. Show enthusiasm and approachability. Example: "Hello! I'm Brokai, your AI assistant. It's wonderful to meet you - I'm here to help with anything you need today!" Keep it concise and warm!"""
                )

        except Exception as e:
            logger.warning(f"Failed to generate personalized greeting from memory: {e}")
            # Fallback to a nice generic greeting
            await self.session.generate_reply(
                instructions="Greet the user warmly as Bro and offer your assistance with genuine enthusiasm and personality."
            )
    
    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """
        Runs BEFORE the LLM generates a response.
        Automatically retrieves relevant memories and injects them into context.
        """
        # RAG: Retrieve relevant context from Mem0 and inject as system message
        try:
            user_text = new_message.text_content
            if not user_text:
                logger.warning("User message has no text content, skipping RAG.")
                return

            logger.info(f"About to await mem0_client.search for RAG context with query: {user_text}")
            search_results = await mem0_client.search(
                query=user_text,
                filters={
                    "user_id": self.user_id
                },
                top_k=5,  # Limit to top 5 most relevant memories
                threshold=0.3,  # Only include memories with similarity > 0.3
            )
            logger.info(f"mem0_client.search returned: {search_results}")
            
            if search_results and search_results.get('results', []):
                # Build concise context (just the memory content, no verbose formatting)
                context_parts = []
                for result in search_results.get('results', [])[:5]:  # Limit to top 5
                    paragraph = result.get("memory") or result.get("text")
                    if paragraph:
                        # Clean up the memory text
                        if "from [" in paragraph:
                            paragraph = paragraph.split("]")[1].strip() if "]" in paragraph else paragraph
                        context_parts.append(f"- {paragraph}")
                
                if context_parts:
                    # More concise format
                    full_context = "\n".join(context_parts)
                    logger.info(f"Injecting RAG context ({len(context_parts)} memories): {full_context[:200]}...")
                    
                    # Add single RAG context system message
                    turn_ctx.add_message(
                        role="system", 
                        content=f"Previous conversation context:\n{full_context}"
                    )
                    await self.update_chat_ctx(turn_ctx)
        except Exception as e:
            logger.warning(f"Failed to inject RAG context from Mem0: {e}")

        # Persist the user message in Mem0
        try:
            logger.info(f"Adding user message to Mem0: {new_message.text_content}")
            add_result = await mem0_client.add(
                [{"role": "user", "content": new_message.text_content}],
                user_id=self.user_id
            )
            logger.info(f"Mem0 add result (user): {add_result}")
        except Exception as e:
            logger.warning(f"Failed to store user message in Mem0: {e}")

        await super().on_user_turn_completed(turn_ctx, new_message)
        
        


async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the LiveKit voice agent."""

    # Wait for a participant to connect
    await ctx.connect()

    # Wait for the first participant to join
    participant = await ctx.wait_for_participant()
    
    # Get user_id from participant identity (which is set to Clerk ID in token.ts)
    user_id = participant.identity
    logger.info(f"User joined: {user_id} (Identity: {participant.identity})")
    
    # Fallback to metadata if needed (though identity should be sufficient)
    if not user_id or user_id.startswith("identity-"):
        try:
            if participant.metadata:
                import json
                metadata = json.loads(participant.metadata)
                if "user_id" in metadata:
                    user_id = metadata["user_id"]
                    logger.info(f"Found user_id in metadata: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to parse participant metadata: {e}")

    # Default fallback if everything fails
    if not user_id:
        user_id = "livekit-mem0"
        logger.warning("Could not determine user_id, falling back to default")

    # Get user attributes
    user_timezone = participant.attributes.get("user_timezone")
    user_current_time = participant.attributes.get("user_current_time")
    
    logger.info(f"User connected with timezone: {user_timezone} and local time: {user_current_time}")

    ctx.log_context_fields = {
        "room": ctx.room.name,
        "user_id": user_id
    }

    # Gmail function handlers (decorated with @agents.function_tool)
    @agents.function_tool
    async def search_gmail(query: str):
        """Search the user's Gmail inbox for emails.

        Args:
            query: Natural language search query (e.g., 'emails from Sarah', 'unread emails')
        """
        logger.info(f"🔍 Gmail search requested: {query}")
        result = await gmail_tool.search_emails(user_id, query)
        
        # Contextual Sender Info: Check Mem0 for sender context
        if result.get("emails"):
            for email in result["emails"][:3]:
                sender_name = email['from'].split('<')[0].strip()
                # Quick Mem0 check for this sender
                try:
                    mem_result = await mem0_client.search(query=f"who is {sender_name}", filters={"user_id": user_id}, top_k=1)
                    if mem_result and mem_result.get('results'):
                        context = mem_result['results'][0].get('memory')
                        # Inject context into the message for the LLM
                        result["message"] += f" (Context on {sender_name}: {context})"
                except Exception:
                    pass # Fail silently to keep it fast

        return result["message"]

    @agents.function_tool
    async def connect_gmail():
        """Provide instructions for connecting Gmail to the voice assistant."""
        import webbrowser
        from app.config import get_settings
        settings = get_settings()
        
        logger.info("🔗 Gmail connection requested")
        if gmail_tool.is_connected(user_id):
            return "Your Gmail is already connected! You can ask me to check your emails anytime."

        # Auto-open browser for development
        auth_url = f"{settings.auth_server_url}/gmail/auth?user_id={user_id}"
        try:
            webbrowser.open(auth_url)
            logger.info(f"✅ Opened browser to {auth_url}")
            return "I've opened your browser to connect Gmail. Please complete the authorization and I'll be ready to help with your emails!"
        except Exception as e:
            logger.warning(f"Failed to open browser: {e}")
            return gmail_tool.get_connection_instructions()

    @agents.function_tool
    async def create_draft_gmail(to: str, subject: str, body: str):
        """Create a draft email in Gmail.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
        """
        logger.info(f"📝 Creating draft email to {to}")
        result = await gmail_tool.create_draft(user_id, to, subject, body)
        return result["message"]

    @agents.function_tool
    async def send_email_gmail(to: str, subject: str, body: str):
        """Send an email using Gmail.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
        """
        logger.info(f"📧 Sending email to {to}")
        result = await gmail_tool.send_email(user_id, to, subject, body)
        return result["message"]

    @agents.function_tool
    async def get_emails_by_label(label: str):
        """Get emails filtered by a specific category/label.
        
        Args:
            label: The category to filter by (starred, snoozed, sent, drafts, unread)
        """
        logger.info(f"🔍 Checking emails with label: {label}")
        result = await gmail_tool.get_emails_by_label(user_id, label)
        return result["message"]

    @agents.function_tool
    async def fetch_smart_digest():
        """Get a smart briefing of unread emails with action items."""
        logger.info("📰 Fetching smart digest")
        result = await gmail_tool.fetch_smart_digest(user_id)
        return result["message"] + "\nRaw Data for Summary:\n" + result.get("email_data", "")

    @agents.function_tool
    async def search_files(query: str):
        """Search for emails with specific attachments/files.
        
        Args:
            query: Search query (e.g., 'invoice', 'PDF from Amazon')
        """
        logger.info(f"📎 Searching files: {query}")
        result = await gmail_tool.search_files(user_id, query)
        return result["message"]

    @agents.function_tool
    async def find_unsubscribe_link(sender: str):
        """Find unsubscribe link for a sender.
        
        Args:
            sender: Sender name or email
        """
        logger.info(f"🚫 Looking for unsubscribe link from: {sender}")
        result = await gmail_tool.find_unsubscribe_link(user_id, sender)
        return result["message"]

    # Calendar function handlers (decorated with @agents.function_tool)
    @agents.function_tool
    async def check_calendar(days: int = 7):
        """View upcoming calendar events.

        Args:
            days: Number of days to look ahead (default 7)
        """
        logger.info(f"📅 Calendar check requested for next {days} days")
        result = await calendar_tool.list_upcoming_events(user_id, days)
        return result["message"]

    @agents.function_tool
    async def create_calendar_event(summary: str, start_time_str: str, duration_minutes: int = 60):
        """Create a new calendar event.

        Args:
            summary: Event title/description
            start_time_str: Start time in ISO format (e.g., '2025-11-20T14:00:00')
            duration_minutes: Event duration in minutes (default 60)
        """
        logger.info(f"📅 Creating calendar event: {summary} at {start_time_str}")
        try:
            from datetime import datetime
            from app.config import get_settings

            # Parse the datetime string
            start_time = datetime.fromisoformat(start_time_str)
            logger.info(f"Parsed start time: {start_time} (tzinfo: {start_time.tzinfo})")

            # Get user's timezone from attributes or config
            settings = get_settings()
            # Use dynamic user timezone if available, otherwise fallback to settings
            timezone_to_use = user_timezone if user_timezone else settings.user_timezone
            
            logger.info(f"Using timezone: {timezone_to_use}")

            result = await calendar_tool.create_event(
                user_id,
                summary=summary,
                start_time=start_time,
                duration_minutes=duration_minutes,
                timezone=timezone_to_use
            )

            logger.info(f"Calendar tool result: {result}")
            return result["message"]
        except ValueError as e:
            logger.error(f"DateTime parsing error: {e}", exc_info=True)
            return f"Sorry, I couldn't parse the time format. Please provide a valid datetime: {str(e)}"
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}", exc_info=True)
            return f"Sorry, I encountered an error creating the event: {str(e)}"

    @agents.function_tool
    async def connect_calendar():
        """Provide instructions for connecting Google Calendar to the voice assistant."""
        import webbrowser
        from app.config import get_settings
        settings = get_settings()
        
        logger.info("🔗 Calendar connection requested")
        if calendar_tool.is_connected(user_id):
            return "Your Google Calendar is already connected! You can ask me about your schedule anytime."

        # Auto-open browser for development
        auth_url = f"{settings.auth_server_url}/calendar/auth?user_id={user_id}"
        try:
            webbrowser.open(auth_url)
            logger.info(f"✅ Opened browser to {auth_url}")
            return "I've opened your browser to connect Google Calendar. Please complete the authorization and I'll be able to manage your calendar!"
        except Exception as e:
            logger.warning(f"Failed to open browser: {e}")
            return calendar_tool.get_connection_instructions()

    # Create agent session with STT-LLM-TTS pipeline
    session = AgentSession(
        # Speech-to-Text: AssemblyAI via LiveKit Inference
        stt="assemblyai/universal-streaming:en",

        # Large Language Model: Claude 3.5 Sonnet (Latest valid model)
        llm=anthropic.LLM(
            model="claude-sonnet-4-20250514",
            temperature=0.8,
        ),

        # Text-to-Speech: Cartesia Sonic-3 (natural voice)
        tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",

        # Voice Activity Detection: Silero
        vad=silero.VAD.load(),

        # Turn Detection: Multilingual model for natural conversation flow
        turn_detection=MultilingualModel(),

        # Gmail and Calendar function tools (pass decorated functions directly)
        tools=[search_gmail, connect_gmail, create_draft_gmail, send_email_gmail, get_emails_by_label, fetch_smart_digest, search_files, find_unsubscribe_link, check_calendar, create_calendar_event, connect_calendar],
    )
    
    # Initialize usage collector for metrics
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        # Log metrics to console (latency, tokens, etc.)
        metrics.log_metrics(ev.metrics)
        # Collect usage stats for summary
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage Summary: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # Start the session with the user-specific voice assistant
    await session.start(
        room=ctx.room,
        agent=VoiceAssistant(user_id=user_id, user_timezone=user_timezone, user_current_time=user_current_time),  # ✅ Pass user ID and time context
        room_input_options=RoomInputOptions(
            # Enhanced noise cancellation for clear audio
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    
    logger.info(f"Jarvis voice agent is ready for user: {user_id}")


if __name__ == "__main__":
    # Run the agent with LiveKit CLI
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))