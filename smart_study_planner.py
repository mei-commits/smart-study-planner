"""
Smart Study Planner and Personalized Quiz System
------------------------------------------------
Files (keep them in the same folder):
  smart_study_planner.py  -> this program
  questions.csv           -> quiz questions (edit this file to add questions)

Auto-created on first run:
  subjects.json           -> your subjects and topics
  quiz_history.csv        -> your quiz results
"""

import json
import os
import random
import sys
from datetime import datetime

import pandas as pd

# matplotlib is used for charts. The program still works without it.
try:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    HAS_PLT = True
except ImportError:
    HAS_PLT = False

# ----------------------------------------------------------------------
# File locations (always next to this script, whatever folder you run from)
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE = os.path.join(BASE_DIR, "questions.csv")
SUBJECTS_FILE = os.path.join(BASE_DIR, "subjects.json")
HISTORY_FILE = os.path.join(BASE_DIR, "quiz_history.csv")
CHART_FILE = os.path.join(BASE_DIR, "quiz_chart.png")

QUESTION_COLS = ["subject", "question", "a", "b", "c", "d", "answer"]
HISTORY_COLS = ["date", "subject", "correct"]

WEAK_THRESHOLD = 60  # subject accuracy (%) below this = weak subject

# Starter subjects used only the first time the program runs
SAMPLE_SUBJECTS = {
    "Python": {
        "priority": 5,
        "topics": {
            "Variables": {"difficulty": 1, "done": False},
            "Data Structures": {"difficulty": 2, "done": False},
            "Functions": {"difficulty": 2, "done": False},
            "OOP": {"difficulty": 3, "done": False},
            "Pandas": {"difficulty": 3, "done": False},
        },
    },
    "Math": {
        "priority": 3,
        "topics": {
            "Algebra": {"difficulty": 2, "done": False},
            "Geometry": {"difficulty": 2, "done": False},
        },
    },
}


