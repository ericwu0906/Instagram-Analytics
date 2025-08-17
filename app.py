import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
import csv
import io
import re
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = 'uploads/thumbnails'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['DATABASE'] = 'data/ig_data.db'

Session(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        db = get_db_connection()
        
        # Create users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        
        # Create projects table
        db.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_name TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Create posts table
        db.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                post_type TEXT NOT NULL,
                post_date TEXT NOT NULL,
                post_time TEXT NOT NULL,
                reel_length INTEGER,
                thumbnail_path TEXT,
                caption TEXT,
                caption_category TEXT,
                likes INTEGER,
                shares INTEGER,
                comments INTEGER,
                reach INTEGER,
                saves INTEGER,
                followers_gained INTEGER,
                watch_time INTEGER,
                avg_view_duration REAL,
                engagement_rate REAL,
                engagement_rate_weighted REAL,
                avd_ratio REAL,
                follower_gain_rate REAL,
                performance_score REAL,
                dominant_color TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        # Create trends table
        db.execute('''
            CREATE TABLE IF NOT EXISTS trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                trend_type TEXT NOT NULL,
                trend_value TEXT NOT NULL,
                avg_performance_score REAL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        # Create reports table
        db.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                report_date TEXT NOT NULL,
                report_text TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        # Create hashtags table for analysis
        db.execute('''
            CREATE TABLE IF NOT EXISTS hashtags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                hashtag TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')
        
        # Create post_comments table for collaboration
        db.execute('''
            CREATE TABLE IF NOT EXISTS post_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                comment_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        db.commit()
        db.close()

def calculate_metrics(likes, comments, shares, saves, reach, avg_view_duration, reel_length, followers_gained):
    # Engagement Rate (Unweighted)
    engagement_rate = ((likes + comments + shares + saves) / reach) * 100 if reach > 0 else 0
    
    # Engagement Rate (Weighted)
    engagement_rate_weighted = ((likes + comments + (shares * 2) + (saves * 2)) / reach) * 100 if reach > 0 else 0
    
    # Average View Duration Ratio
    avd_ratio = (avg_view_duration / reel_length) * 100 if reel_length > 0 else 0
    
    # Follower Gain Rate
    follower_gain_rate = (followers_gained / reach) * 100 if reach > 0 else 0
    
    # Performance Score
    performance_score = (engagement_rate_weighted * 0.5) + (avd_ratio * 0.3) + (follower_gain_rate * 0.2)
    
    return {
        'engagement_rate': round(engagement_rate, 2),
        'engagement_rate_weighted': round(engagement_rate_weighted, 2),
        'avd_ratio': round(avd_ratio, 2),
        'follower_gain_rate': round(follower_gain_rate, 2),
        'performance_score': round(performance_score, 2)
    }

def extract_hashtags(text):
    """Extract hashtags from caption text"""
    if not text:
        return []
    # Find all hashtags (# followed by word characters)
    hashtags = re.findall(r'#\w+', text.lower())
    # Remove duplicates and return clean hashtags
    return list(set([tag[1:] for tag in hashtags]))  # Remove the # symbol

def save_hashtags(post_id, caption, db):
    """Extract and save hashtags from post caption"""
    hashtags = extract_hashtags(caption)
    for hashtag in hashtags:
        db.execute(
            'INSERT INTO hashtags (post_id, hashtag) VALUES (?, ?)',
            (post_id, hashtag)
        )

def predict_post_performance(post_type, post_hour, caption_category, project_ids_str, db):
    """Predict post performance based on historical data"""
    # Get average performance for similar posts
    similar_posts = db.execute(f'''
        SELECT 
            AVG(performance_score) as avg_score,
            AVG(engagement_rate_weighted) as avg_engagement,
            COUNT(*) as similar_count
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        AND post_type = ?
        AND CAST(substr(post_time, 1, 2) AS INTEGER) = ?
        AND caption_category = ?
    ''', (post_type, post_hour, caption_category)).fetchone()
    
    # Get overall averages as baseline
    baseline = db.execute(f'''
        SELECT 
            AVG(performance_score) as avg_score,
            AVG(engagement_rate_weighted) as avg_engagement
        FROM posts 
        WHERE project_id IN ({project_ids_str})
    ''').fetchone()
    
    if similar_posts and similar_posts['similar_count'] >= 3:
        # Use similar posts data
        predicted_score = similar_posts['avg_score']
        predicted_engagement = similar_posts['avg_engagement']
        confidence = min(95, 50 + (similar_posts['similar_count'] * 5))
    else:
        # Use baseline with adjustments
        predicted_score = baseline['avg_score'] or 20
        predicted_engagement = baseline['avg_engagement'] or 5
        confidence = 30
    
    return {
        'predicted_score': round(predicted_score, 1),
        'predicted_engagement': round(predicted_engagement, 2),
        'confidence': confidence,
        'similar_posts': similar_posts['similar_count'] if similar_posts else 0
    }

def analyze_growth_trends(project_ids_str, db):
    """Analyze growth trends and provide insights"""
    # Get monthly growth data
    monthly_growth = db.execute(f'''
        SELECT 
            strftime('%Y-%m', post_date) as month,
            AVG(performance_score) as avg_score,
            AVG(engagement_rate_weighted) as avg_engagement,
            SUM(followers_gained) as followers_gained,
            COUNT(*) as post_count
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        GROUP BY month
        ORDER BY month
    ''').fetchall()
    
    if len(monthly_growth) < 2:
        return {'trend': 'insufficient_data', 'growth_rate': 0, 'insights': []}
    
    # Calculate growth rate (comparing last 2 months)
    recent = monthly_growth[-1]
    previous = monthly_growth[-2]
    
    score_change = ((recent['avg_score'] - previous['avg_score']) / previous['avg_score']) * 100
    engagement_change = ((recent['avg_engagement'] - previous['avg_engagement']) / previous['avg_engagement']) * 100
    
    insights = []
    if score_change > 10:
        insights.append(f"Performance improved {score_change:.1f}% this month")
    elif score_change < -10:
        insights.append(f"Performance declined {abs(score_change):.1f}% this month")
    
    if engagement_change > 15:
        insights.append(f"Engagement up {engagement_change:.1f}% - great content strategy")
    elif engagement_change < -15:
        insights.append(f"Engagement down {abs(engagement_change):.1f}% - review content mix")
    
    return {
        'trend': 'improving' if score_change > 5 else 'declining' if score_change < -5 else 'stable',
        'score_growth': round(score_change, 1),
        'engagement_growth': round(engagement_change, 1),
        'insights': insights
    }

def generate_smart_recommendations(project_ids_str, db):
    """Generate intelligent recommendations based on data analysis"""
    recommendations = []
    
    # Best posting times recommendation
    best_times = db.execute(f'''
        SELECT 
            CAST(substr(post_time, 1, 2) AS INTEGER) as hour,
            AVG(engagement_rate_weighted) as avg_engagement,
            COUNT(*) as post_count
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        GROUP BY hour
        HAVING post_count >= 2
        ORDER BY avg_engagement DESC
        LIMIT 3
    ''').fetchall()
    
    if best_times:
        top_hour = best_times[0]['hour']
        recommendations.append({
            'type': 'timing',
            'priority': 'high',
            'title': f'Post at {top_hour}:00 for {best_times[0]["avg_engagement"]:.1f}% engagement',
            'description': f'Your best performing time slot based on {best_times[0]["post_count"]} posts'
        })
    
    # Content type recommendations
    content_performance = db.execute(f'''
        SELECT 
            post_type,
            AVG(performance_score) as avg_score,
            COUNT(*) as count
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        GROUP BY post_type
        ORDER BY avg_score DESC
    ''').fetchall()
    
    if len(content_performance) > 1:
        best_type = content_performance[0]
        worst_type = content_performance[-1]
        if best_type['avg_score'] > worst_type['avg_score'] * 1.2:
            recommendations.append({
                'type': 'content',
                'priority': 'medium',
                'title': f'Focus more on {best_type["post_type"]} content',
                'description': f'{best_type["post_type"]} posts score {best_type["avg_score"]:.1f} vs {worst_type["avg_score"]:.1f} for {worst_type["post_type"]}'
            })
    
    # Caption length optimization
    caption_analysis = db.execute(f'''
        SELECT 
            CASE 
                WHEN LENGTH(caption) < 50 THEN 'Short'
                WHEN LENGTH(caption) < 150 THEN 'Medium'
                ELSE 'Long'
            END as caption_length,
            AVG(engagement_rate_weighted) as avg_engagement,
            COUNT(*) as count
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        AND caption IS NOT NULL
        GROUP BY caption_length
        ORDER BY avg_engagement DESC
    ''').fetchall()
    
    if caption_analysis and caption_analysis[0]['count'] >= 3:
        best_length = caption_analysis[0]
        recommendations.append({
            'type': 'caption',
            'priority': 'low',
            'title': f'{best_length["caption_length"]} captions perform best',
            'description': f'{best_length["avg_engagement"]:.1f}% engagement with {best_length["caption_length"].lower()} captions'
        })
    
    # Posting frequency recommendation
    posting_frequency = db.execute(f'''
        SELECT 
            strftime('%Y-%W', post_date) as week,
            COUNT(*) as posts_per_week,
            AVG(engagement_rate_weighted) as avg_engagement
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        AND post_date >= date('now', '-8 weeks')
        GROUP BY week
        ORDER BY week DESC
        LIMIT 4
    ''').fetchall()
    
    if len(posting_frequency) >= 3:
        avg_posts = sum(week['posts_per_week'] for week in posting_frequency) / len(posting_frequency)
        if avg_posts < 3:
            recommendations.append({
                'type': 'frequency',
                'priority': 'medium',
                'title': 'Consider posting more frequently',
                'description': f'Currently averaging {avg_posts:.1f} posts per week. 3-5 posts weekly typically improve reach'
            })
        elif avg_posts > 7:
            recommendations.append({
                'type': 'frequency',
                'priority': 'low',
                'title': 'Quality over quantity',
                'description': f'Posting {avg_posts:.1f} times per week. Focus on fewer, higher-quality posts'
            })
    
    return recommendations

def check_performance_alerts(project_ids_str, db):
    """Check for performance alerts and notifications"""
    alerts = []
    
    # Get recent posts (last 7 days)
    recent_posts = db.execute(f'''
        SELECT 
            id, caption, post_type, post_date, 
            performance_score, engagement_rate_weighted
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        AND date(post_date) >= date('now', '-7 days')
        ORDER BY post_date DESC
    ''').fetchall()
    
    if not recent_posts:
        return alerts
    
    # Get historical average for comparison
    historical_avg = db.execute(f'''
        SELECT 
            AVG(performance_score) as avg_score,
            AVG(engagement_rate_weighted) as avg_engagement
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        AND date(post_date) < date('now', '-7 days')
    ''').fetchone()
    
    if not historical_avg or not historical_avg['avg_score']:
        return alerts
    
    avg_score = historical_avg['avg_score']
    avg_engagement = historical_avg['avg_engagement']
    
    for post in recent_posts:
        # Check for underperforming posts
        if post['performance_score'] < avg_score * 0.7:  # 30% below average
            alerts.append({
                'type': 'underperforming',
                'priority': 'medium',
                'post_id': post['id'],
                'title': f'{post["post_type"]} underperforming',
                'description': f'Score: {post["performance_score"]:.1f} (avg: {avg_score:.1f})',
                'date': post['post_date'],
                'caption_preview': post['caption'][:40] + '...' if post['caption'] else 'No caption'
            })
        
        # Check for high-performing posts
        elif post['performance_score'] > avg_score * 1.5:  # 50% above average
            alerts.append({
                'type': 'outperforming',
                'priority': 'low',
                'post_id': post['id'],
                'title': f'{post["post_type"]} is a hit!',
                'description': f'Score: {post["performance_score"]:.1f} (avg: {avg_score:.1f})',
                'date': post['post_date'],
                'caption_preview': post['caption'][:40] + '...' if post['caption'] else 'No caption'
            })
    
    # Check posting frequency
    if len(recent_posts) == 0:
        alerts.append({
            'type': 'frequency',
            'priority': 'high',
            'title': 'No posts this week',
            'description': 'Consider posting to maintain audience engagement',
            'date': None
        })
    elif len(recent_posts) == 1:
        alerts.append({
            'type': 'frequency',
            'priority': 'medium',
            'title': 'Low posting frequency',
            'description': 'Only 1 post this week - consider increasing frequency',
            'date': None
        })
    
    return alerts

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db_connection()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        db.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get dashboard stats
    db = get_db_connection()
    
    # Get user's project IDs
    projects = db.execute(
        'SELECT id FROM projects WHERE user_id = ?', 
        (session['user_id'],)
    ).fetchall()
    
    stats = {
        'total_posts': 0,
        'avg_engagement': 0,
        'total_reach': 0,
        'new_followers': 0
    }
    
    if projects:
        project_ids = [str(p['id']) for p in projects]
        project_ids_str = ','.join(project_ids)
        
        # Get post stats
        post_stats = db.execute(f'''
            SELECT 
                COUNT(*) as total_posts,
                AVG(engagement_rate) as avg_engagement,
                SUM(reach) as total_reach,
                SUM(followers_gained) as new_followers
            FROM posts 
            WHERE project_id IN ({project_ids_str})
        ''').fetchone()
        
        if post_stats and post_stats['total_posts'] > 0:
            stats = {
                'total_posts': post_stats['total_posts'],
                'avg_engagement': round(post_stats['avg_engagement'] or 0, 1),
                'total_reach': int(post_stats['total_reach'] or 0),
                'new_followers': int(post_stats['new_followers'] or 0)
            }
    
    # Get quick recommendations and alerts for dashboard
    quick_recommendations = []
    alerts = []
    if projects:
        project_ids = [str(p['id']) for p in projects]
        project_ids_str = ','.join(project_ids)
        quick_recommendations = generate_smart_recommendations(project_ids_str, db)[:2]  # Top 2 recommendations
        alerts = check_performance_alerts(project_ids_str, db)[:3]  # Top 3 alerts
    
    db.close()
    
    return render_template('dashboard.html', username=session['username'], stats=stats, recommendations=quick_recommendations, alerts=alerts)

@app.route('/add-post', methods=['GET', 'POST'])
def add_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user's projects for the form
    db = get_db_connection()
    user_projects = db.execute(
        'SELECT id, project_name FROM projects WHERE user_id = ? ORDER BY project_name',
        (session['user_id'],)
    ).fetchall()
    db.close()
    
    if request.method == 'POST':
        # Get form data
        project_id = request.form.get('project_id')
        post_type = request.form['post_type']
        post_date = request.form['post_date']
        post_time = request.form['post_time']
        caption = request.form.get('caption', '')
        caption_category = request.form['caption_category']
        dominant_color = request.form.get('dominant_color', '')
        
        # Metrics
        likes = int(request.form['likes'])
        comments = int(request.form['comments'])
        shares = int(request.form['shares'])
        saves = int(request.form['saves'])
        reach = int(request.form['reach'])
        followers_gained = int(request.form['followers_gained'])
        
        # Reel-specific data
        reel_length = int(request.form['reel_length']) if request.form.get('reel_length') else None
        watch_time = int(request.form['watch_time']) if request.form.get('watch_time') else None
        avg_view_duration = float(request.form['avg_view_duration']) if request.form.get('avg_view_duration') else None
        
        # Handle file upload - skip in production/cloud environments
        thumbnail_path = None
        if 'thumbnail' in request.files:
            file = request.files['thumbnail']
            if file and file.filename != '' and allowed_file(file.filename):
                # In cloud environment, just store the filename without actually saving
                # This prevents filesystem errors on read-only systems like Railway
                try:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    filename = timestamp + filename
                    
                    # Try to create upload directory if it doesn't exist
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    thumbnail_path = filename
                except (OSError, PermissionError):
                    # If file saving fails (read-only filesystem), continue without thumbnail
                    thumbnail_path = None
                    flash('Note: File uploads are disabled in this environment. Post saved without thumbnail.', 'info')
        
        # Use selected project or create default
        db = get_db_connection()
        
        if not project_id:
            # Get or create default project
            project = db.execute(
                'SELECT id FROM projects WHERE user_id = ? LIMIT 1', 
                (session['user_id'],)
            ).fetchone()
            
            if not project:
                # Create default project
                db.execute(
                    'INSERT INTO projects (user_id, project_name, description) VALUES (?, ?, ?)',
                    (session['user_id'], f"{session['username']}'s Instagram", "Default project")
                )
                db.commit()
                project = db.execute(
                    'SELECT id FROM projects WHERE user_id = ? LIMIT 1', 
                    (session['user_id'],)
                ).fetchone()
            
            project_id = project['id']
        else:
            # Verify user owns the selected project
            project = db.execute(
                'SELECT id FROM projects WHERE id = ? AND user_id = ?',
                (project_id, session['user_id'])
            ).fetchone()
            
            if not project:
                flash('Invalid project selected')
                return redirect(url_for('add_post'))
            
            project_id = int(project_id)
        
        # Calculate metrics
        metrics = calculate_metrics(
            likes, comments, shares, saves, reach, 
            avg_view_duration, reel_length, followers_gained
        )
        
        # Insert post
        db.execute('''
            INSERT INTO posts (
                project_id, post_type, post_date, post_time, reel_length,
                thumbnail_path, caption, caption_category, likes, shares,
                comments, reach, saves, followers_gained, watch_time,
                avg_view_duration, engagement_rate, engagement_rate_weighted,
                avd_ratio, follower_gain_rate, performance_score, dominant_color
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id, post_type, post_date, post_time, reel_length,
            thumbnail_path, caption, caption_category, likes, shares,
            comments, reach, saves, followers_gained, watch_time,
            avg_view_duration, metrics['engagement_rate'], 
            metrics['engagement_rate_weighted'], metrics['avd_ratio'],
            metrics['follower_gain_rate'], metrics['performance_score'], 
            dominant_color
        ))
        
        # Get the ID of the newly inserted post
        post_id = db.lastrowid
        
        # Extract and save hashtags
        save_hashtags(post_id, caption, db)
        
        db.commit()
        db.close()
        
        flash('Post added successfully!')
        return redirect(url_for('posts'))
    
    return render_template('add_post.html', projects=user_projects)

@app.route('/posts')
def posts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get sorting parameter
    sort_by = request.args.get('sort', 'post_date')
    order = request.args.get('order', 'desc')
    
    # Validate sort parameters
    valid_sorts = ['post_date', 'engagement_rate', 'performance_score', 'reach', 'likes']
    if sort_by not in valid_sorts:
        sort_by = 'post_date'
    
    if order not in ['asc', 'desc']:
        order = 'desc'
    
    # Get user's posts
    db = get_db_connection()
    
    # First get user's project IDs
    projects = db.execute(
        'SELECT id FROM projects WHERE user_id = ?', 
        (session['user_id'],)
    ).fetchall()
    
    if projects:
        project_ids = [str(p['id']) for p in projects]
        project_ids_str = ','.join(project_ids)
        
        query = f'''
            SELECT * FROM posts 
            WHERE project_id IN ({project_ids_str})
            ORDER BY {sort_by} {order.upper()}
        '''
        posts_data = db.execute(query).fetchall()
    else:
        posts_data = []
    
    db.close()
    
    return render_template('posts.html', posts=posts_data, sort_by=sort_by, order=order)

@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get analytics data for charts
    db = get_db_connection()
    
    # Get user's project IDs
    projects = db.execute(
        'SELECT id FROM projects WHERE user_id = ?', 
        (session['user_id'],)
    ).fetchall()
    
    analytics_data = {
        'engagement_over_time': [],
        'reach_over_time': [],
        'posting_time_analysis': [],
        'caption_category_performance': [],
        'performance_distribution': [],
        'hashtag_performance': [],
        'content_insights': [],
        'day_of_week_analysis': [],
        'monthly_trends': [],
        'engagement_velocity': []
    }
    
    if projects:
        project_ids = [str(p['id']) for p in projects]
        project_ids_str = ','.join(project_ids)
        
        # Engagement and reach over time (last 30 posts)
        time_data = db.execute(f'''
            SELECT post_date, AVG(engagement_rate) as avg_engagement, SUM(reach) as total_reach
            FROM posts 
            WHERE project_id IN ({project_ids_str})
            GROUP BY post_date
            ORDER BY post_date DESC
            LIMIT 30
        ''').fetchall()
        
        analytics_data['engagement_over_time'] = [
            {'date': row['post_date'], 'engagement': round(row['avg_engagement'], 2)}
            for row in reversed(time_data)
        ]
        
        analytics_data['reach_over_time'] = [
            {'date': row['post_date'], 'reach': row['total_reach']}
            for row in reversed(time_data)
        ]
        
        # Posting time analysis
        posting_time_data = db.execute(f'''
            SELECT 
                CAST(substr(post_time, 1, 2) AS INTEGER) as hour,
                AVG(engagement_rate_weighted) as avg_engagement,
                COUNT(*) as post_count
            FROM posts 
            WHERE project_id IN ({project_ids_str})
            GROUP BY hour
            ORDER BY hour
        ''').fetchall()
        
        analytics_data['posting_time_analysis'] = [
            {
                'hour': row['hour'], 
                'engagement': round(row['avg_engagement'], 2),
                'count': row['post_count']
            }
            for row in posting_time_data
        ]
        
        # Caption category performance
        category_data = db.execute(f'''
            SELECT 
                caption_category,
                AVG(performance_score) as avg_score,
                COUNT(*) as post_count
            FROM posts 
            WHERE project_id IN ({project_ids_str})
            AND caption_category IS NOT NULL
            AND caption_category != ''
            GROUP BY caption_category
            ORDER BY avg_score DESC
        ''').fetchall()
        
        analytics_data['caption_category_performance'] = [
            {
                'category': row['caption_category'], 
                'score': round(row['avg_score'], 1),
                'count': row['post_count']
            }
            for row in category_data
        ]
        
        # Performance score distribution
        perf_data = db.execute(f'''
            SELECT 
                CASE 
                    WHEN performance_score < 10 THEN '0-10'
                    WHEN performance_score < 20 THEN '10-20'
                    WHEN performance_score < 30 THEN '20-30'
                    WHEN performance_score < 40 THEN '30-40'
                    WHEN performance_score < 50 THEN '40-50'
                    ELSE '50+'
                END as score_range,
                COUNT(*) as count
            FROM posts 
            WHERE project_id IN ({project_ids_str})
            GROUP BY score_range
            ORDER BY count DESC
        ''').fetchall()
        
        analytics_data['performance_distribution'] = [
            {'range': row['score_range'], 'count': row['count']}
            for row in perf_data
        ]
        
        # Hashtag performance analysis
        hashtag_data = db.execute(f'''
            SELECT 
                h.hashtag,
                AVG(p.performance_score) as avg_score,
                COUNT(*) as usage_count,
                AVG(p.engagement_rate_weighted) as avg_engagement
            FROM hashtags h
            JOIN posts p ON h.post_id = p.id
            WHERE p.project_id IN ({project_ids_str})
            GROUP BY h.hashtag
            HAVING usage_count >= 2
            ORDER BY avg_score DESC
            LIMIT 15
        ''').fetchall()
        
        analytics_data['hashtag_performance'] = [
            {
                'hashtag': row['hashtag'],
                'score': round(row['avg_score'], 1),
                'count': row['usage_count'],
                'engagement': round(row['avg_engagement'], 2)
            }
            for row in hashtag_data
        ]
        
        # Content type insights
        content_insights = db.execute(f'''
            SELECT 
                post_type,
                AVG(performance_score) as avg_score,
                AVG(engagement_rate) as avg_engagement,
                AVG(reach) as avg_reach,
                COUNT(*) as post_count
            FROM posts 
            WHERE project_id IN ({project_ids_str})
            GROUP BY post_type
            ORDER BY avg_score DESC
        ''').fetchall()
        
        analytics_data['content_insights'] = [
            {
                'type': row['post_type'],
                'score': round(row['avg_score'], 1),
                'engagement': round(row['avg_engagement'], 2),
                'reach': int(row['avg_reach']),
                'count': row['post_count']
            }
            for row in content_insights
        ]
        
        # Day of week analysis
        day_of_week_data = db.execute(f'''
            SELECT 
                CASE CAST(strftime('%w', post_date) AS INTEGER)
                    WHEN 0 THEN 'Sunday'
                    WHEN 1 THEN 'Monday'
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                END as day_name,
                CAST(strftime('%w', post_date) AS INTEGER) as day_num,
                AVG(engagement_rate_weighted) as avg_engagement,
                AVG(performance_score) as avg_score,
                COUNT(*) as post_count
            FROM posts 
            WHERE project_id IN ({project_ids_str})
            GROUP BY day_num
            ORDER BY day_num
        ''').fetchall()
        
        analytics_data['day_of_week_analysis'] = [
            {
                'day': row['day_name'],
                'engagement': round(row['avg_engagement'], 2),
                'score': round(row['avg_score'], 1),
                'count': row['post_count']
            }
            for row in day_of_week_data
        ]
        
        # Monthly trends
        monthly_data = db.execute(f'''
            SELECT 
                strftime('%Y-%m', post_date) as month,
                AVG(engagement_rate_weighted) as avg_engagement,
                AVG(performance_score) as avg_score,
                COUNT(*) as post_count,
                SUM(followers_gained) as total_followers
            FROM posts 
            WHERE project_id IN ({project_ids_str})
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        ''').fetchall()
        
        analytics_data['monthly_trends'] = [
            {
                'month': row['month'],
                'engagement': round(row['avg_engagement'], 2),
                'score': round(row['avg_score'], 1),
                'count': row['post_count'],
                'followers': row['total_followers']
            }
            for row in reversed(monthly_data)
        ]
        
        # Engagement velocity (posts gaining traction quickly)
        velocity_data = db.execute(f'''
            SELECT 
                id, caption, post_date, post_type,
                engagement_rate_weighted,
                performance_score,
                (engagement_rate_weighted * reach / 1000) as velocity_score
            FROM posts 
            WHERE project_id IN ({project_ids_str})
            AND engagement_rate_weighted > 0
            ORDER BY velocity_score DESC
            LIMIT 10
        ''').fetchall()
        
        analytics_data['engagement_velocity'] = [
            {
                'id': row['id'],
                'caption': row['caption'][:50] + '...' if row['caption'] and len(row['caption']) > 50 else row['caption'],
                'date': row['post_date'],
                'type': row['post_type'],
                'engagement': round(row['engagement_rate_weighted'], 2),
                'score': round(row['performance_score'], 1),
                'velocity': round(row['velocity_score'], 1)
            }
            for row in velocity_data
        ]
        
        # Growth trends analysis
        analytics_data['growth_trends'] = analyze_growth_trends(project_ids_str, db)
        
        # Smart recommendations
        analytics_data['recommendations'] = generate_smart_recommendations(project_ids_str, db)
    
    db.close()
    
    return render_template('reports.html', analytics=analytics_data)

# API endpoints for chart data
@app.route('/api/engagement-data')
def api_engagement_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db = get_db_connection()
    projects = db.execute(
        'SELECT id FROM projects WHERE user_id = ?', 
        (session['user_id'],)
    ).fetchall()
    
    if not projects:
        return jsonify({'dates': [], 'engagement': []})
    
    project_ids = [str(p['id']) for p in projects]
    project_ids_str = ','.join(project_ids)
    
    data = db.execute(f'''
        SELECT post_date, AVG(engagement_rate) as avg_engagement
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        GROUP BY post_date
        ORDER BY post_date
        LIMIT 30
    ''').fetchall()
    
    db.close()
    
    return jsonify({
        'dates': [row['post_date'] for row in data],
        'engagement': [round(row['avg_engagement'], 2) for row in data]
    })

@app.route('/api/reach-data')
def api_reach_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db = get_db_connection()
    projects = db.execute(
        'SELECT id FROM projects WHERE user_id = ?', 
        (session['user_id'],)
    ).fetchall()
    
    if not projects:
        return jsonify({'dates': [], 'reach': []})
    
    project_ids = [str(p['id']) for p in projects]
    project_ids_str = ','.join(project_ids)
    
    data = db.execute(f'''
        SELECT post_date, SUM(reach) as total_reach
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        GROUP BY post_date
        ORDER BY post_date
        LIMIT 30
    ''').fetchall()
    
    db.close()
    
    return jsonify({
        'dates': [row['post_date'] for row in data],
        'reach': [row['total_reach'] for row in data]
    })

@app.route('/export/csv')
def export_csv():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user's posts
    db = get_db_connection()
    projects = db.execute(
        'SELECT id FROM projects WHERE user_id = ?', 
        (session['user_id'],)
    ).fetchall()
    
    if not projects:
        flash('No posts to export')
        return redirect(url_for('posts'))
    
    project_ids = [str(p['id']) for p in projects]
    project_ids_str = ','.join(project_ids)
    
    posts_data = db.execute(f'''
        SELECT 
            post_type, post_date, post_time, caption, caption_category,
            likes, comments, shares, saves, reach, followers_gained,
            reel_length, watch_time, avg_view_duration,
            engagement_rate, engagement_rate_weighted, avd_ratio,
            follower_gain_rate, performance_score, dominant_color
        FROM posts 
        WHERE project_id IN ({project_ids_str})
        ORDER BY post_date DESC
    ''').fetchall()
    
    db.close()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Post Type', 'Date', 'Time', 'Caption', 'Category',
        'Likes', 'Comments', 'Shares', 'Saves', 'Reach', 'Followers Gained',
        'Reel Length (s)', 'Watch Time (s)', 'Avg View Duration (s)',
        'Engagement Rate (%)', 'Weighted Engagement (%)', 'AVD Ratio (%)',
        'Follower Gain Rate (%)', 'Performance Score', 'Dominant Color'
    ])
    
    # Write data
    for post in posts_data:
        writer.writerow([
            post['post_type'], post['post_date'], post['post_time'],
            post['caption'][:100] + '...' if post['caption'] and len(post['caption']) > 100 else post['caption'],
            post['caption_category'], post['likes'], post['comments'],
            post['shares'], post['saves'], post['reach'], post['followers_gained'],
            post['reel_length'] or '', post['watch_time'] or '', post['avg_view_duration'] or '',
            post['engagement_rate'], post['engagement_rate_weighted'], post['avd_ratio'],
            post['follower_gain_rate'], post['performance_score'], post['dominant_color']
        ])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=instagram_posts_{session["username"]}_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return response

