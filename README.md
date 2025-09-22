---

# 🔥 Reddit Karma Farmer Comment Bot 🤖

An intelligent Reddit bot that automatically generates and posts relevant comments using **Groq's lightning-fast AI models**. Perfect for engaging with communities while maintaining natural interaction patterns.

---

## ✨ Key Features

* 🤖 **AI-Powered Comments** – Uses Groq's **LLaMA 3 model** to generate context-aware responses
* ⏱️ **Smart Timing** – Posts comments at natural intervals (11–16 minutes) to avoid detection
* 🎯 **Targeted Engagement** – Prioritizes new posts with few comments for maximum visibility
* 📊 **Intelligent Scoring** – Advanced algorithm to identify optimal posts to engage
* 📝 **Detailed Logging** – Tracks activity and saves logs in JSON format
* 🛡️ **Safety First** – Multiple safeguards to prevent spam and flagging
* ⚙️ **Flexible Modes** – Supports single subreddit, continuous, or file-based input

---

## 📋 Requirements

* Python 3.8+
* Reddit Developer Account
* Groq API Key
* Basic command line knowledge

---

## 🚀 Step-by-Step Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/reddit-auto-comment-bot.git
cd reddit-auto-comment-bot
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root:

```ini
# Reddit API Credentials (from https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT="CommentAnalyzer/1.0 by YourUsername"

# Groq API Key (from https://console.groq.com/)
GROQ_API_KEY=your_groq_api_key_here
```

### 5. Configure Subreddits (Optional)

Create a `subreddits.txt` file:

```txt
# Add subreddits without r/ prefix
funny
mildlyinteresting
showerthoughts
todayilearned
LifeProTips
explainlikeimfive
```

### 6. Run the Bot

```bash
python bot.py
```

---

## 🎮 Usage Options

### ➤ Single Subreddit Mode

```bash
python bot.py --subreddit funny --posts 3
```

### ➤ Continuous Mode (Multiple Subreddits)

```bash
python bot.py --posts 5
```

### ➤ Process Subreddits from File

```bash
python bot.py --file subreddits.txt
```

### ➤ Dry Run (Test Without Posting)

```bash
python bot.py --dry-run
```

---

## ⚠️ Important Notes

### ⏳ Rate Limiting

* Bot enforces **11–16 minute delays** between comments
* Avoid running more than once every **24 hours**

### 🗨️ Comment Quality

* AI-generated comments are designed to be **natural and relevant**
* Monitor early runs to ensure comment quality

### 🛡️ Account Safety

* Use a **dedicated Reddit account**
* Start small (3–5 comments per subreddit)
* Avoid controversial or sensitive topics

### 📜 Subreddit Rules

* Always **check subreddit rules**
* Avoid subreddits with strict “no bots” policies
* Respect community norms and moderation

---

## 📜 Disclaimer

This bot is intended for **educational purposes** and responsible community engagement. Misuse may violate Reddit’s terms of service and can result in **account suspension**. The developers are not responsible for any misuse. Always prioritize **authentic interaction**.

---

## 📁 Project Structure

```
reddit-auto-comment-bot/
├── bot.py                 # Main bot script
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
├── subreddits.txt         # Example subreddit list
├── logs/                  # Activity logs directory
├── README.md              # This documentation
└── .gitignore             # Git ignore patterns
```

---

## 🤝 Contributing

Contributions are welcome! 

---

