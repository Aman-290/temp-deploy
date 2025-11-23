"""Calendar Manager - Simple wrapper for voice agent integration"""
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.services.calendar_service import CalendarService
from app.utils.token_storage import TokenStorage
from app.utils.logger import get_logger

logger = get_logger("calendar_tool")

class CalendarTool:
    """Manages Google Calendar operations for voice assistant"""

    def __init__(self):
        """Initialize Calendar tool"""
        self.service = CalendarService()
        # Use centralized token storage
        self.token_storage = TokenStorage()

    def is_connected(self, user_id: str) -> bool:
        """Check if user has Calendar connected"""
        return self.token_storage.has_token(user_id, "calendar")

    async def list_upcoming_events(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """List upcoming calendar events

        Args:
            user_id: User identifier
            days: Number of days to look ahead (default 7)

        Returns:
            Dictionary with success status and formatted message
        """
        try:
            if not self.is_connected(user_id):
                return {
                    "success": False,
                    "message": "Calendar is not connected. Please connect your Google Calendar first by visiting localhost:8000/calendar/auth",
                    "events": []
                }

            token_json = self.token_storage.get_token(user_id, "calendar")
            credentials = self.service.get_credentials_from_token(token_json)

            time_max = datetime.utcnow() + timedelta(days=days)
            events = await self.service.list_events(
                credentials,
                time_min=datetime.utcnow(),
                time_max=time_max,
                max_results=10
            )

            if not events:
                return {
                    "success": True,
                    "message": f"You have no upcoming events in the next {days} days.",
                    "events": []
                }

            # Format voice-friendly response
            message = f"You have {len(events)} upcoming event"
            if len(events) > 1:
                message += "s"
            message += ". "

            for i, event in enumerate(events[:3], 1):
                summary = event['summary']
                start = event['start']
                # Parse and format datetime
                try:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    time_str = start_dt.strftime("%A at %I:%M %p")
                except:
                    time_str = start

                message += f"Event {i}: {summary}, {time_str}. "

            if len(events) > 3:
                message += f"And {len(events) - 3} more."

            return {
                "success": True,
                "message": message,
                "events": events
            }

        except Exception as e:
            logger.error(f"Error listing events: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Sorry, I encountered an error while checking your calendar: {str(e)}",
                "events": []
            }

    async def create_event(
        self,
        user_id: str,
        summary: str,
        start_time: datetime,
        duration_minutes: int = 60,
        description: str = "",
        timezone: str = "America/Los_Angeles"
    ) -> Dict[str, Any]:
        """Create a calendar event

        Args:
            user_id: User identifier
            summary: Event title
            start_time: Event start time
            duration_minutes: Event duration in minutes
            description: Event description
            timezone: Timezone for the event (default: America/Los_Angeles)

        Returns:
            Dictionary with success status and message
        """
        try:
            logger.info(f"📅 Creating event for user {user_id}: '{summary}' at {start_time}")

            if not self.is_connected(user_id):
                logger.warning(f"User {user_id} is not connected to Calendar")
                return {
                    "success": False,
                    "message": "Calendar is not connected. Please connect your Google Calendar first.",
                }

            token_json = self.token_storage.get_token(user_id, "calendar")
            credentials = self.service.get_credentials_from_token(token_json)

            end_time = start_time + timedelta(minutes=duration_minutes)

            logger.info(f"Creating event: {summary}, Start: {start_time}, End: {end_time}, TZ: {timezone}")

            event = await self.service.create_event(
                credentials,
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                timezone=timezone
            )

            if not event:
                logger.error("Calendar API returned None - event creation failed!")
                return {
                    "success": False,
                    "message": "Failed to create the event. Please check the logs for details."
                }

            logger.info(f"✅ Event created successfully: {event.get('id')} - {event.get('link')}")

            time_str = start_time.strftime("%A, %B %d at %I:%M %p")
            event_link = event.get('link', '')

            return {
                "success": True,
                "message": f"I've created an event called '{summary}' for {time_str}. You can view it in your Google Calendar.",
                "event": event
            }

        except Exception as e:
            logger.error(f"❌ Error creating event: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Sorry, I couldn't create the event: {str(e)}"
            }

    def get_connection_instructions(self) -> str:
        """Get instructions for connecting Calendar"""
        return (
            "To connect your Google Calendar, please use the 'Connect Calendar' button in the Jarvis dashboard."
        )
