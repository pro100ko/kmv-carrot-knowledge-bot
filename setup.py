from setuptools import setup, find_packages

setup(
    name="kmv-carrot-knowledge-bot",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "aiogram==3.20.0",
        "aiohttp==3.11.0",
        "python-dotenv==1.0.0",
        "pillow==10.0.1",
        "aiosqlite==0.19.0",
        "pytz==2024.1",
        "python-magic==0.4.27",
        "requests==2.31.0",
        "gunicorn==21.2.0",
        "uvicorn==0.27.1",
        "python-multipart==0.0.9",
        "aiofiles==23.2.1",
        "bcrypt==4.1.2",
        "psutil==5.9.8",
    ],
    python_requires=">=3.11",
) 