# Project Management Routes
@app.route('/projects')
def projects():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    user_projects = db.execute(
        'SELECT p.*, COUNT(posts.id) as post_count FROM projects p '
        'LEFT JOIN posts ON p.id = posts.project_id '
        'WHERE p.user_id = ? '
        'GROUP BY p.id ORDER BY p.project_name',
        (session['user_id'],)
    ).fetchall()
    db.close()
    
    return render_template('projects.html', projects=user_projects)

@app.route('/projects/add', methods=['GET', 'POST'])
def add_project():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        project_name = request.form['project_name'].strip()
        description = request.form.get('description', '').strip()
        
        if not project_name:
            flash('Project name is required')
            return render_template('add_project.html')
        
        db = get_db_connection()
        
        # Check if project name already exists for this user
        existing = db.execute(
            'SELECT id FROM projects WHERE user_id = ? AND project_name = ?',
            (session['user_id'], project_name)
        ).fetchone()
        
        if existing:
            flash('Project name already exists')
            db.close()
            return render_template('add_project.html')
        
        # Create new project
        db.execute(
            'INSERT INTO projects (user_id, project_name, description) VALUES (?, ?, ?)',
            (session['user_id'], project_name, description)
        )
        db.commit()
        db.close()
        
        flash('Project created successfully!')
        return redirect(url_for('projects'))
    
    return render_template('add_project.html')

