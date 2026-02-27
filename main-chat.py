from synthchat.app import create_standalone_app

if __name__ == "__main__":
    app = create_standalone_app()
    app.run(host="0.0.0.0", port=3000, debug=False)
