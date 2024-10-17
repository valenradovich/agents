import time
from agent import ReActAgent
from tools import InternetSearch, GetWeather, PlayMusic, GoogleCalendarCreateEvent, GoogleCalendarUpdateEvent, \
                  GoogleCalendarDeleteEvent, GoogleCalendarFindEventInRange, ReadEmails, WriteEmail, SendEmail, \
                 DeleteEmail, GetDrafts
import json
import os
from colorama import init, Fore, Style
from stt import initialize_whisper, initialize_audio, process_audio, audio_queue, toggle_listening
from pynput import mouse
import queue
from email_manager import EmailManager

init(autoreset=True)

# Global variables
stop_thread = False
is_listening = False
audio_queue = queue.Queue()

def main():
    email_manager = EmailManager()
    tools = [
        InternetSearch(),
        GetWeather(),
        PlayMusic(),
        GoogleCalendarCreateEvent(),
        GoogleCalendarUpdateEvent(),
        GoogleCalendarDeleteEvent(),
        GoogleCalendarFindEventInRange(),
        ReadEmails(),
        WriteEmail(email_manager),
        SendEmail(email_manager),
        DeleteEmail(email_manager),
        GetDrafts(email_manager)
    ]
    
    agent = ReActAgent(tools, email_manager=email_manager)
    
    global stop_thread, model
    model = initialize_whisper()
    p, stream = initialize_audio()
    
    # Create a queue to communicate between threads
    query_queue = queue.Queue()

    def on_click_wrapper(x, y, button, pressed):
        if button == mouse.Button.button9:
            if pressed:
                print(Fore.YELLOW + "Listening...")
                audio_queue.queue.clear()
                toggle_listening(True)
            else:
                #print(Fore.YELLOW + "Stopped listening.")
                toggle_listening(False)
                transcribed_text = process_audio(model)
                if transcribed_text:
                    query_queue.put(transcribed_text)
                else:
                    print(Fore.RED + "No speech detected or audio level too low.")
                    
    def get_user_input():
        query = None
        # Check if there's a transcribed query in the queue
        if not query_queue.empty():
            transcribed_query = query_queue.get()
            print(Fore.WHITE + f"\n- {transcribed_query}")
            return transcribed_query
        else:
            # If queue is empty, prompt for manual input
            print(Fore.CYAN + "\nInput (or press the side button to speak): " + Fore.WHITE, end='', flush=True)
            while not input_available() and query_queue.empty():
                time.sleep(0.1)
            if not query_queue.empty():
                return get_user_input()  # Recursively call to process the voice input
            query = input()
        return query


    listener = mouse.Listener(on_click=on_click_wrapper)
    listener.start()
    
    os.system('clear')
    print(Fore.CYAN + Style.BRIGHT + "\nHey there! What do you need?" + Style.RESET_ALL + " Type 'exit' to quit.")
    print(Fore.YELLOW + "\nAvailable tools:")
    for tool_info in agent.tool_info:
        print(Fore.GREEN + f"- {tool_info['name']}")#: " + Fore.WHITE + f"{tool_info['description']}")
    print("\n" + Fore.MAGENTA + "-"*150 + "\n")
    
    try:         
        while not stop_thread:
            query = get_user_input()
            
            if query:
                if query.lower() == 'exit':
                    stop_thread = True
                    break
                
                try:
                    response = agent.run(query)
                    agent.save_interaction_log(query, response)
                except Exception as e:
                    print(Fore.RED + f"An error occurred: {str(e)}")
                
                print("\n" + Fore.MAGENTA + "-"*50 + "\n")
            else:
                # No query available, wait a bit before checking again
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("Stopping...")
        stop_thread = True
    finally:
        listener.stop()
        stream.stop_stream()
        stream.close()
        p.terminate()
        
    print(Fore.YELLOW + "\nFinal metrics:")
    print(Fore.WHITE + json.dumps(agent.metrics, indent=2))

def input_available():
    import select
    import sys
    return select.select([sys.stdin], [], [], 0.0)[0]


if __name__ == "__main__":
    main()