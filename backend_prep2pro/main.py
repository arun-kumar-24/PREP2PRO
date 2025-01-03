from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=False)  # Set debug=False in production
