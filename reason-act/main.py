from agent import ReActAgent
from tools import InternetSearch, GetWeather, PlayMusic
import json
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

def main():
    tools = [InternetSearch(), GetWeather(), PlayMusic()]
    
    agent = ReActAgent(tools)
    
    print(Fore.CYAN + Style.BRIGHT + "\nWelcome to the ReAct Agent!" + Style.RESET_ALL + " Type 'exit' to quit.")
    print(Fore.YELLOW + "\nAvailable tools:")
    for tool_info in agent.tool_info:
        print(Fore.GREEN + f"- {tool_info['name']}: " + Fore.WHITE + f"{tool_info['description']}")
    print("\n" + Fore.MAGENTA + "-"*150 + "\n")
    
    while True:
        query = input(Fore.CYAN + "Enter your query: " + Fore.WHITE)
        if query.lower() == 'exit':
            break
        
        try:
            response = agent.run(query)
            #print("\nThought process:")
            #for i, thought in enumerate(agent.thought_history, 1):
                #print(f"{i}. {thought}")
            
            agent.save_interaction_log(query, response)
        except Exception as e:
            print(Fore.RED + f"An error occurred: {str(e)}")
        
        print("\n" + Fore.MAGENTA + "-"*50 + "\n")

    print(Fore.YELLOW + "\nFinal metrics:")
    print(Fore.WHITE + json.dumps(agent.metrics, indent=2))

if __name__ == "__main__":
    main()