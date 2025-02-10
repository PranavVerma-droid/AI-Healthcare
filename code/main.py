import tkinter as tk
import customtkinter as ctk  # type: ignore
from tkinter import messagebox, scrolledtext
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
import numpy as np 
import pytz  # type: ignore
import time

class MentalHealthApp:
    def __init__(self, root):
        self.root = root
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("dark-blue")
        
        self.root.title("Stacy - AI Mental Health Assistant")
        self.root.geometry("1000x700")
        
        self.db = Database()
        self.ai_helper = AIHelper()
        self.ai_helper.set_database(self.db)
        self.sentiment_analyzer = SentimentAnalyzer()
        
        self.current_activities = []
        self.username = "User"
        self.current_mood = self.db.get_daily_mood_average() or 0.5
        self.detail_popup = None
        self.timezone = pytz.timezone('Asia/Kolkata')
        self.current_week_offset = 0
        self.meditation_timer = None
        self.meditation_start_time = None
        self.meditation_duration = 0
        
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

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def create_gui(self):
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.notebook = ctk.CTkTabview(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.chat_tab = self.notebook.add("Chat with Stacy")
        self.activities_tab = self.notebook.add("Daily Activities")  
        self.progress_tab = self.notebook.add("Weekly Progress")
        self.meditation_tab = self.notebook.add("Meditation")

        self.setup_chat_tab()
        self.setup_activities_tab()
        self.setup_progress_tab()
        self.setup_meditation_tab()

    def setup_chat_tab(self):
        title_frame = ctk.CTkFrame(self.chat_tab)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="💭 Chat with Stacy", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(side=tk.LEFT)
        
        self.status_label = ctk.CTkLabel(
            title_frame, 
            text="● Online", 
            text_color="green",
            font=ctk.CTkFont(size=10)
        )
        self.status_label.pack(side=tk.RIGHT)

        chat_frame = ctk.CTkFrame(self.chat_tab)
        chat_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chat_area = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=('Segoe UI', 10),
            bg='#ffffff',
            borderwidth=1,
            relief="solid",
            padx=10,
            pady=10,
            state='disabled'
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
        input_frame = ctk.CTkFrame(self.chat_tab)
        input_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.message_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type your message here...",
            font=ctk.CTkFont(size=11),
            height=40
        )
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        send_button = ctk.CTkButton(
            input_frame,
            text="Send Message",
            font=ctk.CTkFont(size=11),
            command=self.send_message,
            width=120,
            height=40
        )
        send_button.pack(side=tk.RIGHT)

        help_label = ctk.CTkLabel(
            self.chat_tab,
            text="Type /help for available commands",
            font=ctk.CTkFont(size=9),
            text_color="gray"
        )
        help_label.pack(pady=(10, 0))
        
        stats_frame = ctk.CTkFrame(self.chat_tab)
        stats_frame.pack(fill=tk.X, pady=(20, 10))
        
        self.points_label = ctk.CTkLabel(stats_frame, text="Points: 0")
        self.points_label.pack(side=tk.LEFT, padx=15)
        
        self.mood_label = ctk.CTkLabel(stats_frame, text="Weekly Mood: N/A")
        self.mood_label.pack(side=tk.LEFT, padx=15)
        
        self.streak_label = ctk.CTkLabel(stats_frame, text="Activities completed: 0")
        self.streak_label.pack(side=tk.LEFT, padx=15)

        self.message_input.bind("<Return>", lambda e: self.send_message())
        self.display_message("Hello! I'm Stacy, your AI mental health assistant. How are you feeling today?", 'assistant')

    def setup_activities_tab(self):
        self.activities_frame = ctk.CTkFrame(self.activities_tab)
        self.activities_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        controls_frame = ctk.CTkFrame(self.activities_tab)
        controls_frame.pack(fill=tk.X, padx=20, pady=10)

        generate_button = ctk.CTkButton(
            controls_frame,
            text="Generate New Activities",
            command=self.generate_new_activities
        )
        generate_button.pack(side=tk.LEFT, padx=5)

        self.auto_refresh_var = tk.BooleanVar(value=False)
        auto_refresh_check = ctk.CTkCheckBox(
            controls_frame,
            text="Auto-refresh when completed",
            variable=self.auto_refresh_var
        )
        auto_refresh_check.pack(side=tk.LEFT, padx=5)

        self.refresh_activities()

    def setup_progress_tab(self):
        progress_header = ctk.CTkFrame(self.progress_tab)
        progress_header.pack(fill=tk.X, padx=20, pady=10)

        progress_label = ctk.CTkLabel(
            progress_header,
            text="Weekly Progress Tracker",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        progress_label.pack(side=tk.LEFT)

        nav_frame = ctk.CTkFrame(progress_header)
        nav_frame.pack(side=tk.RIGHT)

        prev_week_button = ctk.CTkButton(
            nav_frame,
            text="← Previous Week",
            command=self.previous_week
        )
        prev_week_button.pack(side=tk.LEFT, padx=5)

        self.week_label = ctk.CTkLabel(
            nav_frame,
            text="Current Week",
            font=ctk.CTkFont(size=10)
        )
        self.week_label.pack(side=tk.LEFT, padx=10)

        next_week_button = ctk.CTkButton(
            nav_frame,
            text="Next Week →",
            command=self.next_week
        )
        next_week_button.pack(side=tk.LEFT, padx=5)

        today_button = ctk.CTkButton(
            nav_frame,
            text="Today",
            command=self.goto_current_week
        )
        today_button.pack(side=tk.LEFT, padx=(15, 5))

        calendar_frame = ctk.CTkFrame(self.progress_tab)
        calendar_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.calendar_cells = []
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        for i, day in enumerate(days):
            day_label = ctk.CTkLabel(calendar_frame, text=day)
            day_label.grid(row=0, column=i, padx=5, pady=5)
            cell = ctk.CTkLabel(
                calendar_frame, 
                text="No activities", 
                bg_color='white', 
                padx=10, 
                pady=10
            )
            cell.grid(row=1, column=i, padx=5, pady=5, sticky='nsew')
            self.calendar_cells.append(cell)

        log_frame = ctk.CTkFrame(self.progress_tab)
        log_frame.pack(fill=tk.X, padx=20, pady=10)

        log_button = ctk.CTkButton(
            log_frame,
            text="Log Activity",
            command=self.show_log_activity_dialog
        )
        log_button.pack(side=tk.LEFT)

        self.stats_display = ctk.CTkLabel(
            self.progress_tab,
            text="",
            font=ctk.CTkFont(size=11),
            justify=tk.LEFT
        )
        self.stats_display.pack(pady=10)

        mood_frame = ctk.CTkFrame(self.progress_tab)
        mood_frame.pack(fill=tk.X, padx=20, pady=10)

        self.fig = Figure(figsize=(8, 2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=mood_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.X)

        today_mood = ctk.CTkLabel(
            mood_frame,
            text="Today's Mood: N/A",
            font=ctk.CTkFont(size=10, weight="bold")
        )
        today_mood.pack(pady=5)

        self.mood_labels = {
            'today': today_mood,
            'week': self.mood_label 
        }

        self.update_progress_view()

    def setup_meditation_tab(self):
        title_frame = ctk.CTkFrame(self.meditation_tab)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="🧘 Meditation Timer", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(side=tk.LEFT)

        # Timer settings
        settings_frame = ctk.CTkFrame(self.meditation_tab)
        settings_frame.pack(pady=20)

        ctk.CTkLabel(
            settings_frame,
            text="Set Timer Duration (minutes):",
            font=ctk.CTkFont(size=12)
        ).pack(pady=5)

        duration_frame = ctk.CTkFrame(settings_frame)
        duration_frame.pack()

        durations = ["5", "10", "15", "20", "30"]
        self.duration_var = tk.StringVar(value="5")
        
        for duration in durations:
            ctk.CTkRadioButton(
                duration_frame,
                text=f"{duration} min",
                variable=self.duration_var,
                value=duration
            ).pack(side=tk.LEFT, padx=10, pady=10)

        # Timer display
        self.timer_label = ctk.CTkLabel(
            self.meditation_tab,
            text="00:00",
            font=ctk.CTkFont(size=48, weight="bold")
        )
        self.timer_label.pack(pady=30)

        # Control buttons
        self.start_button = ctk.CTkButton(
            self.meditation_tab,
            text="Start Meditation",
            command=self.start_meditation,
            font=ctk.CTkFont(size=14),
            width=200,
            height=40
        )
        self.start_button.pack(pady=10)

        self.stop_button = ctk.CTkButton(
            self.meditation_tab,
            text="End Session",
            command=self.stop_meditation,
            font=ctk.CTkFont(size=14),
            width=200,
            height=40,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_button.pack(pady=10)

        # Tips
        tips_frame = ctk.CTkFrame(self.meditation_tab)
        tips_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ctk.CTkLabel(
            tips_frame,
            text="Meditation Tips:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=5)
        
        tips = [
            "Find a quiet, comfortable place",
            "Sit in a relaxed but alert position",
            "Focus on your breath",
            "Let thoughts come and go without judgment",
            "Start with short sessions and gradually increase"
        ]
        
        for tip in tips:
            ctk.CTkLabel(
                tips_frame,
                text=f"• {tip}",
                font=ctk.CTkFont(size=11)
            ).pack(anchor=tk.W, padx=20, pady=2)

    def handle_command(self, cmd):
        if cmd in self.commands:
            self.commands[cmd]()
            return True
        return False

    def cmd_clear(self):
        self.db.clear_history()
        self.chat_area.configure(state='normal')
        self.chat_area.delete('1.0', tk.END)
        self.chat_area.configure(state='disabled')
        self.display_message("System: Chat history cleared.", 'system')

    def cmd_exit(self):
        self.on_closing()

    def cmd_list(self):
        history = self.db.get_all_chats()
        self.display_message("System: Chat History:")
        for timestamp, msg, resp in history:
            try:
                time_str = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            except AttributeError: 
                time_str = timestamp.split('.')[0].replace('T', ' ')
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

        if (user_message.startswith('/')):
            if not self.handle_command(user_message):
                self.display_message("System: Unknown command. Type /help for available commands.", 'system')
            self.message_input.delete(0, tk.END)
            return

        self.display_message(user_message, 'user')
        self.message_input.delete(0, tk.END)
        self.message_input.configure(state='disabled')
        threading.Thread(target=self.get_ai_response, args=(user_message,), daemon=True).start()

    def get_ai_response(self, user_message):
        try:
            ai_response = self.ai_helper.get_response(user_message)
            
            self.root.after(0, self.handle_ai_response, user_message, ai_response)
        except Exception as e:
            self.root.after(0, self.display_message, f"Error: {str(e)}")

    def handle_ai_response(self, user_message, ai_response):
        sentiment_score, mood, mood_impact = self.sentiment_analyzer.analyze_sentiment(user_message)
        
        old_mood = self.current_mood
        self.current_mood = max(0.0, min(1.0, self.current_mood + mood_impact))
        
        if mood == "low":
            recommendations, recent = self.db.get_activity_recommendations(sentiment_score)
            if recommendations:
                ai_response += "\n\nHere are some activities that might help:"
                for name, desc, points in recommendations:
                    ai_response += f"\n• {name} ({points} points) - {desc}"
        

        self.display_message(ai_response, 'assistant')
        
        if abs(mood_impact) >= 0.01:
            change_text = f"Mood {'increased' if mood_impact > 0 else 'decreased'} by {abs(mood_impact):.2f}"
            mood_color = self._get_mood_color(self.current_mood)
            self.display_message(f"〉 {change_text} ({self.current_mood:.2f})", 'system')
        
        self.message_input.configure(state='normal')
        self.db.add_chat_entry(user_message, ai_response, sentiment_score)
        self.db.add_mood_entry(self.current_mood)
        self.update_stats()

    def display_message(self, message, msg_type='system'):
        self.chat_area.configure(state='normal')  # Changed from config to configure
        self.chat_area.insert(tk.END, "\n", msg_type)
        if msg_type == 'user':
            message = "You: " + message
        elif msg_type == 'assistant':
            message = "Stacy: " + message
        elif msg_type == 'system' and message.startswith('〉'):
            msg_type = 'mood_change'
            
        self.chat_area.insert(tk.END, message + "\n", msg_type)
        self.chat_area.see(tk.END)
        self.chat_area.configure(state='disabled')

    def update_stats(self):
        points = self.db.get_total_points()
        mood_avg = self.db.get_weekly_mood_average()
        progress = self.db.get_weekly_progress()
        
        self.points_label.configure(text=f"Points: {points}")
        self.mood_label.configure(text=f"Weekly Mood: {mood_avg:.2f}")
        if progress:
            activities_completed = sum(count for _, count, _ in progress)
            self.streak_label.configure(text=f"Activities completed: {activities_completed}")
        
        daily_mood = self.db.get_daily_mood_average()
        weekly_mood = self.db.get_weekly_mood_average()
        
        self.mood_labels['today'].configure(
            text=f"Today's Mood: {daily_mood:.2f} ({self._get_mood_message(daily_mood)})",
            text_color=self._get_mood_color(daily_mood)
        )
        self.mood_labels['week'].configure( 
            text=f"Weekly Mood: {weekly_mood:.2f} ({self._get_mood_message(weekly_mood)})",
            text_color=self._get_mood_color(weekly_mood) 
        )
        
        self.update_mood_trend()
        self.root.after(60000, self.update_stats)

    def update_mood_trend(self):
        try:
            self.ax.clear()

            trend_data = self.db.get_mood_trend(7)
            if trend_data and len(trend_data) > 1:
                dates, moods, entries = zip(*trend_data)

                self.ax.plot(range(len(dates)), moods, 'b-', label='Mood')
                self.ax.scatter(range(len(dates)), moods, c='blue')

                self.ax.set_ylim(0, 1)
                self.ax.set_xticks(range(len(dates)))
                self.ax.set_xticklabels([d.split('-')[2] for d in dates], rotation=45)
                self.ax.grid(True, linestyle='--', alpha=0.7)

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
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Complete Activity")
        dialog.geometry("300x200")
        dialog.lift()
        dialog.focus_force()
        
        ctk.CTkLabel(dialog, text="Select activity to complete:").pack(pady=10)
        
        activity_var = tk.StringVar()
        activity_combobox = ctk.CTkComboBox(dialog, variable=activity_var)
        activity_combobox.pack(pady=10)
        
        conn = self.db._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM activities')
        activities = [row[0] for row in cursor.fetchall()]
        activity_combobox.configure(values=activities)
        
        def complete_activity():
            selected_activity = activity_var.get()
            if selected_activity:
                self.db.complete_activity(selected_activity)
                self.display_message(f"System: Activity '{selected_activity}' completed!", 'system')
                self.update_stats()
                dialog.destroy()
        
        ctk.CTkButton(dialog, text="Complete", command=complete_activity).pack(pady=10)

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
            for widget in self.activities_frame.winfo_children():
                widget.destroy()

            mood_score = self.db.get_weekly_mood_average()
            recommendations, recent = self.db.get_activity_recommendations(mood_score)

            recent_activities = [str(act) for act in recent] if recent else []

            activities = None
            if not self.current_activities or not any(not self.is_activity_completed(a['name']) for a in self.current_activities):
                activities = self.ai_helper.generate_activities(mood_score, recent_activities)
                if activities:
                    self.current_activities = activities
                    for activity in activities:
                        self.db.add_generated_activity(activity)
            else:
                activities = self.current_activities

            mood_label = ctk.CTkLabel(
                self.activities_frame,
                text=f"Personalized Activities for {'Low' if mood_score < 0.3 else 'Neutral' if mood_score < 0.7 else 'Positive'} Mood",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            mood_label.pack(pady=10)

            if activities:
                for activity in activities:
                    self.create_activity_card(activity)
            else:
                error_label = ctk.CTkLabel(
                    self.activities_frame,
                    text="Unable to generate activities. Click 'Generate New Activities' to try again.",
                    font=ctk.CTkFont(size=10),
                    text_color="red"
                )
                error_label.pack(pady=20)

        except Exception as e:
            print(f"Error refreshing activities: {e}")
            self.current_activities = [] 

    def quick_complete_activity(self, activity_name):
        points = self.db.complete_activity(activity_name)
        messagebox.showinfo(
            "Activity Completed",
            f"Great job! You earned {points} points!"
        )
        self.update_stats()
        self.update_progress_view()
        
        if self.auto_refresh_var.get() and all(self.is_activity_completed(a['name']) for a in self.current_activities):
            self.generate_new_activities()
        else:
            self.refresh_activities()

    def generate_new_activities(self):
        self.current_activities = []
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
        card = ctk.CTkFrame(self.activities_frame)
        card.pack(fill=tk.X, pady=5, padx=10)

        header_frame = ctk.CTkFrame(card)
        header_frame.pack(fill=tk.X, padx=10, pady=(10,5))

        title = ctk.CTkLabel(
            header_frame,
            text=activity['name'],
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(side=tk.LEFT)

        category_label = ctk.CTkLabel(
            header_frame,
            text=f"Category: {activity['category']}",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        category_label.pack(side=tk.RIGHT)

        desc_label = ctk.CTkLabel(
            card,
            text=activity['description'],
            wraplength=400
        )
        desc_label.pack(pady=5, padx=10)

        is_completed = self.is_activity_completed(activity['name'])

        if is_completed:
            complete_label = ctk.CTkLabel(
                card,
                text="✓ Completed",
                text_color="green",
                font=ctk.CTkFont(size=11, weight="bold")
            )
            complete_label.pack(pady=(0,10), padx=10)
        else:
            complete_btn = ctk.CTkButton(
                card,
                text=f"Complete (+{activity['points']} pts)",
                command=lambda: self.quick_complete_activity(activity['name']),
                font=ctk.CTkFont(size=11),
                height=32
            )
            complete_btn.pack(pady=(5,10), padx=10)

    def show_log_activity_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Log Activity")
        dialog.geometry("500x400")
        dialog.lift()  # Bring to front
        dialog.focus_force()  # Force focus
        
        tab_view = ctk.CTkTabview(dialog)
        tab_view.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        existing_tab = tab_view.add("Existing Activities")
        custom_tab = tab_view.add("Custom Activity")

        # Initialize buttons first
        buttons_frame = ctk.CTkFrame(custom_tab)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)  # Pack the frame first

        preview_button = ctk.CTkButton(
            buttons_frame,
            text="Preview Activity",
            width=120
        )
        edit_button = ctk.CTkButton(
            buttons_frame,
            text="Edit Activity",
            state="disabled",
            width=120
        )
        log_button = ctk.CTkButton(
            buttons_frame,
            text="Log Activity",
            state="disabled",
            width=120
        )

        preview_button.pack(side=tk.LEFT, padx=5)
        edit_button.pack(side=tk.LEFT, padx=5)
        log_button.pack(side=tk.LEFT, padx=5)

        ctk.CTkLabel(
            custom_tab,
            text="Describe your activity:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=10)

        description_text = ctk.CTkTextbox(custom_tab, height=100)
        description_text.pack(fill=tk.X, padx=10, pady=5)

        preview_frame = ctk.CTkFrame(custom_tab)
        preview_frame.pack(fill=tk.X, padx=10, pady=10)

        ctk.CTkLabel(
            preview_frame,
            text="Activity Preview",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=5)

        preview_labels = {
            'name': ctk.CTkLabel(preview_frame, text=""),
            'category': ctk.CTkLabel(preview_frame, text=""),
            'points': ctk.CTkLabel(preview_frame, text=""),
            'description': ctk.CTkLabel(preview_frame, text="", wraplength=400)
        }
        for label in preview_labels.values():
            label.pack(anchor=tk.W, pady=2)

        current_preview = {'activity': None}

        def preview_custom_activity():
            description = description_text.get("1.0", tk.END).strip()
            if description:
                activity = self.ai_helper.parse_custom_activity(description)
                if activity:
                    preview_labels['name'].configure(text=f"Name: {activity['name']}")
                    preview_labels['category'].configure(text=f"Category: {activity['category']}")
                    preview_labels['points'].configure(text=f"Points: {activity['points']}")
                    preview_labels['description'].configure(text=f"Description: {activity['description']}")
                    current_preview['activity'] = activity
                    edit_button.configure(state="normal")
                    log_button.configure(state="normal")
                    return activity
            return None

        preview_button.configure(command=preview_custom_activity)

        # Setup edit functionality
        def edit_preview():
            if not current_preview['activity']:
                return
                
            edit_dialog = ctk.CTkToplevel(dialog)
            edit_dialog.title("Edit Activity")
            edit_dialog.geometry("400x400")
            edit_dialog.lift()  # Bring to front
            edit_dialog.focus_force()  # Force focus
            
            fields = {}
            
            ctk.CTkLabel(edit_dialog, text="Activity Name:").pack(pady=(10,0))
            fields['name'] = ctk.CTkEntry(edit_dialog)
            fields['name'].insert(0, current_preview['activity']['name'])
            fields['name'].pack(pady=(0,10))
            
            ctk.CTkLabel(edit_dialog, text="Description:").pack()
            fields['description'] = ctk.CTkTextbox(edit_dialog, height=100)
            fields['description'].insert('1.0', current_preview['activity']['description'])
            fields['description'].pack(pady=(0,10))
            
            ctk.CTkLabel(edit_dialog, text=f"Points: {current_preview['activity']['points']}").pack()
            
            ctk.CTkLabel(edit_dialog, text="Category:").pack()
            categories = ["mindfulness", "exercise", "reflection", "social", "creative"]
            fields['category'] = ctk.CTkComboBox(edit_dialog, values=categories)
            fields['category'].set(current_preview['activity']['category'])
            fields['category'].pack(pady=(0,10))
            
            def save_edits():
                try:
                    current_preview['activity'].update({
                        'name': fields['name'].get(),
                        'description': fields['description'].get('1.0', tk.END).strip(),
                        'category': fields['category'].get()
                    })
                    
                    preview_labels['name'].configure(text=f"Name: {current_preview['activity']['name']}")
                    preview_labels['category'].configure(text=f"Category: {current_preview['activity']['category']}")
                    preview_labels['points'].configure(text=f"Points: {current_preview['activity']['points']}")
                    preview_labels['description'].configure(text=f"Description: {current_preview['activity']['description']}")
                    
                    edit_dialog.destroy()
                except ValueError as e:
                    messagebox.showerror("Error", str(e))
            
            ctk.CTkButton(edit_dialog, text="Save Changes", command=save_edits).pack(pady=10)

        edit_button.configure(command=edit_preview)

        def log_custom_activity():
            activity = current_preview['activity']
            if activity:
                activity_id = self.db.add_generated_activity(activity)
                points = self.db.complete_activity(activity['name'])
                messagebox.showinfo(
                    "Activity Logged",
                    f"Custom activity '{activity['name']}' logged! You earned {points} points!"
                )
                dialog.destroy()
                self.update_stats()
                self.update_progress_view()

        log_button.configure(command=log_custom_activity)

        # Pack buttons at the end
        buttons_frame.pack(pady=5)
        preview_button.pack(side=tk.LEFT, padx=5)
        edit_button.pack(side=tk.LEFT, padx=5)
        log_button.pack(side=tk.LEFT, padx=5)

        ctk.CTkLabel(
            existing_tab,
            text="Select an activity to complete:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=10)
        
        activity_var = tk.StringVar()
        activity_combobox = ctk.CTkComboBox(
            existing_tab,
            variable=activity_var,
            width=300
        )
        activity_combobox.pack(pady=10)
        
        conn = self.db._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM activities')
        activities = [row[0] for row in cursor.fetchall()]
        activity_combobox.configure(values=activities)

        notes_frame = ctk.CTkFrame(existing_tab)
        notes_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(
            notes_frame,
            text="Notes (optional):",
            font=ctk.CTkFont(size=11)
        ).pack(anchor=tk.W, pady=5)

        notes_text = ctk.CTkTextbox(notes_frame, height=100)
        notes_text.pack(fill=tk.X, pady=5)

        def save_existing_activity():
            selected_activity = activity_var.get()
            notes = notes_text.get("1.0", tk.END).strip()
            if selected_activity:
                points = self.db.complete_activity(selected_activity)
                if notes:
                    self.db.add_activity_note(selected_activity, notes)
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

        save_button = ctk.CTkButton(
            existing_tab,
            text="Save Activity",
            command=save_existing_activity
        )
        save_button.pack(pady=10)

    def update_progress_view(self):
        today = datetime.now(self.timezone)
        current_date = today + timedelta(weeks=self.current_week_offset)
        start_of_week = (current_date - timedelta(days=current_date.weekday()))
        end_of_week = start_of_week + timedelta(days=6)

        if self.current_week_offset == 0:
            week_text = "Current Week"
        else:
            week_text = f"Week of {start_of_week.strftime('%B %d, %Y')}"
        self.week_label.configure(text=week_text)  # Changed from config to configure

        week_activities = self.db.get_activities_for_week(start_of_week)
        print(f"Showing activities for week: {start_of_week.strftime('%Y-%m-%d')} to {end_of_week.strftime('%Y-%m-%d')}")
        
        for i, cell in enumerate(self.calendar_cells):
            day_activities = week_activities.get(i, [])
            if day_activities:
                cell.configure(
                    text="\n".join(day_activities),
                    fg_color='#e3f2fd',  # Light blue background
                    text_color='black'  # Changed from default gray to black
                )
                cell.bind('<Button-1>', lambda e, day=i, date=start_of_week+timedelta(days=i): 
                         self.show_day_details(day, date))
            else:
                cell.configure(
                    text="No activities",
                    fg_color='white',
                    text_color='black'  # Changed from default gray to black
                )
                cell.unbind('<Button-1>')

        # Update stats for selected week
        stats = self.db.get_stats_for_week(start_of_week)
        stats_text = f"""
Weekly Stats ({start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d')}):
• Activities Completed: {stats['activity_count']}
• Total Points: {stats['points']}
• Average Mood: {stats['mood_avg']:.2f}
        """
        self.stats_display.configure(text=stats_text)

    def show_day_details(self, day_index, selected_date=None):
        if self.detail_popup:
            self.detail_popup.destroy()

        if selected_date is None:
            today = datetime.now(self.timezone)
            start_of_week = (today - timedelta(days=today.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            selected_date = start_of_week + timedelta(days=day_index)
        
        print(f"Showing details for: {selected_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        self.detail_popup = ctk.CTkToplevel(self.root)
        self.detail_popup.title(f"Activities for {selected_date.strftime('%A, %B %d')}")
        self.detail_popup.geometry("500x400")
        self.detail_popup.lift()  # Bring to front
        self.detail_popup.focus_force()  # Force focus

        # Create scrollable container
        container = ctk.CTkFrame(self.detail_popup)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        activities = self.db.get_day_activities(selected_date)
        if activities:
            scrollable_frame = ctk.CTkScrollableFrame(container)
            scrollable_frame.pack(fill=tk.BOTH, expand=True)
            
            for activity in activities:
                self.create_activity_detail_card(scrollable_frame, activity, selected_date)
        else:
            empty_label = ctk.CTkLabel(
                container,
                text="No activities recorded for this day",
                font=ctk.CTkFont(size=10, slant="italic")
            )
            empty_label.pack(pady=20)

    def create_activity_detail_card(self, parent, activity, date):
        card = ctk.CTkFrame(parent)
        card.pack(fill=tk.X, pady=5, padx=10)

        title = ctk.CTkLabel(
            card,
            text=activity['name'],
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=(10,5))

        details_frame = ctk.CTkFrame(card)
        details_frame.pack(fill=tk.X, padx=10)

        activity_time = datetime.fromisoformat(activity['timestamp'])
        if not activity_time.tzinfo:
            activity_time = self.timezone.localize(activity_time)
        time_str = activity_time.strftime('%I:%M %p')
        
        time_label = ctk.CTkLabel(
            details_frame,
            text=f"Time: {time_str}",
            font=ctk.CTkFont(size=9)
        )
        time_label.pack(side=tk.LEFT, padx=5)

        category_label = ctk.CTkLabel(
            details_frame,
            text=f"Category: {activity['category']}",
            font=ctk.CTkFont(size=9)
        )
        category_label.pack(side=tk.LEFT, padx=5)

        points_label = ctk.CTkLabel(
            details_frame,
            text=f"Points: {activity['points']}",
            font=ctk.CTkFont(size=9)
        )
        points_label.pack(side=tk.LEFT, padx=5)

        if activity['notes']:
            notes_label = ctk.CTkLabel(
                card,
                text=f"Notes: {activity['notes']}",
                wraplength=400
            )
            notes_label.pack(fill=tk.X, pady=(5,0), padx=10)

        def confirm_delete():
            if messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete this activity? This will remove {activity['points']} points and adjust your mood tracking."
            ):
                self.db.delete_activity(activity['id'], date)
                card.destroy()
                self.update_stats()
                self.update_progress_view()
                if not parent.winfo_children():
                    self.detail_popup.destroy()

        delete_btn = ctk.CTkButton(
            card,
            text="Delete Activity",
            command=confirm_delete,
            fg_color="red",
            hover_color="darkred"
        )
        delete_btn.pack(anchor=tk.E, pady=(5,10), padx=10)

    def previous_week(self):
        self.current_week_offset -= 1
        self.update_progress_view()
    def next_week(self):
        if self.current_week_offset < 0:  # cant go future than current week
            self.current_week_offset += 1
            self.update_progress_view()

    def goto_current_week(self):
        self.current_week_offset = 0
        self.update_progress_view()

    def start_meditation(self):
        self.meditation_duration = int(self.duration_var.get()) * 60  # Convert to seconds
        self.meditation_start_time = time.time()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.update_timer()

    def stop_meditation(self):
        if self.meditation_timer:
            self.root.after_cancel(self.meditation_timer)
        elapsed_time = int(time.time() - self.meditation_start_time)
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.show_meditation_feedback(elapsed_time)

    def update_timer(self):
        if not self.meditation_start_time:
            return
            
        elapsed = int(time.time() - self.meditation_start_time)
        remaining = max(0, self.meditation_duration - elapsed)
        
        minutes = remaining // 60
        seconds = remaining % 60
        self.timer_label.configure(text=f"{minutes:02d}:{seconds:02d}")
        
        if remaining > 0:
            self.meditation_timer = self.root.after(1000, self.update_timer)
        else:
            self.meditation_timer = None
            elapsed_time = self.meditation_duration
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.show_meditation_feedback(elapsed_time)

    def show_meditation_feedback(self, meditation_time):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Meditation Feedback")
        dialog.geometry("500x300")
        dialog.lift()
        dialog.focus_force()
        
        minutes = meditation_time // 60
        seconds = meditation_time % 60
        
        ctk.CTkLabel(
            dialog,
            text=f"You meditated for {minutes}:{seconds:02d}",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10)
        
        ctk.CTkLabel(
            dialog,
            text="How are you feeling after your meditation?",
            font=ctk.CTkFont(size=12)
        ).pack(pady=5)
        
        feedback_text = ctk.CTkTextbox(dialog, height=100)
        feedback_text.pack(fill=tk.X, padx=20, pady=10)
        
        def submit_feedback():
            feedback = feedback_text.get("1.0", tk.END).strip()
            if feedback:
                self.process_meditation_feedback(feedback, meditation_time)
                dialog.destroy()
            else:
                messagebox.showwarning(
                    "Missing Feedback",
                    "Please share how you're feeling before submitting."
                )
        
        ctk.CTkButton(
            dialog,
            text="Submit Feedback",
            command=submit_feedback
        ).pack(pady=10)

    def process_meditation_feedback(self, feedback, duration):
        # Analyze sentiment
        sentiment_score, mood, _ = self.sentiment_analyzer.analyze_sentiment(feedback)
        
        # Calculate points based on duration and sentiment
        # Base points: 1 point per minute
        base_points = max(1, duration // 60)
        
        # Sentiment multiplier: 0.8 to 1.2 based on sentiment score
        sentiment_multiplier = 0.8 + (sentiment_score * 0.4)
        
        total_points = round(base_points * sentiment_multiplier)
        
        # Create activity description
        minutes = duration // 60
        seconds = duration % 60
        description = f"Meditation session ({minutes}:{seconds:02d}). Feedback: {feedback}"
        
        # Create activity
        activity = {
            'name': "Meditation Session",
            'description': description,
            'points': total_points,
            'category': 'mindfulness'
        }
        
        # Log the activity
        activity_id = self.db.add_generated_activity(activity)
        self.db.complete_activity(activity['name'])
        
        messagebox.showinfo(
            "Meditation Complete",
            f"Great job! You earned {total_points} points for your meditation session."
        )
        
        self.update_stats()
        self.update_progress_view()

if __name__ == "__main__": 
    root = ctk.CTk()    
    app = MentalHealthApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
