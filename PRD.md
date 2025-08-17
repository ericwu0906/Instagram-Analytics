# Product Requirements Document – Instagram Growth Analysis App

## 1. Problem Statement
Instagram creators struggle to understand which factors drive content performance. While Instagram Insights provides basic metrics, it lacks deep analysis, trend detection, and personalized recommendations — especially without API access.

Our solution: A private web-based app for two users to manually input Instagram post data, store it locally, and generate actionable insights through rule-based analysis and lightweight AI-style logic.

---

## 2. Goals & Objectives
- Centralized analytics dashboard for all Instagram content types.
- Manual data entry with image and caption analysis.
- Identify trends and provide improvement suggestions.
- Predict future post performance without Instagram API.
- Allow multiple projects/accounts per user.

---

## 3. Target Users
**Primary:** Two specific content creators (internal use only).
- Post reels, stories, carousels, and single-image posts.
- Want deep, niche-specific insights from historical performance.

---

## 4. Features

### 4.1 Data Input
- Manual entry for:
  - Thumbnail upload (image stored locally)
  - Caption
  - Post type (Reel, Story, Carousel, Single)
  - Posting date & time
  - Reel length (seconds)
  - Metrics: Likes, Shares, Comments, Reach, Saves, Followers gained, Watch time, Average view duration
- Manual tagging:
  - Caption category (niche-specific content type)
  - Dominant color in thumbnail (optional)

---

### 4.2 Data Analysis (Rule-Based MVP)
- Engagement Rate (weighted and unweighted)
- Average View Duration Ratio
- Follower Gain Rate
- Composite Performance Score
- Best posting time (hour-based)
- Best caption category
- Best thumbnail style (color-based)
- Historical performance trends
- Written monthly report

---

### 4.3 Output & Visualization
- Dashboard view with sortable post table
- Graphs & charts:
  - Engagement rate over time
  - Reach over time
  - Performance score distribution
- Export options:
  - CSV (raw data)
  - PDF (reports)
- Monthly written summaries with actionable recommendations

---

## 5. Technical Requirements
- **Platform:** Web-based, local hosting
- **Storage:** SQLite database (`data/ig_data.db`) in shared folder for both accounts
- **Frontend:** HTML/CSS/JavaScript (Bootstrap or Tailwind)
- **Backend:** Flask (Python) or Node.js + Express
- **Charts:** Chart.js
- **Exports:** jsPDF for PDF, CSV export via native JS
- **Image Processing:** Basic dominant color detection using local JS library

---

## 6. Security & Privacy
- Two user accounts with hashed passwords
- Local storage — no external API or cloud storage
- Private access — not publicly hosted
- All thumbnails stored in `/uploads/thumbnails/` and linked in database

---

## 7. Success Metrics
- Persistent data for both accounts after logout
- Performance score calculation accurate for all posts
- At least 3 actionable recommendations in each report
- Post entry time ≤ 2 minutes

---

## 8. Risks & Constraints
- Manual data entry required (no API)
- Predictions based only on internal data
- Image analysis limited to basic color detection

---

## 9. Future Enhancements
- AI-powered caption and thumbnail analysis
- Hashtag optimization suggestions
- Competitor tracking
- Cross-platform support (YouTube Shorts, TikTok)

---

## 10. Deliverables
- Local web app
- SQLite database with schema as per `schema.md`
- Report generation feature
- Export capabilities