@app.route('/projects/<int:project_id>/posts')
def project_posts(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Verify user owns this project
    db = get_db_connection()
    project = db.execute(
        'SELECT * FROM projects WHERE id = ? AND user_id = ?',
        (project_id, session['user_id'])
    ).fetchone()
    
    if not project:
        flash('Project not found')
        return redirect(url_for('projects'))
    
    # Get posts for this project
    posts_data = db.execute(
        'SELECT * FROM posts WHERE project_id = ? ORDER BY post_date DESC',
        (project_id,)
    ).fetchall()
    
    db.close()
    
    return render_template('project_posts.html', project=project, posts=posts_data)

# Comments System Routes
@app.route('/posts/<int:post_id>/comments', methods=['GET', 'POST'])
def post_comments(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    
    # Verify post exists and user has access (through their projects)
    post = db.execute('''
        SELECT p.*, pr.project_name 
        FROM posts p 
        JOIN projects pr ON p.project_id = pr.id 
        WHERE p.id = ? AND (pr.user_id = ? OR pr.id IN (
            SELECT project_id FROM posts WHERE project_id IN (
                SELECT id FROM projects WHERE user_id = ?
            )
        ))
    ''', (post_id, session['user_id'], session['user_id'])).fetchone()
    
    if not post:
        flash('Post not found')
        return redirect(url_for('posts'))
    
    if request.method == 'POST':
        comment_text = request.form.get('comment_text', '').strip()
        if comment_text:
            db.execute(
                'INSERT INTO post_comments (post_id, user_id, comment_text, created_at) VALUES (?, ?, ?, ?)',
                (post_id, session['user_id'], comment_text, datetime.now().isoformat())
            )
            db.commit()
            flash('Comment added successfully!')
        else:
            flash('Comment cannot be empty')
    
    # Get all comments for this post
    comments = db.execute('''
        SELECT pc.*, u.username 
        FROM post_comments pc 
        JOIN users u ON pc.user_id = u.id 
        WHERE pc.post_id = ? 
        ORDER BY pc.created_at DESC
    ''', (post_id,)).fetchall()
    
    db.close()
    
    return render_template('post_comments.html', post=post, comments=comments)

@app.route('/api/posts/<int:post_id>/comments')
def api_post_comments(post_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db = get_db_connection()
    comments = db.execute('''
        SELECT pc.comment_text, pc.created_at, u.username 
        FROM post_comments pc 
        JOIN users u ON pc.user_id = u.id 
        WHERE pc.post_id = ? 
        ORDER BY pc.created_at DESC
        LIMIT 10
    ''', (post_id,)).fetchall()
    
    db.close()
    
    return jsonify([{
        'text': comment['comment_text'],
        'author': comment['username'],
        'created_at': comment['created_at']
    } for comment in comments])

@app.route('/api/predict-performance')
def api_predict_performance():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get prediction parameters
    post_type = request.args.get('type', 'Reel')
    post_hour = int(request.args.get('hour', 12))
    caption_category = request.args.get('category', 'Educational')
    
    db = get_db_connection()
    projects = db.execute(
        'SELECT id FROM projects WHERE user_id = ?', 
        (session['user_id'],)
    ).fetchall()
    
    if not projects:
        return jsonify({'error': 'No projects found'}), 404
    
    project_ids = [str(p['id']) for p in projects]
    project_ids_str = ','.join(project_ids)
    
    prediction = predict_post_performance(post_type, post_hour, caption_category, project_ids_str, db)
    db.close()
    
    return jsonify(prediction)

# Delete Routes
@app.route('/posts/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    db = get_db_connection()
    
    # Verify user owns this post (through project ownership)
    post = db.execute('''
        SELECT p.*, pr.user_id 
        FROM posts p 
        JOIN projects pr ON p.project_id = pr.id 
        WHERE p.id = ? AND pr.user_id = ?
    ''', (post_id, session['user_id'])).fetchone()
    
    if not post:
        db.close()
        return jsonify({'success': False, 'error': 'Post not found or unauthorized'}), 404
    
    try:
        # Delete related comments first
        db.execute('DELETE FROM post_comments WHERE post_id = ?', (post_id,))
        
        # Delete hashtags related to this post
        db.execute('DELETE FROM hashtags WHERE post_id = ?', (post_id,))
        
        # Delete the post
        db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        
        db.commit()
        db.close()
        
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/posts/delete-multiple', methods=['POST'])
def delete_multiple_posts():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    data = request.json
    post_ids = data.get('post_ids', [])
    
    if not post_ids:
        return jsonify({'success': False, 'error': 'No posts selected'}), 400
    
    db = get_db_connection()
    
    try:
        # Verify user owns all these posts
        placeholders = ','.join('?' * len(post_ids))
        owned_posts = db.execute(f'''
            SELECT p.id 
            FROM posts p 
            JOIN projects pr ON p.project_id = pr.id 
            WHERE p.id IN ({placeholders}) AND pr.user_id = ?
        ''', post_ids + [session['user_id']]).fetchall()
        
        owned_post_ids = [post['id'] for post in owned_posts]
        
        if len(owned_post_ids) != len(post_ids):
            db.close()
            return jsonify({'success': False, 'error': 'Some posts not found or unauthorized'}), 404
        
        # Delete related data for all posts
        for post_id in owned_post_ids:
            db.execute('DELETE FROM post_comments WHERE post_id = ?', (post_id,))
            db.execute('DELETE FROM hashtags WHERE post_id = ?', (post_id,))
            db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        
        db.commit()
        db.close()
        
        return jsonify({'success': True, 'deleted_count': len(owned_post_ids)})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/projects/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    db = get_db_connection()
    
    # Verify user owns this project
    project = db.execute(
        'SELECT * FROM projects WHERE id = ? AND user_id = ?',
        (project_id, session['user_id'])
    ).fetchone()
    
    if not project:
        db.close()
        return jsonify({'success': False, 'error': 'Project not found or unauthorized'}), 404
    
    try:
        # Get all posts in this project
        posts = db.execute('SELECT id FROM posts WHERE project_id = ?', (project_id,)).fetchall()
        
        # Delete all related data
        for post in posts:
            post_id = post['id']
            db.execute('DELETE FROM post_comments WHERE post_id = ?', (post_id,))
            db.execute('DELETE FROM hashtags WHERE post_id = ?', (post_id,))
        
        # Delete all posts in the project
        db.execute('DELETE FROM posts WHERE project_id = ?', (project_id,))
        
        # Delete the project
        db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        
        db.commit()
        db.close()
        
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 500

# Report Generation Routes
@app.route('/projects/<int:project_id>/report')
def generate_project_report(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    
    # Verify user owns this project
    project = db.execute(
        'SELECT * FROM projects WHERE id = ? AND user_id = ?',
        (project_id, session['user_id'])
    ).fetchone()
    
    if not project:
        flash('Project not found')
        return redirect(url_for('projects'))
    
    # Get project posts
    posts = db.execute(
        'SELECT * FROM posts WHERE project_id = ? ORDER BY post_date DESC',
        (project_id,)
    ).fetchall()
    
    if not posts:
        flash('No posts in this project to generate report')
        return redirect(url_for('project_posts', project_id=project_id))
    
    # Calculate metrics for the project
    metrics = calculate_metrics(posts)
    analytics = {
        'engagement_over_time': metrics.get('engagement_over_time', []),
        'reach_over_time': metrics.get('reach_over_time', []),
        'performance_distribution': metrics.get('performance_distribution', []),
        'posting_time_analysis': metrics.get('posting_time_analysis', []),
        'caption_category_performance': metrics.get('caption_category_performance', []),
        'hashtag_performance': metrics.get('hashtag_performance', []),
        'content_insights': metrics.get('content_insights', []),
        'day_of_week_analysis': metrics.get('day_of_week_analysis', []),
        'monthly_trends': metrics.get('monthly_trends', []),
        'growth_trends': metrics.get('growth_trends', {}),
        'engagement_velocity': metrics.get('engagement_velocity', []),
        'recommendations': generate_smart_recommendations(posts)
    }
    
    db.close()
    
    return render_template('project_report.html', project=project, posts=posts, analytics=analytics)

if __name__ == '__main__':
    # Try to ensure upload directory exists (skip if read-only filesystem)
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except (OSError, PermissionError):
        print("Warning: Cannot create upload directory (read-only filesystem)")
    
    # Initialize database
    init_db()
    
    # Create default users if they don't exist
    db = get_db_connection()
    
    # Check if users exist
    existing_users = db.execute('SELECT COUNT(*) as count FROM users').fetchone()
    
    if existing_users['count'] == 0:
        # Create two default users
        user1_hash = generate_password_hash('password123')
        user2_hash = generate_password_hash('password456')
        
        db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', ('user1', user1_hash))
        db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', ('user2', user2_hash))
        db.commit()
        
        print("Created default users:")
        print("Username: user1, Password: password123")
        print("Username: user2, Password: password456")
    
    db.close()
    
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)