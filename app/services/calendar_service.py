"""Google Calendar Service - OAuth and Calendar Operations"""
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, List, Dict
import json
from datetime import datetime, timedelta
from app.utils.logger import get_logger
from app.config import get_settings

# Relax OAuth scope validation to allow shared OAuth clients
# This allows the same OAuth client to be used for both Gmail and Calendar
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

logger = get_logger()

class CalendarService:
    SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events'
    ]

    def __init__(self):
        settings = get_settings()
        self.client_id = settings.calendar_client_id
        self.client_secret = settings.calendar_client_secret
        self.redirect_uri = settings.calendar_redirect_uri
        self._oauth_states: Dict[str, str] = {}

    def get_user_id_by_state(self, state: str) -> Optional[str]:
        """Find user_id by OAuth state"""
        for user_id, stored_state in self._oauth_states.items():
            if stored_state == state:
                return user_id
        return None

    def get_authorization_url(self, user_id: str) -> str:
        """Get OAuth authorization URL with state for CSRF protection"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.SCOPES
        )
        flow.redirect_uri = self.redirect_uri

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        self._oauth_states[user_id] = state
        logger.info(f"Generated Calendar auth URL for user {user_id}")
        return authorization_url

    async def handle_oauth_callback(self, code: str, state: str, user_id: str) -> str:
        """Handle OAuth callback and return token JSON with state validation"""
        if user_id not in self._oauth_states:
            raise ValueError("OAuth state not found. Please restart the authorization flow.")

        if self._oauth_states[user_id] != state:
            del self._oauth_states[user_id]
            raise ValueError("Invalid OAuth state. Possible CSRF attack.")

        del self._oauth_states[user_id]

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.SCOPES
        )
        flow.redirect_uri = self.redirect_uri

        flow.fetch_token(code=code)

        credentials = flow.credentials

        if credentials.refresh_token:
            logger.info(f"Successfully obtained refresh_token for user {user_id}")
        else:
            logger.warning(f"No refresh_token received for user {user_id}")

        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }

        return json.dumps(token_data)

    def get_credentials_from_token(self, token: str) -> Credentials:
        """Get credentials from stored token and refresh if needed"""
        token_data = json.loads(token)
        credentials = Credentials.from_authorized_user_info(token_data)

        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                logger.info("Successfully refreshed expired Calendar credentials")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}", exc_info=True)
                raise ValueError("Calendar credentials expired and could not be refreshed.")

        return credentials

    def validate_credentials(self, credentials: Credentials) -> bool:
        """Validate credentials"""
        try:
            if not credentials.token:
                return False
            if credentials.expired and not credentials.refresh_token:
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating credentials: {e}")
            return False

    def build_service(self, credentials: Credentials):
        """Build Calendar service from credentials"""
        return build('calendar', 'v3', credentials=credentials)

    async def list_events(
        self,
        credentials: Credentials,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10
    ) -> List[Dict]:
        """List calendar events"""
        try:
            service = self.build_service(credentials)

            if not time_min:
                time_min = datetime.utcnow()
            if not time_max:
                time_max = time_min + timedelta(days=7)

            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            event_list = []

            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                event_list.append({
                    "id": event['id'],
                    "summary": event.get('summary', 'No title'),
                    "start": start,
                    "end": event['end'].get('dateTime', event['end'].get('date')),
                    "description": event.get('description', ''),
                    "location": event.get('location', '')
                })

            return event_list
        except HttpError as e:
            logger.error(f"Error listing events: {e}", exc_info=True)
            return []

    async def create_event(
        self,
        credentials: Credentials,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: str = "",
        location: str = "",
        timezone: str = "America/Los_Angeles"
    ) -> Optional[Dict]:
        """Create a calendar event

        Args:
            credentials: Google Calendar credentials
            summary: Event title
            start_time: Event start time (naive or timezone-aware datetime)
            end_time: Event end time (naive or timezone-aware datetime)
            description: Event description
            location: Event location
            timezone: Timezone for the event (default: America/Los_Angeles)
        """
        try:
            service = self.build_service(credentials)

            # If datetime is naive (no timezone), treat it as local time in specified timezone
            # If datetime is timezone-aware, convert to ISO with timezone
            if start_time.tzinfo is None:
                # Naive datetime - use specified timezone
                start_dt_str = start_time.isoformat()
                end_dt_str = end_time.isoformat()
                logger.info(f"Creating event with naive datetime. Using timezone: {timezone}")
            else:
                # Timezone-aware datetime - use its timezone
                start_dt_str = start_time.isoformat()
                end_dt_str = end_time.isoformat()
                timezone = str(start_time.tzinfo)
                logger.info(f"Creating event with timezone-aware datetime: {timezone}")

            event = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_dt_str,
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_dt_str,
                    'timeZone': timezone,
                },
            }

            logger.info(f"Creating event with payload: {event}")

            created_event = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            logger.info(f"✅ Successfully created event: {created_event.get('id')} - {created_event.get('htmlLink')}")
            return {
                "id": created_event['id'],
                "summary": created_event.get('summary'),
                "start": created_event['start'].get('dateTime'),
                "link": created_event.get('htmlLink')
            }
        except HttpError as e:
            logger.error(f"❌ HTTP Error creating event: {e}", exc_info=True)
            logger.error(f"Error details: {e.resp.status} - {e.content}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error creating event: {e}", exc_info=True)
            return None

    async def update_event(
        self,
        credentials: Credentials,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> Optional[Dict]:
        """Update a calendar event"""
        try:
            service = self.build_service(credentials)

            # Get existing event
            event = service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()

            # Update fields
            if summary:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if start_time:
                event['start'] = {'dateTime': start_time.isoformat(), 'timeZone': 'UTC'}
            if end_time:
                event['end'] = {'dateTime': end_time.isoformat(), 'timeZone': 'UTC'}

            updated_event = service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()

            logger.info(f"Updated event: {event_id}")
            return {
                "id": updated_event['id'],
                "summary": updated_event.get('summary'),
                "start": updated_event['start'].get('dateTime')
            }
        except HttpError as e:
            logger.error(f"Error updating event: {e}", exc_info=True)
            return None

    async def delete_event(self, credentials: Credentials, event_id: str) -> bool:
        """Delete a calendar event"""
        try:
            service = self.build_service(credentials)
            service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            logger.info(f"Deleted event: {event_id}")
            return True
        except HttpError as e:
            logger.error(f"Error deleting event: {e}", exc_info=True)
            return False
