from openenv.core.env_server import create_web_interface_app
from server.env_logic import CodeReviewEnvironment
from models import CodeReviewAction, CodeReviewObservation
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "openenv.yaml")

app = create_web_interface_app(
    env_class=CodeReviewEnvironment, 
    action_model=CodeReviewAction, 
    observation_model=CodeReviewObservation,
    config_path=CONFIG_PATH 
)

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
