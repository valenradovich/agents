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
from google.oauth2.credentials import Credentials as OAuth2Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from utils import AutoRefreshingCredentials
from email_manager import EmailManager
from contacts import get_contact_email
import json
import webbrowser
import threading

init(autoreset=True)

class Tool(ABC):
    def __init__(self, name: str, args: list[str], description: str, interactive: bool = False):
        self.name = name
        self.args = args
        self.description = description
        self.interactive = interactive

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
            args=["query", "search_depth", "include_images", "include_image_descriptions"],
            description="Searches the internet for information. Input should be a query string, optionally followed by search depth ('basic' or 'advanced', default is 'basic'), include_images: used to specify if images should be included in the search results (True/False), and include_image_descriptions: used to specify if image descriptions should be included in the search results (True/False)."
        )

    def __call__(self, input: str) -> str:
        try:
            parts = input.split(',')
            query = parts[0].strip()
            search_depth = parts[1].strip().lower() if len(parts) > 1 else 'basic'
            include_images = parts[2].strip().lower() == 'true' if len(parts) > 2 else False
            include_image_descriptions = parts[3].strip().lower() == 'true' if len(parts) > 3 else False

            if search_depth not in ['basic', 'advanced']:
                search_depth = 'basic'

            payload = {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": search_depth,
                "include_images": include_images,
                "include_image_descriptions": include_image_descriptions
            }

            response = requests.post("https://api.tavily.com/search", json=payload)
            response.raise_for_status()
            results = response.json()

            output = f"Search results for '{query}':\n\n"
            for result in results['results']:
                output += f"Title: {result['title']}\n"
                output += f"URL: {result['url']}\n"
                output += f"Content: {result['content']}\n\n"

            def open_images(image_urls):
                for url in image_urls:
                    webbrowser.open_new_tab(url)
                    time.sleep(0.5)  

            if include_images and 'images' in results:
                print("Images found in the search results. Opening in browser...")
                image_urls = []
                for image in results['images']:
                    if isinstance(image, dict):
                        image_url = image['url']
                        if include_image_descriptions:
                            #print(f"Description: {image['description']}")
                            pass
                    else:
                        image_url = image
                    image_urls.append(image_url)
                
                max_images_to_open = 5 
                threading.Thread(target=open_images, args=(image_urls[:max_images_to_open],)).start()
                
            return output
        except requests.RequestException as e:
            return f"Error performing internet search: {str(e)}"

class PlayMusic(Tool):
    def __init__(self):
        super().__init__(
            name="play_music",
            args=["spotify_query", "type"],
            description="Search and play a song on Spotify. Input query should be a song name followed by the artist. Type should be 'track', 'album' or 'playlist'."
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
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        token_path = os.path.join(project_root, 'token.json')
        credentials_path = os.path.join(project_root, 'credentials.json')

        try:
            if os.path.exists(token_path):
                creds = AutoRefreshingCredentials(token_path, SCOPES)
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(f"credentials.json file not found at {credentials_path}")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            return build('calendar', 'v3', credentials=creds)
        except (RefreshError, ValueError) as e:
            print(f"Error with token: {e}")
            print("You may need to re-authenticate. Deleting the existing token and retrying...")
            if os.path.exists(token_path):
                os.remove(token_path)
            return self._get_calendar_service()  # Recursive call to retry authentication
        except Exception as e:
            print(f"An unexpected error occurred during authentication: {e}")
            raise

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
                        "{'summary': 'Event name', 'description': 'Event description', 'start': {'dateTime': 'YYYY-MM-DDTHH:MM:SS', 'timeZone': 'America/Argentina/Buenos_Aires'}, 'end': {'dateTime': 'YYYY-MM-DDTHH:MM:SS', 'timeZone': 'America/Argentina/Buenos_Aires'}}"
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
            description="Find events within a date range in Google Calendar. Event name is a string (could be not specified and use empty with "" to general searches), start and end date must be in the format YYYY-MM-DD."
        )

    def __call__(self, input: str) -> str:
        event_name, start_date, end_date = input.split(',', 2)
        print(Fore.WHITE + f"\nSearching for events in range: {event_name} from {start_date} to {end_date}")
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

class GoogleGmailBase(Tool):
    def __init__(self, name: str, args: list[str], description: str):
        super().__init__(name, args, description)
        self.service = self._get_gmail_service()

    def _get_gmail_service(self):
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        token_path = os.path.join(project_root, 'token_gmail.json')
        credentials_path = os.path.join(project_root, 'credentials.json')

        try:
            if os.path.exists(token_path):
                creds = AutoRefreshingCredentials(token_path, SCOPES)
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(f"credentials.json file not found at {credentials_path}")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            return build('gmail', 'v1', credentials=creds)
        except (RefreshError, ValueError) as e:
            print(f"Error with token: {e}")
            print("You may need to re-authenticate. Deleting the existing token and retrying...")
            if os.path.exists(token_path):
                os.remove(token_path)
            return self._get_gmail_service()  
        except Exception as e:
            print(f"An unexpected error occurred during authentication: {e}")
            raise