# ----------------------------------------------------------------------
# Small input helpers
# ----------------------------------------------------------------------
def ask_text(prompt):
    """Ask until the user types something non-empty."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  Please enter a value.")


def ask_int(prompt, low, high):
    """Ask until the user enters an integer between low and high."""
    while True:
        try:
            value = int(input(prompt).strip())
            if low <= value <= high:
                return value
        except ValueError:
            pass
        print(f"  Please enter a whole number between {low} and {high}.")


def choose_from(options, title):
    """Show a numbered list and return the chosen item (or None if empty)."""
    if not options:
        print("  Nothing available yet.")
        return None
    print(f"\n{title}")
    for i, item in enumerate(options, start=1):
        print(f"  {i}. {item}")
    return options[ask_int("Choose number: ", 1, len(options)) - 1]


# ----------------------------------------------------------------------
# OOP part: Topic, Subject
# ----------------------------------------------------------------------
class Topic:
    def __init__(self, name, difficulty=2, done=False):
        self.name = name
        self.difficulty = difficulty  # 1 = easy, 2 = medium, 3 = hard
        self.done = done

    def to_dict(self):
        return {"difficulty": self.difficulty, "done": self.done}


class Subject:
    def __init__(self, name, priority=3):
        self.name = name
        self.priority = priority  # 1 = low, 5 = high
        self.topics = {}  # name -> Topic

    def add_topic(self, name, difficulty):
        if name in self.topics:
            return False
        self.topics[name] = Topic(name, difficulty)
        return True

    def to_dict(self):
        return {
            "priority": self.priority,
            "topics": {n: t.to_dict() for n, t in self.topics.items()},
        }


# ----------------------------------------------------------------------
# Study planner (subjects, topics, daily plan)
# ----------------------------------------------------------------------
class StudyPlanner:
    def __init__(self):
        self.subjects = {}  # name -> Subject
        self.load()

    # ---- saving / loading ----
    def load(self):
        if os.path.exists(SUBJECTS_FILE):
            with open(SUBJECTS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
        else:
            raw = SAMPLE_SUBJECTS  # first run: start with demo data
        for s_name, s_data in raw.items():
            subject = Subject(s_name, s_data["priority"])
            for t_name, t_data in s_data["topics"].items():
                subject.topics[t_name] = Topic(t_name, t_data["difficulty"], t_data["done"])
            self.subjects[s_name] = subject
        self.save()

    def save(self):
        data = {name: s.to_dict() for name, s in self.subjects.items()}
        with open(SUBJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ---- actions ----
    def add_subject(self):
        name = ask_text("Subject name: ").title()
        if name in self.subjects:
            print("  That subject already exists.")
            return
        priority = ask_int("Priority (1 = low ... 5 = high): ", 1, 5)
        self.subjects[name] = Subject(name, priority)
        self.save()
        print(f"  Subject '{name}' added.")

    def add_topic(self):
        name = choose_from(list(self.subjects), "Select subject:")
        if name is None:
            return
        topic = ask_text("Topic name: ").title()
        difficulty = ask_int("Difficulty (1 = easy, 2 = medium, 3 = hard): ", 1, 3)
        if self.subjects[name].add_topic(topic, difficulty):
            self.save()
            print(f"  Topic '{topic}' added to {name}.")
        else:
            print("  That topic already exists.")

    def mark_done(self):
        name = choose_from(list(self.subjects), "Select subject:")
        if name is None:
            return
        pending = [t for t, obj in self.subjects[name].topics.items() if not obj.done]
        topic = choose_from(pending, "Pending topics:")
        if topic:
            self.subjects[name].topics[topic].done = True
            self.save()
            print(f"  '{topic}' marked as completed.")

    def show_subjects(self):
        if not self.subjects:
            print("  No subjects yet.")
            return
        for s in self.subjects.values():
            print(f"\n{s.name} (priority {s.priority})")
            for t in s.topics.values():
                status = "done" if t.done else "pending"
                print(f"   - {t.name:<20} difficulty {t.difficulty}  [{status}]")

    def make_daily_plan(self, hours, weak_subjects):
        """
        Weight of each pending topic = subject priority x topic difficulty
        (x1.5 if the subject is weak in quiz results).
        Time is split in proportion to the weight, rounded to 5 minutes.
        """
        items = []
        for s in self.subjects.values():
            for t in s.topics.values():
                if t.done:
                    continue
                weight = s.priority * t.difficulty
                if s.name in weak_subjects:
                    weight *= 1.5
                items.append((s.name, t.name, weight))

        if not items:
            print("  No pending topics. Add topics or you are all done!")
            return

        total_minutes = int(hours * 60)
        total_weight = sum(w for _, _, w in items)
        items.sort(key=lambda x: x[2], reverse=True)

        print(f"\n=== Study plan for {hours} hour(s) ===")
        used = 0
        for subject, topic, weight in items:
            minutes = round(total_minutes * weight / total_weight / 5) * 5
            if minutes < 5:
                continue  # too small to be useful
            flag = "  <- weak subject" if subject in weak_subjects else ""
            print(f"  {subject:<12} {topic:<20} {minutes:>3} min{flag}")
            used += minutes
        print(f"  Total planned: {used} min")


# ----------------------------------------------------------------------
# Quiz system (questions loaded from questions.csv)
# ----------------------------------------------------------------------
class QuizSystem:
    @staticmethod
    def load_questions():
        """Read questions.csv every time, so edits to the file show up at once."""
        if not os.path.exists(QUESTIONS_FILE):
            print(f"  questions.csv not found. Put it in: {BASE_DIR}")
            return None
        df = pd.read_csv(QUESTIONS_FILE, dtype=str).fillna("")
        missing = [c for c in QUESTION_COLS if c not in df.columns]
        if missing:
            print(f"  questions.csv is missing column(s): {', '.join(missing)}")
            return None
        df["answer"] = df["answer"].str.strip().str.lower()
        df["subject"] = df["subject"].str.strip()
        df = df[df["answer"].isin(list("abcd")) & (df["question"] != "")]
        if df.empty:
            print("  questions.csv has no valid questions.")
            return None
        return df.reset_index(drop=True)

    def add_question(self, planner):
        """Append a new question to questions.csv from inside the program."""
        subject = choose_from(list(planner.subjects), "Select subject:")
        if subject is None:
            return
        text = ask_text("Question: ")
        options = [ask_text(f"Option {letter.upper()}: ") for letter in "abcd"]
        while True:
            answer = ask_text("Correct option (a/b/c/d): ").lower()
            if answer in ("a", "b", "c", "d"):
                break
        new_row = pd.DataFrame([[subject, text] + options + [answer]], columns=QUESTION_COLS)
        write_header = not os.path.exists(QUESTIONS_FILE)
        try:
            new_row.to_csv(QUESTIONS_FILE, mode="a", header=write_header, index=False)
            print("  Question saved to questions.csv.")
        except PermissionError:
            print("  Cannot save: questions.csv is open in another program. Close it and try again.")

    def take_quiz(self):
        questions = self.load_questions()
        if questions is None:
            return
        available = sorted(questions["subject"].unique())
        subject = choose_from(available, "Select quiz subject:")
        if subject is None:
            return
        pool = questions[questions["subject"] == subject]
        count = ask_int(f"How many questions (1-{len(pool)}): ", 1, len(pool))

        # random sample of questions
        chosen = pool.iloc[random.sample(range(len(pool)), count)]

        score = 0
        results = []
        for number, (_, q) in enumerate(chosen.iterrows(), start=1):
            print(f"\nQ{number}. {q['question']}")
            for letter in "abcd":
                print(f"   {letter}) {q[letter]}")
            while True:
                reply = input("Your answer: ").strip().lower()
                if reply in ("a", "b", "c", "d"):
                    break
                print("  Enter a, b, c or d.")
            correct = reply == q["answer"]
            if correct:
                score += 1
                print("  Correct!")
            else:
                print(f"  Wrong. Correct answer: {q['answer']}) {q[q['answer']]}")
            results.append([datetime.now().strftime("%Y-%m-%d %H:%M"),
                            q["subject"], int(correct)])

        percent = score / count * 100
        print(f"\nScore: {score}/{count} ({percent:.0f}%)")
        self.save_history(results)
        show_quiz_chart(subject, score, count)

    @staticmethod
    def save_history(rows):
        history = pd.read_csv(HISTORY_FILE)
        new_rows = pd.DataFrame(rows, columns=HISTORY_COLS)
        history = pd.concat([history, new_rows], ignore_index=True)
        # If the file is open in Excel, Windows blocks writing. Let the user retry.
        while True:
            try:
                history.to_csv(HISTORY_FILE, index=False)
                print("  Result saved to quiz_history.csv.")
                return
            except PermissionError:
                print("\n  Cannot save: quiz_history.csv is open in another program (e.g. Excel).")
                again = input("  Close it, then press Enter to retry (or type 'skip' to not save): ")
                if again.strip().lower() == "skip":
                    print("  Result not saved.")
                    return


# ----------------------------------------------------------------------
# Performance analysis with Pandas (by subject)
# ----------------------------------------------------------------------
class Analyzer:
    @staticmethod
    def load_history():
        return pd.read_csv(HISTORY_FILE)

    def show_history(self):
        history = self.load_history()
        if history.empty:
            print("  No quiz history yet. Take a quiz first.")
            return
        sessions = history.groupby(["date", "subject"])["correct"].agg(["sum", "count"])
        sessions["score %"] = (sessions["sum"] / sessions["count"] * 100).round(1)
        sessions = sessions.rename(columns={"sum": "correct", "count": "questions"})
        print("\n=== Quiz history ===")
        print(sessions.to_string())

    def subject_summary(self):
        history = self.load_history()
        if history.empty:
            print("  No quiz data yet. Take a quiz first.")
            return
        summary = history.groupby("subject")["correct"].agg(["sum", "count"])
        summary["accuracy %"] = (summary["sum"] / summary["count"] * 100).round(1)
        summary = summary.rename(columns={"sum": "correct", "count": "attempted"})
        print("\n=== Performance by subject ===")
        print(summary.to_string())

        print(f"\nStrongest subject: {summary['accuracy %'].idxmax()}")
        print(f"Weakest subject:   {summary['accuracy %'].idxmin()}")

    def weak_subjects(self):
        """Return a set of subject names whose accuracy is below the threshold."""
        history = self.load_history()
        if history.empty:
            return set()
        accuracy = history.groupby("subject")["correct"].mean() * 100
        return set(accuracy[accuracy < WEAK_THRESHOLD].index)

    def recommend(self, planner):
        history = self.load_history()
        weak = self.weak_subjects()
        tested = set(history["subject"]) if not history.empty else set()

        print("\n=== Revision recommendations ===")
        if weak:
            accuracy = history.groupby("subject")["correct"].mean() * 100
            print(f"Revise these first (accuracy below {WEAK_THRESHOLD}%):")
            for subject in sorted(weak):
                print(f"  - {subject} ({accuracy[subject]:.0f}%)")
                pending = [t.name for s in planner.subjects.values()
                           if s.name == subject for t in s.topics.values() if not t.done]
                if pending:
                    print(f"      pending topics: {', '.join(pending)}")
        else:
            print("No weak subjects found from your quiz results.")

        not_tested = [name for name in planner.subjects if name not in tested]
        if not_tested:
            print("\nNot tested yet (take a quiz on these):")
            for name in not_tested:
                print(f"  - {name}")


# ----------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------
def text_bar(percent, width=20):
    """Simple text progress bar, works in any terminal."""
    filled = round(percent / 100 * width)
    return "#" * filled + "-" * (width - filled)


def show_quiz_chart(subject, score, count):
    """Shown right after a quiz: this quiz result + overall accuracy per subject."""
    percent = score / count * 100
    print(f"\n  Score: [{text_bar(percent)}] {percent:.0f}%")

    if not HAS_PLT:
        print("  (To see charts, run: pip install matplotlib)")
        return

    history = pd.read_csv(HISTORY_FILE)
    accuracy = history.groupby("subject")["correct"].mean() * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    # Left chart: correct vs wrong in this quiz
    bars1 = ax1.bar(["Correct", "Wrong"], [score, count - score], color=["green", "red"])
    ax1.bar_label(bars1)
    ax1.set_title(f"This quiz: {subject} ({score}/{count} = {percent:.0f}%)")
    ax1.set_ylabel("Number of questions")
    ax1.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Right chart: overall accuracy by subject (orange = below the weak threshold)
    colors = ["green" if v >= WEAK_THRESHOLD else "orange" for v in accuracy.values]
    bars2 = ax2.bar(accuracy.index, accuracy.values, color=colors)
    ax2.bar_label(bars2, labels=[f"{v:.0f}%" for v in accuracy.values])
    ax2.axhline(WEAK_THRESHOLD, linestyle="--", color="gray")
    ax2.text(-0.4, WEAK_THRESHOLD + 2, f"weak below {WEAK_THRESHOLD}%", color="gray", fontsize=8)
    ax2.set_ylim(0, 110)
    ax2.set_title("Overall accuracy by subject")
    ax2.set_ylabel("Accuracy %")

    plt.tight_layout()
    plt.savefig(CHART_FILE)
    print(f"  Chart saved as: {CHART_FILE}")
    print("  Close the chart window to continue.")
    plt.show()


def show_progress_chart():
    """Line chart of score % for every quiz attempt, one line per subject."""
    history = pd.read_csv(HISTORY_FILE)
    if history.empty:
        print("  No quiz data yet. Take a quiz first.")
        return
    if not HAS_PLT:
        print("  To see charts, run: pip install matplotlib")
        return

    attempts = history.groupby(["date", "subject"])["correct"].mean().mul(100).reset_index()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for subject, group in attempts.groupby("subject"):
        ax.plot(range(1, len(group) + 1), group["correct"], marker="o", label=subject)
    ax.axhline(WEAK_THRESHOLD, linestyle="--", color="gray")
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel("Attempt number")
    ax.set_ylabel("Score %")
    ax.set_title("Quiz progress over time")
    ax.legend()
    plt.tight_layout()
    print("  Close the chart window to continue.")
    plt.show()


# ----------------------------------------------------------------------
# Setup and menu
# ----------------------------------------------------------------------
def setup_files():
    if not os.path.exists(QUESTIONS_FILE):
        print(f"ERROR: questions.csv not found.\nPlace it in the same folder as this program:\n{BASE_DIR}")
        sys.exit(1)
    if not os.path.exists(HISTORY_FILE):
        pd.DataFrame(columns=HISTORY_COLS).to_csv(HISTORY_FILE, index=False)


MENU = """
===== SMART STUDY PLANNER =====
 1. Add subject
 2. Add topic
 3. View subjects and topics
 4. Mark topic as completed
 5. Today's study plan
 6. Add quiz question
 7. Take a quiz
 8. Quiz history
 9. Performance by subject
10. Revision recommendations
11. Progress chart
 0. Exit
"""


def main():
    setup_files()
    planner = StudyPlanner()
    quiz = QuizSystem()
    analyzer = Analyzer()

    while True:
        print(MENU)
        choice = input("Enter choice: ").strip()

        if choice == "1":
            planner.add_subject()
        elif choice == "2":
            planner.add_topic()
        elif choice == "3":
            planner.show_subjects()
        elif choice == "4":
            planner.mark_done()
        elif choice == "5":
            try:
                hours = float(input("Hours available today: "))
                if hours <= 0:
                    raise ValueError
            except ValueError:
                print("  Enter a positive number, e.g. 2 or 1.5")
                continue
            planner.make_daily_plan(hours, analyzer.weak_subjects())
        elif choice == "6":
            quiz.add_question(planner)
        elif choice == "7":
            quiz.take_quiz()
        elif choice == "8":
            analyzer.show_history()
        elif choice == "9":
            analyzer.subject_summary()
        elif choice == "10":
            analyzer.recommend(planner)
        elif choice == "11":
            show_progress_chart()
        elif choice == "0":
            print("Goodbye! Keep studying.")
            break
        else:
            print("  Invalid choice, try again.")


if __name__ == "__main__":
    main()
