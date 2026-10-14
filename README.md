# Smart Study Planner and Personalized Quiz System

A Python command-line application that helps students organize subjects, plan daily study sessions, practice quizzes, and track progress.

## Features
- Add subjects and topics with priority and difficulty
- Daily study plan based on priority, difficulty and weak subjects
- Random quizzes loaded from `questions.csv`
- Score calculation and quiz history
- Pandas analysis of performance by subject
- Revision recommendations from quiz results
- Charts after each quiz and a progress chart (matplotlib)
- Data saved between runs (JSON and CSV files)

## Concepts used
Variables and data types, control statements, lists / dictionaries / sets / tuples, functions, `random` module, OOP (classes and objects), Pandas DataFrames, file handling, matplotlib.

## Requirements
- Python 3.9 or newer
- pandas and matplotlib

```
pip install -r requirements.txt
```

## How to run
Keep `smart_study_planner.py` and `questions.csv` in the same folder, then run:

```
python smart_study_planner.py
```

## Adding questions
Open `questions.csv` and add a row per question:

```
subject,question,a,b,c,d,answer
Python,Which keyword creates a class?,def,class,object,new,b
```

`answer` must be `a`, `b`, `c` or `d`. Put text that contains a comma inside double quotes. You can also add questions from menu option 6.

## Project files
| File | Purpose |
|---|---|
| `smart_study_planner.py` | Main application |
| `questions.csv` | Quiz question bank |
| `requirements.txt` | Python libraries needed |
| `subjects.json`, `quiz_history.csv` | Created automatically when you use the program |

## Menu options
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
