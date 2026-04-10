from flask import Flask
from flask_cors import CORS

from .config import Config
from .database import Database
from .routes import build_blueprint


def create_app() -> Flask:
	app = Flask(__name__)
	app.config.from_object(Config)
	CORS(app)

	db = Database(app.config["DATABASE_PATH"])
	app.register_blueprint(build_blueprint(db))

	@app.get("/health")
	def health_check():
		return {"status": "ok"}

	return app


if __name__ == "__main__":
	flask_app = create_app()
	flask_app.run(host=Config.API_HOST, port=Config.API_PORT, debug=Config.DEBUG)
