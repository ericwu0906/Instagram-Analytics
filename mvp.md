# Instagram Growth Analysis App – MVP Plan

## 1. Goal
Build a private, web-based analytics tool for two users to manually input Instagram post data, store it locally, and generate actionable performance insights without using the Instagram API.

---

## 2. Core Features (Phase 1 MVP)
- **Login System**: Two hardcoded user accounts with secure passwords.
- **Post Entry Form**:
  - Upload thumbnail (stored in local folder)
  - Enter caption
  - Select post type (Reel, Story, Carousel, Single Post, etc.)
  - Enter posting date & time
  - Enter reel length (seconds)
  - Enter metrics: Likes, Shares, Comments, Reach, Saves, Followers gained, Watch time, Average view duration
- **Data Storage**: SQLite database in shared folder so both accounts have access.
- **Post Listing**: Table view of all posts with sorting by engagement rate, reach, performance score.
- **Reports**:
  - Engagement rate chart over time
  - Reach over time
  - Written summary of top posts, best posting time, best content type

---

## 3. Additional Phase 1 Insights
- **Best Posting Time** detection
- **Best Caption Category** analysis (manual tagging on input)
- **Best Thumbnail Style** detection (manual dominant color tagging)
- **Predicted Performance Score** for new posts using manual formulas
- **Export** to CSV & PDF

---

## 4. Local Storage Setup
- Use **SQLite** for database (file stored in `data/ig_data.db`)
- Thumbnails stored in `uploads/thumbnails/`
- Ensure both user accounts point to same local directory

---

## 5. Tech Stack Recommendation
- **Backend**: Flask (Python) or Node.js + Express
- **Database**: SQLite
- **Frontend**: HTML/CSS/JavaScript + Bootstrap or Tailwind
- **Charts**: Chart.js for visualizations
- **Export**: jsPDF for PDF, native CSV export

---

## 6. User Flow
1. **Login** → User selects account
2. **Add Post** → Fill form, upload thumbnail, save
3. **View Dashboard** → See latest performance scores and trends
4. **View Reports** → Monthly breakdown, actionable advice
5. **Export Data** → CSV/PDF for offline review

---

## 7. Success Criteria for MVP
- Data persists for both accounts after logout/login
- Engagement rate and performance score calculations run correctly
- Reports provide at least three actionable recommendations
- Average time to input one post ≤ 2 minutes