import praw
import time
import json
from groq import Groq
import random
from datetime import datetime
import os
from dotenv import load_dotenv
import argparse
import sys

# Load environment variables
load_dotenv()

class RedditAutoCommentBot:
    def __init__(self, reddit_client_id, reddit_client_secret, reddit_user_agent, 
                 reddit_username, reddit_password, groq_api_key):
        self.reddit = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent,
            username=reddit_username,
            password=reddit_password
        )
        self.groq_client = Groq(api_key=groq_api_key)
        self.model = "llama-3.3-70b-versatile"
        self.processed_posts = set()
        self.last_comment_time = 0
        self.min_wait = 11 * 60  # 11 minutes
        self.max_wait = 16 * 60  # 16 minutes
        self.start_time = time.time()
        self.comments_posted = []
        self.subreddits_visited = set()
        self.log_data = {
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": None,
            "status": "running",
            "subreddits": {},
            "run_duration": None
        }

    def generate_comment(self, post_title, post_content, subreddit_name):
        """Generate a comment using Groq API, and strip quotes if present."""
        try:
            prompt = f"""
            You are a helpful Reddit user commenting on a post. Generate a thoughtful, relevant comment that adds value to the discussion.

            Subreddit: r/{subreddit_name}
            Post Title: {post_title}
            Post Content: {post_content[:500]}...

            Guidelines:
            - Keep the comment under 10 words
            - Prioritize humor, sarcasm, or dry wit
            - Feel free to use emojis or slang (if natural)
            - Avoid formal language or generic positivity
            - Don't explain the joke—let it land
            - If the post is visual (art, cosplay, etc.), focus on punchy reactions
            - If the post is text-based (story, opinion, etc.), respond with clever, layered remarks
            - if post is story based and requires explanation or opinion increase word limit to 100 words
            - Don’t be promotional, robotic, or overly polite
            - Don’t mention you're a bot or reference the prompt

            Generate a comment:
            """
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )
            comment = response.choices[0].message.content.strip()
            # Remove surrounding quotes if present
            if (comment.startswith('"') and comment.endswith('"')) or (comment.startswith("'") and comment.endswith("'")):
                comment = comment[1:-1].strip()
            return comment
        except Exception as e:
            print(f"❌ Error generating comment: {str(e)}")
            return None

    def should_comment_on_post(self, submission):
        """Determine if we should comment on this post"""
        if submission.id in self.processed_posts:
            return False
        post_age = time.time() - submission.created_utc
        if post_age > 24 * 3600:
            return False
        if submission.num_comments > 100:
            return False
        if submission.locked or submission.archived:
            return False
        if submission.is_self and len(submission.selftext) < 30:
            return False
        return True

    def score_post(self, submission):
        """Score posts to prioritize new posts with few or no comments."""
        age_minutes = (time.time() - submission.created_utc) / 60
        comments = submission.num_comments
        upvotes = submission.score

        # Age: Max 40 points for <30min, then linearly down to 0 by 12h
        if age_minutes < 30:
            age_score = 40
        elif age_minutes < 720:
            age_score = max(5, 40 - ((age_minutes - 30) / 690) * 35)
        else:
            age_score = 0

        # Comments: Strongly favor 0 or 1 comments
        if comments == 0:
            comment_score = 40
        elif comments == 1:
            comment_score = 32
        elif comments <= 3:
            comment_score = 20
        elif comments <= 5:
            comment_score = 10
        else:
            comment_score = 0  # Too many comments

        # Upvotes: Small bonus for a few upvotes, but not required
        if upvotes == 0:
            upvote_score = 5
        elif upvotes <= 10:
            upvote_score = 10
        elif upvotes <= 50:
            upvote_score = 7
        else:
            upvote_score = 2

        # Total out of 90
        total_score = round(age_score + comment_score + upvote_score, 2)
        return total_score

    def analyze_and_comment_subreddit(self, subreddit_name, limit=5, sort_by='new', dry_run=False):
        """Analyze posts in a subreddit and comment on suitable ones"""
        try:
            print(f"\n🔍 Analyzing r/{subreddit_name} (sorting by {sort_by}, comments per subreddit: {limit})")
            subreddit = self.reddit.subreddit(subreddit_name)
            comments_made = 0

            while comments_made < limit:
                # Fetch new batch of posts each iteration
                batch_size = 20  # Number of posts to fetch per batch
                if sort_by == 'hot':
                    posts = subreddit.hot(limit=batch_size)
                elif sort_by == 'rising':
                    posts = subreddit.rising(limit=batch_size)
                elif sort_by == 'top':
                    posts = subreddit.top(time_filter='day', limit=batch_size)
                else:
                    posts = subreddit.new(limit=batch_size)
                    
                # Filter and score posts
                candidate_posts = []
                for submission in posts:
                    if self.should_comment_on_post(submission):
                        score = self.score_post(submission)
                        if score >= 45:  # Minimum score threshold
                            candidate_posts.append((submission, score))
                
                if not candidate_posts:
                    print("   ⚠️ No suitable posts found in this batch")
                    break
                
                # Sort by score descending
                candidate_posts.sort(key=lambda x: x[1], reverse=True)
                submission, score = candidate_posts[0]  # Highest scoring post
                
                print(f"\n📝 Post: {submission.title[:60]}...")
                print(f"   Score: {submission.score} | Comments: {submission.num_comments} | BotScore: {score:.1f}")

                post_content = submission.selftext if submission.is_self else f"Link post: {submission.url}"
                comment_text = self.generate_comment(submission.title, post_content, subreddit_name)

                if not comment_text:
                    print("   ❌ Failed to generate comment")
                    self.processed_posts.add(submission.id)  # Mark as processed to avoid retries
                    continue

                print(f"   💭 Generated comment: {comment_text[:100]}...")

                if dry_run:
                    print("   🔍 DRY RUN - Comment not posted")
                    comments_made += 1
                    self.processed_posts.add(submission.id)
                    if comments_made < limit:
                        random_wait = random.randint(self.min_wait, self.max_wait)
                        print(f"   ⏳ DRY RUN: Simulating {random_wait//60} minute delay...")
                        time.sleep(2)
                else:
                    success, comment_obj = self.post_comment(submission, comment_text)
                    if success:
                        comments_made += 1
                        self.processed_posts.add(submission.id)
                        if comments_made < limit:
                            random_wait = random.randint(self.min_wait, self.max_wait)
                            print(f"   ⏳ Waiting {random_wait//60} minutes before next comment...")
                            time.sleep(random_wait)
                    else:
                        print("   ❌ Failed to post comment")
                        # Still mark as processed to avoid repeated attempts
                        self.processed_posts.add(submission.id)

            print(f"\n📊 Subreddit Analysis Complete:")
            print(f"   Comments {'generated' if dry_run else 'posted'}: {comments_made} of {limit}")

        except Exception as e:
            print(f"❌ Error analyzing subreddit r/{subreddit_name}: {str(e)}")

    def continuous_auto_comment(self, subreddits, posts_per_subreddit=5, sort_by='new', dry_run=False):
        print(f"\n🔄 Starting continuous auto-commenting...")
        print(f"   Subreddits: {', '.join(subreddits)}")
        print(f"   Comments per subreddit: {posts_per_subreddit}")
        print(f"   Interval: 11-16 minutes between comments")
        print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print("\n   Press Ctrl+C to stop\n")
        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                print(f"\n🔄 Cycle {cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                current_subreddit = random.choice(subreddits)
                self.analyze_and_comment_subreddit(current_subreddit, posts_per_subreddit, sort_by, dry_run)
                print(f"✅ Cycle {cycle_count} complete")
                
                # Wait before next cycle
                random_wait = random.randint(self.min_wait, self.max_wait)
                print(f"⏳ Waiting {random_wait//60} minutes before next cycle...")
                if not dry_run:
                    time.sleep(random_wait)
                else:
                    print("⏳ DRY RUN: Skipping wait time")
                    time.sleep(2)
                    
        except KeyboardInterrupt:
            print(f"\n🛑 Continuous commenting stopped after {cycle_count} cycles")

    def process_subreddits_from_file(self, filename, dry_run=False):
        try:
            if not os.path.exists(filename):
                print(f"❌ File not found: {filename}")
                return
            with open(filename, 'r') as f:
                lines = f.readlines()
            subreddits = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    subreddit = line.replace('r/', '').strip()
                    if subreddit:
                        subreddits.append(subreddit)
            if not subreddits:
                print(f"❌ No valid subreddits found in {filename}")
                return
            print(f"📄 Processing {len(subreddits)} subreddits from {filename}")
            print(f"   Subreddits: {', '.join(subreddits)}")
            for i, subreddit in enumerate(subreddits, 1):
                print(f"\n🔄 Processing {i}/{len(subreddits)}: r/{subreddit}")
                self.analyze_and_comment_subreddit(subreddit, 3, 'new', dry_run)
                if i < len(subreddits):
                    random_wait = random.randint(self.min_wait, self.max_wait)
                    print(f"⏳ Waiting {random_wait//60} minutes before next subreddit...")
                    if not dry_run:
                        time.sleep(random_wait)
                    else:
                        print("⏳ DRY RUN: Skipping wait time")
                        time.sleep(2)
            print(f"\n✅ Completed processing all subreddits from {filename}")
        except Exception as e:
            print(f"❌ Error processing file {filename}: {str(e)}")

    def post_comment(self, submission, comment_text):
        try:
            comment = submission.reply(comment_text)
            print(f"✅ Comment posted successfully!")
            print(f"🆔 Comment ID: {comment.id}")
            print(f"🔗 Direct URL: https://reddit.com{comment.permalink}")
            self.last_comment_time = time.time()
            comment_data = {
                "post_title": submission.title,
                "post_url": f"https://reddit.com{submission.permalink}",
                "comment_text": comment_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            subreddit = submission.subreddit.display_name
            if subreddit not in self.log_data["subreddits"]:
                self.log_data["subreddits"][subreddit] = []
            self.log_data["subreddits"][subreddit].append(comment_data)
            self.comments_posted.append(comment_data)
            self.subreddits_visited.add(subreddit)
            return True, comment
        except praw.exceptions.APIException as e:
            print(f"❌ API Error: {str(e)}")
            return False, None
        except Exception as e:
            print(f"❌ Unexpected error posting comment: {str(e)}")
            return False, None

    def save_run_log(self, interrupted=False):
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        self.log_data["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_data["status"] = "interrupted" if interrupted else "completed"
        self.log_data["run_duration"] = time.time() - self.start_time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reddit_bot_log_{timestamp}.json"
        filepath = os.path.join(log_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(self.log_data, f, indent=2)
        print(f"📝 Run log saved to: {filepath}")
        return filepath

def check_last_run_time():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        return
    log_files = [f for f in os.listdir(log_dir) if f.startswith("reddit_bot_log_")]
    if not log_files:
        return
    latest_log = max(log_files, key=lambda f: os.path.getctime(os.path.join(log_dir, f)))
    latest_path = os.path.join(log_dir, latest_log)
    create_time = os.path.getctime(latest_path)
    time_since_last = time.time() - create_time
    if time_since_last < 24 * 3600:
        last_run_time = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n⚠️ WARNING: Last run was at {last_run_time}")
        print(f"   Only {time_since_last/3600:.1f} hours ago (less than 24 hours)")
        print("   Consider waiting before running again to avoid rate limits")
        print("-" * 60)

def main():
    print("🚀 Reddit Auto Comment Bot")
    print("=" * 50)
    check_last_run_time()
    REDDIT_CONFIG = {
        'client_id': os.getenv('REDDIT_CLIENT_ID'),
        'client_secret': os.getenv('REDDIT_CLIENT_SECRET'),
        'user_agent': os.getenv('REDDIT_USER_AGENT') or 'CommentAnalyzer/1.0',
        'username': os.getenv('REDDIT_USERNAME'),
        'password': os.getenv('REDDIT_PASSWORD')
    }
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    missing_vars = []
    if not REDDIT_CONFIG['client_id']:
        missing_vars.append('REDDIT_CLIENT_ID')
    if not REDDIT_CONFIG['client_secret']:
        missing_vars.append('REDDIT_CLIENT_SECRET')
    if not GROQ_API_KEY:
        missing_vars.append('GROQ_API_KEY')
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file or environment")
        return
    SUBREDDITS = [
        'funny',
        'mildlyinteresting', 
        'showerthoughts',
        'todayilearned',
        'LifeProTips',
        'explainlikeimfive'
    ]
    parser = argparse.ArgumentParser(description='Reddit Auto Comment Bot')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no actual posting)')
    parser.add_argument('--subreddit', type=str, help='Target specific subreddit')
    parser.add_argument('--posts', type=int, default=5, help='Number of posts to analyze per subreddit')
    parser.add_argument('--file', type=str, help='Process subreddits from file with 24-hour filter')
    args = parser.parse_args()
    if not REDDIT_CONFIG['username'] or not REDDIT_CONFIG['password']:
        print("❌ Missing Reddit username/password in environment variables")
        print("   Set REDDIT_USERNAME and REDDIT_PASSWORD to enable posting")
        if not args.dry_run:
            choice = input("Run in dry-run mode instead? (y/n): ").lower()
            if choice == 'y':
                args.dry_run = True
            else:
                return
    bot = None
    interrupted = False
    try:
        bot = RedditAutoCommentBot(
            reddit_client_id=REDDIT_CONFIG['client_id'],
            reddit_client_secret=REDDIT_CONFIG['client_secret'],
            reddit_user_agent=REDDIT_CONFIG['user_agent'],
            reddit_username=REDDIT_CONFIG['username'],
            reddit_password=REDDIT_CONFIG['password'],
            groq_api_key=GROQ_API_KEY
        )
        print("🔗 Testing Reddit connection...")
        test_subreddit = bot.reddit.subreddit('funny')
        print(f"✅ Connected to Reddit! Test subreddit: r/{test_subreddit.display_name}")
        if not args.dry_run and REDDIT_CONFIG['username']:
            print(f"👤 Logged in as: {REDDIT_CONFIG['username']}")
        print("\nChoose analysis mode:")
        print("1. Single subreddit analysis")
        print("2. Continuous auto-commenting (11-16 minute intervals)")
        print("3. Process subreddits from file (24-hour filter)")
        choice = input("\nEnter choice (1, 2, or 3): ").strip()
        if choice == '3':
            filename = input("Enter subreddits file name (default: subreddits.txt): ").strip() or "subreddits.txt"
            print(f"\n📄 Using file: {filename}")
            print("💡 File format: One subreddit per line (with or without 'r/' prefix)")
            print("💡 Lines starting with '#' are treated as comments")
            if not os.path.exists(filename):
                print(f"📝 Creating example file: {filename}")
                with open(filename, 'w') as f:
                    f.write("# Reddit Subreddits List\n")
                    f.write("# One subreddit per line (without r/ prefix)\n")
                    f.write("# Lines starting with # are comments\n\n")
                    f.write("funny\n")
                    f.write("mildlyinteresting\n")
                    f.write("showerthoughts\n")
                    f.write("todayilearned\n")
                    f.write("LifeProTips\n")
                    f.write("explainlikeimfive\n")
                print(f"✅ Created {filename} with example subreddits")
                print("💡 Edit this file to add your target subreddits")
            confirm = input(f"\nProceed with processing subreddits from {filename}? (y/n): ").lower().strip()
            if confirm == 'y':
                bot.process_subreddits_from_file(filename, args.dry_run)
            else:
                print("❌ Operation cancelled")
            return
        print("\nChoose post sorting:")
        print("1. New (latest posts)")
        print("2. Hot (trending posts)")
        print("3. Rising (gaining traction)")
        print("4. Top (best of today)")
        sort_choice = input("\nEnter sorting choice (1-4, default 1): ").strip() or '1'
        sort_options = {'1': 'new', '2': 'hot', '3': 'rising', '4': 'top'}
        sort_by = sort_options.get(sort_choice, 'new')
        if choice == '1':
            subreddit = args.subreddit or input("Enter subreddit name (without r/): ").strip()
            limit = args.posts
            bot.analyze_and_comment_subreddit(subreddit, limit, sort_by, args.dry_run)
        elif choice == '2':
            target_subreddits = [args.subreddit] if args.subreddit else SUBREDDITS
            print(f"Starting continuous auto-commenting on: {', '.join(target_subreddits)}")
            print(f"Comment interval: 11-16 minutes")
            bot.continuous_auto_comment(target_subreddits, posts_per_subreddit=args.posts, sort_by=sort_by, dry_run=args.dry_run)
        else:
            print("Invalid choice. Running single analysis on r/funny")
            bot.analyze_and_comment_subreddit('funny', 5, sort_by, args.dry_run)
    except KeyboardInterrupt:
        print("\n🛑 Script interrupted by user")
        interrupted = True
    except Exception as e:
        print(f"❌ Error initializing bot: {str(e)}")
        print("\nMake sure you have:")
        print("1. Valid Reddit API credentials")
        print("2. Valid Groq API key")
        print("3. Reddit username/password for posting")
        print("4. Installed required packages: pip install praw groq python-dotenv")
    finally:
        if bot:
            log_file = bot.save_run_log(interrupted)
            print("\n📊 Run Summary:")
            print(f"   Status: {'INTERRUPTED' if interrupted else 'COMPLETED'}")
            print(f"   Start: {bot.log_data['start_time']}")
            print(f"   End: {bot.log_data['end_time']}")
            print(f"   Duration: {bot.log_data['run_duration']:.1f} seconds")
            if bot.comments_posted:
                print(f"\n💬 Comments posted: {len(bot.comments_posted)}")
                for i, comment in enumerate(bot.comments_posted, 1):
                    print(f"   {i}. [{comment['timestamp']}] {comment['post_title'][:50]}...")
                    print(f"      URL: {comment['post_url']}")
            else:
                print("\n📭 No comments posted during this run")
            print(f"\n📝 Full log saved to: {log_file}")
        else:
            print("❌ Bot not initialized - no log saved")

if __name__ == "__main__":
    main()