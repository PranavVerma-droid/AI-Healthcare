import tkinter as tk
from tkinter import ttk, scrolledtext
from ai_helper import AIHelper
from database import Database
import threading
import signal
import sys
from datetime import datetime 

class MentalHealthApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Mental Health Assistant")
        self.root.geometry("800x600")
        
        self.db = Database()
        self.ai_helper = AIHelper()
        self.ai_helper.set_database(self.db)  # Give AI helper access to database
        
        self.create_gui()

        self.commands = {
            '/clear': self.cmd_clear,
            '/bye': self.cmd_exit,
            '/list': self.cmd_list,
            '/help': self.cmd_help
        }

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def create_gui(self):
        # Chat display area
        self.chat_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=20)
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Input area frame
        input_frame = ttk.Frame(self.root)
        input_frame.pack(padx=10, pady=5, fill=tk.X)
        
        # Message input
        self.message_input = ttk.Entry(input_frame)
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Send button
        send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        send_button.pack(side=tk.RIGHT, padx=5)
        
        # Bind Enter key to send message
        self.message_input.bind("<Return>", lambda e: self.send_message())
        
        # Initial greeting
        self.display_message("AI Assistant: Hello! I'm here to listen and help. How are you feeling today?")

    def handle_command(self, cmd):
        if cmd in self.commands:
            self.commands[cmd]()
            return True
        return False

    def cmd_clear(self):
        self.db.clear_history()
        self.chat_area.delete(1.0, tk.END)
        self.display_message("System: Chat history cleared.")

    def cmd_exit(self):
        self.on_closing()

    def cmd_list(self):
        history = self.db.get_all_chats()
        self.display_message("System: Chat History:")
        for timestamp, msg, resp in history:
            try:
                time_str = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            except AttributeError:  # For older Python versions
                time_str = timestamp.split('.')[0].replace('T', ' ')  # Simple ISO format parsing
            self.display_message(f"[{time_str}]")
            self.display_message(f"You: {msg}")
            self.display_message(f"AI Assistant: {resp}")

    def cmd_help(self):
        help_text = """
Available commands:
/clear - Clear chat history
/list  - Show chat history
/bye   - Exit application
/help  - Show this help message
        """
        self.display_message("System: " + help_text)

    def send_message(self):
        user_message = self.message_input.get().strip()
        if not user_message:
            return

        # Check if it's a command
        if user_message.startswith('/'):
            if not self.handle_command(user_message):
                self.display_message("System: Unknown command. Type /help for available commands.")
            self.message_input.delete(0, tk.END)
            return

        # Regular message handling
        self.display_message(f"You: {user_message}")
        self.message_input.delete(0, tk.END)
        threading.Thread(target=self.get_ai_response, args=(user_message,), daemon=True).start()

    def get_ai_response(self, user_message):
        try:
            # Get AI response
            ai_response = self.ai_helper.get_response(user_message)
            
            # Update GUI in main thread
            self.root.after(0, self.handle_ai_response, user_message, ai_response)
        except Exception as e:
            self.root.after(0, self.display_message, f"Error: {str(e)}")

    def handle_ai_response(self, user_message, ai_response):
        self.display_message(f"AI Assistant: {ai_response}")
        # Save to database
        self.db.add_chat_entry(user_message, ai_response)

    def display_message(self, message):
        self.chat_area.insert(tk.END, message + "\n\n")
        self.chat_area.see(tk.END)

    def _signal_handler(self, signum, frame):
        self.on_closing()
        sys.exit(0)

    def on_closing(self):
        try:
            self.db.close()
        except Exception as e:
            print(f"Error during shutdown: {e}")
        finally:
            self.root.quit()
            self.root.destroy()

if __name__ == "__main__": 
    root = tk.Tk()
    app = MentalHealthApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