class ReadEmails(GoogleGmailBase):
    def __init__(self):
        super().__init__(
            name="read_emails",
            args=["max_results"],
            description="Read recent emails from your Gmail inbox. Specify the maximum number of emails to retrieve."
        )

    def __call__(self, max_results: str) -> str:
        try:
            max_results = int(max_results.strip())
            results = self.service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return "No messages found."

            email_summaries = []
            for message in messages:
                msg = self.service.users().messages().get(userId='me', id=message['id']).execute()
                subject = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), 'No Subject')
                sender = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), 'Unknown Sender')
                email_summaries.append(f"From: {sender}\nSubject: {subject}\n")

            return "\n".join(email_summaries)
        except Exception as e:
            return f"An error occurred while reading emails: {str(e)}"

class WriteEmail(Tool):
    def __init__(self, email_manager: EmailManager):
        super().__init__(
            name="write_email",
            args=["email_data"],
            description="Write or edit an email draft. Provide a JSON string containing 'to' (name or email), 'subject', 'body', and optionally 'draft_id'. Use null for draft_id if creating a new draft."
        )
        self.email_manager = email_manager

    def __call__(self, input: str) -> str:
        try:
            email_data = json.loads(input)
            to = email_data['to']
            subject = email_data['subject']
            body = email_data['body']
            draft_id = email_data.get('draft_id')
            
            # The agent should use the get_contact_email tool before calling this tool
            # If it's not an email address, we'll use a default one
            if '@' not in to:
                to = f"{to}@example.com"
            
            draft_id = self.email_manager.write_email(to, subject, body, draft_id)
            print(Fore.WHITE + f"\nEmail draft saved with ID: {draft_id}")
            return f"Email draft saved with ID: {draft_id}"
        except json.JSONDecodeError:
            return "Invalid JSON input. Please provide a valid JSON string."
        except KeyError as e:
            return f"Missing required field in JSON input: {str(e)}"
        except Exception as e:
            return f"An error occurred while writing the email: {str(e)}"

class SendEmail(GoogleGmailBase):
    def __init__(self, email_manager: EmailManager):
        super().__init__(
            name="send_email",
            args=["draft_id"],
            description="Send an email from a draft. Provide the draft_id of the email to send."
        )
        self.email_manager = email_manager

    def __call__(self, input: str) -> str:
        try:
            draft_id = input.strip()
            draft = self.email_manager.get_draft(draft_id)
            if draft == {}:
                return f"No draft found with ID: {draft_id}"
            
            message = self._create_message(draft['to'], draft['subject'], draft['body'])
            sent_message = self._send_message(message)
            
            self.email_manager.delete_draft(draft_id)
            return f"Email sent successfully. Message ID: {sent_message['id']}"
        except Exception as e:
            return f"An error occurred while sending the email: {str(e)}"

    def _create_message(self, to, subject, body):
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}

    def _send_message(self, message):
        try:
            sent_message = self.service.users().messages().send(userId='me', body=message).execute()
            return sent_message
        except Exception as e:
            print(f"An error occurred: {e}")
            raise

class DeleteEmail(Tool):
    def __init__(self, email_manager: EmailManager):
        super().__init__(
            name="delete_email",
            args=["draft_id"],
            description="Delete an email draft. Provide the draft_id of the email to delete."
        )
        self.email_manager = email_manager

    def __call__(self, input: str) -> str:
        try:
            draft_id = input.strip()
            if self.email_manager.delete_draft(draft_id):
                return f"Email draft with ID {draft_id} deleted successfully."
            else:
                return f"No draft found with ID: {draft_id}"
        except Exception as e:
            return f"An error occurred while deleting the email draft: {str(e)}"
        
class GetDrafts(Tool):
    def __init__(self, email_manager: EmailManager):
        super().__init__(
            name="get_drafts",
            args=["action", "parameter"],
            description="List email drafts or get full content of a specific draft. Action should be 'list' or 'full'. For 'list', parameter is the number of drafts to retrieve. For 'full', parameter is the draft ID."
        )
        self.email_manager = email_manager

    def __call__(self, input: str) -> str:
        try:
            action, parameter = input.split(',')
            action = action.strip().lower()
            parameter = parameter.strip()

            if action == 'list':
                return self._list_drafts(int(parameter))
            elif action == 'full':
                return self._get_full_draft(parameter)
            else:
                return "Invalid action. Use 'list' or 'full'."
        except ValueError:
            return "Invalid input. Please provide action and parameter separated by a comma."
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def _list_drafts(self, amount: int) -> str:
        drafts = self.email_manager.list_drafts(amount)
        
        if not drafts:
            return "No email drafts found."
        
        draft_list = "\n".join([f"ID: {draft['id']}, To: {draft['to']}, Subject: {draft['subject']}" for draft in drafts])
        return f"Email drafts:\n{draft_list}"

    def _get_full_draft(self, draft_id: str) -> str:
        draft = self.email_manager.get_draft(draft_id)
        
        if not draft:
            return f"No draft found with ID: {draft_id}"
        
        return f"Draft ID: {draft_id}\nTo: {draft['to']}\nSubject: {draft['subject']}\nBody:\n{draft['body']}"

class GetContactEmail(Tool):
    def __init__(self):
        super().__init__(
            name="get_contact_email",
            args=["contact_name"],
            description="Get the email address for a given contact name. If not found, returns None."
        )

    def __call__(self, contact_name: str) -> str:
        email = get_contact_email(contact_name.strip())
        if email:
            return f"Email for {contact_name}: {email}"
        else:
            return f"No email found for contact: {contact_name}"

def get_all_tool_info(tools: list[Tool]) -> list[Dict[str, str]]:
    return [tool.get_info() for tool in tools]

