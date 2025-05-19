from app import app, initialize

# Инициализация планировщика при старте через Gunicorn
initialize()

if __name__ == "__main__":
    app.run()
