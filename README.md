# Knowledge Bot

A Telegram bot for managing and testing knowledge about products and categories. Built with Python and aiogram, designed to run efficiently on Render's free tier.

## Features

- User Management
  - Registration and authentication
  - Role-based access control (admin/user)
  - Session management
  - Activity tracking

- Test Management
  - Create and edit tests
  - Multiple question types
  - Time limits and scoring
  - Test results tracking

- Knowledge Base
  - Category management
  - Product management
  - Search functionality
  - Product viewing

- Admin Panel
  - User management
  - Test management
  - Category and product management
  - Statistics and monitoring

## Technical Features

- Efficient resource management
  - Connection pooling for database operations
  - Memory usage monitoring and limits
  - Rate limiting for API requests
  - Automatic cleanup of old data

- Robust error handling
  - Comprehensive logging
  - Graceful error recovery
  - Transaction management
  - Backup and restore capabilities

- Monitoring and maintenance
  - System health monitoring
  - Performance metrics collection
  - Database backup and migration
  - Resource usage tracking

## Project Structure

```
.
├── alembic/              # Database migrations
├── backups/             # Database backups
├── data/               # Data files
├── handlers/           # Bot command handlers
│   ├── admin.py       # Admin commands
│   ├── user.py        # User commands
│   └── knowledge.py   # Knowledge base commands
├── migrations/         # Migration files
├── monitoring/         # Monitoring tools
├── scripts/           # Utility scripts
├── tests/             # Test files
├── utils/             # Utility modules
│   ├── db_pool.py     # Database connection pool
│   ├── keyboards.py   # Keyboard layouts
│   ├── message_utils.py # Message handling
│   └── resource_manager.py # Resource management
├── config.py          # Configuration
├── dispatcher.py      # Bot dispatcher
├── logging_config.py  # Logging setup
├── main.py           # Application entry point
├── middleware.py     # Middleware components
├── sqlite_db.py      # Database operations
└── requirements.txt   # Dependencies
```

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/knowledge-bot.git
cd knowledge-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```env
# Bot settings
BOT_TOKEN=your_bot_token
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=8000
WEBHOOK_URL=https://your-domain.com/webhook
ENABLE_WEBHOOK=true

# Admin settings
ADMIN_IDS=123456789,987654321
ENABLE_ADMIN_PANEL=true

# Database settings
DB_FILE=knowledge_bot.db
DB_BACKUP_DIR=backups
DB_MIGRATIONS_DIR=migrations
DB_POOL_SIZE=5

# Resource limits
MAX_MEMORY_USAGE_MB=512
MAX_CPU_USAGE_PERCENT=80
RATE_LIMIT_MESSAGES=20
RATE_LIMIT_CALLBACKS=30
RATE_LIMIT_WINDOW=60

# Monitoring
ENABLE_METRICS=true
METRICS_DIR=metrics
METRICS_RETENTION_DAYS=7
```

5. Initialize the database:
```bash
python scripts/migrate_db.py
```

6. Run the bot:
```bash
python main.py
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Database Migrations
To create a new migration:
1. Create a new JSON file in `migrations/` with a sequential number
2. Add your SQL queries to the file
3. Run migrations:
```bash
python scripts/migrate_db.py
```

### Database Backups
To create a backup:
```bash
python scripts/backup_db.py
```

### System Monitoring
To monitor system health:
```bash
python scripts/monitor_system.py
```

## Deployment

The bot is designed to run on Render's free tier. Follow these steps to deploy:

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
   - Environment Variables: Add all variables from your `.env` file

## Resource Management

The bot is optimized for Render's free tier limitations:
- Memory limit: 512MB
- CPU: Shared
- Storage: 1GB
- Bandwidth: Limited

To ensure efficient operation:
- Database connections are pooled
- Memory usage is monitored
- Rate limiting is enforced
- Old data is automatically cleaned up
- Backups are compressed

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# Corporate Knowledge Base

A modern, responsive corporate knowledge base website designed for employees to easily find product information and documentation.

## Features

- **Modern Design**: Clean, professional interface with gradient backgrounds and smooth animations
- **Responsive Layout**: Works perfectly on desktop, tablet, and mobile devices
- **Product Categories**: Organized product categories with visual icons and descriptions
- **Product Cards**: Detailed product information with features, versions, and action buttons
- **Anchor Navigation**: Quick navigation buttons at the top of product pages
- **Search Functionality**: Built-in search capability (can be extended with backend integration)
- **Smooth Animations**: CSS transitions and JavaScript animations for better user experience

## Structure

```
├── index.html              # Main homepage with category buttons
├── styles.css              # Main stylesheet with responsive design
├── script.js               # JavaScript for interactivity
└── products/               # Product category pages
    ├── software.html       # Software products page (example)
    ├── hardware.html       # Hardware products page (to be created)
    ├── services.html       # Services page (to be created)
    ├── cloud.html          # Cloud solutions page (to be created)
    ├── security.html       # Security products page (to be created)
    └── analytics.html      # Analytics products page (to be created)
```

## GitHub Pages Setup

### Option 1: Automatic Setup (Recommended)

1. **Push to GitHub**: Push this repository to your GitHub account
2. **Enable GitHub Pages**:
   - Go to your repository on GitHub
   - Click on "Settings" tab
   - Scroll down to "Pages" section
   - Under "Source", select "Deploy from a branch"
   - Choose "main" branch and "/ (root)" folder
   - Click "Save"

3. **Access Your Site**: Your knowledge base will be available at:
   `https://yourusername.github.io/your-repo-name/`

### Option 2: Manual Setup

1. **Create a new repository** on GitHub
2. **Clone the repository** to your local machine
3. **Copy all files** from this project to the repository
4. **Commit and push** the changes
5. **Follow the automatic setup steps** above

## Customization

### Adding New Product Categories

1. Create a new HTML file in the `products/` directory (e.g., `hardware.html`)
2. Copy the structure from `software.html`
3. Update the product cards with your specific products
4. Add the category link to `index.html`

### Modifying Styles

- Edit `styles.css` to change colors, fonts, and layout
- The design uses CSS custom properties for easy theming
- All components are responsive and mobile-friendly

### Adding Search Functionality

The current search shows an alert. To implement real search:

1. **Client-side search**: Add JavaScript to filter product cards
2. **Backend search**: Integrate with a search API or database
3. **External search**: Use services like Algolia or Elasticsearch

## Browser Support

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Performance

- Optimized images and icons using Font Awesome CDN
- Minified CSS and JavaScript (recommended for production)
- Lazy loading for better performance
- Responsive images and efficient CSS Grid layouts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on different devices and browsers
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or support:
- Create an issue in the GitHub repository
- Contact your IT department for internal support
- Check the documentation in the knowledge base itself

---

**Note**: This is a static website template. For dynamic features like user authentication, real-time search, or content management, you'll need to integrate with a backend service or CMS.
