import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Fetch the port from the environment variable or default to 5000 for local development
    port = int(os.environ.get("PORT", 5000))
    # Run the app on 0.0.0.0 and the specified port
    app.run(host="0.0.0.0", port=port, debug=False)