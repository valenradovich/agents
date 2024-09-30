import requests
from abc import ABC, abstractmethod
from typing import Any, Dict
from config import TAVILY_API_KEY, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, OPENWEATHER_API_KEY
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import subprocess
from colorama import Fore, init
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime, timedelta

init(autoreset=True)

class Tool(ABC):
    def __init__(self, name: str, args: list[str], description: str):
        self.name = name
        self.args = args
        self.description = description

    @abstractmethod
    def __call__(self, input: Any) -> str:
        pass

    def get_info(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "args": self.args,
            "description": self.description
        }

class InternetSearch(Tool):
    def __init__(self):
        super().__init__(
            name="internet_search",
            args=["query"],
            description="Searches the internet for information. Input should be a search query."
        )

    def __call__(self, query: str) -> str:
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": TAVILY_API_KEY, "query": query}
            )
            response.raise_for_status()
            results = response.json()
            return f"Search results for '{query}': {results['results'][:3]}"
        except requests.RequestException as e:
            return f"Error performing internet search: {str(e)}"

class PlayMusic(Tool):
    def __init__(self):
        super().__init__(
            name="play_music",
            args=["spotify_query", "type_of_item"],
            description="Search and play a song on Spotify. Input query should be a song name followed by the artist. Type of item should be 'track', 'album' or 'playlist'."
        )
        self.sp = self._setup_spotify()

    def _setup_spotify(self):
        scope = "user-library-read user-read-playback-state user-modify-playback-state"
        return spotipy.Spotify(auth_manager=SpotifyOAuth(
            scope=scope,
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri="http://localhost:8888/callback"
        ))

    def __call__(self, input: str) -> str:
        query, type = [item.strip() for item in input.split(',')]
        return self.search_and_play(query, type)

    def search_and_play(self, query, type, retry=False):
        print(Fore.WHITE + f"\nSearching for {type}: {query}")
        
        results = self.sp.search(q=query, type=type)
        item = results[f"{type}s"]['items'][0]
        item_name = item['name']
        item_uri = item['uri']
        
        print(Fore.WHITE + f"\nFound {type}: {item_name}")
        
        devices = self.sp.devices()
        if not devices['devices']:
            if not retry:
                print(Fore.WHITE + "No active devices found. Attempting to open Spotify...")
                subprocess.Popen(['spotify'], start_new_session=True)
                print(Fore.WHITE + "Waiting for Spotify to start...")
                time.sleep(4)
                return self.search_and_play(query, type, retry=True)
            else:
                return "Failed to find an active device after opening Spotify. Please ensure Spotify is running and a device is active."
        
        device_id = devices['devices'][0]['id']
        
        try:
            print(Fore.WHITE + f"\nAttempting to play on device: {device_id}")
            if type == 'track':
                self.sp.start_playback(device_id=device_id, uris=[item_uri])
            else:
                self.sp.start_playback(device_id=device_id, context_uri=item_uri)
            return f"Now playing: {item_name}"
        except spotipy.exceptions.SpotifyException as e:
            return f"Error starting playback: {e}\nThis error may occur if Spotify is not active on the selected device. Try manually starting playback on your device, then run this script again."
        except Exception as e:
            return f"An unexpected error occurred: {e}\nPlease check your internet connection and Spotify account status."

class GetWeather(Tool):
    def __init__(self):
        super().__init__(
            name="get_weather",
            args=["city_name"],
            description="Retrieves weather information for a specific city. Input should be a city name."
        )

    def __call__(self, city_name: str) -> str:
        try:
            response = requests.get(
                "http://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": city_name,
                    "appid": OPENWEATHER_API_KEY,
                    "units": "metric"
                }
            )
            response.raise_for_status()
            data = response.json()
            return f"Weather in {city_name}: {data['weather'][0]['description']}, {data['main']['temp']}°C"
        except requests.RequestException as e:
            return f"Error getting weather information: {str(e)}"

class GoogleCalendarBase(Tool):
    def __init__(self, name: str, args: list[str], description: str):
        super().__init__(name, args, description)
        self.service = self._get_calendar_service()

    def _get_calendar_service(self):
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = None
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        token_path = os.path.join(project_root, 'token.json')
        credentials_path = os.path.join(project_root, 'credentials.json')

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(f"credentials.json file not found at {credentials_path}")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        return build('calendar', 'v3', credentials=creds)

class GoogleCalendarCreateEvent(GoogleCalendarBase):
    def __init__(self):
        super().__init__(
            name="google_calendar_create_event",
            args=["event_details"],
            description="Create a new event in Google Calendar. Event details should be a dictionary with the following format:\n"
                        "{'summary': 'Event name', 'description': 'Event description', 'start': {'dateTime': 'YYYY-MM-DDTHH:MM:SS', 'timeZone': 'Time zone'}, 'end': {'dateTime': 'YYYY-MM-DDTHH:MM:SS', 'timeZone': 'Time zone'}}"
        )

    def __call__(self, input: str) -> str:
        event_details = eval(input.strip())
        event = self.service.events().insert(calendarId='primary', body=event_details).execute()
        return f"Event created: {event.get('htmlLink')}"

class GoogleCalendarUpdateEvent(GoogleCalendarBase):
    def __init__(self):
        super().__init__(
            name="google_calendar_update_event",
            args=["event_id", "event_details"],
            description="Update an existing event in Google Calendar. Provide the event ID and updated event details. Event details should be a dictionary with the following format:\n"
                        "{'summary': 'Event name', 'description': 'Event description', 'start': {'dateTime': 'YYYY-MM-DDTHH:MM:SS', 'timeZone': 'Time zone'}, 'end': {'dateTime': 'YYYY-MM-DDTHH:MM:SS', 'timeZone': 'Time zone'}}"
        )

    def __call__(self, input: str) -> str:
        event_id, event_details = input.split(',', 1)
        event_id = event_id.strip()
        event_details = eval(event_details.strip())
        updated_event = self.service.events().update(calendarId='primary', eventId=event_id, body=event_details).execute()
        return f"Event updated: {updated_event['updated']}"

class GoogleCalendarDeleteEvent(GoogleCalendarBase):
    def __init__(self):
        super().__init__(
            name="google_calendar_delete_event",
            args=["event_id"],
            description="Delete an event from Google Calendar. Provide the event ID."
        )

    def __call__(self, event_id: str) -> str:
        self.service.events().delete(calendarId='primary', eventId=event_id.strip()).execute()
        return "Event deleted"

class GoogleCalendarFindEventInRange(GoogleCalendarBase):
    def __init__(self):
        super().__init__(
            name="find_event_in_range",
            args=["event_name", "start_date", "end_date"],
            description="Find events within a date range in Google Calendar. Event name is a string (could be not specified and use empty with "" to general searches), start and end date should be in the format YYYY-MM-DD."
        )

    def __call__(self, input: str) -> str:
        event_name, start_date, end_date = input.split(',', 2)
        start_date = datetime.fromisoformat(start_date.strip())
        end_date = datetime.fromisoformat(end_date.strip())
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=start_date.isoformat() + 'Z',
            timeMax=end_date.isoformat() + 'Z',
            q=event_name.strip(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        return f"Events matching '{event_name}' between {start_date.date()} and {end_date.date()}: {events}"

def get_all_tool_info(tools: list[Tool]) -> list[Dict[str, str]]:
    return [tool.get_info() for tool in tools]