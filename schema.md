# SQLite Schema – Instagram Growth Analysis App

## Tables

### 1. users
Stores account login info for the two users.
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
```

### 2. projects
Represents each Instagram account/project being tracked.
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_name TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 3. posts
Stores the performance data for each Instagram post.
```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    post_type TEXT NOT NULL, -- Reel, Story, Carousel, Single
    post_date TEXT NOT NULL,
    post_time TEXT NOT NULL,
    reel_length INTEGER, -- seconds
    thumbnail_path TEXT, -- local file path
    caption TEXT,
    caption_category TEXT, -- manually tagged niche category
    likes INTEGER,
    shares INTEGER,
    comments INTEGER,
    reach INTEGER,
    saves INTEGER,
    followers_gained INTEGER,
    watch_time INTEGER, -- total seconds
    avg_view_duration REAL, -- seconds
    engagement_rate REAL,
    engagement_rate_weighted REAL,
    avd_ratio REAL,
    follower_gain_rate REAL,
    performance_score REAL,
    dominant_color TEXT, -- manual or auto-detected
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

### 4. trends
Stores aggregated trends for quick reference.
```sql
CREATE TABLE trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    trend_type TEXT NOT NULL, -- posting_time, caption_category, thumbnail_color
    trend_value TEXT NOT NULL,
    avg_performance_score REAL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

### 5. reports
Stores generated written reports for each project.
```sql
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    report_date TEXT NOT NULL,
    report_text TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```