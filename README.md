# Instagram Growth Analysis App

A private web-based analytics tool for two users to manually input Instagram post data, store it locally, and generate actionable performance insights without using the Instagram API.

## Features

### Core Functionality ✅
- **User Authentication**: Two secure user accounts with session management
- **Post Management**: Manual entry for all Instagram post types (Reel, Story, Carousel, Single)
- **Metric Calculation**: Automatic calculation of engagement rates, performance scores, and analytics
- **File Upload**: Secure thumbnail storage with conflict prevention
- **Data Visualization**: Interactive charts showing engagement, reach, and performance trends
- **Export Options**: CSV export for all post data and metrics

### Analytics Dashboard
- Real-time statistics: total posts, average engagement, reach, new followers
- Sortable posts table with thumbnails and performance indicators
- Performance score distribution and trends
- Best posting time analysis
- Caption category performance comparison

### Key Metrics Calculated
- **Engagement Rate**: (Likes + Comments + Shares + Saves) / Reach × 100
- **Weighted Engagement**: Prioritizes shares and saves for algorithm optimization
- **Average View Duration Ratio**: For reels, measures content quality
- **Follower Gain Rate**: New followers per post reach
- **Performance Score**: Composite score combining all metrics

## Quick Start

### Requirements
- Python 3.9+
- Flask and dependencies (see requirements.txt)

### Installation
1. Clone or download the project
2. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python app.py
   ```
5. Open browser to `http://localhost:5001`

### Default Users
- **User 1**: username: `user1`, password: `password123`
- **User 2**: username: `user2`, password: `password456`

## Usage

### Adding Posts
1. Navigate to "Add Post" from the dashboard
2. Fill in post details:
   - Post type (Reel, Story, Carousel, Single)
   - Date and time posted
   - Caption and category
   - Metrics: likes, comments, shares, saves, reach, followers gained
   - For reels: length, watch time, average view duration
3. Optionally upload thumbnail image
4. Submit - metrics are automatically calculated

### Viewing Analytics
- **Dashboard**: Overview of key statistics and recent posts
- **Posts**: Sortable table of all posts with performance indicators
- **Reports**: Interactive charts and detailed analytics

### Exporting Data
- Use "Export CSV" button on Posts page
- Downloads complete dataset with all metrics
- Filename includes username and date

## Technical Details

### Database Schema
- **SQLite** database stored in `data/ig_data.db`
- 5 tables: users, projects, posts, trends, reports
- All metrics stored as calculated values for performance

### File Structure
```
├── app.py                 # Main Flask application
├── data/
│   └── ig_data.db        # SQLite database
├── uploads/thumbnails/   # User-uploaded images
├── templates/           # HTML templates
├── static/             # CSS, JS, images
└── requirements.txt    # Python dependencies
```

### Security
- Password hashing with Werkzeug
- Session management with Flask-Session
- Secure file uploads with validation
- Local storage only - no external APIs

## Success Criteria ✅

All MVP requirements met:
- ✅ Data persists for both accounts after logout/login
- ✅ Performance score calculations accurate for all posts
- ✅ Reports provide actionable recommendations (best time, category, performance)
- ✅ Post entry time ≤ 2 minutes
- ✅ Both users can access shared database
- ✅ Export functions work correctly

## Future Enhancements

- PDF report generation
- AI-powered caption and thumbnail analysis
- Hashtag optimization suggestions
- Competitor tracking
- Cross-platform support (YouTube Shorts, TikTok)

## Support

For issues or questions, refer to the TODO.md file for development status and planned features.