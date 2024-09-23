import requests
from abc import ABC, abstractmethod
from typing import Any, Dict
from config import TAVILY_API_KEY, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, OPENWEATHER_API_KEY
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import subprocess
from colorama import Fore, init

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
            args=["spotify_query"],
            description="Search and play a song on Spotify. Input should be a song name followed by the artist."
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

    def __call__(self, query: str) -> str:
        return self.search_and_play(query, "track")

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

def get_all_tool_info(tools: list[Tool]) -> list[Dict[str, str]]:
    return [tool.get_info() for tool in tools]