from flask import Flask
import config
from database import init_db, close_connection
from api.routes import api

# Create Flask app
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

app.secret_key = config.SECRET_KEY
app.teardown_appcontext(close_connection)

# Register Blueprint
app.register_blueprint(api)

# Initialize database
init_db(app)

# Run app
if __name__ == '__main__':
    print(f"🚀 Police Portal running at http://{config.HOST}:{config.PORT}")
    print(f"📝 Default Login: admin / admin123")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)