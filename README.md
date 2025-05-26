# KMV Carrot Knowledge Bot

Telegram bot for corporate training in a company selling fruits, vegetables, berries, nuts, and dried fruits. The bot serves as a knowledge base and testing platform for employees.

## Features

- User authentication (administrators and regular users)
- Knowledge base with product cards
- Employee testing system
- Search functionality for product cards
- Administrative panel for managing content and tests

## Technical Stack

- Python 3.11+
- aiogram 3.20.0 (Telegram Bot Framework)
- SQLite (Database)
- aiohttp (Web Framework)
- Gunicorn (WSGI Server)

## Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/kmv-carrot-knowledge-bot.git
cd kmv-carrot-knowledge-bot
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

4. Create a `.env` file with the following variables:
```env
BOT_TOKEN=your_telegram_bot_token
WEBHOOK_URL=your_webhook_url  # Only needed for production
WEBHOOK_PATH=/webhook
ENVIRONMENT=development
ADMIN_USER_IDS=123456789,987654321  # Comma-separated list of admin Telegram IDs
```

5. Run the bot in development mode:
```bash
python main.py
```

## Deployment on Render

1. Fork this repository to your GitHub account

2. Create a new Web Service on Render:
   - Connect your GitHub repository
   - Select "Python" as the environment
   - The build command and start command are already configured in `render.yaml`

3. Configure the following environment variables in Render:
   - `BOT_TOKEN`: Your Telegram bot token
   - `WEBHOOK_URL`: Your Render service URL (e.g., https://your-app.onrender.com)
   - `ADMIN_USER_IDS`: Comma-separated list of admin Telegram IDs

4. Deploy the service

## Project Structure

```
.
├── main.py              # Main bot application
├── config.py            # Configuration settings
├── sqlite_db.py         # Database operations
├── dispatcher.py        # Bot dispatcher setup
├── handlers/            # Bot command handlers
│   ├── admin.py         # Admin panel handlers
│   ├── knowledge_base.py # Knowledge base handlers
│   ├── testing.py       # Testing system handlers
│   └── user_management.py # User management handlers
├── utils/              # Utility functions
├── requirements.txt    # Python dependencies
└── render.yaml        # Render deployment configuration
```

## Database Schema

The bot uses SQLite with the following main tables:
- `users`: User information and authentication
- `categories`: Product categories
- `products`: Product information
- `product_images`: Product images
- `tests`: Test definitions
- `questions`: Test questions
- `options`: Question options
- `test_attempts`: User test attempts
- `user_answers`: User test answers

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
