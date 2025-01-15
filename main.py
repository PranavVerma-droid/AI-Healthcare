import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from ai_helper import AIHelper
from database import Database
from sentiment import SentimentAnalyzer
import threading
import signal
import sys
from datetime import datetime, timedelta
import calendar
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np  # Add this import
import pytz  # Add this import at the top

class MentalHealthApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stacy - AI Mental Health Assistant")
        self.root.geometry("1000x700")
        
        # Configure the style
        self.style = ttk.Style()
        self.style.theme_use('clam')  # or 'vista' for Windows-like theme
        
        # Initialize components first
        self.db = Database()
        self.ai_helper = AIHelper()
        self.ai_helper.set_database(self.db)
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Initialize instance variables
        self.current_activities = []  # Add this line here
        self.username = "User"  # TODO: Add login system
        self.current_mood = self.db.get_daily_mood_average() or 0.5  # Initialize with today's average or neutral
        self.detail_popup = None  # Add this line
        self.timezone = pytz.timezone('Asia/Kolkata')  # Add this line
        
        # Configure custom styles
        self.style.configure('Send.TButton', 
                           padding=10, 
                           font=('Segoe UI', 10))
        self.style.configure('Chat.TFrame', 
                           background='#f0f0f0')
        self.style.configure('Input.TEntry', 
                           padding=5, 
                           font=('Segoe UI', 11))
        
        # Initialize components
        self.create_gui()
        self.update_stats()

        self.commands = {
            '/clear': self.cmd_clear,
            '/bye': self.cmd_exit,
            '/list': self.cmd_list,
            '/help': self.cmd_help,
            '/stats': self.cmd_stats,
            '/activities': self.cmd_activities,
            '/complete': self.cmd_complete,
            '/mood': self.cmd_mood
        }

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def create_gui(self):
        # Main container
        main_container = ttk.Frame(self.root, style='Chat.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.chat_tab = ttk.Frame(self.notebook)
        self.activities_tab = ttk.Frame(self.notebook)
        self.progress_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.chat_tab, text="Chat with Stacy")
        self.notebook.add(self.activities_tab, text="Daily Activities")
        self.notebook.add(self.progress_tab, text="Weekly Progress")

        # Setup each tab
        self.setup_chat_tab()
        self.setup_activities_tab()
        self.setup_progress_tab()

    def setup_chat_tab(self):
        # Title frame
        title_frame = ttk.Frame(self.chat_tab)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(title_frame, 
                               text="💭 Chat with Stacy", 
                               font=('Segoe UI', 16, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        # Status indicator
        self.status_label = ttk.Label(title_frame, 
                                     text="● Online", 
                                     font=('Segoe UI', 10),
                                     foreground='green')
        self.status_label.pack(side=tk.RIGHT)

        # Chat area with custom styling
        chat_frame = ttk.Frame(self.chat_tab, style='Chat.TFrame')
        chat_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chat_area = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=('Segoe UI', 10),
            background='#ffffff',
            borderwidth=1,
            relief="solid",
            padx=10,
            pady=10
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        self.chat_area.tag_configure('user', 
                                   background='#e3f2fd',
                                   font=('Segoe UI', 10))
        self.chat_area.tag_configure('assistant', 
                                   background='#f5f5f5',
                                   font=('Segoe UI', 10))
        self.chat_area.tag_configure('system', 
                                   foreground='#666666',
                                   font=('Segoe UI', 9, 'italic'))
        self.chat_area.tag_configure('mood_change',
                                   foreground='#666666',
                                   font=('Segoe UI', 9, 'italic'))

        # Input area
        input_frame = ttk.Frame(self.chat_tab)
        input_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.message_input = ttk.Entry(
            input_frame,
            style='Input.TEntry',
            font=('Segoe UI', 11)
        )
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        send_button = ttk.Button(
            input_frame,
            text="Send Message",
            style='Send.TButton',
            command=self.send_message
        )
        send_button.pack(side=tk.RIGHT)

        # Command help text
        help_label = ttk.Label(
            self.chat_tab,
            text="Type /help for available commands",
            font=('Segoe UI', 9),
            foreground='#666666'
        )
        help_label.pack(pady=(10, 0))
        
        # Add stats panel
        stats_frame = ttk.LabelFrame(self.chat_tab, text="Progress & Stats", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.points_label = ttk.Label(stats_frame, text="Points: 0")
        self.points_label.pack(side=tk.LEFT, padx=5)
        
        self.mood_label = ttk.Label(stats_frame, text="Weekly Mood: N/A")
        self.mood_label.pack(side=tk.LEFT, padx=5)
        
        self.streak_label = ttk.Label(stats_frame, text="Activities completed: 0")
        self.streak_label.pack(side=tk.LEFT, padx=5)

        # Bind events
        self.message_input.bind("<Return>", lambda e: self.send_message())
        
        # Initial greeting
        self.display_message("Hello! I'm Stacy, your AI mental health assistant. How are you feeling today?", 'assistant')

    def setup_activities_tab(self):
        # Configure style for completed activities
        self.style.configure('Completed.TLabelframe', 
                           background='#e8f5e9')

        # Activities recommendation panel
        ttk.Label(
            self.activities_tab,
            text=f"Hello {self.username}!",
            font=('Segoe UI', 16, 'bold')
        ).pack(pady=10)

        self.activities_frame = ttk.Frame(self.activities_tab)
        self.activities_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        # Add refresh controls frame
        controls_frame = ttk.Frame(self.activities_tab)
        controls_frame.pack(fill=tk.X, padx=20, pady=10)

        # Force refresh button
        ttk.Button(
            controls_frame,
            text="Generate New Activities",
            command=self.generate_new_activities
        ).pack(side=tk.LEFT, padx=5)

        # Auto-refresh toggle
        self.auto_refresh_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            controls_frame,
            text="Auto-refresh when completed",
            variable=self.auto_refresh_var
        ).pack(side=tk.LEFT, padx=5)

        self.refresh_activities()

    def setup_progress_tab(self):
        # Weekly progress tracking
        progress_header = ttk.Frame(self.progress_tab)
        progress_header.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(
            progress_header,
            text="Weekly Progress Tracker",
            font=('Segoe UI', 16, 'bold')
        ).pack(side=tk.LEFT)

        # Calendar view
        calendar_frame = ttk.LabelFrame(self.progress_tab, text="Activity Log", padding=10)
        calendar_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Create calendar grid
        self.calendar_cells = []
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        for i, day in enumerate(days):
            ttk.Label(calendar_frame, text=day).grid(row=0, column=i, padx=5, pady=5)
            cell = ttk.Label(calendar_frame, 
                           text="No activities",
                           background='white',
                           padding=10)
            cell.grid(row=1, column=i, padx=5, pady=5, sticky='nsew')
            self.calendar_cells.append(cell)

        # Log activity button
        log_frame = ttk.Frame(self.progress_tab)
        log_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(
            log_frame,
            text="Log Activity",
            command=self.show_log_activity_dialog
        ).pack(side=tk.LEFT)

        # Stats display
        self.stats_display = ttk.Label(
            self.progress_tab,
            text="",
            font=('Segoe UI', 11),
            justify=tk.LEFT
        )
        self.stats_display.pack(pady=10)

        # Add mood trend section
        mood_frame = ttk.LabelFrame(self.progress_tab, text="Mood Trend", padding=10)
        mood_frame.pack(fill=tk.X, padx=20, pady=10)

        # Create matplotlib figure for mood trend
        self.fig = Figure(figsize=(8, 2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=mood_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.X)

        # Today's mood average
        today_mood = ttk.Label(
            mood_frame,
            text="Today's Mood: N/A",
            font=('Segoe UI', 10, 'bold')
        )
        today_mood.pack(pady=5)

        self.mood_labels = {
            'today': today_mood,
            'week': self.mood_label  # existing weekly mood label
        }

        self.update_progress_view()

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
/stats - Show weekly progress report
/activities - List available activities
/complete - Complete an activity
/mood - Show current mood
        """
        self.display_message("System: " + help_text)

    def send_message(self):
        user_message = self.message_input.get().strip()
        if not user_message:
            return

        # Check if it's a command
        if (user_message.startswith('/')):
            if not self.handle_command(user_message):
                self.display_message("System: Unknown command. Type /help for available commands.", 'system')
            self.message_input.delete(0, tk.END)
            return

        # Regular message handling
        self.display_message(user_message, 'user')
        self.message_input.delete(0, tk.END)
        self.message_input.config(state='disabled')
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
        # Analyze sentiment with mood impact
        sentiment_score, mood, mood_impact = self.sentiment_analyzer.analyze_sentiment(user_message)
        
        # Update current mood
        old_mood = self.current_mood
        self.current_mood = max(0.0, min(1.0, self.current_mood + mood_impact))  # Keep between 0 and 1
        
        # Get activity recommendations based on mood
        if mood == "low":
            recommendations, recent = self.db.get_activity_recommendations(sentiment_score)
            if recommendations:
                ai_response += "\n\nHere are some activities that might help:"
                for name, desc, points in recommendations:
                    ai_response += f"\n• {name} ({points} points) - {desc}"
        
        # Display response and save to database
        self.display_message(ai_response, 'assistant')
        
        # Show mood change if significant
        if abs(mood_impact) >= 0.01:  # Only show if change is notable
            change_text = f"Mood {'increased' if mood_impact > 0 else 'decreased'} by {abs(mood_impact):.2f}"
            mood_color = self._get_mood_color(self.current_mood)
            self.display_message(f"〉 {change_text} ({self.current_mood:.2f})", 'system')
        
        self.message_input.config(state='normal')
        self.db.add_chat_entry(user_message, ai_response, sentiment_score)
        self.db.add_mood_entry(self.current_mood)  # Save new mood score
        self.update_stats()

    def display_message(self, message, msg_type='system'):
        self.chat_area.insert(tk.END, "\n", msg_type)
        if msg_type == 'user':
            message = "You: " + message
        elif msg_type == 'assistant':
            message = "Stacy: " + message
        elif msg_type == 'system' and message.startswith('〉'):
            # Special formatting for mood changes
            msg_type = 'mood_change'
            
        self.chat_area.insert(tk.END, message + "\n", msg_type)
        self.chat_area.see(tk.END)

    def update_stats(self):
        points = self.db.get_total_points()
        mood_avg = self.db.get_weekly_mood_average()
        progress = self.db.get_weekly_progress()
        
        self.points_label.config(text=f"Points: {points}")
        self.mood_label.config(text=f"Weekly Mood: {mood_avg:.2f}")
        if progress:
            activities_completed = sum(count for _, count, _ in progress)
            self.streak_label.config(text=f"Activities completed: {activities_completed}")
        
        # Update mood averages and trend
        daily_mood = self.db.get_daily_mood_average()
        weekly_mood = self.db.get_weekly_mood_average()
        
        # Update mood labels
        self.mood_labels['today'].config(
            text=f"Today's Mood: {daily_mood:.2f} ({self._get_mood_message(daily_mood)})",
            foreground=self._get_mood_color(daily_mood)
        )
        self.mood_labels['week'].config(
            text=f"Weekly Mood: {weekly_mood:.2f} ({self._get_mood_message(weekly_mood)})",
            foreground=self._get_mood_color(weekly_mood)
        )
        
        # Update mood trend graph
        self.update_mood_trend()

        # Schedule next update
        self.root.after(60000, self.update_stats)  # Update every minute

    def update_mood_trend(self):
        try:
            # Clear previous plot
            self.ax.clear()
            
            # Get mood trend data
            trend_data = self.db.get_mood_trend(7)
            if trend_data and len(trend_data) > 1:  # Need at least 2 points for trend line
                dates, moods, entries = zip(*trend_data)
                
                # Plot mood line
                self.ax.plot(range(len(dates)), moods, 'b-', label='Mood')
                self.ax.scatter(range(len(dates)), moods, c='blue')
                
                # Customize plot
                self.ax.set_ylim(0, 1)
                self.ax.set_xticks(range(len(dates)))
                self.ax.set_xticklabels([d.split('-')[2] for d in dates], rotation=45)
                self.ax.grid(True, linestyle='--', alpha=0.7)
                
                # Add trend line only if we have enough data
                if len(dates) > 1:
                    z = np.polyfit(range(len(dates)), moods, 1)
                    p = np.poly1d(z)
                    self.ax.plot(range(len(dates)), p(range(len(dates))), "r--", alpha=0.8, label='Trend')
                    
                self.ax.legend()
            else:
                self.ax.text(0.5, 0.5, 'Not enough mood data yet', 
                           ha='center', va='center')
                self.ax.set_xticks([])
                self.ax.set_yticks([])
            
            self.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            print(f"Error updating mood trend: {e}")

    def _get_mood_color(self, mood_score):
        if mood_score < 0.3:
            return '#e57373'  # Light red
        elif mood_score < 0.7:
            return '#4fc3f7'  # Light blue
        return '#81c784'      # Light green

    def _get_mood_message(self, mood_score):
        if mood_score < 0.3:
            return "feeling down"
        elif mood_score < 0.7:
            return "doing okay"
        else:
            return "feeling good"

    def cmd_stats(self):
        progress = self.db.get_weekly_progress()
        self.display_message("Weekly Progress Report:", 'system')
        for activity, count, points in progress:
            self.display_message(f"• {activity}: Completed {count} times, earned {points} points", 'system')

    def cmd_activities(self):
        self.display_message("Available Activities:", 'system')
        conn = self.db._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT name, description, points FROM activities')
        for name, desc, points in cursor.fetchall():
            self.display_message(f"• {name} ({points} points) - {desc}", 'system')

    def cmd_complete(self):
        # Show completion dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Complete Activity")
        dialog.geometry("300x200")
        
        ttk.Label(dialog, text="Select activity to complete:").pack(pady=10)
        
        activity_var = tk.StringVar()
        activity_combobox = ttk.Combobox(dialog, textvariable=activity_var)
        activity_combobox.pack(pady=10)
        
        conn = self.db._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM activities')
        activities = [row[0] for row in cursor.fetchall()]
        activity_combobox['values'] = activities
        
        def complete_activity():
            selected_activity = activity_var.get()
            if selected_activity:
                self.db.complete_activity(selected_activity)
                self.display_message(f"System: Activity '{selected_activity}' completed!", 'system')
                self.update_stats()
                dialog.destroy()
        
        ttk.Button(dialog, text="Complete", command=complete_activity).pack(pady=10)

    def cmd_mood(self):
        mood_avg = self.db.get_weekly_mood_average()
        self.display_message(f"System: Your current weekly mood average is {mood_avg:.2f}", 'system')

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

    def refresh_activities(self):
        try:
            # Clear existing recommendations
            for widget in self.activities_frame.winfo_children():
                widget.destroy()

            # Get user's recent mood and activities
            mood_score = self.db.get_weekly_mood_average()
            recommendations, recent = self.db.get_activity_recommendations(mood_score)
            
            # Convert recent activities list to strings if needed
            recent_activities = [str(act) for act in recent] if recent else []

            # Force new activities if requested or none exist
            activities = None
            if not self.current_activities or not any(not self.is_activity_completed(a['name']) for a in self.current_activities):
                activities = self.ai_helper.generate_activities(mood_score, recent_activities)
                if activities:
                    self.current_activities = activities
                    # Save new activities to database
                    for activity in activities:
                        self.db.add_generated_activity(activity)
            else:
                activities = self.current_activities

            # Display header
            ttk.Label(
                self.activities_frame,
                text=f"Personalized Activities for {'Low' if mood_score < 0.3 else 'Neutral' if mood_score < 0.7 else 'Positive'} Mood",
                font=('Segoe UI', 12, 'bold')
            ).pack(pady=10)

            if activities:
                # Display activity cards
                for activity in activities:
                    self.create_activity_card(activity)
            else:
                ttk.Label(
                    self.activities_frame,
                    text="Unable to generate activities. Click 'Generate New Activities' to try again.",
                    font=('Segoe UI', 10),
                    foreground='red'
                ).pack(pady=20)

        except Exception as e:
            print(f"Error refreshing activities: {e}")
            self.current_activities = []  # Reset on error

    def quick_complete_activity(self, activity_name):
        points = self.db.complete_activity(activity_name)
        messagebox.showinfo(
            "Activity Completed",
            f"Great job! You earned {points} points!"
        )
        self.update_stats()
        self.update_progress_view()
        
        # Check if auto-refresh is enabled and all activities are completed
        if self.auto_refresh_var.get() and all(self.is_activity_completed(a['name']) for a in self.current_activities):
            self.generate_new_activities()
        else:
            self.refresh_activities()  # Just update completion status

    def generate_new_activities(self):
        self.current_activities = []  # Force new activities
        self.refresh_activities()

    def is_activity_completed(self, activity_name):
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        
        conn = self.db._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM user_progress p
            JOIN activities a ON p.activity_id = a.id
            WHERE a.name = ? AND datetime(p.timestamp) BETWEEN datetime(?) AND datetime(?)
        ''', (activity_name, today_start, today_end))
        return cursor.fetchone()[0] > 0

    def create_activity_card(self, activity):
        card = ttk.LabelFrame(
            self.activities_frame,
            text=activity['name'],
            padding=10
        )
        card.pack(fill=tk.X, pady=5)

        desc_frame = ttk.Frame(card)
        desc_frame.pack(fill=tk.X)

        # Check if activity is completed
        is_completed = False
        if self.db:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
            
            conn = self.db._get_conn()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM user_progress p
                JOIN activities a ON p.activity_id = a.id
                WHERE a.name = ? AND datetime(p.timestamp) BETWEEN datetime(?) AND datetime(?)
            ''', (activity['name'], today_start, today_end))
            is_completed = cursor.fetchone()[0] > 0

        ttk.Label(
            desc_frame,
            text=activity['description'],
            wraplength=400
        ).pack(side=tk.LEFT, pady=5)

        status_frame = ttk.Frame(desc_frame)
        status_frame.pack(side=tk.RIGHT, padx=5)

        ttk.Label(
            status_frame,
            text=f"Category: {activity['category']}",
            font=('Segoe UI', 9, 'italic')
        ).pack()

        if is_completed:
            ttk.Label(
                status_frame,
                text="✓ Completed",
                foreground='green',
                font=('Segoe UI', 9, 'bold')
            ).pack()
            
            card.configure(style='Completed.TLabelframe')
        else:
            ttk.Button(
                card,
                text=f"Complete (+{activity['points']} pts)",
                command=lambda: self.quick_complete_activity(activity['name'])
            ).pack(anchor=tk.E)

    def show_log_activity_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Log Activity")
        dialog.geometry("500x400")

        # Notebook for different logging methods
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Existing activities tab
        existing_tab = ttk.Frame(notebook)
        notebook.add(existing_tab, text="Existing Activities")

        # Custom activity tab
        custom_tab = ttk.Frame(notebook)
        notebook.add(custom_tab, text="Custom Activity")

        # Set up existing activities tab
        ttk.Label(existing_tab, text="Select an activity:").pack(pady=10)
        
        activity_var = tk.StringVar()
        activity_combo = ttk.Combobox(existing_tab, textvariable=activity_var)
        cursor = self.db._get_conn().cursor()
        cursor.execute('SELECT name FROM activities')
        activities = [row[0] for row in cursor.fetchall()]
        activity_combo['values'] = activities
        activity_combo.pack(pady=5)

        # Set up custom activity tab
        ttk.Label(
            custom_tab, 
            text="Describe your activity:",
            font=('Segoe UI', 10, 'bold')
        ).pack(pady=10)
        
        description_text = tk.Text(custom_tab, height=4, width=40)
        description_text.pack(pady=5)

        preview_frame = ttk.LabelFrame(custom_tab, text="Activity Preview", padding=10)
        preview_frame.pack(fill=tk.X, padx=10, pady=10)

        preview_labels = {
            'name': ttk.Label(preview_frame, text=""),
            'category': ttk.Label(preview_frame, text=""),
            'points': ttk.Label(preview_frame, text=""),
            'description': ttk.Label(preview_frame, text="", wraplength=400)
        }
        for label in preview_labels.values():
            label.pack(anchor=tk.W, pady=2)

        # Create but don't pack the log button yet
        log_button = ttk.Button(
            custom_tab,
            text="Log this Activity",
            state='disabled'
        )

        current_preview = {'activity': None}  # Store current preview

        def preview_custom_activity():
            description = description_text.get("1.0", tk.END).strip()
            if description:
                activity = self.ai_helper.parse_custom_activity(description)
                if activity:
                    preview_labels['name'].config(
                        text=f"Name: {activity['name']}"
                    )
                    preview_labels['category'].config(
                        text=f"Category: {activity['category']}"
                    )
                    preview_labels['points'].config(
                        text=f"Points: {activity['points']}"
                    )
                    preview_labels['description'].config(
                        text=f"Description: {activity['description']}"
                    )
                    
                    # Enable and show log button
                    current_preview['activity'] = activity
                    log_button.config(state='normal')
                    log_button.pack(pady=5)
                    return activity
            return None

        def log_previewed_activity():
            activity = current_preview['activity']
            if activity:
                # Add to database and complete
                activity_id = self.db.add_generated_activity(activity)
                points = self.db.complete_activity(activity['name'])
                
                # Get notes if any
                notes = notes_text.get("1.0", tk.END).strip()
                if notes:
                    self.db.add_activity_note(activity['name'], notes)
                
                messagebox.showinfo(
                    "Activity Logged",
                    f"Custom activity '{activity['name']}' logged! You earned {points} points!"
                )
                dialog.destroy()
                self.update_stats()
                self.update_progress_view()

        # Configure log button command
        log_button.config(command=log_previewed_activity)

        preview_button = ttk.Button(
            custom_tab,
            text="Preview Activity",
            command=preview_custom_activity
        )
        preview_button.pack(pady=5)

        # Notes section
        notes_frame = ttk.LabelFrame(dialog, text="Notes (optional)", padding=10)
        notes_frame.pack(fill=tk.X, padx=10, pady=5)
        notes_text = tk.Text(notes_frame, height=3)
        notes_text.pack(fill=tk.X)

        # Add save button for existing activities tab
        def save_existing_activity():
            activity = activity_var.get()
            notes = notes_text.get("1.0", tk.END).strip()
            if activity:
                points = self.db.complete_activity(activity)
                if notes:
                    self.db.add_activity_note(activity, notes)
                messagebox.showinfo(
                    "Activity Logged",
                    f"Activity logged successfully! You earned {points} points!"
                )
                dialog.destroy()
                self.update_stats()
                self.update_progress_view()
            else:
                messagebox.showerror(
                    "Error",
                    "Please select an activity"
                )

        ttk.Button(
            existing_tab,
            text="Save Activity",
            command=save_existing_activity
        ).pack(pady=10)

    def update_progress_view(self):
        # Get activities and print for debugging
        week_activities = self.db.get_weekly_activities()
        print("Weekly activities:", week_activities)
        
        # Update calendar cells with proper day mapping
        for i, cell in enumerate(self.calendar_cells):
            # i is already correct (0=Monday to 6=Sunday)
            day_activities = week_activities.get(i, [])
            if day_activities:
                cell.configure(
                    text="\n".join(day_activities),
                    background='#e3f2fd'
                )
                cell.bind('<Button-1>', lambda e, day=i: self.show_day_details(day))
                print(f"Cell {i}: {day_activities}")
            else:
                cell.configure(
                    text="No activities",
                    background='white'
                )
                cell.unbind('<Button-1>')

        # Update stats
        total_points = self.db.get_total_points()
        weekly_count = self.db.get_weekly_activity_count()
        mood_avg = self.db.get_weekly_mood_average()

        stats_text = f"""
Weekly Stats:
• Activities Completed: {weekly_count}
• Total Points: {total_points}
• Average Mood: {mood_avg:.2f}
        """
        self.stats_display.configure(text=stats_text)

    def show_day_details(self, day_index):
        # Close existing popup if any
        if self.detail_popup:
            self.detail_popup.destroy()

        # Calculate date for the selected day in IST
        today = datetime.now(self.timezone)
        start_of_week = (today - timedelta(days=today.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        selected_date = start_of_week + timedelta(days=day_index)
        
        print(f"Showing details for: {selected_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Rest of the method remains the same
        # Create popup window
        self.detail_popup = tk.Toplevel(self.root)
        self.detail_popup.title(f"Activities for {selected_date.strftime('%A, %B %d')}")
        self.detail_popup.geometry("500x400")

        # Create scrollable container
        container = ttk.Frame(self.detail_popup)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Add activity details
        activities = self.db.get_day_activities(selected_date)
        if activities:
            for activity in activities:
                self.create_activity_detail_card(scrollable_frame, activity, selected_date)
        else:
            ttk.Label(
                scrollable_frame,
                text="No activities recorded for this day",
                font=('Segoe UI', 10, 'italic')
            ).pack(pady=20)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_activity_detail_card(self, parent, activity, date):
        # Create card frame
        card = ttk.LabelFrame(
            parent,
            text=activity['name'],
            padding=10
        )
        card.pack(fill=tk.X, pady=5)

        # Activity details
        details = ttk.Frame(card)
        details.pack(fill=tk.X)

        # Time and category
        # Convert timestamp to IST for display
        activity_time = datetime.fromisoformat(activity['timestamp'])
        if not activity_time.tzinfo:
            activity_time = self.timezone.localize(activity_time)
        time_str = activity_time.strftime('%I:%M %p')
        ttk.Label(
            details,
            text=f"Time: {time_str}",
            font=('Segoe UI', 9)
        ).pack(side=tk.LEFT)

        ttk.Label(
            details,
            text=f"Category: {activity['category']}",
            font=('Segoe UI', 9)
        ).pack(side=tk.LEFT, padx=10)

        ttk.Label(
            details,
            text=f"Points: {activity['points']}",
            font=('Segoe UI', 9)
        ).pack(side=tk.LEFT)

        # Notes if any
        if activity['notes']:
            ttk.Label(
                card,
                text=f"Notes: {activity['notes']}",
                wraplength=400
            ).pack(fill=tk.X, pady=(5, 0))

        # Delete button
        def confirm_delete():
            if messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete this activity? This will remove {activity['points']} points and adjust your mood tracking."
            ):
                self.db.delete_activity(activity['id'], date)
                card.destroy()
                self.update_stats()
                self.update_progress_view()
                # If no more activities, close popup
                if not parent.winfo_children():
                    self.detail_popup.destroy()

        ttk.Button(
            card,
            text="Delete Activity",
            style='Danger.TButton',
            command=confirm_delete
        ).pack(anchor=tk.E, pady=(5, 0))

if __name__ == "__main__": 
    root = tk.Tk()
    app = MentalHealthApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
