from datetime import datetime, timezone
from zoneinfo import ZoneInfo   # from Python 3.9
from pathlib import Path
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger("dchanbot.cogs.schednotifier.gcalendar")

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

class GCalenderClient:
    """A client for accessing Google Calendar via the Calendar API.

    Provides methods to authenticate, check availability, fetch events, and convert datetime objects.
    """

    def __init__(self):
        """Initializes an unauthenticated Google Calendar client."""
        self._creds = None
        self._service = None

    def is_enable(self) -> bool:
        """Checks whether the client is authorized and ready to use the API.

        Returns:
            bool: True if the Calendar API service is available, False otherwise.
        """
        return self._service is not None

    def authorize(
        self,
        reflesh_token_path : Path,
        client_secrets_path : Path
    ):
        """Performs OAuth2 authorization using stored credentials or user login.

        Args:
            reflesh_token_path (Path): Path to the file where the refresh token is stored or will be saved.
            client_secrets_path (Path): Path to the client_secrets.json file from Google Cloud Console.
        """
        if self._creds is not None:
            return
        
        # 1. Load refresh token from file if it exists
        if reflesh_token_path.exists():
            self._creds = Credentials.from_authorized_user_file(
                filename = str(reflesh_token_path),
                scopes = SCOPES
            )

        # 2. If not loaded or invalid, perform OAuth flow
        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                # Refresh expired credentials
                self._creds.refresh(Request())
            else:
                # Launch OAuth browser-based flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file = str(client_secrets_path),
                    scopes = SCOPES
                )
                self._creds = flow.run_local_server(port=0)

            # Save new credentials to file
            with reflesh_token_path.open(mode="w") as token:
                token.write(self._creds.to_json())
        
    def build(self) -> bool:
        """Initializes the Google Calendar API service using stored credentials.

        Returns:
            bool: True if the service was successfully built, False otherwise.
        """
        if self._creds is not None:
            self._service = build("calendar", "v3", credentials=self._creds)
        return (self._service is not None)

    def list_events(
        self, 
        calendarId : str,
        timeMin : datetime,
        timeMax : datetime
    ) -> list:
        """Retrieves a list of events within a specified time range.

        Args:
            calendarId (str): The ID of the calendar to retrieve events from.
            timeMin (datetime): The start of the time range (inclusive).
            timeMax (datetime): The end of the time range (exclusive).

        Returns:
            list: A list of event objects, or None if an error occurs.

        Raises:
            ValueError: If timeMin is later than or equal to timeMax.
        """
        if self._service is None:
            return ""

        if timeMin >= timeMax:
            raise ValueError("dateMin must be less than dateMax")

        try:
            # Call the Calendar API
            event_result = self._service.events().list(
                calendarId = calendarId,
                orderBy = "startTime",      # Sort by event start time
                singleEvents = True,
                maxResults = 100,           # Limit to 100 events
                timeMin = self._to_utc_string(timeMin),
                timeMax = self._to_utc_string(timeMax)
            ).execute()
            events = event_result.get('items', [])
        except HttpError as e:
            logger.error(f"HttpError: {e}")
            return None

        return events

    def _to_utc_string(self, time : datetime) -> str:
        """Converts a datetime object to a UTC string in ISO 8601 format.

        Args:
            time (datetime): A datetime object to convert.

        Returns:
            str: A UTC-formatted string (e.g., '2025-01-01T06:00:00Z').
        """
        dtutc = None

        # Convert to UTC; assume UTC if no tzinfo is present
        if time.tzinfo is None:
            dtutc = time.replace(tzinfo = timezone.utc)
        else:
            dtutc = time.astimezone(ZoneInfo("UTC"))
        
        # Google API expects UTC strings ending in 'Z'
        return dtutc.strftime('%Y-%m-%dT%H:%M:%SZ')
